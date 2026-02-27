from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.base_model import AuditMixin


class Unit(Base, AuditMixin):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # 单位名称，如"g", "kg", "cup"
    abbreviation = Column(String(20), unique=True, nullable=False)  # 缩写
    plural_form = Column(String(50))  # 复数形式
    unit_type = Column(String(50), nullable=False)  # 类型，如"mass"（质量）, "volume"（体积）
    base_unit_id = Column(Integer, ForeignKey("units.id"))  # 基础单位ID，用于派生单位
    si_factor = Column(Numeric(15, 10), default=1.0)  # 转换为国际单位制的因子
    is_si_base = Column(Boolean, default=False)  # 是否是国际单位制基本单位
    is_common = Column(Boolean, default=False)  # 是否为常用单位
    display_order = Column(Integer, default=0)  # 显示顺序

    # created_at, updated_at, created_by, updated_by, is_active 等审计字段从 AuditMixin 继承

    # 关系
    base_unit = relationship("Unit", remote_side=[id], backref="derived_units")
    conversions_from = relationship("UnitConversion", foreign_keys="UnitConversion.from_unit_id", back_populates="from_unit")
    conversions_to = relationship("UnitConversion", foreign_keys="UnitConversion.to_unit_id", back_populates="to_unit")


class UnitConversion(Base, AuditMixin):
    __tablename__ = "unit_conversions"

    id = Column(Integer, primary_key=True, index=True)
    from_unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)  # 源单位
    to_unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)  # 目标单位
    conversion_factor = Column(Numeric(15, 10), nullable=False)  # 转换因子
    formula = Column(String(200))  # 可选的转换公式
    is_bidirectional = Column(Boolean, default=True)  # 是否双向转换
    precision = Column(Integer, default=2)  # 精度

    # created_at, updated_at, created_by, updated_by, is_active 等审计字段从 AuditMixin 继承

    # 关系
    from_unit = relationship("Unit", foreign_keys=[from_unit_id], back_populates="conversions_from")
    to_unit = relationship("Unit", foreign_keys=[to_unit_id], back_populates="conversions_to")