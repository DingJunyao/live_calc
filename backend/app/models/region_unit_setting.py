from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class RegionUnitSetting(Base):
    __tablename__ = "region_unit_settings"

    id = Column(Integer, primary_key=True, index=True)
    region_code = Column(String(10), unique=True, nullable=False)  # 地区代码，如"CN"、"US"
    region_name = Column(String(100), nullable=False)  # 地区名称
    default_mass_unit = Column(Integer, ForeignKey("units.id"))  # 默认质量单位ID
    default_volume_unit = Column(Integer, ForeignKey("units.id"))  # 默认体积单位ID
    default_length_unit = Column(Integer, ForeignKey("units.id"))  # 默认长度单位ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserUnitPreference(Base):
    __tablename__ = "user_unit_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)  # 用户ID
    preferred_mass_unit = Column(Integer, ForeignKey("units.id"))  # 首选质量单位
    preferred_volume_unit = Column(Integer, ForeignKey("units.id"))  # 首选体积单位
    preferred_length_unit = Column(Integer, ForeignKey("units.id"))  # 首选长度单位
    temperature_unit = Column(String(10), default="celsius")  # 温度单位（摄氏/华氏）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())