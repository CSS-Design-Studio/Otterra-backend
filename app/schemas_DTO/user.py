from pydantic import BaseModel, EmailStr, HttpUrl, Field, field_validator
from typing import Optional
from datetime import datetime
import zxcvbn as zxcvbn_lib

SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;':\",./<>?"

class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = Field(None, max_length=20)
    first_name: Optional[str] = Field(None, max_length=20)
    last_name: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=500)

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, max_length=20)
    first_name: Optional[str] = Field(None, max_length=20)
    last_name: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=500)
    phone_number: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[HttpUrl] = None

class UserProfileResponse(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    username: str
    first_name: str
    last_name: str
    bio: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None
    role_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        # Require at least one uppercase letter
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        # Require at least one digit
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        # Require at least one special character
        if not any(c in SPECIAL_CHARS for c in v):
            raise ValueError("Password must contain at least one special character")

        # zxcvbn score: 0 (very weak) to 4 (very strong)
        # Score >= 2 means resistant to dictionary and common pattern attacks
        result = zxcvbn_lib.zxcvbn(v)
        if result["score"] < 2:
            warning = result["feedback"].get("warning", "")
            suggestions = result["feedback"].get("suggestions", [])
            detail = warning or (suggestions[0] if suggestions else "Password is too easy to guess")
            raise ValueError(f"Password too weak: {detail}")

        return v

class UserResponse(UserBase):
    id: Optional[str] = None
