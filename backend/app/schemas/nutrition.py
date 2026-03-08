from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List
from datetime import datetime


class IngredientResponse(BaseModel):
    """原料响应模型（仅包含必要字段，避免序列化 Unit 对象）"""
    id: int
    name: str
    aliases: Optional[List[str]]
    created_at: datetime

    class Config:
        from_attributes = True


class NutritionDataResponse(BaseModel):
    id: int
    usda_id: str
    name_en: str
    name_zh: Optional[str]
    calories: Optional[Decimal]
    protein: Optional[Decimal]
    fat: Optional[Decimal]
    carbs: Optional[Decimal]
    fiber: Optional[Decimal]
    sugar: Optional[Decimal]
    sodium: Optional[Decimal]

    class Config:
        from_attributes = True


class IngredientMatch(BaseModel):
    nutrition_id: int
    name_en: str
    name_zh: Optional[str]
    confidence: Decimal


class NutritionMatchResponse(BaseModel):
    matches: List[IngredientMatch]


class NutritionCorrectRequest(BaseModel):
    ingredient_name: str
    nutrition_id: int
