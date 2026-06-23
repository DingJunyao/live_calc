# backend/app/models/user_merchant_product_order.py

import sqlalchemy as sa
from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class UserMerchantProductOrder(Base):
    """用户 × 商家 × 商品的每日排序记录。"""

    __tablename__ = "user_merchant_product_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    session_date = Column(Date, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        sa.UniqueConstraint(
            "user_id", "merchant_id", "product_id", "session_date",
            name="uq_umpo_user_merchant_product_date",
        ),
        sa.Index("idx_umpo_lookup", "user_id", "merchant_id", "session_date"),
    )
