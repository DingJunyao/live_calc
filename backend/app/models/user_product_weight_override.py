from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class UserProductWeightOverride(Base, AuditMixin):
    """用户对商品价格权重的私有覆盖（个人偏好，不走审核）。

    读取优先级：本表(is_active) → Product.price_weight → 兜底 50。
    """
    __tablename__ = "user_product_weight_overrides"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    weight = Column(Integer, nullable=False, default=50)

    user = relationship("User")
    product = relationship("Product")

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_user_product_weight"),
        Index("ix_upwo_user_active", "user_id", "is_active"),
    )
