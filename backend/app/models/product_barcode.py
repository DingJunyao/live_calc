"""商品条码模型"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.base_model import AuditMixin
from app.core.database import Base


class ProductBarcode(Base, AuditMixin):
    """商品条码 - 支持一个商品对应多个条码（店内自编条码场景）"""
    __tablename__ = "product_barcodes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    barcode = Column(String(50), nullable=False, index=True)
    barcode_type = Column(String(20), default="internal")  # internal/gtin/upc/ean等
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    product = relationship("Product", back_populates="barcodes")

    def __repr__(self):
        return f"<ProductBarcode(id={self.id}, barcode={self.barcode}, product_id={self.product_id})>"
