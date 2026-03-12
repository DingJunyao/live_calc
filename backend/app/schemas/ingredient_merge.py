from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class IngredientMergeRequest(BaseModel):
    """食材合并请求"""
    source_ingredient_ids: List[int]  # 源食材ID列表
    target_ingredient_id: int  # 目标食材ID


class IngredientMergeResponse(BaseModel):
    """食材合并响应"""
    success: bool
    message: str
    merged_count: Optional[int] = 0
    updated_recipes_count: Optional[int] = 0
    updated_products_count: Optional[int] = 0
    updated_mappings_count: Optional[int] = 0
    updated_hierarchies_count: Optional[int] = 0
    merged_nutrition_count: Optional[int] = 0
    stats_change: Optional[Dict[str, Any]] = None