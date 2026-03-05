from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class ProductIngredientLink(Base, AuditMixin):
    """商品与食材之间的映射关系"""
    __tablename__ = "product_ingredient_links"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)

    # created_at, updated_at, created_by, updated_by, is_active 从 AuditMixin 继承

    # 关系
    product = relationship("Product")
    ingredient = relationship("Ingredient", back_populates="product_links")
