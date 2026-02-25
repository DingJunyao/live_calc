from sqlalchemy import Column, Integer, String, DateTime, Decimal, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class NutritionData(Base):
    __tablename__ = "nutrition_data"

    id = Column(Integer, primary_key=True, index=True)
    usda_id = Column(String(50), unique=True, index=True)
    name_en = Column(String(200), nullable=False)
    name_zh = Column(String(200))
    calories = Column(Decimal(10, 2))
    protein = Column(Decimal(10, 2))
    fat = Column(Decimal(10, 2))
    carbs = Column(Decimal(10, 2))
    fiber = Column(Decimal(10, 2))
    sugar = Column(Decimal(10, 2))
    sodium = Column(Decimal(10, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    nutrition_id = Column(Integer, ForeignKey("nutrition_data.id"))
    aliases = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IngredientNutritionMapping(Base):
    __tablename__ = "ingredient_nutrition_mapping"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    nutrition_id = Column(Integer, ForeignKey("nutrition_data.id"), nullable=False, index=True)
    priority = Column(Integer, default=0)
    confidence = Column(Decimal(3, 2), default=1.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
