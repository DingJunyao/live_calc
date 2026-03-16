from sqlalchemy import Column, Integer, String, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.base_model import AuditMixin


class Recipe(Base, AuditMixin):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    source = Column(String(100))
    user_id = Column(Integer, ForeignKey("users.id"))
    category = Column(String(50))  # 菜谱分类：荤菜、素菜、水产、主食、汤与粥、早餐、甜品、调料、半成品、小食
    tags = Column(JSON)
    cooking_steps = Column(JSON)
    total_time_minutes = Column(Integer)
    difficulty = Column(String(20))
    servings = Column(Integer, default=1)
    tips = Column(JSON)
    images = Column(JSON, default=list)  # 菜谱图片路径列表
    # created_at, updated_at, created_by, updated_by, is_active 从 AuditMixin 继承

    # 新增：成品对应食材
    result_ingredient_id = Column(Integer, ForeignKey("ingredients.id"))

    # 关系
    user = relationship("User", back_populates="recipes", foreign_keys="Recipe.user_id")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    result_ingredient = relationship("Ingredient", foreign_keys=[result_ingredient_id], lazy="select")
    cost_history = relationship("RecipeCostHistory", back_populates="recipe")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    quantity = Column(String(50))  # 改为可空，允许没有数量的原料
    quantity_range = Column(JSON)  # 数量范围（JSON，如 {"min": 80, "max": 120}）
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, index=True)  # 单位外键
    is_optional = Column(Boolean, default=False)  # 是否可选
    note = Column(Text)  # 备注信息
    original_quantity = Column(JSON)  # 原始数量描述（JSON，如 {"min": 100, "max": 150}）

    # 关系
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("app.models.nutrition.Ingredient", back_populates="recipe_ingredients", lazy="select")
    unit = relationship("Unit", lazy="select")


class RecipeCostHistory(Base, AuditMixin):
    """菜谱成本历史记录"""
    __tablename__ = "recipe_cost_history"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, index=True)
    total_cost = Column(Integer, nullable=False)  # 总成本（分）
    recorded_at = Column(Integer, nullable=False)  # 记录时间戳（秒）
    exchange_rate = Column(Integer, default=100)  # 汇率（100表示无汇率转换）

    # 关系
    recipe = relationship("Recipe", back_populates="cost_history")
