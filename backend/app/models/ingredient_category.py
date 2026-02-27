from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.base_model import AuditMixin


class IngredientCategory(Base, AuditMixin):
    __tablename__ = "ingredient_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # 类别名称，如"谷物"
    display_name = Column(String(100), nullable=False)  # 显示名称
    parent_category_id = Column(Integer, ForeignKey("ingredient_categories.id"))  # 父类别ID，用于分级
    sort_order = Column(Integer, default=0)  # 排序
    description = Column(Text)  # 描述

    # created_at, updated_at, created_by, updated_by, is_active 等审计字段从 AuditMixin 继承

    # 层级关系
    parent = relationship("IngredientCategory", remote_side=[id], backref="children")
    ingredients = relationship("Ingredient", back_populates="category_obj")