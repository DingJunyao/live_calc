"""
单位管理 API
提供单位的增删改查和换算关系管理功能
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.unit import Unit, UnitConversion
from app.services.unit_matcher import UnitMatcher

router = APIRouter(prefix="/units", tags=["单位管理"])


# ============ Pydantic 模式 ============

class UnitBase(BaseModel):
    """单位基础模式"""
    name: str = Field(..., description="单位名称")
    abbreviation: str = Field(..., description="单位缩写")
    plural_form: Optional[str] = Field(None, description="复数形式")
    unit_type: str = Field(..., description="单位类型（mass/volume/length/count等）")
    si_factor: float = Field(default=1.0, description="转换为国际单位制的因子")
    is_si_base: bool = Field(default=False, description="是否是国际单位制基本单位")
    is_common: bool = Field(default=False, description="是否为常用单位")
    display_order: int = Field(default=0, description="显示顺序")


class UnitCreate(UnitBase):
    """创建单位模式"""
    pass


class UnitUpdate(BaseModel):
    """更新单位模式"""
    name: Optional[str] = None
    abbreviation: Optional[str] = None
    plural_form: Optional[str] = None
    unit_type: Optional[str] = None
    si_factor: Optional[float] = None
    is_si_base: Optional[bool] = None
    is_common: Optional[bool] = None
    display_order: Optional[int] = None


class UnitResponse(UnitBase):
    """单位响应模式"""
    id: int
    base_unit_id: Optional[int] = None

    class Config:
        from_attributes = True


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


class UnitConvertRequest(BaseModel):
    """单位转换请求模式"""
    from_unit_id: int = Field(..., description="源单位ID")
    to_unit_id: int = Field(..., description="目标单位ID")
    value: float = Field(..., description="要转换的值")


class UnitConvertResponse(BaseModel):
    """单位转换响应模式"""
    from_value: float
    to_value: float
    from_unit: str
    to_unit: str
    conversion_factor: float


# ============ API 端点 ============

@router.get("/", response_model=List[UnitResponse])
def list_units(
    unit_type: Optional[str] = None,
    is_common: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    获取单位列表

    - **unit_type**: 按单位类型过滤（mass/volume/length/count等）
    - **is_common**: 只返回常用单位
    """
    query = db.query(Unit)

    if unit_type:
        query = query.filter(Unit.unit_type == unit_type)

    if is_common is not None:
        query = query.filter(Unit.is_common == is_common)

    units = query.order_by(Unit.unit_type, Unit.display_order).all()
    return units


@router.get("/{unit_id}", response_model=UnitResponse)
def get_unit(unit_id: int, db: Session = Depends(get_db)):
    """获取单个单位"""
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="单位不存在")
    return unit


@router.post("/", response_model=UnitResponse)
def create_unit(unit_data: UnitCreate, db: Session = Depends(get_db)):
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
    db: Session = Depends(get_db)
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
def delete_unit(unit_id: int, db: Session = Depends(get_db)):
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
def list_unit_conversions(unit_id: int, db: Session = Depends(get_db)):
    """获取单位的所有换算关系"""
    conversions = db.query(UnitConversion).filter(
        (UnitConversion.from_unit_id == unit_id) | (UnitConversion.to_unit_id == unit_id)
    ).all()
    return conversions


@router.post("/conversions/", response_model=UnitConversionResponse)
def create_conversion(conversion_data: UnitConversionCreate, db: Session = Depends(get_db)):
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
def delete_conversion(conversion_id: int, db: Session = Depends(get_db)):
    """删除换算关系"""
    conversion = db.query(UnitConversion).filter(UnitConversion.id == conversion_id).first()
    if not conversion:
        raise HTTPException(status_code=404, detail="换算关系不存在")

    db.delete(conversion)
    db.commit()
    return {"message": "换算关系已删除"}


# ============ 单位匹配 ============

@router.post("/match", response_model=UnitMatchResponse)
def match_unit(request: UnitMatchRequest, db: Session = Depends(get_db)):
    """
    匹配单位字符串

    - **unit_str**: 单位字符串（如"g"、"kg"、"克"等）

    返回匹配到的单位，如果不存在则自动创建
    """
    matcher = UnitMatcher(db)
    unit, is_new = matcher.match_unit(request.unit_str)
    return UnitMatchResponse(unit=unit, is_new=is_new)


# ============ 单位转换 ============

@router.post("/convert", response_model=UnitConvertResponse)
def convert_units(request: UnitConvertRequest, db: Session = Depends(get_db)):
    """
    单位转换

    - **from_unit_id**: 源单位ID
    - **to_unit_id**: 目标单位ID
    - **value**: 要转换的值

    返回转换后的值
    """
    # 检查单位是否存在
    from_unit = db.query(Unit).filter(Unit.id == request.from_unit_id).first()
    to_unit = db.query(Unit).filter(Unit.id == request.to_unit_id).first()

    if not from_unit:
        raise HTTPException(status_code=404, detail=f"源单位 ID {request.from_unit_id} 不存在")
    if not to_unit:
        raise HTTPException(status_code=404, detail=f"目标单位 ID {request.to_unit_id} 不存在")

    # 如果是同一个单位，直接返回
    if request.from_unit_id == request.to_unit_id:
        return UnitConvertResponse(
            from_value=request.value,
            to_value=request.value,
            from_unit=from_unit.abbreviation,
            to_unit=to_unit.abbreviation,
            conversion_factor=1.0
        )

    # 尝试通过换算关系查找转换因子
    conversion = db.query(UnitConversion).filter(
        UnitConversion.from_unit_id == request.from_unit_id,
        UnitConversion.to_unit_id == request.to_unit_id
    ).first()

    if not conversion:
        raise HTTPException(
            status_code=400,
            detail=f"未找到从 {from_unit.name} 到 {to_unit.name} 的换算关系"
        )

    to_value = request.value * conversion.conversion_factor
    return UnitConvertResponse(
        from_value=request.value,
        to_value=to_value,
        from_unit=from_unit.abbreviation,
        to_unit=to_unit.abbreviation,
        conversion_factor=conversion.conversion_factor
    )


# ============ 批量导入 ============

@router.post("/import-batch")
def import_units_batch(unit_names: List[str], db: Session = Depends(get_db)):
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
