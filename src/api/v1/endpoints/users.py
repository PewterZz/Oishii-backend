from fastapi import APIRouter, HTTPException, status, Depends, Path, Query, BackgroundTasks, Request, Response
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from ....schemas.user import UserCreate, UserResponse, UserUpdate, Token, TokenData, VerificationRequest
from ....core.supabase import execute_query, sign_up, sign_in, get_user, get_supabase_client, execute_raw_sql, check_user_exists
import random
import string
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import UUID4, EmailStr
from dotenv import load_dotenv
import httpx
import json
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

router = APIRouter(tags=["users"])

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "30"))

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.example.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@oishii.com")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Update OAuth2PasswordBearer to include description for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/users/login",
    description="Enter the access token directly (without 'Bearer' prefix)",
    scheme_name="JWT"
)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

async def send_verification_email(email: str, code: str):
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = EMAIL_FROM
        message["To"] = email
        message["Subject"] = "Oishii - Verify Your Email"
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>Welcome to Oishii!</h2>
            <p>Thank you for registering. Please verify your email address to continue.</p>
            <p>Your verification code is: <strong>{code}</strong></p>
            <p>This code will expire in 24 hours.</p>
            <p>If you did not request this code, please ignore this email.</p>
        </body>
        </html>
        """
        
        # Attach body to message
        message.attach(MIMEText(body, "html"))
        
        # Connect to SMTP server and send email
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(message)
            
        print(f"Verification email sent to {email}")
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        # Fall back to printing the code for development purposes
        print(f"Verification code for {email}: {code}")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Print token for debugging (first 10 chars)
        token_preview = token[:10] + "..." if len(token) > 10 else token
        print(f"Validating token: {token_preview}")
        
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            print("Token missing 'sub' claim")
            raise credentials_exception
            
        print(f"Token contains user_id: {user_id}")
        
        # Try to get user from Supabase auth first
        try:
            from ....core.supabase import get_supabase_client
            supabase_client = get_supabase_client()
            
            # Try to get user from Supabase auth
            try:
                auth_user = supabase_client.auth.admin.get_user_by_id(user_id)
                print(f"User found in Supabase auth: {auth_user.user.id if auth_user and auth_user.user else 'None'}")
            except Exception as auth_error:
                print(f"Error getting user from Supabase auth: {str(auth_error)}")
                print(f"Error type: {type(auth_error)}")
                # Continue to database check even if Supabase auth check fails
        except Exception as client_error:
            print(f"Error getting Supabase client: {str(client_error)}")
    except JWTError as e:
        print(f"JWT Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    try:
        print(f"Querying database for user with ID: {user_id}")
        user = await execute_query(
            table="users",
            query_type="select",
            filters={"id": user_id}
        )
        
        print(f"Database query result: {user}")
        
        if not user or len(user) == 0:
            print(f"User not found in database with ID: {user_id}")
            
            # Try to check if user exists in auth.users table directly
            try:
                check_query = f"""
                SELECT id FROM auth.users WHERE id = '{user_id}';
                """
                check_result = await execute_raw_sql(check_query)
                print(f"Auth users check result: {check_result}")
                
                if check_result and check_result.get("data") and len(check_result.get("data", [])) > 0:
                    print(f"User exists in auth.users table but not in our database table")
                    # This suggests a sync issue between our database and auth.users
                else:
                    print(f"User not found in auth.users table either")
            except Exception as check_error:
                print(f"Error checking auth.users table: {str(check_error)}")
            
            raise credentials_exception
        
        print(f"User authenticated: {user[0].get('email')}")
        return user[0]
    except Exception as e:
        print(f"Database error in get_current_user: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Error details: {repr(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user: {str(e)}",
        )

# Routes
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user."""
    try:
        # Check if user exists
        existing_user = await execute_query(
            table="users",
            query_type="select",
            filters={"email": user_data.email}
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash the password
        hashed_password = pwd_context.hash(user_data.password)
        
        # Sign up with Supabase
        # Sign up with Supabase with retry logic
        supabase = get_supabase_client()
        max_retries = 3
        auth_response = None
        
        for attempt in range(max_retries):
            try:
                auth_response = supabase.auth.sign_up({
                    "email": user_data.email,
                    "password": user_data.password
                })
                if auth_response and auth_response.user:
                    break
            except Exception as e:
                print(f"Supabase signup attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    raise
                continue
        
        if not auth_response or not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user in Supabase"
            )
            
        # Create user in our database
        user_data_dict = user_data.dict()
        user_data_dict.update({
            "id": auth_response.user.id,
            "email": auth_response.user.email,
            "is_verified": False,
            "password": hashed_password,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
        
        new_user = await execute_query(
            table="users",
            query_type="insert",
            data=user_data_dict
        )
        
        if not new_user:
            try:
                await supabase.auth.admin.delete_user(auth_response.user.id)
            except Exception as cleanup_error:
                print(f"Failed to cleanup Supabase user: {cleanup_error}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user in database"
            )
        
        # Remove sensitive data from response
        user_response = new_user[0]
        if "password" in user_response:
            del user_response["password"]
            
        return user_response
            
    except Exception as e:
        print(f"Registration error: {str(e)}")
        print(f"Error type: {type(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Log in a user and return an access token."""
    try:
        # Authenticate with Supabase
        auth_response = await sign_in(form_data.username, form_data.password)
        
        # Get user from database
        user = await execute_query(
            table="users",
            query_type="select",
            filters={"email": form_data.username}
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        user = user[0]
        
        # Check if user is verified
        if not user.get("is_verified"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email before logging in"
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": user["id"]})
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@router.get("/verify")
async def verify_email(
    token: str = Query(None),
    confirmation_token: str = Query(None),
    email: str = Query(None)
):
    """Verify a user's email address."""
    try:
        # Get the verification token from either parameter
        verification_token = token or confirmation_token
        if not verification_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No verification token provided"
            )
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email parameter is required"
            )
        
        try:
            # Get user from database using email
            user = await execute_query(
                table="users",
                query_type="select",
                filters={"email": email}
            )
            
            if not user or len(user) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            user = user[0]
            user_id = user["id"]
            
            # Update user verification status
            updated_user = await execute_query(
                table="users",
                query_type="update",
                filters={"id": user_id},
                data={"is_verified": True, "updated_at": datetime.now().isoformat()}
            )
            
            if not updated_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update user verification status"
                )
            
            # Return success message with a frontend redirect URL if available
            frontend_url = os.getenv("FRONTEND_URL")
            if frontend_url:
                return {
                    "message": "Email verified successfully",
                    "redirect_url": f"{frontend_url}/login"
                }
            return {"message": "Email verified successfully"}
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid verification token: {str(e)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Verification failed: {str(e)}"
        )

@router.get("/callback")
async def auth_callback(
    token_hash: str = Query(None),
    type: str = Query(None),
    email: str = Query(None),
    next: str = Query(None)
):
    """Handle Supabase auth callback for email verification."""
    try:
        print(f"Auth callback received: token_hash={token_hash}, type={type}, email={email}")
        
        if not token_hash or not type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters"
            )

        # Get Supabase client
        from ....core.supabase import get_supabase_client
        supabase = get_supabase_client()
        
        try:
            # Verify OTP using the token_hash
            verify_response = await supabase.auth.verify_otp({
                "token_hash": token_hash,
                "type": type
            })
            
            if not verify_response or not verify_response.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid verification token"
                )

            user_email = verify_response.user.email
            
            # Update user verification in database
            updated_user = await execute_query(
                table="users",
                query_type="update",
                filters={"email": user_email},
                data={
                    "is_verified": True,
                    "updated_at": datetime.now().isoformat()
                }
            )
            
            if not updated_user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update verification status"
                )

            # Redirect to frontend
            frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
            from fastapi.responses import RedirectResponse
            return RedirectResponse(
                url=f"{frontend_url}/auth/verified?success=true",
                status_code=status.HTTP_302_FOUND
            )
            
        except Exception as e:
            print(f"Verification error: {str(e)}")
            return RedirectResponse(
                url=f"{frontend_url}/auth/error?message=verification_failed",
                status_code=status.HTTP_302_FOUND
            )
            
    except Exception as e:
        print(f"Callback error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )

@router.get("/dev/token", response_model=Token)
async def get_dev_token(
    email: str = Query(None),
    expires_minutes: int = Query(30, ge=1, le=1440)  # Default 30 min, max 24 hours
):
    """
    Generate a temporary access token for testing.
    
    Args:
        email: Email of an existing user to generate token for (optional)
        expires_minutes: Token expiration time in minutes (default: 30, max: 1440)
    
    Returns:
        A temporary access token
    """
    try:
        # If email is provided, find that user
        if email:
            user = await execute_query(
                table="users",
                query_type="select",
                filters={"email": email}
            )
            
            if not user or len(user) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User not found with email: {email}"
                )
            
            user = user[0]
        else:
            # Find any verified user to use
            users = await execute_query(
                table="users",
                query_type="select",
                filters={"is_verified": True},
                limit=1
            )
            
            if not users or len(users) == 0:
                # If no verified users exist, find any user
                users = await execute_query(
                    table="users",
                    query_type="select",
                    limit=1
                )
                
                if not users or len(users) == 0:
                    # Create a dummy user if no users exist
                    hashed_password = pwd_context.hash("dummy-password")
                    
                    # Generate a UUID for the user
                    import uuid
                    user_id = str(uuid.uuid4())
                    
                    # Create dummy user data
                    dummy_user_data = {
                        "id": user_id,
                        "email": "dummy@example.com",
                        "password": hashed_password,
                        "first_name": "Dummy",
                        "last_name": "User",
                        "bio": "This is a dummy user created for development purposes.",
                        "cook_type": "the meal prepper",
                        "cook_frequency": "3-4 times",
                        "dietary_requirements": ["none"],
                        "allergies": "None",
                        "purpose": "try out new dishes",
                        "home_address": "123 Test Street, Test City",
                        "is_verified": True,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    # Insert the dummy user into the database
                    new_user = await execute_query(
                        table="users",
                        query_type="insert",
                        data=dummy_user_data
                    )
                    
                    if not new_user or len(new_user) == 0:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to create dummy user"
                        )
                    
                    user = new_user[0]
                else:
                    user = users[0]
            else:
                user = users[0]
        
        # Create access token with specified expiration
        expires_delta = timedelta(minutes=expires_minutes)
        access_token = create_access_token(
            data={"sub": user["id"]},
            expires_delta=expires_delta
        )
        
        # Log the token generation for audit purposes
        print(f"TOKEN GENERATED for user {user['email']} (ID: {user['id']})")
        print(f"Token expires in {expires_minutes} minutes")
        
        # Return the token
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_minutes * 60,
            "user_id": user["id"],
            "email": user["email"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate token: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get the current user's profile."""
    # Log the headers request
    print(f"Request headers: {dict(request.headers)}")
    print(f"Current user: {current_user}")
    
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    request: Request,  # Remove Depends()
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update the current user's profile."""
    try:
        # Log request headers and body
        print(f"Request headers: {dict(request.headers)}")
        print(f"Request body: {user_update.model_dump()}")
        print(f"Current user: {current_user}")

        # Convert to dict and handle URL serialization
        raw_data = user_update.model_dump(exclude_unset=True)
        update_data = {}
        
        # Process each field to ensure JSON serializable
        for key, value in raw_data.items():
            if hasattr(value, 'url'):
                update_data[key] = str(value)
            elif isinstance(value, (str, int, float, bool, type(None))):
                update_data[key] = value
            elif isinstance(value, list):
                update_data[key] = [str(item) if hasattr(item, 'url') else item for item in value]
            else:
                update_data[key] = str(value)

        update_data["updated_at"] = datetime.now().isoformat()

        # Get Supabase client
        from ....core.supabase import get_supabase_client
        supabase = get_supabase_client()
        
        # Update user
        result = supabase.from_("users")\
            .update(update_data)\
            .eq("id", current_user["id"])\
            .execute()

        if not result or not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile"
            )
            
        return result.data[0]
        
    except Exception as e:
        print(f"Error updating user profile: {str(e)}")
        print(f"Update data: {update_data}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user profile: {str(e)}"
        )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: UUID4):
    """Get a user's public profile by ID."""
    user = await execute_query(
        table="users",
        query_type="select",
        filters={"id": str(user_id)}
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user[0]

@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """Get a list of users."""
    users = await execute_query(
        table="users",
        query_type="select",
        limit=limit
    )
    
    return users[skip:skip + limit]

@router.get("/check-auth")
async def check_auth(current_user: dict = Depends(get_current_user)):
    """
    Check if the current user is authenticated.
    """
    return {"authenticated": True, "user_id": current_user["id"]}

@router.post("/verify-code")
async def verify_code(email: str = Query(...), code: str = Query(...)):
    """Verify a user's email using the verification code."""
    try:
        # Get user from database
        user = await execute_query(
            table="users",
            query_type="select",
            filters={"email": email}
        )
        
        if not user or len(user) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = user[0]
        
        # Check if user is already verified
        if user.get("is_verified"):
            return {"message": "Email already verified"}
        
        # Verify with Supabase
        supabase = get_supabase_client()
        try:
            verify_response = supabase.auth.verify_otp({
                "email": email,
                "token": code,
                "type": "signup"
            })
            
            if not verify_response or not verify_response.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid verification code"
                )
        except Exception as e:
            print(f"Supabase verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
        
        # Update our database
        updated_user = await execute_query(
            table="users",
            query_type="update",
            filters={"id": user["id"]},
            data={
                "is_verified": True,
                "updated_at": datetime.now().isoformat()
            }
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update verification status"
            )
        
        return {"message": "Email verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )

@router.post("/resend-code")
async def resend_verification_code(email: str = Query(...)):
    """Resend verification code to user's email."""
    try:
        # Get user from database
        user = await execute_query(
            table="users",
            query_type="select",
            filters={"email": email}
        )
        
        if not user or len(user) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user = user[0]
        
        # Check if user is already verified
        if user.get("is_verified"):
            return {"message": "Email already verified"}
        
        # Generate new verification code
        new_code = generate_verification_code()
        
        # Update user with new verification code
        updated_user = await execute_query(
            table="users",
            query_type="update",
            filters={"id": user["id"]},
            data={
                "verification_code": new_code,
                "verification_code_expires": (datetime.now() + timedelta(hours=24)).isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update verification code"
            )
        
        # Send new verification email
        await send_verification_email(email, new_code)
        
        return {"message": "Verification code resent successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend verification code: {str(e)}"
        ) 