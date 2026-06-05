from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class EntityUnitOverride(Base):
    """实体单位覆盖表，用于记录特定原料或商品的自定义单位换算"""
    __tablename__ = "entity_unit_overrides"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(20), nullable=False)  # 'ingredient' 或 'product'
    entity_id = Column(Integer, nullable=False)
    unit_name = Column(String(50), nullable=False)  # 如 "盒(12个)"、"根"
    base_unit_id = Column(Integer, ForeignKey("units.id"))  # 指向基础单位（如 "个"）
    conversion_factor = Column(Numeric(15, 10))  # 换算系数，如 12（一盒12个）
    weight_per_unit = Column(Numeric(10, 3))  # 单位重量，如 55（一个55g）
    weight_unit_id = Column(Integer, ForeignKey("units.id"))  # 指向质量单位
    is_default = Column(Boolean, default=False)  # 是否为该实体的默认单位
    source = Column(String(20), default="manual")  # 来源：import(导入自动创建) / manual(手动维护)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "unit_name", name="uq_entity_unit"),
    )

    # 关系
    base_unit = relationship("Unit", foreign_keys=[base_unit_id])
    weight_unit = relationship("Unit", foreign_keys=[weight_unit_id])
