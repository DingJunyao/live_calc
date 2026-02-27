from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.base_model import AuditMixin


class IngredientDensity(Base, AuditMixin):
    __tablename__ = "ingredient_densities"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)  # 食材ID
    from_unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)  # 源单位ID（通常是体积单位）
    to_unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)  # 目标单位ID（通常是质量单位）
    density_value = Column(Numeric(10, 6), nullable=False)  # 密度值
    condition = Column(String(200))  # 条件描述，如"干燥"、"湿润"等
    confidence = Column(Numeric(3, 2), default=1.00)  # 数据可信度
    source = Column(String(200))  # 数据来源

    # created_at, updated_at, created_by, updated_by, is_active 等审计字段从 AuditMixin 继承

    # 关系
    ingredient = relationship("Ingredient", back_populates="densities")
    from_unit = relationship("Unit", foreign_keys=[from_unit_id])
    to_unit = relationship("Unit", foreign_keys=[to_unit_id])