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


class NutritionData(Base, AuditMixin):
    __tablename__ = "nutrition_data"

    id = Column(Integer, primary_key=True, index=True)
    usda_id = Column(String(50), unique=True, index=True)
    name_en = Column(String(200), nullable=False)
    name_zh = Column(String(200))

    # 营养素值存储为JSON，包含值、测量状态和单位
    nutrients = Column(JSON)  # 例如: {"calories": {"value": 365, "status": "measured", "unit": "kcal/100g"}, "protein": {"value": 12.6, "status": "trace", "unit": "g/100g"}, "fiber": {"value": 0, "status": "zero", "unit": "g/100g"}, "vitamin_c": {"value": null, "status": "not_tested", "unit": "mg/100g"}}

    # 标准营养素字段（保留向后兼容性）
    calories = Column(Numeric(10, 2))
    protein = Column(Numeric(10, 2))
    fat = Column(Numeric(10, 2))
    carbs = Column(Numeric(10, 2))
    fiber = Column(Numeric(10, 2))
    sugar = Column(Numeric(10, 2))
    sodium = Column(Numeric(10, 2))

    serving_size = Column(String(50))  # 标准份量描述
    density = Column(Numeric(10, 6))  # 密度值，用于体积重量换算

    # created_at, updated_at, created_by, updated_by, is_active 等审计字段从 AuditMixin 继承


class Ingredient(Base, AuditMixin):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("ingredient_categories.id"))  # 食材类别ID
    density = Column(Numeric(10, 6))  # 密度值（g/mL 或 kg/L），用于体积重量换算
    default_unit = Column(String(20))  # 默认单位

    # 别名列表，如 ["土豆", "马铃薯", "洋芋"]
    aliases = Column(JSON)

    nutrition_id = Column(Integer, ForeignKey("nutrition_data.id"))

    # 是否为导入菜谱时顺带导入的原料
    is_imported = Column(Boolean, default=False, nullable=False)

    # created_at, updated_at, created_by, updated_by, is_active 等审计字段从 AuditMixin 继承

    # 关系
    category_obj = relationship("IngredientCategory", back_populates="ingredients")
    nutrition_data = relationship("NutritionData")
    densities = relationship("IngredientDensity", back_populates="ingredient")
    nutrition_mappings = relationship("IngredientNutritionMapping", back_populates="ingredient")
    hierarchy_children = relationship("IngredientHierarchy", foreign_keys="IngredientHierarchy.parent_id", back_populates="parent")
    hierarchy_parents = relationship("IngredientHierarchy", foreign_keys="IngredientHierarchy.child_id", back_populates="child")
    recipe_ingredients = relationship("RecipeIngredient", back_populates="ingredient")  # 添加反向关系
    products = relationship("Product", back_populates="ingredient", lazy="select")
    product_links = relationship("ProductIngredientLink", back_populates="ingredient", lazy="select")


class IngredientNutritionMapping(Base, AuditMixin):
    __tablename__ = "ingredient_nutrition_mapping"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    nutrition_id = Column(Integer, ForeignKey("nutrition_data.id"), nullable=False, index=True)
    priority = Column(Integer, default=0)
    confidence = Column(Numeric(3, 2), default=1.00)

    # created_at, updated_at, created_by, updated_by, is_active 等审计字段从 AuditMixin 继承

    # 关系
    ingredient = relationship("Ingredient", back_populates="nutrition_mappings")
    nutrition_data = relationship("NutritionData")
