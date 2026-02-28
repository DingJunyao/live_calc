from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Recipe(Base):
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="recipes")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    quantity = Column(String(50))  # 改为可空，允许没有数量的原料
    unit = Column(String(20))

    # 关系
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient = relationship("app.models.nutrition.Ingredient", back_populates="recipe_ingredients", lazy="select")
