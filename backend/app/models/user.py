from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator
from bson import ObjectId

# Custom ObjectId handling for MongoDB
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# Base User model that can be used for requests
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    disabled: bool = False

# User model for database operations (includes hashed password)
class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # Store user preferences/settings
    preferences: Dict[str, Any] = Field(default_factory=dict)
    # Store AR experience history
    ar_experiences: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "_id": "60d5ec9af682dbd134b1022c",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "disabled": False,
                "hashed_password": "hashedpassword",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "preferences": {
                    "theme": "dark",
                    "notifications_enabled": True
                },
                "ar_experiences": []
            }
        }

# User model for create operations (includes password)
class UserCreate(UserBase):
    password: str
    
    @validator("password")
    def password_strength_check(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

# User model for update operations
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    disabled: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None
    
    class Config:
        arbitrary_types_allowed = True
        schema_extra = {
            "example": {
                "email": "newemail@example.com",
                "full_name": "New Name",
                "password": "newpassword",
                "preferences": {
                    "theme": "light"
                }
            }
        }

# User model for response (no password)
class User(UserBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime
    preferences: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "60d5ec9af682dbd134b1022c",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "disabled": False,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "preferences": {
                    "theme": "dark",
                    "notifications_enabled": True
                }
            }
        }
