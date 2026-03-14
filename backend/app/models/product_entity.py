from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class Product(Base, AuditMixin):
    """商品实体 - 代表可在商店购买的具体商品"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    brand = Column(String(100))
    barcode = Column(String(50), unique=True)
    image_url = Column(String(500))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    tags = Column(String(500))  # JSON 字符串存储标签列表

    # 自定义营养数据（可选，优先级高于食材的营养数据）
    # 格式同 NutritionData.nutrition_data
    custom_nutrition_data = Column(JSON, nullable=True)
    custom_nutrition_source = Column(String(50), default="custom")  # custom, ai_match

    # 关系
    ingredient = relationship("Ingredient", back_populates="products")
    price_records = relationship("ProductRecord", back_populates="product")
    barcodes = relationship("ProductBarcode", back_populates="product", cascade="all, delete-orphan", lazy="dynamic")

    @property
    def primary_barcode(self):
        """获取主条码"""
        from app.models.product_barcode import ProductBarcode
        primary = self.barcodes.filter(
            ProductBarcode.is_primary == True,
            ProductBarcode.is_active == True
        ).first()
        return primary.barcode if primary else None

    @property
    def all_barcodes(self):
        """获取所有活跃条码"""
        from app.models.product_barcode import ProductBarcode
        return [barcode.barcode for barcode in self.barcodes.filter(ProductBarcode.is_active == True).all()]
