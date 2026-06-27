"""商品×商家 价格聚合汇总（去标识，不含 user/record_type）。写入时增量更新。"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class ProductMerchantPriceSummary(Base):
    __tablename__ = "product_merchant_price_summary"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=True, index=True)
    sample_count = Column(Integer, nullable=False, default=0)
    recent_price = Column(Numeric(10, 2), nullable=True)
    avg_price_30d = Column(Numeric(10, 2), nullable=True)
    min_price = Column(Numeric(10, 2), nullable=True)
    max_price = Column(Numeric(10, 2), nullable=True)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now())
