"""
单位管理 API
提供单位的增删改查、换算关系管理、实体单位覆盖和密度管理功能
"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.models.unit import Unit, UnitConversion
from app.models.user import User
from app.models.entity_unit_override import EntityUnitOverride
from app.models.entity_density import EntityDensity
from app.schemas.unit import (
    UnitCreate,
    UnitUpdate,
    UnitResponse,
    EntityUnitOverrideCreate,
    EntityUnitOverrideUpdate,
    EntityUnitOverrideResponse,
    EntityDensityCreate,
    EntityDensityUpdate,
    EntityDensityResponse,
    UnitConvertRequest,
    UnitConvertResponse,
    UnmappedUnitItem,
)
from app.services.unit_matcher import UnitMatcher
from app.services.unit_conversion_service import UnitConversionService

router = APIRouter(prefix="/units", tags=["单位管理"])

# ============ 辅助：保留内联模式（换算关系、匹配） ============

class UnitConversionCreate(BaseModel):
    """创建换算关系模式"""
    from_unit_id: int = Field(..., description="源单位ID")
    to_unit_id: int = Field(..., description="目标单位ID")
    conversion_factor: float = Field(..., description="转换因子")
    formula: Optional[str] = Field(None, description="可选的转换公式")
    is_bidirectional: bool = Field(default=True, description="是否双向转换")
    precision: int = Field(default=2, description="精度")


class UnitConversionResponse(BaseModel):
    """换算关系响应模式"""
    id: int
    from_unit_id: int
    to_unit_id: int
    conversion_factor: float
    formula: Optional[str]
    is_bidirectional: bool
    precision: int
    from_unit: UnitResponse
    to_unit: UnitResponse

    class Config:
        from_attributes = True


class UnitMatchRequest(BaseModel):
    """单位匹配请求模式"""
    unit_str: str = Field(..., description="单位字符串")


class UnitMatchResponse(BaseModel):
    """单位匹配响应模式"""
    unit: Optional[UnitResponse]
    is_new: bool = Field(..., description="是否为新创建的单位")


# ============ 辅助函数 ============

VALID_ENTITY_TYPES = {"ingredient", "product"}


def _validate_entity_type(entity_type: str):
    """验证 entity_type 参数"""
    if entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 entity_type: '{entity_type}'，只接受 {VALID_ENTITY_TYPES}"
        )


# ============ 单位 CRUD ============

@router.get("/", response_model=List[UnitResponse])
def list_units(
    unit_type: Optional[str] = None,
    unit_system: Optional[str] = None,
    is_common: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取单位列表

    - **unit_type**: 按单位类型过滤（mass/volume/length/count等）
    - **unit_system**: 按单位制过滤（metric/market/imperial/count/vague）
    - **is_common**: 只返回常用单位
    """
    query = db.query(Unit)

    if unit_type:
        query = query.filter(Unit.unit_type == unit_type)

    if unit_system:
        query = query.filter(Unit.unit_system == unit_system)

    if is_common is not None:
        query = query.filter(Unit.is_common == is_common)

    units = query.order_by(Unit.unit_type, Unit.display_order).all()
    return units


@router.get("/{unit_id}", response_model=UnitResponse)
def get_unit(unit_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取单个单位"""
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="单位不存在")
    return unit


@router.post("/", response_model=UnitResponse)
def create_unit(unit_data: UnitCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """
    创建新单位

    - **name**: 单位名称（必须唯一）
    - **abbreviation**: 单位缩写（必须唯一）
    - **unit_type**: 单位类型
    - **is_common**: 是否为常用单位
    """
    # 检查名称和缩写是否已存在
    existing = db.query(Unit).filter(
        (Unit.name == unit_data.name) | (Unit.abbreviation == unit_data.abbreviation)
    ).first()

    if existing:
        if existing.name == unit_data.name:
            raise HTTPException(status_code=400, detail=f"单位名称 '{unit_data.name}' 已存在")
        else:
            raise HTTPException(status_code=400, detail=f"单位缩写 '{unit_data.abbreviation}' 已存在")

    unit = Unit(**unit_data.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.put("/{unit_id}", response_model=UnitResponse)
def update_unit(
    unit_id: int,
    unit_data: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """更新单位"""
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="单位不存在")

    # 检查名称和缩写是否与其他单位冲突
    if unit_data.name is not None or unit_data.abbreviation is not None:
        existing = db.query(Unit).filter(
            (Unit.name == unit_data.name) | (Unit.abbreviation == unit_data.abbreviation),
            Unit.id != unit_id
        ).first()

        if existing:
            if existing.name == unit_data.name:
                raise HTTPException(status_code=400, detail=f"单位名称 '{unit_data.name}' 已存在")
            else:
                raise HTTPException(status_code=400, detail=f"单位缩写 '{unit_data.abbreviation}' 已存在")

    # 更新字段
    update_data = unit_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(unit, field, value)

    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/{unit_id}")
def delete_unit(unit_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """
    删除单位

    注意：如果单位被其他记录引用，将无法删除
    """
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="单位不存在")

    try:
        db.delete(unit)
        db.commit()
        return {"message": "单位已删除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"无法删除单位，可能被其他记录引用：{str(e)}"
        )


# ============ 换算关系管理 ============

@router.get("/{unit_id}/conversions", response_model=List[UnitConversionResponse])
def list_unit_conversions(unit_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取单位的所有换算关系"""
    conversions = db.query(UnitConversion).filter(
        (UnitConversion.from_unit_id == unit_id) | (UnitConversion.to_unit_id == unit_id)
    ).all()
    return conversions


@router.post("/conversions/", response_model=UnitConversionResponse)
def create_conversion(conversion_data: UnitConversionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """
    创建换算关系

    - **from_unit_id**: 源单位ID
    - **to_unit_id**: 目标单位ID
    - **conversion_factor**: 转换因子
    - **is_bidirectional**: 是否双向转换
    """
    # 检查单位是否存在
    from_unit = db.query(Unit).filter(Unit.id == conversion_data.from_unit_id).first()
    to_unit = db.query(Unit).filter(Unit.id == conversion_data.to_unit_id).first()

    if not from_unit:
        raise HTTPException(status_code=404, detail=f"源单位 ID {conversion_data.from_unit_id} 不存在")
    if not to_unit:
        raise HTTPException(status_code=404, detail=f"目标单位 ID {conversion_data.to_unit_id} 不存在")

    # 检查是否已存在相同的换算关系
    existing = db.query(UnitConversion).filter(
        UnitConversion.from_unit_id == conversion_data.from_unit_id,
        UnitConversion.to_unit_id == conversion_data.to_unit_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="换算关系已存在")

    conversion = UnitConversion(**conversion_data.model_dump())
    db.add(conversion)
    db.commit()
    db.refresh(conversion)

    # 如果是双向转换，自动创建反向关系
    if conversion_data.is_bidirectional:
        reverse_existing = db.query(UnitConversion).filter(
            UnitConversion.from_unit_id == conversion_data.to_unit_id,
            UnitConversion.to_unit_id == conversion_data.from_unit_id
        ).first()

        if not reverse_existing:
            reverse_conversion = UnitConversion(
                from_unit_id=conversion_data.to_unit_id,
                to_unit_id=conversion_data.from_unit_id,
                conversion_factor=1.0 / conversion_data.conversion_factor,
                formula=conversion_data.formula,
                is_bidirectional=False,  # 反向关系不标记为双向，避免无限循环
                precision=conversion_data.precision
            )
            db.add(reverse_conversion)
            db.commit()

    return conversion


@router.delete("/conversions/{conversion_id}")
def delete_conversion(conversion_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """删除换算关系"""
    conversion = db.query(UnitConversion).filter(UnitConversion.id == conversion_id).first()
    if not conversion:
        raise HTTPException(status_code=404, detail="换算关系不存在")

    db.delete(conversion)
    db.commit()
    return {"message": "换算关系已删除"}


# ============ 单位匹配 ============

@router.post("/match", response_model=UnitMatchResponse)
def match_unit(request: UnitMatchRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    匹配单位字符串

    - **unit_str**: 单位字符串（如"g"、"kg"、"克"等）

    返回匹配到的单位，如果不存在则自动创建
    """
    matcher = UnitMatcher(db)
    unit, is_new = matcher.match_unit(request.unit_str)
    return UnitMatchResponse(unit=unit, is_new=is_new)


# ============ 单位转换（使用 UnitConversionService） ============

@router.post("/convert", response_model=UnitConvertResponse)
def convert_units(request: UnitConvertRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    单位转换

    使用 UnitConversionService 进行统一换算，支持：
    - 同类型 SI 因子换算
    - 实体覆盖单位换算（需提供 entity_type 和 entity_id）
    - 体积/质量跨类型密度换算（需提供 entity_type 和 entity_id）

    - **value**: 要转换的值
    - **from_unit**: 源单位缩写
    - **to_unit**: 目标单位缩写
    - **entity_type**: 实体类型（可选，'ingredient' 或 'product'）
    - **entity_id**: 实体ID（可选）
    """
    service = UnitConversionService(db)

    result = service.convert(
        value=request.value,
        from_unit_abbr=request.from_unit,
        to_unit_abbr=request.to_unit,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
    )

    if result is None:
        raise HTTPException(
            status_code=400,
            detail=f"不支持从 '{request.from_unit}' 到 '{request.to_unit}' 的换算"
        )

    converted_value, method = result
    return UnitConvertResponse(
        value=converted_value,
        from_unit=request.from_unit,
        to_unit=request.to_unit,
        method=method,
    )


# ============ 批量导入 ============

@router.post("/import-batch")
def import_units_batch(unit_names: List[str], db: Session = Depends(get_db), current_user: User = Depends(get_current_admin_user)):
    """
    批量导入单位

    - **unit_names**: 单位名称列表

    返回导入结果，包括成功和失败的数量
    """
    matcher = UnitMatcher(db)
    results = {
        "total": len(unit_names),
        "matched": 0,
        "created": 0,
        "errors": []
    }

    for unit_name in unit_names:
        try:
            unit, is_new = matcher.match_unit(unit_name)
            if unit:
                if is_new:
                    results["created"] += 1
                else:
                    results["matched"] += 1
            else:
                results["errors"].append(f"空单位名称: {unit_name}")
        except Exception as e:
            results["errors"].append(f"{unit_name}: {str(e)}")

    return results


# ============ 实体单位覆盖 API ============

entities_unit_router = APIRouter(
    prefix="/entities/{entity_type}/{entity_id}/units",
    tags=["实体单位覆盖"],
)


@entities_unit_router.get("", response_model=List[EntityUnitOverrideResponse])
@entities_unit_router.get("/", response_model=List[EntityUnitOverrideResponse])
def list_entity_unit_overrides(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取实体自定义单位列表

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    """
    _validate_entity_type(entity_type)
    overrides = (
        db.query(EntityUnitOverride)
        .filter(
            EntityUnitOverride.entity_type == entity_type,
            EntityUnitOverride.entity_id == entity_id,
        )
        .all()
    )
    return overrides


@entities_unit_router.post("", response_model=EntityUnitOverrideResponse, status_code=201)
@entities_unit_router.post("/", response_model=EntityUnitOverrideResponse, status_code=201)
def create_entity_unit_override(
    entity_type: str,
    entity_id: int,
    data: EntityUnitOverrideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    创建实体单位覆盖

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    """
    _validate_entity_type(entity_type)

    # 检查是否已存在同名的覆盖
    existing = (
        db.query(EntityUnitOverride)
        .filter(
            EntityUnitOverride.entity_type == entity_type,
            EntityUnitOverride.entity_id == entity_id,
            EntityUnitOverride.unit_name == data.unit_name,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"实体 {entity_type}/{entity_id} 已存在单位覆盖 '{data.unit_name}'"
        )

    override = EntityUnitOverride(
        entity_type=entity_type,
        entity_id=entity_id,
        **data.model_dump(),
    )
    db.add(override)
    db.commit()
    db.refresh(override)
    return override


@entities_unit_router.put("/{override_id}", response_model=EntityUnitOverrideResponse)
def update_entity_unit_override(
    entity_type: str,
    entity_id: int,
    override_id: int,
    data: EntityUnitOverrideUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    更新实体单位覆盖

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    - **override_id**: 覆盖记录ID
    """
    _validate_entity_type(entity_type)

    override = (
        db.query(EntityUnitOverride)
        .filter(
            EntityUnitOverride.id == override_id,
            EntityUnitOverride.entity_type == entity_type,
            EntityUnitOverride.entity_id == entity_id,
        )
        .first()
    )
    if not override:
        raise HTTPException(status_code=404, detail="实体单位覆盖不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(override, field, value)

    db.commit()
    db.refresh(override)
    return override


@entities_unit_router.delete("/{override_id}")
def delete_entity_unit_override(
    entity_type: str,
    entity_id: int,
    override_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    删除实体单位覆盖

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    - **override_id**: 覆盖记录ID
    """
    _validate_entity_type(entity_type)

    override = (
        db.query(EntityUnitOverride)
        .filter(
            EntityUnitOverride.id == override_id,
            EntityUnitOverride.entity_type == entity_type,
            EntityUnitOverride.entity_id == entity_id,
        )
        .first()
    )
    if not override:
        raise HTTPException(status_code=404, detail="实体单位覆盖不存在")

    db.delete(override)
    db.commit()
    return {"message": "实体单位覆盖已删除"}


@entities_unit_router.get("/unmapped-units", response_model=List[UnmappedUnitItem])
def get_unmapped_units(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取实体在菜谱中使用的 count 类型单位中，尚未配置 Override 的列表

    按使用频率降序排列，供前端下拉选择。

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    """
    _validate_entity_type(entity_type)
    ucs = UnitConversionService(db)
    return ucs.get_unmapped_units(entity_type, entity_id)


# ============ 实体密度 API ============

entities_density_router = APIRouter(
    prefix="/entities/{entity_type}/{entity_id}/density",
    tags=["实体密度"],
)


@entities_density_router.get("", response_model=List[EntityDensityResponse])
@entities_density_router.get("/", response_model=List[EntityDensityResponse])
def list_entity_densities(
    entity_type: str,
    entity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取实体密度列表

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    """
    _validate_entity_type(entity_type)
    densities = (
        db.query(EntityDensity)
        .filter(
            EntityDensity.entity_type == entity_type,
            EntityDensity.entity_id == entity_id,
        )
        .all()
    )
    return densities


@entities_density_router.post("", response_model=EntityDensityResponse)
@entities_density_router.post("/", response_model=EntityDensityResponse)
def upsert_entity_density(
    entity_type: str,
    entity_id: int,
    data: EntityDensityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    创建或更新实体密度（upsert）

    如果相同 entity_type + entity_id + condition 的记录已存在，则更新；否则创建。

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    - **density**: 密度（kg/m³）
    - **condition**: 状态描述（用于区分同实体不同状态，如"切碎"、"压碎"）
    """
    _validate_entity_type(entity_type)

    # 查找已有记录（按 entity_type + entity_id + condition 唯一约束匹配）
    existing = (
        db.query(EntityDensity)
        .filter(
            EntityDensity.entity_type == entity_type,
            EntityDensity.entity_id == entity_id,
            EntityDensity.condition == data.condition,
        )
        .first()
    )

    if existing:
        # 更新已有记录
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    # 创建新记录
    density_record = EntityDensity(
        entity_type=entity_type,
        entity_id=entity_id,
        **data.model_dump(),
    )
    db.add(density_record)
    db.commit()
    db.refresh(density_record)
    return density_record


@entities_density_router.delete("/{density_id}")
def delete_entity_density(
    entity_type: str,
    entity_id: int,
    density_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    删除实体密度

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    - **density_id**: 密度记录ID
    """
    _validate_entity_type(entity_type)

    density_record = (
        db.query(EntityDensity)
        .filter(
            EntityDensity.id == density_id,
            EntityDensity.entity_type == entity_type,
            EntityDensity.entity_id == entity_id,
        )
        .first()
    )
    if not density_record:
        raise HTTPException(status_code=404, detail="实体密度记录不存在")

    db.delete(density_record)
    db.commit()
    return {"message": "实体密度记录已删除"}
