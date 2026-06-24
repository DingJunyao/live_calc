"""
每日饮食推荐 - 请求/响应 Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class NutritionGoals(BaseModel):
    """营养目标"""
    daily_calorie_target: Optional[float] = 2000
    daily_protein_target: Optional[float] = 60
    daily_carb_target: Optional[float] = 300
    daily_fat_target: Optional[float] = 65
    daily_budget: Optional[float] = None


class RecipeBrief(BaseModel):
    """推荐中的菜谱简要信息"""
    id: int
    name: str
    category: Optional[str] = None
    images: Optional[List[str]] = None
    servings: int = 1
    cost_estimate: Optional[float] = None
    nutrition_per_serving: Optional[dict] = None

    class Config:
        from_attributes = True


class MealRecommendationItem(BaseModel):
    """单餐推荐"""
    meal_type: str
    recipe: Optional[RecipeBrief] = None
    is_current_meal: bool = False


class DailyTotals(BaseModel):
    """当日汇总"""
    cost: Optional[float] = None
    calories: Optional[float] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    refresh_counts: Optional[dict] = None


class MealRecommendationsResponse(BaseModel):
    """完整推荐响应"""
    date: str
    recommendations: List[MealRecommendationItem]
    totals: Optional[DailyTotals] = None


class RefreshMealRequest(BaseModel):
    """刷新某一餐请求"""
    meal_type: str = Field(..., pattern="^(breakfast|lunch|dinner)$")
