from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.base_model import AuditMixin


class HierarchyRelationType(Enum):
    CONTAINS = "contains"          # 包含关系（父类包含子类）
    SUBSTITUTABLE = "substitutable" # 可替代关系（可以相互替代）
    FALLBACK = "fallback"          # 回退关系（找不到子类时可用父类替代）


class IngredientHierarchy(Base, AuditMixin):
    """食材层级关系模型"""

    __tablename__ = "ingredient_hierarchies"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    child_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    relation_type = Column(String(20), nullable=False)  # 关系类型
    strength = Column(Integer, default=50)  # 关系强度（0-100）

    # 关系
    parent = relationship("Ingredient", foreign_keys=[parent_id], back_populates="hierarchy_children")
    child = relationship("Ingredient", foreign_keys=[child_id], back_populates="hierarchy_parents")