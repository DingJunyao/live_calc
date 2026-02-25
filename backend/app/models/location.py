from sqlalchemy import Column, Integer, String, Date, Decimal, ForeignKey, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    address = Column(String(500))
    latitude = Column(Decimal(10, 7))
    longitude = Column(Decimal(10, 7))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="locations")
    product_records = relationship("ProductRecord", back_populates="location")


class FavoriteLocation(Base):
    __tablename__ = "favorite_locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), default="other")  # home, work, other
    latitude = Column(Decimal(10, 7), nullable=False)
    longitude = Column(Decimal(10, 7), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", back_populates="favorite_locations")
