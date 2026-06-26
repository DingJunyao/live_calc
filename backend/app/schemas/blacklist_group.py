"""原料黑名单分组 Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BlacklistGroupIngredientCreate(BaseModel):
    ingredient_ids: List[int]


class BlacklistGroupCreate(BaseModel):
    name: str = Field(..., max_length=50)
    display_order: int = 0


class BlacklistGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class BlacklistGroupIngredientResponse(BaseModel):
    id: int
    ingredient_id: int
    ingredient_name: Optional[str] = None
    is_ai_matched: bool

    class Config:
        from_attributes = True


class BlacklistGroupResponse(BaseModel):
    id: int
    name: str
    display_order: int
    is_active: bool
    ingredients: List[BlacklistGroupIngredientResponse] = []
    ingredient_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class BlacklistGroupPublicResponse(BaseModel):
    """公开只读：给用户端快速选择用"""
    id: int
    name: str
    ingredient_ids: List[int]
    ingredient_names: List[str]
