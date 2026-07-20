"""行政区划 API（懒加载树形选择器）"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.administrative_region import AdministrativeRegion
from app.models.user import User
from app.schemas.region import RegionResponse, RegionDetailResponse, RegionAncestor
from app.services.region_seed import upsert_administrative_regions, need_region_seed

router = APIRouter(tags=["行政区划"])


def _region_to_response(region: AdministrativeRegion) -> RegionResponse:
    """ORM → Pydantic 响应"""
    return RegionResponse(
        id=region.id,
        code=region.code,
        name=region.name,
        name_en=region.name_en,
        level=region.level,
        iso_country=region.iso_country,
        path=region.path,
        has_children=False,  # 由调用方覆写
    )


def _count_children(db: Session, parent_id: int) -> bool:
    """判断指定节点是否有活跃子节点。"""
    return (
        db.query(AdministrativeRegion.id)
        .filter(
            AdministrativeRegion.parent_id == parent_id,
            AdministrativeRegion.is_active == True,
        )
        .first()
        is not None
    )


@router.get("/regions", response_model=list[RegionResponse])
@router.get("/regions/", response_model=list[RegionResponse])
def list_regions(
    parent_id: Optional[int] = Query(None),
    level: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """懒加载子节点列表。

    - ``parent_id`` 给定 → 返回该节点的活跃子节点（按 code 排序）
    - ``level`` 给定（无 parent_id）→ 返回该层级所有节点
    - 默认 → 返回 level=0（国家）
    """
    query = db.query(AdministrativeRegion).filter(
        AdministrativeRegion.is_active == True,
    )

    if parent_id is not None:
        query = query.filter(AdministrativeRegion.parent_id == parent_id)

    if level is not None:
        query = query.filter(AdministrativeRegion.level == level)

    # 默认（两者均未给定）：返回顶层，即 level=0
    if parent_id is None and level is None:
        query = query.filter(AdministrativeRegion.level == 0)

    rows = query.order_by(AdministrativeRegion.code).all()

    results = []
    for r in rows:
        resp = _region_to_response(r)
        resp.has_children = _count_children(db, r.id)
        results.append(resp)
    return results


@router.get("/regions/{region_id}", response_model=RegionDetailResponse)
@router.get("/regions/{region_id}/", response_model=RegionDetailResponse)
def get_region(region_id: int, db: Session = Depends(get_db)):
    """获取单个行政区划详情（含祖先链）。"""
    region = (
        db.query(AdministrativeRegion)
        .filter(
            AdministrativeRegion.id == region_id,
            AdministrativeRegion.is_active == True,
        )
        .first()
    )
    if not region:
        raise HTTPException(status_code=404, detail="行政区划不存在")

    # 通过 path 字段解析祖先链
    ancestors: list[RegionAncestor] = []
    if region.path:
        parts = region.path.split("/")
        for code in parts:
            if not code:
                continue
            ancestor = (
                db.query(AdministrativeRegion)
                .filter(
                    AdministrativeRegion.code == code,
                    AdministrativeRegion.is_active == True,
                )
                .first()
            )
            if ancestor and ancestor.id != region.id:
                ancestors.append(
                    RegionAncestor(
                        id=ancestor.id,
                        code=ancestor.code,
                        name=ancestor.name,
                        level=ancestor.level,
                    )
                )

    resp = _region_to_response(region)
    resp.has_children = _count_children(db, region.id)
    return RegionDetailResponse(
        **resp.model_dump(),
        ancestors=ancestors,
    )


@router.get("/admin/regions/seed-status")
def region_seed_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """行政区划数据状态：各级数量 + 是否需要 seed。仅管理员。"""
    counts = {}
    for lv in range(4):
        counts[str(lv)] = (
            db.query(AdministrativeRegion)
            .filter(
                AdministrativeRegion.level == lv,
                AdministrativeRegion.is_active == True,
            )
            .count()
        )
    return {
        "counts": counts,
        "needed": need_region_seed(db),
        "total": sum(counts.values()),
    }


@router.post("/admin/regions/seed")
def region_seed_run(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """手动 upsert 行政区划数据（更新/补缺失）。仅管理员。同步执行。"""
    result = upsert_administrative_regions(db)
    return result
