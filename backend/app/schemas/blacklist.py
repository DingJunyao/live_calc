from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BlacklistCreate(BaseModel):
    ingredient_id: int
    reason: Optional[str] = None


class BlacklistBatchCreate(BaseModel):
    ingredient_ids: List[int]
    reason: Optional[str] = None
    allergen_group_id: Optional[int] = None


class BlacklistBatchDelete(BaseModel):
    ingredient_ids: List[int]


class BlacklistResponse(BaseModel):
    id: int
    user_id: int
    ingredient_id: int
    ingredient_name: Optional[str] = None
    reason: Optional[str] = None
    source: str
    allergen_group_id: Optional[int] = None
    allergen_group_name: Optional[str] = None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class BlacklistIngredientIdsResponse(BaseModel):
    ingredient_ids: List[int]
