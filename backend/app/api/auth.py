import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    validate_token_type,
    verify_password,
    get_current_user,
    get_current_admin_user,
)
from app.models.user import User
from app.models.unit import Unit
from app.models.invite_code import InviteCode
from app.models.system_config import SystemConfig
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
    ConfigResponse,
    UserUpdate,
    ConfigUpdate,
    UserAdminCreate,
    UserAdminUpdate,
    UserAdminStatusUpdate,
    UserProfileUpdate,
    UserAccountUpdate,
    UserAccountResponse,
    UnitPreference,
    UnitPreferences,
)
from app.schemas.common import PaginatedResponse
from typing import List, Optional
from pydantic import BaseModel
import datetime
from app.utils.datetime_utils import serialize_datetime


def _get_dynamic_config(db: Session, key: str, default: str = "") -> str:
    """从数据库读取动态配置，无记录时返回默认值。"""
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return row.value if row else default


def _get_bool_config(db: Session, key: str, default: bool = False) -> bool:
    """从数据库读取布尔型动态配置。"""
    val = _get_dynamic_config(db, key, "true" if default else "false")
    return val.lower() in ("true", "1", "yes")


def _build_unit_preferences(user: User, db: Session) -> UnitPreferences:
    """从 User 的 4 个单位字段构造 unit_preferences，解析单位名。"""
    def _pref(uid):
        if uid is None:
            return None
        u = db.query(Unit).filter(Unit.id == uid).first()
        if not u:
            return None
        return UnitPreference(id=u.id, name=u.name, abbreviation=u.abbreviation)

    return UnitPreferences(
        energy_unit=user.default_energy_unit,
        mass_unit=_pref(user.default_mass_unit_id),
        volume_unit=_pref(user.default_volume_unit_id),
        price_unit=_pref(user.default_price_unit_id),
    )


def validate_invite_code(code: str, db: Session) -> InviteCode:
    """验证邀请码是否有效。返回 InviteCode 对象，无效则返回 None。

    使用次数上限（max_uses）和过期时间（expires_at）为可选限制条件。
    """
    invite_code = db.query(InviteCode).filter(InviteCode.code == code).first()

    if not invite_code:
        return None

    if not invite_code.is_valid:
        return None

    # 标记使用次数 +1
    invite_code.used_count += 1
    db.commit()

    return invite_code


class UserStatsResponse(BaseModel):
    total: int


router = APIRouter()
security = HTTPBearer()


@router.get("/config", response_model=ConfigResponse)
async def get_config(db: Session = Depends(get_db)):
    """获取注册配置（动态读取数据库，fallback .env 默认值）。"""
    require_invite = _get_bool_config(
        db, "registration_require_invite_code", False
    )
    return ConfigResponse(
        registration_require_invite_code=require_invite
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

    # 检查邀请码（如需要）——动态读取配置
    is_first_user = db.query(User).count() == 0
    require_invite = _get_bool_config(
        db, "registration_require_invite_code", False
    )

    # 对于第一个用户，不需要邀请码，直接成为管理员
    if not is_first_user and require_invite:
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
        password_hash=get_password_hash(user_data.password_hash),
        is_admin=is_first_user  # 第一个用户自动成为管理员
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 创建令牌
    access_token = create_access_token(data={"sub": str(user.id), "ver": user.token_version})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "ver": user.token_version})

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

    # 检查账户是否被禁用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )

    # 验证密码（前端已 SHA256，这里再 bcrypt）
    from app.core.security import verify_password
    if not verify_password(user_data.password_hash, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 创建令牌
    access_token = create_access_token(data={"sub": str(user.id), "ver": user.token_version})
    refresh_token = create_refresh_token(data={"sub": str(user.id), "ver": user.token_version})

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

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )

    # refresh token 版本比对：旧 refresh token 在密码被重置后立即失效
    if payload.get("ver", 0) != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="凭证已失效，请重新登录"
        )

    # 创建新的访问令牌
    access_token = create_access_token(data={"sub": str(user.id), "ver": user.token_version})
    return TokenResponse(
        access_token=access_token,
        refresh_token=token  # 返回同一个 refresh token
    )


def _user_to_response(user: "User", db: Session) -> UserResponse:
    """统一构造 UserResponse（含 nutrition_goals / unit_preferences）。

    get_me / patch_me / update_my_account 共用，避免三份重复构造。
    """
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        is_admin=user.is_admin,
        is_active=user.is_active,
        email_verified=user.email_verified,
        avatar=user.avatar,
        nickname=user.nickname,
        created_at=serialize_datetime(user.created_at) if user.created_at else None,
        nutrition_goals={
            "daily_calorie_target": user.daily_calorie_target,
            "daily_protein_target": user.daily_protein_target,
            "daily_carb_target": user.daily_carb_target,
            "daily_fat_target": user.daily_fat_target,
        },
        daily_budget=user.daily_budget,
        unit_preferences=_build_unit_preferences(user, db),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户信息（含营养目标、预算、单位偏好）。"""
    return _user_to_response(current_user, db)


@router.patch("/me", response_model=UserResponse)
async def patch_me(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户更新自己的营养目标、预算、单位偏好设置。"""
    update_data = profile_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有需要更新的字段",
        )

    # 单位偏好校验
    if "default_energy_unit" in update_data:
        val = update_data["default_energy_unit"]
        if val is not None and val not in ("kcal", "kJ"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="default_energy_unit 必须是 kcal 或 kJ",
            )

    _UNIT_TYPE_EXPECT = {
        "default_mass_unit_id": "mass",
        "default_volume_unit_id": "volume",
        "default_price_unit_id": None,  # 允许 mass/volume/count
    }
    _PRICE_ALLOWED = {"mass", "volume", "count"}
    for field, expected_type in _UNIT_TYPE_EXPECT.items():
        if field in update_data and update_data[field] is not None:
            uid = update_data[field]
            u = db.query(Unit).filter(Unit.id == uid).first()
            if not u:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field}={uid} 不存在",
                )
            if expected_type is None:
                if u.unit_type not in _PRICE_ALLOWED:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"价格记录单位必须是 mass/volume/count，得到 {u.unit_type}",
                    )
            elif u.unit_type != expected_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field} 必须是 {expected_type} 类型单位，得到 {u.unit_type}",
                )

    # current_user 由 get_current_user 从独立 session 解析（detached），
    # 在本请求 db 内重新加载，保证 setattr + commit + refresh 生效。
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return _user_to_response(user, db)


@router.put("/me/account", response_model=UserAccountResponse)
async def update_my_account(
    payload: UserAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """当前用户自行更新账号信息（用户名/邮箱/手机/密码）。

    - 用户名/邮箱/手机：传了且与当前不同才改，查重（排除自己），命中 400。
    - 密码：new_password 非空时必须校验 current_password；成功后 token_version+1
      并签发新 token 返回（发起方无缝续登，其他设备旧 token 失效）。
      不改密码时 token_version 不动，不签发 token。
    """
    # current_user 来自 get_current_user 的独立 session（detached），
    # 在本请求 db 内重新加载，保证 setattr + commit + refresh 生效（与 patch_me 一致）。
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 用户名
    if payload.username is not None and payload.username != user.username:
        if db.query(User).filter(
            User.username == payload.username, User.id != user.id
        ).first():
            raise HTTPException(status_code=400, detail="用户名已被占用")
        user.username = payload.username

    # 邮箱
    if payload.email is not None and payload.email != user.email:
        if db.query(User).filter(
            User.email == payload.email, User.id != user.id
        ).first():
            raise HTTPException(status_code=400, detail="邮箱已被占用")
        user.email = payload.email

    # 手机（phone 允许 NULL，查重时 NULL 不算冲突）
    if payload.phone is not None and payload.phone != user.phone:
        if payload.phone and db.query(User).filter(
            User.phone == payload.phone, User.id != user.id
        ).first():
            raise HTTPException(status_code=400, detail="手机号已被占用")
        user.phone = payload.phone

    # 昵称
    if payload.nickname is not None:
        user.nickname = payload.nickname

    # 密码
    changed_password = False
    if payload.new_password is not None:
        if not payload.current_password:
            raise HTTPException(status_code=400, detail="修改密码需提供当前密码")
        if not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=401, detail="当前密码错误")
        user.password_hash = get_password_hash(payload.new_password)
        user.token_version += 1
        changed_password = True

    db.commit()
    db.refresh(user)

    access_token = None
    refresh_token = None
    if changed_password:
        token_data = {"sub": str(user.id), "ver": user.token_version}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

    return UserAccountResponse(
        user=_user_to_response(user, db),
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传/更换头像。

    - 仅允许图片 MIME 类型
    - 上传前自动删除旧头像（如有）
    - 文件存到 storage backend，key = avatars/{uuid}.{ext}
    - 返回 avatar_key + avatar_url
    """
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 JPEG、PNG、GIF、WebP 格式的图片",
        )

    try:
        ext = os.path.splitext(file.filename or "avatar.jpg")[1] or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        key = f"avatars/{filename}"

        from app.services.storage import get_storage

        content = await file.read()
        storage = get_storage()
        storage.put(key, content, file.content_type or "image/jpeg")

        # 删除旧头像
        if current_user.avatar:
            try:
                storage.delete(current_user.avatar)
            except Exception:
                pass  # 旧文件删除失败不影响新头像上传

        # 更新数据库
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        user.avatar = key
        db.commit()

        return {"avatar_key": key, "avatar_url": storage.url_for(key)}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"上传头像失败: {str(e)}")


@router.post("/config", response_model=ConfigResponse)
async def update_config(
    config_update: ConfigUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """更新注册配置 - 仅限管理员，写入数据库动态配置。"""
    row = db.query(SystemConfig).filter(
        SystemConfig.key == "registration_require_invite_code"
    ).first()
    new_val = "true" if config_update.require_invite_code else "false"
    if row:
        row.value = new_val
    else:
        db.add(SystemConfig(key="registration_require_invite_code", value=new_val))
    db.commit()

    return ConfigResponse(
        registration_require_invite_code=config_update.require_invite_code
    )


@router.get("/users", response_model=PaginatedResponse)
async def get_all_users(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    search: Optional[str] = Query(None, description="搜索用户名或邮箱"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取所有用户信息（分页 + 搜索）- 仅限管理员"""
    query = db.query(User)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (User.username.ilike(like)) | (User.email.ilike(like))
        )
    total = query.count()
    users = query.order_by(User.id).offset(skip).limit(limit).all()
    page = skip // limit + 1

    return PaginatedResponse.create(
        items=[
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                phone=user.phone,
                is_admin=user.is_admin,
                is_active=user.is_active,
                email_verified=user.email_verified,
                avatar=user.avatar,
                nickname=user.nickname,
                created_at=serialize_datetime(user.created_at) if user.created_at else None
            ) for user in users
        ],
        total=total,
        page=page,
        page_size=limit
    )


# ==================== 用户管理安全规则 ====================

def _check_user_safety(current_user: User, target_user: User, action: str) -> None:
    """检查用户操作安全规则。

    - 不能操作自己
    - 不能操作系统首个用户（id=1）
    """
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"不能{action}自己的账户"
        )
    if target_user.id == 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"不能{action}系统初始管理员"
        )


@router.get("/users/stats", response_model=UserStatsResponse)
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取用户统计 - 仅限管理员"""
    total_users = db.query(User).count()
    return UserStatsResponse(total=total_users)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取单个用户详情 - 仅限管理员"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        is_admin=user.is_admin,
        is_active=user.is_active,
        email_verified=user.email_verified,
        avatar=user.avatar,
        nickname=user.nickname,
        created_at=serialize_datetime(user.created_at) if user.created_at else None
    )


@router.post("/users", response_model=UserResponse)
async def admin_create_user(
    user_data: UserAdminCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """管理员创建用户（跳过邀请码校验）"""
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册")

    user = User(
        username=user_data.username,
        email=user_data.email,
        phone=user_data.phone,
        password_hash=get_password_hash(user_data.password_hash),
        is_admin=user_data.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        is_admin=user.is_admin,
        is_active=user.is_active,
        email_verified=user.email_verified,
        avatar=user.avatar,
        nickname=user.nickname,
        created_at=serialize_datetime(user.created_at) if user.created_at else None
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """修改用户信息 - 仅限管理员"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if user_update.username and user_update.username != target.username:
        if db.query(User).filter(User.username == user_update.username).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
        target.username = user_update.username
    if user_update.email and user_update.email != target.email:
        if db.query(User).filter(User.email == user_update.email).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册")
        target.email = user_update.email
    if user_update.phone is not None:
        target.phone = user_update.phone
    if user_update.nickname is not None:
        target.nickname = user_update.nickname
    if user_update.email_verified is not None:
        target.email_verified = user_update.email_verified
    if user_update.password_hash is not None:
        target.password_hash = get_password_hash(user_update.password_hash)
        target.token_version += 1

    db.commit()
    db.refresh(target)
    return UserResponse(
        id=target.id,
        username=target.username,
        email=target.email,
        phone=target.phone,
        is_admin=target.is_admin,
        is_active=target.is_active,
        email_verified=target.email_verified,
        avatar=target.avatar,
        nickname=target.nickname,
        created_at=serialize_datetime(target.created_at) if target.created_at else None
    )


@router.put("/users/{user_id}/admin", response_model=UserResponse)
async def toggle_user_admin(
    user_id: int,
    body: UserAdminStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """切换用户管理员身份 - 仅限管理员"""
    if body.is_admin is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 is_admin 字段")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 取消管理员时必须检查安全规则
    if not body.is_admin:
        _check_user_safety(current_user, target, "取消")

    target.is_admin = body.is_admin
    db.commit()
    db.refresh(target)
    return UserResponse(
        id=target.id,
        username=target.username,
        email=target.email,
        phone=target.phone,
        is_admin=target.is_admin,
        is_active=target.is_active,
        email_verified=target.email_verified,
        avatar=target.avatar,
        nickname=target.nickname,
        created_at=serialize_datetime(target.created_at) if target.created_at else None
    )


@router.put("/users/{user_id}/active", response_model=UserResponse)
async def toggle_user_active(
    user_id: int,
    body: UserAdminStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """切换用户激活状态 - 仅限管理员"""
    if body.is_active is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="缺少 is_active 字段")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 失效用户时必须检查安全规则
    if not body.is_active:
        _check_user_safety(current_user, target, "失效")

    target.is_active = body.is_active
    db.commit()
    db.refresh(target)
    return UserResponse(
        id=target.id,
        username=target.username,
        email=target.email,
        phone=target.phone,
        is_admin=target.is_admin,
        is_active=target.is_active,
        email_verified=target.email_verified,
        avatar=target.avatar,
        nickname=target.nickname,
        created_at=serialize_datetime(target.created_at) if target.created_at else None
    )


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
