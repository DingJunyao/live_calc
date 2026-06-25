import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    address = Column(String(500))
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    is_open = Column(Boolean, default=True, nullable=False, server_default=sa.true())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="merchants")
    product_records = relationship("ProductRecord", back_populates="merchant")
