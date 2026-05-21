"""
单位管理相关的 Pydantic 模式
包含单位、实体单位覆盖、实体密度、单位换算等 schemas
"""
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


# ============ 单位相关 Schemas ============

class UnitBase(BaseModel):
    """单位基础模式"""
    name: str
    abbreviation: str
    plural_form: Optional[str] = None
    unit_type: str  # mass/volume/length/count/vague
    unit_system: Optional[str] = None  # metric/market/imperial/count/vague
    si_factor: Optional[Decimal] = None
    is_si_base: bool = False
    is_common: bool = False
    display_order: int = 0
    default_estimate: Optional[Decimal] = None


class UnitCreate(UnitBase):
    """创建单位模式"""
    pass


class UnitUpdate(BaseModel):
    """更新单位模式"""
    name: Optional[str] = None
    abbreviation: Optional[str] = None
    plural_form: Optional[str] = None
    unit_type: Optional[str] = None
    unit_system: Optional[str] = None
    si_factor: Optional[Decimal] = None
    is_si_base: Optional[bool] = None
    is_common: Optional[bool] = None
    display_order: Optional[int] = None
    default_estimate: Optional[Decimal] = None


class UnitResponse(UnitBase):
    """单位响应模式"""
    id: int

    class Config:
        from_attributes = True


# ============ 实体单位覆盖 Schemas ============

class EntityUnitOverrideBase(BaseModel):
    """实体单位覆盖基础模式"""
    unit_name: str
    conversion_factor: Optional[Decimal] = None
    weight_per_unit: Optional[Decimal] = None
    weight_unit_id: Optional[int] = None
    is_default: bool = False


class EntityUnitOverrideCreate(EntityUnitOverrideBase):
    """创建实体单位覆盖模式"""
    pass


class EntityUnitOverrideUpdate(BaseModel):
    """更新实体单位覆盖模式"""
    unit_name: Optional[str] = None
    conversion_factor: Optional[Decimal] = None
    weight_per_unit: Optional[Decimal] = None
    weight_unit_id: Optional[int] = None
    is_default: Optional[bool] = None


class EntityUnitOverrideResponse(EntityUnitOverrideBase):
    """实体单位覆盖响应模式"""
    id: int
    entity_type: str
    entity_id: int
    base_unit_id: Optional[int] = None

    class Config:
        from_attributes = True


# ============ 实体密度 Schemas ============

class EntityDensityBase(BaseModel):
    """实体密度基础模式"""
    density: Decimal  # kg/m³
    temperature: Optional[Decimal] = None
    condition: Optional[str] = None
    source: Optional[str] = None
    confidence: Decimal = Decimal("1.0")


class EntityDensityCreate(EntityDensityBase):
    """创建实体密度模式"""
    pass


class EntityDensityUpdate(BaseModel):
    """更新实体密度模式"""
    density: Optional[Decimal] = None
    temperature: Optional[Decimal] = None
    condition: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[Decimal] = None


class EntityDensityResponse(EntityDensityBase):
    """实体密度响应模式"""
    id: int
    entity_type: str
    entity_id: int

    class Config:
        from_attributes = True


# ============ 单位换算请求/响应 Schemas ============

class UnitConvertRequest(BaseModel):
    """单位换算请求模式（基于缩写）"""
    value: Decimal
    from_unit: str  # 缩写
    to_unit: str  # 缩写
    entity_type: Optional[str] = None  # 'ingredient' 或 'product'
    entity_id: Optional[int] = None


class UnitConvertResponse(BaseModel):
    """单位换算响应模式"""
    value: Decimal
    from_unit: str
    to_unit: str
    method: str  # 'si_factor' / 'entity_override' / 'density' / 'not_supported'
