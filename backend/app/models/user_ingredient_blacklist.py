from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class UserIngredientBlacklist(Base, AuditMixin):
    """用户原料黑名单"""
    __tablename__ = "user_ingredient_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    reason = Column(String(100), nullable=True)
    source = Column(String(50), default="manual", nullable=False)
    allergen_group_id = Column(Integer, ForeignKey("allergen_groups.id"), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'ingredient_id', name='uq_user_ingredient_blacklist'),
    )

    # 关系
    user = relationship("User", back_populates="ingredient_blacklist", foreign_keys=[user_id])
    ingredient = relationship("Ingredient")
    allergen_group = relationship("AllergenGroup", foreign_keys=[allergen_group_id])
