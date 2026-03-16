from pydantic import BaseModel
from decimal import Decimal
from typing import Optional, List
from datetime import datetime


class IngredientResponse(BaseModel):
    """原料响应模型（仅包含必要字段，避免序列化 Unit 对象）"""
    id: int
    name: str
    aliases: Optional[List[str]]
    default_unit_id: Optional[int] = None
    default_unit_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]

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


# 导入合并相关的模型
from .ingredient_merge import IngredientMergeRequest, IngredientMergeResponse


# ==================== 营养编辑 Schema ====================

class NutrientItem(BaseModel):
    """营养素项"""
    name: str  # 营养素名称，如"能量"、"蛋白质"
    value: float  # 营养素值
    unit: str  # 单位，如"kcal"、"g"、"mg"
    key: Optional[str] = None  # USDA 营养素 key（可选）


class NutritionEditRequest(BaseModel):
    """营养数据编辑请求"""
    base_quantity: float = 100.0  # 基准数量，默认 100g
    base_unit: str = "g"  # 基准单位
    nutrients: List[NutrientItem]  # 营养素列表
    source: str = "custom"  # 数据源：custom/usda/ai_match


class NutritionEditResponse(BaseModel):
    """营养编辑响应"""
    success: bool
    message: str
    ingredient_id: Optional[int] = None
    product_id: Optional[int] = None
