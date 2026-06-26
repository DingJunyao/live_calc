"""用户订阅的过敏原分组黑名单"""
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class UserAllergenGroupBlacklist(Base, AuditMixin):
    """用户订阅的过敏原分组——动态黑名单：分组原料变化时自动生效"""
    __tablename__ = "user_allergen_group_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    allergen_group_id = Column(Integer, ForeignKey("allergen_groups.id"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'allergen_group_id', name='uq_user_allergen_group_blacklist'),
    )

    # 关系
    user = relationship("User", foreign_keys=[user_id])
    allergen_group = relationship("AllergenGroup", foreign_keys=[allergen_group_id])
