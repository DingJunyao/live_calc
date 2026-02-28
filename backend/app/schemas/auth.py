from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from app.config import settings


class ConfigResponse(BaseModel):
    registration_require_invite_code: bool = settings.registration_require_invite_code


class ConfigUpdate(BaseModel):
    require_invite_code: bool


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$")
    password_hash: str  # 前端已 SHA256 加密
    invite_code: Optional[str] = None

    @field_validator('phone', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """空字符串转为 None，避免验证失败"""
        if v == '' or v is None:
            return None
        return v


class UserLogin(BaseModel):
    username: str
    password_hash: str  # 前端已 SHA256 加密


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone: Optional[str]
    is_admin: bool
    email_verified: bool
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: str
    email: str
    phone: Optional[str]
    is_admin: bool
    email_verified: bool
