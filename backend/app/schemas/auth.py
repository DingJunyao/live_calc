from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from app.config import settings


class ConfigResponse(BaseModel):
    registration_require_invite_code: bool = settings.registration_require_invite_code


class ConfigUpdate(BaseModel):
    require_invite_code: bool


class AdminConfigUpdate(BaseModel):
    """管理员更新系统动态配置。"""
    registration_require_invite_code: Optional[bool] = None


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
    is_active: bool = True
    email_verified: bool
    created_at: Optional[str] = None
    nutrition_goals: Optional[dict] = None
    daily_budget: Optional[float] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: str
    email: str
    phone: Optional[str]
    is_admin: bool
    email_verified: bool


class UserAdminCreate(BaseModel):
    """管理员创建用户。密码为前端 SHA256 后的值。"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$")
    password_hash: str  # 前端已 SHA256 加密
    is_admin: bool = False

    @field_validator('phone', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class UserAdminUpdate(BaseModel):
    """管理员修改用户信息，所有字段可选，密码传了才更新。"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$")
    password_hash: Optional[str] = None  # 不传则不修改密码
    email_verified: Optional[bool] = None

    @field_validator('phone', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class UserAdminStatusUpdate(BaseModel):
    """切换管理员或激活状态。"""
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class UserProfileUpdate(BaseModel):
    """用户自行更新个人设置（仅允许修改营养目标和预算）。"""
    daily_calorie_target: Optional[float] = None
    daily_protein_target: Optional[float] = None
    daily_carb_target: Optional[float] = None
    daily_fat_target: Optional[float] = None
    daily_budget: Optional[float] = None
