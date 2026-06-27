import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    # 确保密码不超过 72 字节以满足 bcrypt 要求
    truncated_password = plain_password[:72].encode('utf-8') if len(plain_password) > 72 else plain_password.encode('utf-8')
    return bcrypt.checkpw(truncated_password, hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    # 确保密码不超过 72 字节以满足 bcrypt 要求
    truncated_password = password[:72].encode('utf-8') if len(password) > 72 else password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(truncated_password, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """解码令牌"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def validate_token_type(token: str, expected_type: str = "access") -> bool:
    """验证令牌类型"""
    payload = decode_token(token)
    if not payload:
        return False
    return payload.get("type") == expected_type


# FastAPI 依赖注入
security = HTTPBearer()


def resolve_user_from_token(token: "Optional[str]"):
    """根据 access token 解析出 User 对象。

    供 ``get_current_user``（HTTPBearer 依赖注入）与 SSE 端点的 query token
    鉴权（``_auth_user_from_token``）共享同一套校验逻辑：空 token / 解码失败 /
    非 access 类型 / sub 缺失 → 401；用户不存在 → 404；账户已禁用 → 403。

    Args:
        token: JWT 字符串，可为 None（视为未授权）。

    Returns:
        User 对象。

    Raises:
        HTTPException: 401 / 403 / 404。
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未授权"
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )

    # 验证令牌类型必须是 access
    if not validate_token_type(token, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )

    from app.core.database import SessionLocal
    from app.models.user import User

    # 直接 SessionLocal + try/finally，避免 ``next(get_db())`` 反模式：
    # 后者取到的 generator 临时对象无变量绑定，CPython 引用计数下会立即被 GC，
    # 反过来触发 get_db 的 finally 提前 close，使单次鉴权借两次连接；且异常
    # 路径下连接归还依赖 GC 时机，高并发下不稳。这里是每个鉴权请求的必经
    # 高频路径，必须保证异常时也立即归还连接。
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
    finally:
        db.close()

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

    # token 版本比对：重置密码等场景 bump token_version 后，旧 token 立即失效。
    # 老token无 ver claim 时取 0，存量用户 token_version 默认 0，不误伤。
    if payload.get("ver", 0) != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="凭证已失效，请重新登录"
        )

    return user


async def get_current_user(credentials: HTTPBearer = Depends(security)):
    """获取当前登录用户（依赖注入）"""
    return resolve_user_from_token(credentials.credentials)


async def get_current_admin_user(
    current_user: "User" = Depends(get_current_user),
):
    """获取当前管理员用户（依赖注入）。

    在 ``get_current_user`` 基础上追加管理员权限检查，
    非管理员直接返回 403。
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅限管理员访问"
        )
    return current_user