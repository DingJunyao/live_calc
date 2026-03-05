from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class UserIngredientPreference(Base, AuditMixin):
    """用户对食材的默认选择偏好设置"""
    __tablename__ = "user_ingredient_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    default_product_id = Column(Integer, ForeignKey("products.id"), index=True)
    default_recipe_id = Column(Integer, ForeignKey("recipes.id"), index=True)
    preference_type = Column(String(20), default="product", nullable=False)
    is_favorite = Column(Boolean, default=False, index=True)

    # 唯一约束和一致性检查
    __table_args__ = (
        UniqueConstraint('user_id', 'ingredient_id', name='unique_user_ingredient'),
        CheckConstraint(
            "(preference_type = 'product' AND default_product_id IS NOT NULL) OR "
            "(preference_type = 'recipe' AND default_recipe_id IS NOT NULL)",
            name='check_preference_consistency'
        ),
        Index('ix_user_ingredient_preferences_user_favorite', 'user_id', 'is_favorite'),
        Index('ix_user_ingredient_preferences_user_type', 'user_id', 'preference_type'),
    )

    # 关系
    user = relationship("User", back_populates="ingredient_preferences", foreign_keys="UserIngredientPreference.user_id")
    ingredient = relationship("Ingredient")
    default_product = relationship("Product")
    default_recipe = relationship("Recipe")
