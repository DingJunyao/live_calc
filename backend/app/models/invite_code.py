import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


def ensure_utc(dt: datetime.datetime) -> datetime.datetime:
    """把 datetime 统一成 UTC aware（naive 视作 UTC）。

    SQLite 读回的 DateTime(timezone=True) 实际是 naive（无 tzinfo），
    PostgreSQL/MySQL 读回 aware；统一成 UTC aware，避免 naive/aware 比较 TypeError，
    也让序列化输出带明确时区。
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"))  # 由谁创建
    used_count = Column(Integer, default=0)  # 已使用次数
    max_uses = Column(Integer, nullable=True)  # 最大使用次数（NULL = 不限）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 过期时间

    # 关系
    creator = relationship("User", back_populates="created_invite_codes")

    @property
    def is_exhausted(self) -> bool:
        """是否已用完（次数限制）。"""
        return self.max_uses is not None and self.used_count >= self.max_uses

    @property
    def is_expired(self) -> bool:
        """是否已过期。"""
        if self.expires_at is None:
            return False
        return ensure_utc(self.expires_at) < datetime.datetime.now(datetime.timezone.utc)

    @property
    def is_valid(self) -> bool:
        """邀请码是否仍然有效（未过期且未用完）。"""
        return not self.is_expired and not self.is_exhausted


def generate_invite_code(length: int = 8) -> str:
    """生成随机邀请码"""
    import random
    import string

    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))
