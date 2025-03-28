from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
import redis
import uuid

from app.core.config import settings
from app.models.user import User, UserCreate, UserInDB
from app.api.deps import (
    get_user_collection, 
    get_user_by_username, 
    get_user_by_email, 
    create_access_token, 
    create_refresh_token,
    get_current_user
)

router = APIRouter()

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Redis client for storing refresh tokens
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True
)

# Models
class Token(BaseModel):
    """JWT token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until token expires

class RefreshToken(BaseModel):
    """Refresh token request model"""
    refresh_token: str

class WebSocketAuth(BaseModel):
    """WebSocket authentication response"""
    ws_token: str
    ws_url: str

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a password hash"""
    return pwd_context.hash(password)

async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user with username and password"""
    user = await get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# Redis token functions
def store_refresh_token(user_id: str, token: str, expires_in: int = 60*60*24*7):
    """Store a refresh token in Redis"""
    key = f"{settings.REDIS_PREFIX}refresh_token:{token}"
    redis_client.setex(key, expires_in, user_id)

def validate_refresh_token(token: str) -> Optional[str]:
    """Validate a refresh token and return the user_id if valid"""
    key = f"{settings.REDIS_PREFIX}refresh_token:{token}"
    user_id = redis_client.get(key)
    return user_id

def invalidate_refresh_token(token: str) -> bool:
    """Invalidate a refresh token"""
    key = f"{settings.REDIS_PREFIX}refresh_token:{token}"
    return redis_client.delete(key) > 0

def invalidate_all_user_tokens(user_id: str) -> int:
    """Invalidate all refresh tokens for a user"""
    pattern = f"{settings.REDIS_PREFIX}refresh_token:*"
    keys = redis_client.keys(pattern)
    count = 0
    for key in keys:
        if redis_client.get(key) == user_id:
            redis_client.delete(key)
            count += 1
    return count

# Routes
@router.post("/register", response_model=User)
async def register_user(user_data: UserCreate):
    """
    Register a new user
    """
    # Check if username already exists
    existing_user = await get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = await get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user_collection = await get_user_collection()
    
    hashed_password = get_password_hash(user_data.password)
    user_db = UserInDB(
        **user_data.dict(exclude={"password"}),
        hashed_password=hashed_password,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    result = await user_collection.insert_one(user_db.dict(by_alias=True))
    
    # Return user without password
    created_user = User(
        _id=str(result.inserted_id),
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        disabled=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        preferences={}
    )
    
    return created_user

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
        
    # Generate tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": str(user.id)}
    )
    
    # Store refresh token in Redis
    store_refresh_token(str(user.id), refresh_token)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: RefreshToken):
    """
    Refresh access token using refresh token
    """
    # Validate refresh token
    user_id = validate_refresh_token(token_data.refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user
    user_collection = await get_user_collection()
    from bson import ObjectId
    user_data = await user_collection.find_one({"_id": ObjectId(user_id)})
    if not user_data:
        # Invalidate token if user doesn't exist
        invalidate_refresh_token(token_data.refresh_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = UserInDB(**user_data)
    
    # Invalidate old refresh token
    invalidate_refresh_token(token_data.refresh_token)
    
    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": str(user.id)}
    )
    
    # Store new refresh token
    store_refresh_token(str(user.id), refresh_token)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/logout")
async def logout(token_data: RefreshToken, current_user: User = Depends(get_current_user)):
    """
    Logout user by invalidating refresh token
    """
    # Invalidate the refresh token
    invalidate_refresh_token(token_data.refresh_token)
    return {"detail": "Successfully logged out"}

@router.post("/logout-all")
async def logout_all_devices(current_user: User = Depends(get_current_user)):
    """
    Logout from all devices by invalidating all refresh tokens
    """
    count = invalidate_all_user_tokens(str(current_user.id))
    return {"detail": f"Successfully logged out from all devices. Invalidated {count} tokens."}

@router.post("/ws-auth", response_model=WebSocketAuth)
async def websocket_auth(current_user: User = Depends(get_current_user)):
    """
    Get a token for WebSocket authentication to connect to the MCP server
    """
    # Generate a websocket token (same as access token but with shorter expiration)
    ws_token_expires = timedelta(minutes=60)  # 1 hour
    ws_token = create_access_token(
        data={"sub": current_user.username, "user_id": str(current_user.id)},
        expires_delta=ws_token_expires
    )
    
    # Generate client ID
    client_id = str(uuid.uuid4())
    
    # Construct WebSocket URL
    ws_url = f"ws://{settings.MCP_HOST}:{settings.MCP_PORT}{settings.MCP_WEBSOCKET_PATH}/{client_id}?token={ws_token}"
    
    return {
        "ws_token": ws_token,
        "ws_url": ws_url
    }

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current user
    """
    return current_user 