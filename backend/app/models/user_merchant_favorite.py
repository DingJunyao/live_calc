"""用户商家收藏（替代原 Merchant.user_id 的私有归属语义）。"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class UserMerchantFavorite(Base):
    __tablename__ = "user_merchant_favorites"
    __table_args__ = (UniqueConstraint("user_id", "merchant_id", name="uq_user_merchant"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
