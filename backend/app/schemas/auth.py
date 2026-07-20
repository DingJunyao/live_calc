from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional


class ConfigResponse(BaseModel):
    registration_require_invite_code: bool = False


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


class UnitPreference(BaseModel):
    id: int
    name: str
    abbreviation: str


class UnitPreferences(BaseModel):
    energy_unit: Optional[str] = None
    mass_unit: Optional[UnitPreference] = None
    volume_unit: Optional[UnitPreference] = None
    price_unit: Optional[UnitPreference] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone: Optional[str]
    is_admin: bool
    is_active: bool = True
    email_verified: bool
    avatar: Optional[str] = None
    nickname: Optional[str] = None
    created_at: Optional[str] = None
    nutrition_goals: Optional[dict] = None
    daily_budget: Optional[float] = None
    unit_preferences: Optional[UnitPreferences] = None

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
    nickname: Optional[str] = None
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
    """用户自行更新个人设置（营养目标、预算、单位偏好）。"""
    daily_calorie_target: Optional[float] = None
    daily_protein_target: Optional[float] = None
    daily_carb_target: Optional[float] = None
    daily_fat_target: Optional[float] = None
    daily_budget: Optional[float] = None
    default_energy_unit: Optional[str] = None
    default_mass_unit_id: Optional[int] = None
    default_volume_unit_id: Optional[int] = None
    default_price_unit_id: Optional[int] = None


class UserAccountUpdate(BaseModel):
    """用户自行更新账号信息（用户名/邮箱/手机/昵称/密码）。字段全部可选，传了才改。"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$")
    nickname: Optional[str] = Field(None, min_length=1, max_length=50)
    current_password: Optional[str] = None   # 前端 SHA256 后传
    new_password: Optional[str] = None       # 前端 SHA256 后传

    @field_validator('phone', mode='before')
    @classmethod
    def empty_string_to_none(cls, v):
        """空字符串转为 None，避免与 NULL 语义冲突。"""
        if v == '' or v is None:
            return None
        return v


class UserAccountResponse(BaseModel):
    """账号更新响应：user + 可选新 token（仅改密码时返回）。"""
    user: UserResponse
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
