import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Index
from sqlalchemy.sql import func
from app.core.database import Base


class EntityDensity(Base):
    """实体密度表，用于记录特定原料或商品的密度数据（kg/m³）。

    is_active 软删：delete 提议软删，revert 复活。
    原唯一约束 uq_entity_density 已拆为普通复合索引。
    """
    __tablename__ = "entity_densities"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(20), nullable=False)  # 'ingredient' 或 'product'
    entity_id = Column(Integer, nullable=False)
    density = Column(Numeric(10, 6), nullable=False)  # 密度（kg/m³，SI 基准）
    temperature = Column(Numeric(5, 2))  # 参考温度（℃）
    condition = Column(String(100))  # 状态描述，如"切碎"、"压碎"等
    source = Column(String(200))  # 数据来源
    confidence = Column(Numeric(3, 2), default=1.0)  # 数据可信度
    is_active = Column(Boolean, default=True, nullable=False, index=True,
                       server_default=sa.text("true"))  # 软删标记（true/false 跨库兼容）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_entity_density_active", "entity_type", "entity_id", "condition"),
    )
