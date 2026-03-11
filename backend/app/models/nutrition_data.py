"""
营养数据相关模型

适配 HowToCook_json/out/nutritions.json 数据格式
"""

from sqlalchemy import Column, Integer, String, Float, JSON, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class NutritionData(Base):
    """
    营养数据模型

    存储食材的营养信息，支持多种数据源（USDA、自定义、AI 匹配等）

    数据来源:
    - usda_import: 从 HowToCook_json/out/nutritions.json 导入的 USDA 数据
    - custom: 用户自定义的营养数据
    - ai_match: AI 智能匹配的营养数据
    """
    __tablename__ = "nutrition_data"

    id = Column(Integer, primary_key=True, index=True)

    # 关联食材
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    ingredient = relationship("Ingredient", back_populates="nutrition_data", foreign_keys=[ingredient_id])

    # 数据源标识
    source = Column(String(50), nullable=False, index=True)  # usda_import, custom, ai_match

    # USDA 数据源字段（从 nutritions.json 导入）
    usda_id = Column(String(50), nullable=True)  # USDA 数据库 ID
    usda_name = Column(String(255), nullable=True)  # USDA 原始英文名称

    # 营养数据（JSON 格式）
    # {
    #   "core_nutrients": {
    #     "能量": {"value": 70.0, "unit": "kcal", "nrp_pct": 0.84, "standard": "中国GB标准", "key": "energy_kcal"},
    #     "蛋白质": {"value": 1.21, "unit": "g", "nrp_pct": 2.02, "standard": "中国GB标准", "key": "protein"},
    #     ...
    #   },
    #   "all_nutrients": {
    #     "energy_kcal": {"value": 70.0, "unit": "kcal", "nrp_pct": 0.84, "standard": "中国GB标准"},
    #     "protein": {"value": 1.21, "unit": "g", "nrp_pct": 2.02, "standard": "中国GB标准"},
    #     ...
    #   },
    #   "nutrient_details": {
    #     "energy_kcal": {"value": 70.0, "unit": "kcal", "nrp_pct": 0.84, "standard": "中国GB标准", "note": "..."},
    #     ...
    #   }
    # }
    nutrients = Column(JSON, nullable=False)

    # 参考基准（默认为每100g）
    reference_amount = Column(Float, default=100.0, nullable=False)
    reference_unit = Column(String(10), default="g", nullable=False)

    # 匹配置信度（0.0-1.0）
    match_confidence = Column(Float, default=1.0, nullable=False)

    # 验证状态
    is_verified = Column(Boolean, default=False, nullable=False)

    # 元数据
    extra_data = Column(JSON, nullable=True)  # 存储额外的元信息

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<NutritionData(ingredient_id={self.ingredient_id}, source={self.source})>"


class AIIngredientMatch(Base):
    """
    AI 匹配记录模型

    记录 AI 匹配的详细信息，用于追踪和审计
    """
    __tablename__ = "ai_ingredient_matches"

    id = Column(Integer, primary_key=True, index=True)

    # 关联食材
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    ingredient = relationship("Ingredient")

    # 数据源信息
    source = Column(String(50), nullable=False, index=True)  # usda, manual, ai
    source_name = Column(String(255), nullable=True)  # 数据源中的名称
    source_id = Column(String(100), nullable=True)  # 数据源 ID

    # 匹配信息
    match_method = Column(String(50), nullable=False)  # exact_name, fuzzy, semantic, manual
    confidence = Column(Float, nullable=False, index=True)  # 匹配置信度 0.0-1.0

    # 原始营养数据（保存匹配时的数据快照）
    nutrition_data = Column(JSON, nullable=True)

    # 验证信息
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # 审计信息
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<AIIngredientMatch(ingredient_id={self.ingredient_id}, source={self.source}, confidence={self.confidence})>"


class NutritionEditHistory(Base):
    """
    营养数据编辑历史模型

    记录营养数据的修改历史，支持版本控制和审计
    """
    __tablename__ = "nutrition_edit_history"

    id = Column(Integer, primary_key=True, index=True)

    # 关联营养数据
    nutrition_data_id = Column(Integer, ForeignKey("nutrition_data.id"), nullable=False, index=True)

    # 关联食材
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)

    # 修改类型
    edit_type = Column(String(50), nullable=False)  # create, update, override, restore

    # 修改前后的数据
    before_data = Column(JSON, nullable=True)
    after_data = Column(JSON, nullable=True)

    # 修改原因
    reason = Column(Text, nullable=True)

    # 操作者
    edited_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 时间戳
    edited_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<NutritionEditHistory(id={self.id}, edit_type={self.edit_type}, ingredient_id={self.ingredient_id})>"


class NRVStandard(Base):
    """
    营养素参考值（NRV）标准

    存储不同国家/组织的营养素参考值标准
    """
    __tablename__ = "nrv_standards"

    id = Column(Integer, primary_key=True, index=True)

    # 营养素标识
    nutrient_key = Column(String(100), nullable=False, index=True)  # energy_kcal, protein, fat, etc.
    nutrient_name = Column(String(100), nullable=False)  # 显示名称：能量、蛋白质、脂肪

    # 标准值
    standard_value = Column(Float, nullable=False)  # 标准参考值
    unit = Column(String(10), nullable=False)  # 单位

    # 标准来源
    standard_source = Column(String(50), nullable=False, index=True)  # 中国GB标准, 美国FDA标准, etc.

    # 适用人群
    target_group = Column(String(50), nullable=False, default="adult")  # adult, children, pregnant, etc.

    # 描述
    description = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<NRVStandard(nutrient={self.nutrient_name}, source={self.standard_source}, value={self.standard_value}{self.unit})>"
