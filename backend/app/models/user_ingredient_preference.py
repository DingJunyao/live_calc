from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class UserIngredientPreference(Base, AuditMixin):
    """用户对食材的默认选择偏好设置"""
    __tablename__ = "user_ingredient_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    default_product_id = Column(Integer, ForeignKey("products.id"))
    default_recipe_id = Column(Integer, ForeignKey("recipes.id"))
    preference_type = Column(String(20), default="product")
    is_favorite = Column(Boolean, default=False)

    # 唯一约束
    __table_args__ = (
        UniqueConstraint('user_id', 'ingredient_id', name='unique_user_ingredient'),
    )

    # 关系
    user = relationship("User")
    ingredient = relationship("Ingredient")
    default_product = relationship("Product")
    default_recipe = relationship("Recipe")
