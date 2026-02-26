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


async def get_current_user(credentials: HTTPBearer = Depends(security)):
    """获取当前登录用户（依赖注入）"""
    token = credentials.credentials
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

    from app.core.database import get_db
    from app.models.user import User

    db = next(get_db())
    user = db.query(User).filter(User.id == int(user_id)).first()
    db.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return user