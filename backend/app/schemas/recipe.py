from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime
from decimal import Decimal
from app.utils.datetime_utils import TimeZoneAwareModel


class CookingStep(BaseModel):
    step: Optional[int] = None
    content: str
    duration_minutes: Optional[float] = None
    tips: Optional[str] = None


class RecipeIngredientCreate(BaseModel):
    ingredient_name: str
    quantity: Optional[str] = None
    quantity_range: Optional[Union[dict, str]] = None  # JSON 或字符串
    unit_id: Optional[int] = None  # 单位ID（外键）
    is_optional: bool = False
    note: Optional[str] = None
    original_quantity: Optional[Union[dict, str]] = None  # JSON 或字符串


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
    description: Optional[str] = None
    images: Optional[List[str]] = None
    result_ingredient_id: Optional[int] = None


class RecipeResponse(TimeZoneAwareModel):
    id: int
    name: str
    source: str
    category: Optional[str]
    tags: Optional[List[str]]
    cooking_steps: Optional[List[CookingStep]]
    total_time_minutes: Optional[int]
    difficulty: Optional[str]
    servings: int
    tips: Optional[List[str]] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    result_ingredient_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime]
    # 添加成本相关字段，用于前端显示
    estimated_cost: Optional[Decimal] = None
    calories: Optional[int] = None
    protein: Optional[Decimal] = None
    sparkline_data: Optional[List[float]] = None  # 近90天每日平均成本，用于迷你图

    class Config:
        from_attributes = True


class RecipeIngredientUpdate(BaseModel):
    """菜谱原料更新模式 — 按 ingredient_name 匹配"""
    ingredient_name: str
    quantity: Optional[str] = None
    quantity_range: Optional[Union[dict, str]] = None
    unit_id: Optional[int] = None
    is_optional: bool = False
    note: Optional[str] = None
    original_quantity: Optional[Union[dict, str]] = None


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    cooking_steps: Optional[List[CookingStep]] = None
    total_time_minutes: Optional[int] = None
    difficulty: Optional[str] = None
    servings: Optional[int] = None
    tips: Optional[List[str]] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    ingredients: Optional[List[RecipeIngredientUpdate]] = None
    result_ingredient_id: Optional[int] = None


class RecipeIngredientDetail(BaseModel):
    id: int  # recipe_ingredient表的ID，用于区分相同的食材
    ingredient_id: int
    name: str
    quantity: Optional[str]
    quantity_range: Optional[Union[dict, str]]  # JSON 或字符串
    unit: Optional[str]
    is_optional: bool
    note: Optional[str]
    original_quantity: Optional[Union[dict, str]]  # JSON 或字符串
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
    # 添加完整的营养数据结构
    per_serving_nutrition: Optional[dict] = None  # core_nutrients, all_nutrients, nutrient_details
    total_nutrition: Optional[dict] = None  # 核心营养素的总量
    ingredient_details: Optional[list] = None  # 各食材的营养贡献详情（用于营养溯源模块）


class RecipeCostHistoryResponse(BaseModel):
    """菜谱成本历史记录响应"""
    id: int
    recipe_id: int
    recipe_name: str
    total_cost: int
    recorded_at: int
    exchange_rate: int


class RecipeCostRangeResponse(BaseModel):
    """菜谱成本区间响应模型"""
    id: int
    recipe_id: int
    recipe_name: str
    date: str  # 日期 (YYYY-MM-DD)
    min_cost: float  # 最小成本（元）
    max_cost: float  # 最大成本（元）
    avg_cost: float  # 平均成本（元）
    recorded_at: int  # Unix 时间戳（秒）


class MerchantCostItem(BaseModel):
    """按商家维度计算的菜谱成本项"""
    merchant_id: int
    merchant_name: str
    total_cost: Decimal
    covered_count: int
    total_ingredients: int
    missing_ingredients: List[str] = []
    is_recommended: bool = False


class RecipeMerchantCostResponse(BaseModel):
    """菜谱按商家成本估算响应"""
    currency: str = "CNY"
    merchants: List[MerchantCostItem]
