from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Enum as PyEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class RecordType(PyEnum):
    PURCHASE = "purchase"
    PRICE = "price"


class ProductRecord(Base):
    __tablename__ = "product_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(200), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="CNY")
    original_quantity = Column(Numeric(10, 3), nullable=False)
    original_unit = Column(String(20), nullable=False)
    standard_quantity = Column(Numeric(10, 3), nullable=False)
    standard_unit = Column(String(20), default="g")
    record_type = Column(String(20), default=RecordType.PURCHASE)
    exchange_rate = Column(Numeric(10, 6), default=1.0)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String(500), nullable=True)

    # 关系
    user = relationship("User", back_populates="product_records")
    product = relationship("Product", back_populates="price_records")
    location = relationship("Location", back_populates="product_records")
