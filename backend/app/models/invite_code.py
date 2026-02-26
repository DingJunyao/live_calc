from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"))  # 由谁创建
    used = Column(Boolean, default=False)  # 是否已被使用
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))  # 过期时间

    # 关系
    creator = relationship("User", back_populates="created_invite_codes")


def generate_invite_code(length: int = 8) -> str:
    """生成随机邀请码"""
    import random
    import string

    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))