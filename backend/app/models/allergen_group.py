from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class AllergenGroup(Base, AuditMixin):
    """过敏原分组（管理员维护）"""
    __tablename__ = "allergen_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # 关系
    group_ingredients = relationship("AllergenGroupIngredient", back_populates="group",
                                      lazy="selectin", order_by="AllergenGroupIngredient.id")


class AllergenGroupIngredient(Base, AuditMixin):
    """过敏原分组 - 原料映射"""
    __tablename__ = "allergen_group_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("allergen_groups.id"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    is_ai_matched = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('group_id', 'ingredient_id', name='uq_allergen_group_ingredient'),
    )

    # 关系
    group = relationship("AllergenGroup", back_populates="group_ingredients", foreign_keys=[group_id])
    ingredient = relationship("Ingredient")
