from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    validate_token_type,
    verify_password
)
from app.models.user import User
from app.models.invite_code import InviteCode
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
    ConfigResponse,
    UserUpdate,
    ConfigUpdate
)
from app.schemas.common import PaginatedResponse
from app.config import settings
from typing import List
from pydantic import BaseModel
import datetime


def validate_invite_code(code: str, db: Session) -> bool:
    """验证邀请码是否有效"""
    invite_code = db.query(InviteCode).filter(InviteCode.code == code).first()

    if not invite_code:
        return False

    # 检查是否已使用
    if invite_code.used:
        return False

    # 检查是否已过期
    if invite_code.expires_at and invite_code.expires_at < datetime.datetime.now(datetime.timezone.utc):
        return False

    # 标记为已使用
    invite_code.used = True
    db.commit()

    return True


class UserStatsResponse(BaseModel):
    total: int


router = APIRouter()
security = HTTPBearer()


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """获取注册配置"""
    return ConfigResponse(
        registration_require_invite_code=settings.registration_require_invite_code
    )


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否存在
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    # 检查邮箱是否存在
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )

    # 检查邀请码（如需要）
    is_first_user = db.query(User).count() == 0

    # 对于第一个用户，不需要邀请码，直接成为管理员
    if not is_first_user and settings.registration_require_invite_code:
        if not user_data.invite_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要邀请码"
            )

        # 验证邀请码
        if not validate_invite_code(user_data.invite_code, db):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邀请码无效或已使用"
            )

    # 创建用户
    user = User(
        username=user_data.username,
        email=user_data.email,
        phone=user_data.phone,
        password_hash=get_password_hash(user_data.password_hash),  # 密码长度已在 get_password_hash 中处理
        is_admin=is_first_user  # 第一个用户自动成为管理员
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 创建令牌
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    # 查找用户
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 验证密码（前端已 SHA256，这里再 bcrypt）
    from app.core.security import verify_password
    if not verify_password(user_data.password_hash, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 创建令牌
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """刷新访问令牌 - 从请求体接收 refresh_token"""
    token = token_request.refresh_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供刷新令牌"
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 创建新的访问令牌
    access_token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=access_token,
        refresh_token=token  # 返回同一个 refresh token
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    credentials: HTTPBearer = Depends(security),
    db: Session = Depends(get_db)
):
    """获取当前用户信息"""
    # 获取 token
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未授权"
        )

    # 验证令牌类型必须是 access
    if not validate_token_type(token, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型"
        )

    # 解码 token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )

    # 获取用户 ID
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )

    # 查询用户
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 返回用户信息
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        is_admin=user.is_admin,
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat() if user.created_at else None
    )


@router.post("/config", response_model=ConfigResponse)
async def update_config(
    config_update: ConfigUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新注册配置 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限管理员访问"
        )

    # 这里实际上不能动态更新应用配置
    # 通常，这类配置是通过环境变量或配置文件设置的
    # 为演示目的，我们只是简单返回更新后的值

    return ConfigResponse(
        registration_require_invite_code=config_update.require_invite_code
    )


@router.get("/users", response_model=PaginatedResponse)
async def get_all_users(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """获取所有用户信息（分页）- 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限管理员访问"
        )

    total = db.query(User).count()
    users = db.query(User).offset(skip).limit(limit).all()
    page = skip // limit + 1

    return PaginatedResponse.create(
        items=[
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                phone=user.phone,
                is_admin=user.is_admin,
                email_verified=user.email_verified,
                created_at=user.created_at.isoformat() if user.created_at else None
            ) for user in users
        ],
        total=total,
        page=page,
        page_size=limit
    )


@router.get("/users/stats", response_model=UserStatsResponse)
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """获取用户统计 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限管理员访问"
        )

    total_users = db.query(User).count()
    return UserStatsResponse(total=total_users)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """更新用户信息 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限管理员访问"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 更新用户信息
    user.username = user_update.username
    user.email = user_update.email
    user.phone = user_update.phone
    user.is_admin = user_update.is_admin
    user.email_verified = user_update.email_verified

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        is_admin=user.is_admin,
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat() if user.created_at else None
    )


@router.put("/users/{user_id}/admin", response_model=UserResponse)
async def update_user_admin_status(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """更新用户管理员权限 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限管理员访问"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 只更新管理员权限
    user.is_admin = user_update.is_admin

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        is_admin=user.is_admin,
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat() if user.created_at else None
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """删除用户 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限管理员访问"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    db.delete(user)
    db.commit()

    return {"detail": "用户删除成功"}


# 为用户添加个人统计信息端点
class PersonalStatsResponse(BaseModel):
    user_id: int
    username: str
    record_count: int
    recipe_count: int
    merchant_count: int


@router.get("/personal-stats", response_model=PersonalStatsResponse)
async def get_personal_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """获取用户的个人统计信息 - 所有用户可访问自己的统计信息"""
    from app.models.product import ProductRecord
    from app.models.recipe import Recipe
    from app.models.merchant import Merchant

    # 获取用户自己的记录数
    record_count = db.query(ProductRecord).filter(
        ProductRecord.user_id == current_user.id
    ).count()

    # 获取用户的菜谱数
    recipe_count = db.query(Recipe).filter(
        Recipe.user_id == current_user.id
    ).count()

    # 获取用户的商家数
    merchant_count = db.query(Merchant).filter(
        Merchant.user_id == current_user.id
    ).count()

    return PersonalStatsResponse(
        user_id=current_user.id,
        username=current_user.username,
        record_count=record_count,
        recipe_count=recipe_count,
        merchant_count=merchant_count
    )
