from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.base_model import AuditMixin


class NutrientStatus(Enum):
    MEASURED = "measured"      # 已测量实际值
    TRACE = "trace"           # 痕量
    ZERO = "zero"             # 零值
    NOT_TESTED = "not_tested"  # 未测试
    ESTIMATED = "estimated"    # 估算值


class Ingredient(Base, AuditMixin):
    """食材模型"""
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("ingredient_categories.id"))
    density = Column(Numeric(10, 6))  # 密度值（g/mL 或 kg/L），用于体积重量换算
    default_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, index=True)

    # 别名列表，如 ["土豆", "马铃薯", "洋芋"]
    aliases = Column(JSON)

    nutrition_id = Column(Integer, ForeignKey("nutrition_data.id"))

    # 每个单位的标准重量（如1个鸡蛋=50g），用于计数单位到质量单位的转换
    piece_weight = Column(Numeric(10, 3), nullable=True)
    piece_weight_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)

    # 是否为导入菜谱时顺带导入的原料
    is_imported = Column(Boolean, default=False, nullable=False)

    # 关系
    category_obj = relationship("IngredientCategory", back_populates="ingredients")
    nutrition_data = relationship("NutritionData", foreign_keys=[nutrition_id])
    densities = relationship("IngredientDensity", back_populates="ingredient")
    nutrition_mappings = relationship("IngredientNutritionMapping", back_populates="ingredient")
    hierarchy_children = relationship("IngredientHierarchy", foreign_keys="IngredientHierarchy.parent_id", back_populates="parent")
    hierarchy_parents = relationship("IngredientHierarchy", foreign_keys="IngredientHierarchy.child_id", back_populates="child")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")
    products = relationship("Product", back_populates="ingredient", lazy="select")
    product_links = relationship("ProductIngredientLink", back_populates="ingredient", lazy="select")
    default_unit = relationship("Unit", lazy="select", foreign_keys=[default_unit_id])
    piece_weight_unit = relationship("Unit", lazy="select", foreign_keys=[piece_weight_unit_id])


class IngredientNutritionMapping(Base, AuditMixin):
    """食材与营养数据的映射关系"""
    __tablename__ = "ingredient_nutrition_mapping"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    nutrition_id = Column(Integer, ForeignKey("nutrition_data.id"), nullable=False, index=True)
    priority = Column(Integer, default=0)
    confidence = Column(Numeric(3, 2), default=1.00)

    # 关系
    ingredient = relationship("Ingredient", back_populates="nutrition_mappings")
    nutrition_data = relationship("NutritionData")
