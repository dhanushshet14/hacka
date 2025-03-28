from typing import Optional, Union, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pydantic import ValidationError
import motor.motor_asyncio
from bson import ObjectId

from app.core.config import settings
from app.models.user import User, UserInDB

# Modified to make token optional for direct access
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

# MongoDB connection
async def get_mongodb():
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DB_NAME]

# Get user collection
async def get_user_collection():
    db = await get_mongodb()
    return db["users"]

# Get user by username
async def get_user_by_username(username: str) -> Optional[UserInDB]:
    users_collection = await get_user_collection()
    user_data = await users_collection.find_one({"username": username})
    if user_data:
        return UserInDB(**user_data)
    return None

# Get user by email
async def get_user_by_email(email: str) -> Optional[UserInDB]:
    users_collection = await get_user_collection()
    user_data = await users_collection.find_one({"email": email})
    if user_data:
        return UserInDB(**user_data)
    return None

# Get user by ID
async def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    users_collection = await get_user_collection()
    user_data = await users_collection.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return UserInDB(**user_data)
    return None

# JWT token functions
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # Refresh token valid for 7 days
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

# Modified to bypass authentication and return a dummy user
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> User:
    # Return a dummy user without checking authentication
    return User(
        id="dummy_user_id",
        email="user@example.com",
        username="demouser",
        full_name="Demo User",
        is_active=True,
        is_superuser=True,
        created_at=datetime.utcnow(),
        preferences={"theme": "dark"}
    )

# For endpoints that need admin access - modified to always allow access
async def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    # No permission check
    return current_user 