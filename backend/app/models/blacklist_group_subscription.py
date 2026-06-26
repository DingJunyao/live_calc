"""用户订阅的黑名单分组（动态：分组原料变化时自动生效）"""
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class BlacklistGroupSubscription(Base, AuditMixin):
    """用户订阅的黑名单分组"""
    __tablename__ = "blacklist_group_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    blacklist_group_id = Column(Integer, ForeignKey("blacklist_groups.id"), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'blacklist_group_id', name='uq_blacklist_group_subscription'),
    )

    user = relationship("User", foreign_keys=[user_id])
    blacklist_group = relationship("BlacklistGroup", foreign_keys=[blacklist_group_id])
