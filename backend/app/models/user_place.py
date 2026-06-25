import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserPlace(Base):
    """用户常用地点（家、公司等），作为商家管理地图的默认聚焦中心。"""

    __tablename__ = "user_places"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    # home / work / custom
    kind = Column(String(20), nullable=False, default="custom", server_default="custom")
    latitude = Column(Numeric(10, 7), nullable=False)
    longitude = Column(Numeric(10, 7), nullable=False)
    address = Column(String(255))
    is_default = Column(Boolean, nullable=False, default=False, server_default=sa.false())
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    view_radius_km = Column(Numeric(10, 2), nullable=False, default=5, server_default="5")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="user_places")
