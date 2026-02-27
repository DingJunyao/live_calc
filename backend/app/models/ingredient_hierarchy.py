from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.base_model import AuditMixin


class IngredientHierarchy(Base, AuditMixin):
    __tablename__ = "ingredient_hierarchy"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("ingredients.id"))  # 父级食材
    child_id = Column(Integer, ForeignKey("ingredients.id"))   # 子级食材
    relationship_type = Column(String(20))  # 包含关系、替代关系等
    confidence = Column(Numeric(3, 2), default=1.00)  # 关系置信度

    # created_at, updated_at, created_by, updated_by, is_active 等审计字段从 AuditMixin 继承

    # 关系 - 使用字符串格式以避免循环引用
    parent = relationship("Ingredient", foreign_keys="IngredientHierarchy.parent_id", back_populates="hierarchy_children")
    child = relationship("Ingredient", foreign_keys="IngredientHierarchy.child_id", back_populates="hierarchy_parents")