from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class CookingStep(BaseModel):
    step: int
    content: str
    duration_minutes: Optional[int] = None


class RecipeIngredientCreate(BaseModel):
    ingredient_name: str
    quantity: Optional[str] = None
    unit: Optional[str] = None


class RecipeCreate(BaseModel):
    name: str = Field(..., max_length=200)
    source: str = "custom"
    category: Optional[str] = None  # 菜谱分类
    tags: Optional[List[str]] = []
    cooking_steps: List[CookingStep]
    ingredients: List[RecipeIngredientCreate]
    total_time_minutes: Optional[int] = None
    difficulty: Optional[str] = "simple"
    servings: int = 1
    tips: Optional[List[str]] = None


class RecipeResponse(BaseModel):
    id: int
    name: str
    source: str
    category: Optional[str]
    tags: Optional[List[str]]
    cooking_steps: Optional[List[CookingStep]]
    total_time_minutes: Optional[int]
    difficulty: Optional[str]
    servings: int
    tips: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RecipeIngredientDetail(BaseModel):
    ingredient_id: int
    name: str
    quantity: Optional[str]
    unit: Optional[str]
    nutrition_info: Optional[dict]


class RecipeDetailResponse(RecipeResponse):
    ingredients: List[RecipeIngredientDetail]


class RecipeCostResponse(BaseModel):
    total_cost: Decimal
    currency: str
    cost_per_serving: Decimal
    cost_breakdown: List[dict]


class RecipeNutritionResponse(BaseModel):
    total_calories: Optional[Decimal]
    total_protein: Optional[Decimal]
    total_fat: Optional[Decimal]
    total_carbs: Optional[Decimal]
    per_serving: dict
