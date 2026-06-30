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
from app.services.proposals import service as proposal_service
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
def create_unit(unit_data: UnitCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    创建新单位（分流：管理员直写 / 普通用户提议）。

    单位创建在治理总表里默认 auto_approve，故普通用户提交即生效（但经框架留痕）。
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

    payload = unit_data.model_dump()

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="unit", entity_id=None,
            action="create", payload=payload, admin=current_user,
        )
        db.commit()
        unit = db.query(Unit).filter(Unit.name == unit_data.name).first()
        return unit

    p = proposal_service.submit(
        db, entity_type="unit", entity_id=None,
        action="create", payload=payload, proposer=current_user,
    )
    db.commit()
    # auto_approve（治理总表 unit.create 默认）→ 已 applied，返回新建单位；
    # 若策略被改为 manual，返回提议占位（前端按 status 提示）
    if p.status == "applied":
        unit = db.query(Unit).filter(Unit.name == unit_data.name).first()
        return unit
    # 提议待审：返回骨架信息（满足 response_model）
    return Unit(id=0, name=unit_data.name, abbreviation=unit_data.abbreviation)


@router.put("/{unit_id}", response_model=UnitResponse)
def update_unit(
    unit_id: int,
    unit_data: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新单位（分流：管理员直写 / 普通用户提议）。

    标准单位（is_standard=True）仅管理员可改，提议路径由执行器 validate 拒绝。
    """
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

    update_data = unit_data.model_dump(exclude_unset=True)

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="unit", entity_id=unit_id,
            action="update", payload=update_data, admin=current_user,
        )
        db.commit()
        db.refresh(unit)
        return unit

    p = proposal_service.submit(
        db, entity_type="unit", entity_id=unit_id,
        action="update", payload=update_data, proposer=current_user,
    )
    db.commit()
    # unit.update 治理总表默认 manual → 待审；返回当前单位（值未变）
    return unit


@router.delete("/{unit_id}")
def delete_unit(unit_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    删除单位（分流：管理员直写 / 普通用户提议）。

    标准单位（is_standard=True）仅管理员可删，提议路径由执行器 validate 拒绝。
    执行器 delete 为软删（is_active=False），原硬删改为软删以便 revert。
    """
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="单位不存在")

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="unit", entity_id=unit_id,
            action="delete", payload={}, admin=current_user,
        )
        db.commit()
        return {"message": "单位已删除（管理员直写）"}

    p = proposal_service.submit(
        db, entity_type="unit", entity_id=unit_id,
        action="delete", payload={}, proposer=current_user,
    )
    db.commit()
    return {"message": f"删除提议已提交（proposal_id={p.id}, status={p.status}）"}


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
            EntityUnitOverride.is_active.is_(True),
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
    current_user: User = Depends(get_current_user),
):
    """
    创建实体单位覆盖（分流：管理员直写 / 普通用户提议）。

    全 manual——普通用户提交后待管理员审核（同名查重在执行器 validate 带 is_active 过滤）。

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    """
    _validate_entity_type(entity_type)
    # mode="json"：Decimal → str（无损），保证 payload 可入 JSON 列；
    # model 构造器/setattr 接收 Numeric 列时自动再转回 Decimal。
    payload = {"entity_type": entity_type, "entity_id": entity_id, **data.model_dump(mode="json")}

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="entity_unit_override", entity_id=None,
            action="create", payload=payload, admin=current_user,
        )
        db.commit()
        return (
            db.query(EntityUnitOverride)
            .filter(
                EntityUnitOverride.entity_type == entity_type,
                EntityUnitOverride.entity_id == entity_id,
                EntityUnitOverride.unit_name == data.unit_name,
                EntityUnitOverride.is_active.is_(True),
            )
            .order_by(EntityUnitOverride.id.desc())
            .first()
        )

    p = proposal_service.submit(
        db, entity_type="entity_unit_override", entity_id=None,
        action="create", payload=payload, proposer=current_user,
    )
    db.commit()
    # manual → status=pending；返回占位骨架满足 response_model
    return EntityUnitOverride(
        id=0, entity_type=entity_type, entity_id=entity_id,
        unit_name=data.unit_name,
    )


@entities_unit_router.put("/{override_id}", response_model=EntityUnitOverrideResponse)
def update_entity_unit_override(
    entity_type: str,
    entity_id: int,
    override_id: int,
    data: EntityUnitOverrideUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新实体单位覆盖（分流：管理员直写 / 普通用户提议）。

    普通用户待审：值未变，返回当前对象。

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    - **override_id**: 覆盖记录ID
    """
    _validate_entity_type(entity_type)
    obj = (
        db.query(EntityUnitOverride)
        .filter(
            EntityUnitOverride.id == override_id,
            EntityUnitOverride.entity_type == entity_type,
            EntityUnitOverride.entity_id == entity_id,
            EntityUnitOverride.is_active.is_(True),
        )
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="实体单位覆盖不存在")

    update_data = data.model_dump(exclude_unset=True, mode="json")

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="entity_unit_override", entity_id=override_id,
            action="update", payload=update_data, admin=current_user,
        )
        db.commit()
        db.refresh(obj)
        return obj

    proposal_service.submit(
        db, entity_type="entity_unit_override", entity_id=override_id,
        action="update", payload=update_data, proposer=current_user,
    )
    db.commit()
    db.refresh(obj)
    return obj  # 待审：值未变


@entities_unit_router.delete("/{override_id}")
def delete_entity_unit_override(
    entity_type: str,
    entity_id: int,
    override_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除实体单位覆盖（分流，软删）。

    普通用户待审。

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    - **override_id**: 覆盖记录ID
    """
    _validate_entity_type(entity_type)
    obj = (
        db.query(EntityUnitOverride)
        .filter(
            EntityUnitOverride.id == override_id,
            EntityUnitOverride.entity_type == entity_type,
            EntityUnitOverride.entity_id == entity_id,
            EntityUnitOverride.is_active.is_(True),
        )
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="实体单位覆盖不存在")

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="entity_unit_override", entity_id=override_id,
            action="delete", payload={}, admin=current_user,
        )
        db.commit()
        return {"message": "实体单位覆盖已删除（管理员直写，软删）"}

    p = proposal_service.submit(
        db, entity_type="entity_unit_override", entity_id=override_id,
        action="delete", payload={}, proposer=current_user,
    )
    db.commit()
    return {"message": f"删除提议已提交（proposal_id={p.id}, status={p.status}）"}


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
            EntityDensity.is_active.is_(True),
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
    current_user: User = Depends(get_current_user),
):
    """
    创建或更新实体密度（upsert，分流：管理员直写 / 普通用户提议）。

    全 manual。端点层先按 entity_type+entity_id+condition 查活跃记录——
    有则 submit/apply update，无则 submit/apply create。

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    - **density**: 密度（kg/m³）
    - **condition**: 状态描述（用于区分同实体不同状态，如"切碎"、"压碎"）
    """
    _validate_entity_type(entity_type)
    existing = (
        db.query(EntityDensity)
        .filter(
            EntityDensity.entity_type == entity_type,
            EntityDensity.entity_id == entity_id,
            EntityDensity.condition.is_(data.condition) if data.condition is None
            else EntityDensity.condition == data.condition,
            EntityDensity.is_active.is_(True),
        )
        .first()
    )

    if existing:
        update_data = data.model_dump(exclude_unset=True, mode="json")
        if current_user.is_admin:
            proposal_service.apply_as_admin(
                db, entity_type="entity_density", entity_id=existing.id,
                action="update", payload=update_data, admin=current_user,
            )
            db.commit()
            db.refresh(existing)
            return existing
        proposal_service.submit(
            db, entity_type="entity_density", entity_id=existing.id,
            action="update", payload=update_data, proposer=current_user,
        )
        db.commit()
        db.refresh(existing)
        return existing  # 待审：值未变

    # create 路径
    base = {"entity_type": entity_type, "entity_id": entity_id, **data.model_dump(mode="json")}
    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="entity_density", entity_id=None,
            action="create", payload=base, admin=current_user,
        )
        db.commit()
        return (
            db.query(EntityDensity)
            .filter(
                EntityDensity.entity_type == entity_type,
                EntityDensity.entity_id == entity_id,
                EntityDensity.is_active.is_(True),
            )
            .order_by(EntityDensity.id.desc())
            .first()
        )
    p = proposal_service.submit(
        db, entity_type="entity_density", entity_id=None,
        action="create", payload=base, proposer=current_user,
    )
    db.commit()
    return EntityDensity(
        id=0, entity_type=entity_type, entity_id=entity_id,
        density=data.density, confidence=data.confidence,
    )


@entities_density_router.delete("/{density_id}")
def delete_entity_density(
    entity_type: str,
    entity_id: int,
    density_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除实体密度（分流，软删）。

    普通用户待审。

    - **entity_type**: 实体类型（ingredient 或 product）
    - **entity_id**: 实体ID
    - **density_id**: 密度记录ID
    """
    _validate_entity_type(entity_type)
    obj = (
        db.query(EntityDensity)
        .filter(
            EntityDensity.id == density_id,
            EntityDensity.entity_type == entity_type,
            EntityDensity.entity_id == entity_id,
            EntityDensity.is_active.is_(True),
        )
        .first()
    )
    if not obj:
        raise HTTPException(status_code=404, detail="实体密度记录不存在")

    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="entity_density", entity_id=density_id,
            action="delete", payload={}, admin=current_user,
        )
        db.commit()
        return {"message": "实体密度记录已删除（管理员直写，软删）"}

    p = proposal_service.submit(
        db, entity_type="entity_density", entity_id=density_id,
        action="delete", payload={}, proposer=current_user,
    )
    db.commit()
    return {"message": f"删除提议已提交（proposal_id={p.id}, status={p.status}）"}
