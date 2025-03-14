from fastapi import APIRouter, HTTPException, status, Depends, Path, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from ....schemas.user import UserCreate, UserResponse, UserUpdate, Token, TokenData, VerificationRequest
from ....core.supabase import execute_query, sign_up, sign_in, get_user
import random
import string
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import UUID4
from dotenv import load_dotenv

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


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = await execute_query(
        table="users",
        query_type="select",
        filters={"id": token_data.user_id}
    )
    
    if not user or len(user) == 0:
        raise credentials_exception
    
    return user[0]

# Routes
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, background_tasks: BackgroundTasks):
    existing_user = await execute_query(
        table="users",
        query_type="select",
        filters={"email": user.email}
    )
    
    if existing_user and len(existing_user) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    valid_domains = ["rmit.edu.au", "student.rmit.edu.au", "unimelb.edu.au", "student.unimelb.edu.au", "monash.edu", "student.monash.edu"]
    if not any(user.email.endswith(domain) for domain in valid_domains):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please use a valid Australian university email (RMIT, UniMelb, or Monash)"
        )
    
    code = generate_verification_code()
    
    user_data = user.model_dump(exclude={"password"})
    new_user = await sign_up(user.email, user.password, user_data)
    
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    expires_at = datetime.now() + timedelta(hours=24)
    verification_data = {
        "user_id": new_user["id"],
        "email": user.email,
        "code": code,
        "expires_at": expires_at.isoformat()
    }
    
    await execute_query(
        table="verification_codes",
        query_type="insert",
        data=verification_data
    )
    
    background_tasks.add_task(send_verification_email, user.email, code)
    
    return new_user

@router.post("/verify", response_model=UserResponse)
async def verify_email(verification_data: VerificationRequest):
    user = await execute_query(
        table="users",
        query_type="select",
        filters={"email": verification_data.email}
    )
    
    if not user or len(user) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = user[0]
    
    if user["is_verified"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    verification = await execute_query(
        table="verification_codes",
        query_type="select",
        filters={"email": verification_data.email}
    )
    
    if not verification or len(verification) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code not found"
        )
    
    verification = verification[0]
    
    expires_at = datetime.fromisoformat(verification["expires_at"])
    if datetime.now() > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code expired"
        )
    
    if verification["code"] != verification_data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    await execute_query(
        table="users",
        query_type="update",
        filters={"id": user["id"]},
        data={"is_verified": True, "updated_at": datetime.now().isoformat()}
    )
    
    await execute_query(
        table="verification_codes",
        query_type="delete",
        filters={"id": verification["id"]}
    )
    
    updated_user = await execute_query(
        table="users",
        query_type="select",
        filters={"id": user["id"]}
    )
    
    return updated_user[0]

@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification_code(email: str, background_tasks: BackgroundTasks):
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
    
    if user["is_verified"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    await execute_query(
        table="verification_codes",
        query_type="delete",
        filters={"email": email}
    )
    
    code = generate_verification_code()
    
    expires_at = datetime.now() + timedelta(hours=24)
    verification_data = {
        "user_id": user["id"],
        "email": email,
        "code": code,
        "expires_at": expires_at.isoformat()
    }
    
    await execute_query(
        table="verification_codes",
        query_type="insert",
        data=verification_data
    )
    
    background_tasks.add_task(send_verification_email, email, code)
    
    return {"message": "Verification code sent"}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        # Authenticate with Supabase
        await sign_in(form_data.username, form_data.password)
        
        # Get user from database
        user = await execute_query(
            table="users",
            query_type="select",
            filters={"email": form_data.username}
        )
        
        if not user or len(user) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = user[0]
        
        if not user["is_verified"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please verify your email first."
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["id"]},
            expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    update_data = user_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now().isoformat()
    
    updated_user = await execute_query(
        table="users",
        query_type="update",
        filters={"id": current_user["id"]},
        data=update_data
    )
    
    if not updated_user or len(updated_user) == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )
    
    return updated_user[0]

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: UUID4 = Path(...)):
    user = await execute_query(
        table="users",
        query_type="select",
        filters={"id": str(user_id)}
    )
    
    if not user or len(user) == 0:
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
    users = await execute_query(
        table="users",
        query_type="select",
        limit=limit
    )
    
    return users[skip:skip + limit] 