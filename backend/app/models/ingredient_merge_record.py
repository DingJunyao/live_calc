from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.base_model import AuditMixin


class IngredientMergeRecord(Base, AuditMixin):
    """食材合并记录模型，用于记录食材合并的历史信息"""

    __tablename__ = "ingredient_merge_records"

    id = Column(Integer, primary_key=True, index=True)
    source_ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    target_ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    merged_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 关联关系
    source_ingredient = relationship("Ingredient", foreign_keys=[source_ingredient_id])
    target_ingredient = relationship("Ingredient", foreign_keys=[target_ingredient_id])
    merged_by_user = relationship("User", foreign_keys=[merged_by_user_id])