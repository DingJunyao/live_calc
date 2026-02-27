from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProductIngredientLink(Base):
    """商品与食材之间的映射关系，支持多对多关系和置信度"""
    __tablename__ = "product_ingredient_links"

    id = Column(Integer, primary_key=True, index=True)
    product_record_id = Column(Integer, ForeignKey("product_records.id"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"))

    # 匹配信息
    match_confidence = Column(Numeric(3, 2))  # 匹配置信度
    match_method = Column(String(50))  # 匹配方法：exact, fuzzy, manual等

    # 验证状态
    verified_by_user = Column(Boolean, default=False)
    verification_notes = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    product_record = relationship("ProductRecord")
    ingredient = relationship("Ingredient")