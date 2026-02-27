# 食品数据结构设计文档

## 1. 概述

本文档描述了生活成本计算器中食品相关数据的完整结构设计，包括食材、商品、食谱、单位系统、营养信息及其相互关系。该设计考虑了国际化支持、单位换算、密度转换以及复杂的食物层级关系。

## 2. 数据模型设计

### 2.1 食材类别表 (IngredientCategory)
```python
class IngredientCategory(Base):
    __tablename__ = "ingredient_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # 类别名称，如"谷物"
    display_name = Column(String(100), nullable=False)  # 显示名称
    parent_category_id = Column(Integer, ForeignKey("ingredient_categories.id"))  # 父类别ID，用于分级
    sort_order = Column(Integer, default=0)  # 排序
    description = Column(Text)  # 描述
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parent = relationship("IngredientCategory", remote_side=[id], backref="children")
    ingredients = relationship("Ingredient", back_populates="category_obj")
```

### 2.2 食材表 (Ingredient)
```python
class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)  # 标准名称
    category_id = Column(Integer, ForeignKey("ingredient_categories.id"))  # 食材类别ID
    density = Column(Numeric(10, 6))  # 密度值（g/mL 或 kg/L），用于体积重量换算
    default_unit = Column(String(20))  # 默认单位

    # 统一的名称变体，包含别名和地区叫法
    name_variants = Column(JSON)  # 包含别名、地区叫法、规格等

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category_obj = relationship("IngredientCategory", back_populates="ingredients")
    densities = relationship("IngredientDensity", back_populates="ingredient")
    nutrition_mappings = relationship("IngredientNutritionMapping", back_populates="ingredient")
```

### 2.3 营养数据表 (NutritionData)
```python
class NutritionData(Base):
    __tablename__ = "nutrition_data"

    id = Column(Integer, primary_key=True, index=True)
    usda_id = Column(String(50), unique=True, index=True)
    name_en = Column(String(200), nullable=False)
    name_zh = Column(String(200))

    # 营养素值存储为JSON，包含值、测量状态和单位
    nutrients = Column(JSON)  # 包含各种营养素及其状态信息

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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 2.4 单位表 (Unit)
```python
class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # 单位名称，如"g", "kg", "cup"
    abbreviation = Column(String(20), unique=True, nullable=False)  # 缩写
    plural_form = Column(String(50))  # 复数形式
    unit_type = Column(String(50), nullable=False)  # 类型，如"mass"（质量）, "volume"（体积）
    base_unit_id = Column(Integer, ForeignKey("units.id"))  # 基础单位ID，用于派生单位
    si_factor = Column(Numeric(15, 10), default=1.0)  # 转换为国际单位制的因子
    is_si_base = Column(Boolean, default=False)  # 是否是国际单位制基本单位
    is_common = Column(Boolean, default=False)  # 是否为常用单位
    display_order = Column(Integer, default=0)  # 显示顺序

    base_unit = relationship("Unit", remote_side=[id], backref="derived_units")
    conversions_from = relationship("UnitConversion", foreign_keys="UnitConversion.from_unit_id", back_populates="from_unit")
    conversions_to = relationship("UnitConversion", foreign_keys="UnitConversion.to_unit_id", back_populates="to_unit")
```

### 2.5 单位转换表 (UnitConversion)
```python
class UnitConversion(Base):
    __tablename__ = "unit_conversions"

    id = Column(Integer, primary_key=True, index=True)
    from_unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)  # 源单位
    to_unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)  # 目标单位
    conversion_factor = Column(Numeric(15, 10), nullable=False)  # 转换因子
    formula = Column(String(200))  # 可选的转换公式
    is_bidirectional = Column(Boolean, default=True)  # 是否双向转换
    precision = Column(Integer, default=2)  # 精度
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    from_unit = relationship("Unit", foreign_keys=[from_unit_id], back_populates="conversions_from")
    to_unit = relationship("Unit", foreign_keys=[to_unit_id], back_populates="conversions_to")
```

### 2.6 地区单位配置表 (RegionUnitSetting)
```python
class RegionUnitSetting(Base):
    __tablename__ = "region_unit_settings"

    id = Column(Integer, primary_key=True, index=True)
    region_code = Column(String(10), unique=True, nullable=False)  # 地区代码，如"CN"、"US"
    region_name = Column(String(100), nullable=False)  # 地区名称
    default_mass_unit = Column(Integer, ForeignKey("units.id"))  # 默认质量单位ID
    default_volume_unit = Column(Integer, ForeignKey("units.id"))  # 默认体积单位ID
    default_length_unit = Column(Integer, ForeignKey("units.id"))  # 默认长度单位ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 2.7 用户单位偏好表 (UserUnitPreference)
```python
class UserUnitPreference(Base):
    __tablename__ = "user_unit_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)  # 用户ID
    preferred_mass_unit = Column(Integer, ForeignKey("units.id"))  # 首选质量单位
    preferred_volume_unit = Column(Integer, ForeignKey("units.id"))  # 首选体积单位
    preferred_length_unit = Column(Integer, ForeignKey("units.id"))  # 首选长度单位
    temperature_unit = Column(String(10), default="celsius")  # 温度单位（摄氏/华氏）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 2.8 食材密度表 (IngredientDensity)
```python
class IngredientDensity(Base):
    __tablename__ = "ingredient_densities"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)  # 食材ID
    from_unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)  # 源单位ID（通常是体积单位）
    to_unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)  # 目标单位ID（通常是质量单位）
    density_value = Column(Numeric(10, 6), nullable=False)  # 密度值
    condition = Column(String(200))  # 条件描述，如"干燥"、"湿润"等
    confidence = Column(Numeric(3, 2), default=1.00)  # 数据可信度
    source = Column(String(200))  # 数据来源
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ingredient = relationship("Ingredient", back_populates="densities")
    from_unit = relationship("Unit", foreign_keys=[from_unit_id])
    to_unit = relationship("Unit", foreign_keys=[to_unit_id])
```

### 2.9 食材营养映射表 (IngredientNutritionMapping)
```python
class IngredientNutritionMapping(Base):
    __tablename__ = "ingredient_nutrition_mapping"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False, index=True)
    nutrition_id = Column(Integer, ForeignKey("nutrition_data.id"), nullable=False, index=True)
    priority = Column(Integer, default=0)
    confidence = Column(Numeric(3, 2), default=1.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ingredient = relationship("Ingredient", back_populates="nutrition_mappings")
    nutrition_data = relationship("NutritionData")
```

### 2.10 食材层级关系表 (IngredientHierarchy)
```python
class IngredientHierarchy(Base):
    __tablename__ = "ingredient_hierarchy"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("ingredients.id"))  # 父级食材
    child_id = Column(Integer, ForeignKey("ingredients.id"))   # 子级食材
    relationship_type = Column(String(20))  # 包含关系、替代关系等
    confidence = Column(Numeric(3, 2), default=1.00)  # 关系置信度

    parent = relationship("Ingredient", foreign_keys=[parent_id])
    child = relationship("Ingredient", foreign_keys=[child_id])
```

### 2.11 商品食材链接表 (ProductIngredientLink)
```python
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
```

## 3. 服务层设计

### 3.1 单位转换服务
```python
class UnitConversionService:
    def __init__(self, db: Session):
        self.db = db

    def convert(self, value: float, from_unit: str, to_unit: str, ingredient_name: str = None) -> float:
        """单位转换"""
        pass

    def convert_volume_to_weight(self, volume: float, volume_unit: str, ingredient_name: str) -> Tuple[float, str]:
        """体积到重量转换"""
        pass

    def convert_weight_to_volume(self, weight: float, weight_unit: str, ingredient_name: str) -> Tuple[float, str]:
        """重量到体积转换"""
        pass

    def get_preferred_units_for_region(self, region_code: str) -> dict:
        """获取地区首选单位"""
        pass
```

### 3.2 食材匹配服务
```python
class IngredientMatcher:
    """智能食材匹配器"""

    def match_product_to_ingredient(self, product_name: str) -> List[Tuple[Ingredient, float]]:
        """
        将产品名称匹配到可能的食材及其置信度
        例如："金龙鱼高筋小麦粉" -> [(高筋面粉, 0.95), (小麦粉, 0.85), (面粉, 0.75)]
        """
        pass

    def resolve_ingredient_hierarchy(self, base_ingredient: str, grade_requirement: str = None) -> Ingredient:
        """
        解析食材层级关系
        例如：基础食材="面粉"，等级要求="高筋" -> 返回"高筋面粉"
        """
        pass

    def suggest_alternatives(self, unavailable_ingredient: Ingredient) -> List[Ingredient]:
        """
        提供可替代的食材选项
        """
        pass
```

## 4. 实施计划

### 4.1 数据迁移
1. 创建新的数据表结构
2. 迁移现有数据到新结构
3. 验证数据完整性

### 4.2 服务开发
1. 开发单位转换服务
2. 实现食材匹配算法
3. 创建营养计算功能

### 4.3 界面优化
1. 更新表单以支持新单位系统
2. 添加分类筛选功能
3. 实现营养数据显示

## 5. 注意事项

1. 单位换算精度：考虑使用decimal类型以保证精度
2. 性能优化：对频繁查询的单位转换建立缓存
3. 国际化：确保UI能够正确显示区域化单位
4. 数据验证：对输入数据进行严格的验证和清洗