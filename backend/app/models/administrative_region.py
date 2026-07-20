from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class AdministrativeRegion(Base):
    """行政区划模型"""
    __tablename__ = "administrative_regions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(12), unique=True, nullable=False)  # 行政区划编码
    name = Column(String(100), nullable=False)
    name_en = Column(String(100), nullable=True)  # 国际化
    parent_id = Column(Integer, ForeignKey("administrative_regions.id"), nullable=True)
    level = Column(Integer, nullable=False)  # 0=country 1=province 2=city 3=county
    iso_country = Column(String(2), nullable=True)  # ISO 3166-1
    path = Column(String(200), nullable=True)  # e.g. CN/110000/110100
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
