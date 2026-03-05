from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class UserPreferenceBase(BaseModel):
    ingredient_id: int
    default_product_id: Optional[int] = None
    default_recipe_id: Optional[int] = None
    preference_type: str = Field(default="product")
    is_favorite: bool = False

    @field_validator('preference_type')
    @classmethod
    def validate_preference_type(cls, v):
        if v not in ('product', 'recipe'):
            raise ValueError('preference_type must be either "product" or "recipe"')
        return v


class UserPreferenceCreate(UserPreferenceBase):
    pass


class UserPreferenceUpdate(BaseModel):
    ingredient_id: Optional[int] = None
    default_product_id: Optional[int] = None
    default_recipe_id: Optional[int] = None
    preference_type: Optional[str] = None
    is_favorite: Optional[bool] = None

    @field_validator('preference_type')
    @classmethod
    def validate_preference_type(cls, v):
        if v is not None and v not in ('product', 'recipe'):
            raise ValueError('preference_type must be either "product" or "recipe"')
        return v


class UserPreferenceResponse(UserPreferenceBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    model_config = {"from_attributes": True}
