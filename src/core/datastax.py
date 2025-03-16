import os
from typing import Dict, List, Optional, Any
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import SimpleStatement
import logging
from uuid import UUID
import asyncio
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DataStax Astra DB configuration
ASTRA_DB_ID = os.getenv("ASTRA_DB_ID")
ASTRA_DB_REGION = os.getenv("ASTRA_DB_REGION", "us-east1")
ASTRA_DB_KEYSPACE = os.getenv("ASTRA_DB_KEYSPACE", "oishii")
ASTRA_DB_USERNAME = os.getenv("ASTRA_DB_USERNAME")
ASTRA_DB_PASSWORD = os.getenv("ASTRA_DB_PASSWORD")
ASTRA_DB_SECURE_BUNDLE_PATH = os.getenv("ASTRA_DB_SECURE_BUNDLE_PATH")

# Check if we're using Astra DB or a local Cassandra instance
USE_ASTRA = all([ASTRA_DB_ID, ASTRA_DB_USERNAME, ASTRA_DB_PASSWORD])

# Check if we're only using DataStax for LLM functionality
USE_DATASTAX_LLM_ONLY = os.getenv("USE_DATASTAX_LLM_ONLY", "False").lower() == "true"

# Global cluster connection
_cluster = None
_session = None


def get_cluster():
    """Get or create the Cassandra cluster connection"""
    global _cluster
    
    if USE_DATASTAX_LLM_ONLY:
        logger.info("Skipping Cassandra cluster connection (LLM-only mode)")
        return None
    
    if _cluster is None:
        if USE_ASTRA:
            # Connect to Astra DB
            if ASTRA_DB_SECURE_BUNDLE_PATH:
                # Connect using secure connect bundle
                auth_provider = PlainTextAuthProvider(
                    username=ASTRA_DB_USERNAME,
                    password=ASTRA_DB_PASSWORD
                )
                _cluster = Cluster(
                    cloud={
                        'secure_connect_bundle': ASTRA_DB_SECURE_BUNDLE_PATH
                    },
                    auth_provider=auth_provider
                )
                logger.info("Connected to Astra DB using secure connect bundle")
            else:
                # Connect using Astra DB ID and region
                auth_provider = PlainTextAuthProvider(
                    username=ASTRA_DB_USERNAME,
                    password=ASTRA_DB_PASSWORD
                )
                _cluster = Cluster(
                    contact_points=[f'{ASTRA_DB_ID}-{ASTRA_DB_REGION}.db.astra.datastax.com'],
                    port=9042,
                    auth_provider=auth_provider,
                    ssl=True
                )
                logger.info("Connected to Astra DB using ID and region")
        else:
            # Connect to local Cassandra
            _cluster = Cluster(['127.0.0.1'])
            logger.info("Connected to local Cassandra instance")
    
    return _cluster


def get_session():
    """Get or create the Cassandra session"""
    global _session
    
    if USE_DATASTAX_LLM_ONLY:
        logger.info("Skipping Cassandra session creation (LLM-only mode)")
        return None
    
    if _session is None:
        cluster = get_cluster()
        if cluster:
            _session = cluster.connect(ASTRA_DB_KEYSPACE)
            logger.info(f"Connected to keyspace: {ASTRA_DB_KEYSPACE}")
    
    return _session


def run_async(f):
    """Decorator to run synchronous Cassandra operations in an async context"""
    @wraps(f)
    async def wrapper(*args, **kwargs):
        if USE_DATASTAX_LLM_ONLY:
            logger.info(f"Skipping Cassandra operation {f.__name__} (LLM-only mode)")
            return []
        return await asyncio.to_thread(f, *args, **kwargs)
    return wrapper


@run_async
def execute_query(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Execute a CQL query and return the results as a list of dictionaries"""
    session = get_session()
    if not session:
        return []
        
    statement = SimpleStatement(query)
    
    if params:
        rows = session.execute(statement, params)
    else:
        rows = session.execute(statement)
    
    # Convert rows to list of dictionaries
    result = []
    for row in rows:
        row_dict = {}
        for column in row._fields:
            value = getattr(row, column)
            # Convert UUID objects to strings for JSON serialization
            if isinstance(value, UUID):
                value = str(value)
            row_dict[column] = value
        result.append(row_dict)
    
    return result


@run_async
def create_tables():
    """Create the necessary tables for the recommendation system if they don't exist"""
    session = get_session()
    if not session:
        return
        
    # Create user_profiles table
    session.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id uuid PRIMARY KEY,
        taste_preferences set<text>,
        dietary_restrictions set<text>,
        allergies set<text>,
        cuisine_preferences set<text>,
        created_at timestamp,
        updated_at timestamp
    )
    """)
    
    # Create food_items table
    session.execute("""
    CREATE TABLE IF NOT EXISTS food_items (
        food_id uuid PRIMARY KEY,
        name text,
        description text,
        cuisine_type text,
        ingredients set<text>,
        nutritional_info map<text, float>,
        image_url text,
        created_at timestamp,
        updated_at timestamp
    )
    """)
    
    # Create food_by_cuisine table for efficient querying
    session.execute("""
    CREATE TABLE IF NOT EXISTS food_by_cuisine (
        cuisine_type text,
        food_id uuid,
        name text,
        description text,
        ingredients set<text>,
        image_url text,
        PRIMARY KEY (cuisine_type, food_id)
    )
    """)
    
    # Create food_by_ingredient table for ingredient-based matching
    session.execute("""
    CREATE TABLE IF NOT EXISTS food_by_ingredient (
        ingredient text,
        food_id uuid,
        name text,
        cuisine_type text,
        PRIMARY KEY (ingredient, food_id)
    )
    """)
    
    logger.info("Created recommendation system tables")


@run_async
def save_user_profile(
    user_id: UUID,
    taste_preferences: List[str],
    dietary_restrictions: List[str],
    allergies: List[str],
    cuisine_preferences: List[str]
):
    """Save or update a user's food preferences"""
    session = get_session()
    
    query = """
    INSERT INTO user_profiles (
        user_id, taste_preferences, dietary_restrictions, allergies, 
        cuisine_preferences, created_at, updated_at
    )
    VALUES (%s, %s, %s, %s, %s, toTimestamp(now()), toTimestamp(now()))
    """
    
    session.execute(
        query,
        (
            user_id,
            set(taste_preferences),
            set(dietary_restrictions),
            set(allergies),
            set(cuisine_preferences)
        )
    )
    
    return True


@run_async
def get_food_recommendations(search_term: str, user_id: Optional[UUID] = None, limit: int = 10):
    """
    Get food recommendations based on search term and optionally user preferences
    
    This is a simplified implementation. In a production system, you would:
    1. Use more sophisticated matching algorithms
    2. Implement proper text search (possibly with a search engine like Elasticsearch)
    3. Consider user preferences more deeply
    """
    session = get_session()
    
    # Start with a basic search by cuisine type
    cuisine_query = """
    SELECT * FROM food_by_cuisine 
    WHERE cuisine_type = %s 
    LIMIT %s
    """
    
    cuisine_results = session.execute(cuisine_query, (search_term.lower(), limit))
    
    # If we don't have enough results, search by ingredient
    ingredient_query = """
    SELECT * FROM food_by_ingredient 
    WHERE ingredient = %s 
    LIMIT %s
    """
    
    ingredient_results = session.execute(ingredient_query, (search_term.lower(), limit))
    
    # Combine and deduplicate results
    results = []
    food_ids = set()
    
    # Process cuisine results
    for row in cuisine_results:
        if row.food_id not in food_ids:
            food_ids.add(row.food_id)
            results.append({
                "food_id": row.food_id,
                "name": row.name,
                "description": row.description,
                "cuisine_type": row.cuisine_type,
                "ingredients": list(row.ingredients) if row.ingredients else [],
                "match_score": 0.9,  # High match for cuisine type
                "image_url": row.image_url
            })
    
    # Process ingredient results
    for row in ingredient_results:
        if row.food_id not in food_ids and len(results) < limit:
            food_ids.add(row.food_id)
            
            # Get full food details
            food_query = """
            SELECT * FROM food_items WHERE food_id = %s
            """
            food_details = session.execute(food_query, (row.food_id,)).one()
            
            results.append({
                "food_id": row.food_id,
                "name": row.name,
                "description": food_details.description if food_details else None,
                "cuisine_type": row.cuisine_type,
                "ingredients": list(food_details.ingredients) if food_details and food_details.ingredients else [],
                "match_score": 0.7,  # Medium match for ingredient
                "image_url": food_details.image_url if food_details else None
            })
    
    # If we still don't have enough results, do a more general search
    if len(results) < limit:
        # Get additional food items
        general_query = """
        SELECT * FROM food_items LIMIT %s
        """
        general_results = session.execute(general_query, (limit,))
        
        for row in general_results:
            if row.food_id not in food_ids and len(results) < limit:
                food_ids.add(row.food_id)
                
                # Calculate a simple match score based on text similarity
                name_match = search_term.lower() in row.name.lower() if row.name else False
                desc_match = search_term.lower() in row.description.lower() if row.description else False
                
                match_score = 0.5  # Base score
                if name_match:
                    match_score += 0.3
                if desc_match:
                    match_score += 0.2
                
                results.append({
                    "food_id": row.food_id,
                    "name": row.name,
                    "description": row.description,
                    "cuisine_type": row.cuisine_type,
                    "ingredients": list(row.ingredients) if row.ingredients else [],
                    "match_score": match_score,
                    "image_url": row.image_url
                })
    
    # Sort by match score
    results.sort(key=lambda x: x["match_score"], reverse=True)
    
    return {
        "recommendations": results[:limit],
        "total": len(results),
        "search_term": search_term
    }


# Initialize connection and tables on module import
async def initialize_datastax():
    """Initialize DataStax connection and create tables"""
    try:
        if USE_DATASTAX_LLM_ONLY:
            logger.info("DataStax initialization skipped for database (LLM-only mode)")
            return
            
        await create_tables()
        logger.info("DataStax initialization complete")
    except Exception as e:
        logger.error(f"Error initializing DataStax: {e}")
        raise 