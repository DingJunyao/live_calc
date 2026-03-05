from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserPreferenceBase(BaseModel):
    ingredient_id: int
    default_product_id: Optional[int] = None
    default_recipe_id: Optional[int] = None
    preference_type: str = Field(default="product", pattern="^(product|recipe)$")
    is_favorite: bool = False


class UserPreferenceCreate(UserPreferenceBase):
    pass


class UserPreferenceUpdate(BaseModel):
    ingredient_id: Optional[int] = None
    default_product_id: Optional[int] = None
    default_recipe_id: Optional[int] = None
    preference_type: Optional[str] = Field(None, pattern="^(product|recipe)$")
    is_favorite: Optional[bool] = None


class UserPreferenceResponse(UserPreferenceBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True
