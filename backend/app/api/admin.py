from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime, timezone, timedelta
from app.core.security import get_current_user, get_current_admin_user
from app.core.database import get_db
from app.models.user import User
from app.models.product import ProductRecord
from app.models.product_entity import Product as ProductEntity
from app.models.recipe import Recipe
from app.models.merchant import Merchant
from app.models.map_config import MapConfiguration
from app.models.image_tracking import ImageTracking
from app.models.system_config import SystemConfig
from app.schemas.auth import UserResponse, AdminConfigUpdate, ConfigResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.services.recipe_import_service import RecipeImportService
from app.services.storage import get_storage


def _collect_used_image_keys(db) -> set[str]:
    """收集所有图片字段引用的 storage key，供未使用图片清理使用。

    来源：Recipe.images（JSON list）、users.avatar（单 key）、
    ProductEntity.image_url（仅不以 http 开头的内部 key）。
    """
    used: set[str] = set()

    for (images_list,) in db.query(Recipe.images).all():
        if images_list:
            for img in images_list:
                if isinstance(img, str) and img:
                    used.add(img)

    for (avatar,) in db.query(User.avatar).filter(User.avatar.isnot(None)).all():
        if avatar:
            used.add(avatar)

    for (url,) in db.query(ProductEntity.image_url).filter(ProductEntity.image_url.isnot(None)).all():
        if url and not url.startswith("http"):
            used.add(url)

    return used


class TiandituConfig(BaseModel):
    token: str
    type: str = 'vec'


class LocalImportRequest(BaseModel):
    local_path: str


class MapApiKeys(BaseModel):
    amap: Optional[str] = None
    amap_security: Optional[str] = None
    baidu: Optional[str] = None
    tencent: Optional[str] = None
    tianditu: Optional[TiandituConfig] = None


class GeocodingConfig(BaseModel):
    enabled_service: str = 'amap'
    amap_key: Optional[str] = None
    baidu_key: Optional[str] = None
    tencent_key: Optional[str] = None
    nominatim_url: str = ''
    nominatim_email: Optional[str] = None


class MapConfig(BaseModel):
    map_enabled: bool = True
    available_maps: List[str] = ['amap', 'baidu', 'tencent', 'tianditu', 'osm']
    default_map: str = 'amap'
    map_api_keys: MapApiKeys = MapApiKeys()
    geocoding: GeocodingConfig = GeocodingConfig()


class AdminStatsResponse(BaseModel):
    users: int
    products: int
    recipes: int
    merchants: int


router = APIRouter()

# 默认地图配置
DEFAULT_MAP_CONFIG = {
    "map_enabled": True,
    "available_maps": ['amap', 'baidu', 'tencent', 'tianditu', 'osm'],
    "default_map": 'amap',
    "map_api_keys": {
        "amap": None,
        "amap_security": None,
        "baidu": None,
        "tencent": None,
        "tianditu": {"token": "", "type": "vec"}
    },
    "geocoding": {
        "enabled_service": 'amap',
        "amap_key": None,
        "baidu_key": None,
        "tencent_key": None,
        "nominatim_url": '',
        "nominatim_email": None
    }
}


def get_stored_map_config(db: Session) -> MapConfiguration:
    """从数据库获取地图配置，如果不存在则创建默认配置"""
    config = db.query(MapConfiguration).first()
    if not config:
        # 如果没有配置，创建默认配置
        config = MapConfiguration(**DEFAULT_MAP_CONFIG)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def update_stored_map_config(db: Session, config_data: dict) -> MapConfiguration:
    """更新数据库中的地图配置"""
    config = db.query(MapConfiguration).first()
    if not config:
        # 如果没有配置，创建新配置
        config = MapConfiguration(**config_data)
        db.add(config)
    else:
        # 更新现有配置
        for attr, value in config_data.items():
            setattr(config, attr, value)

    db.commit()
    db.refresh(config)
    return config


@router.get("/map-config", response_model=MapConfig)
async def get_map_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取地图配置 - 仅限管理员"""
    stored_config = get_stored_map_config(db)
    return MapConfig(**stored_config.to_dict())


@router.put("/map-config", response_model=MapConfig)
async def update_map_config(
    config: MapConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """更新地图配置 - 仅限管理员"""
    config_data = {
        "map_enabled": config.map_enabled,
        "available_maps": config.available_maps,
        "default_map": config.default_map,
        "map_api_keys": config.map_api_keys.dict(),
        "geocoding": config.geocoding.dict()
    }

    updated_config = update_stored_map_config(db, config_data)
    return MapConfig(**updated_config.to_dict())


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取管理员统计信息 - 仅限管理员"""
    users_count = db.query(User).count()
    products_count = db.query(ProductRecord).count()
    recipes_count = db.query(Recipe).count()
    merchants_count = db.query(Merchant).count()

    return AdminStatsResponse(
        users=users_count,
        products=products_count,
        recipes=recipes_count,
        merchants=merchants_count
    )


@router.post("/import-recipes-from-url")
async def import_recipes_from_url(
    url: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """从URL导入菜谱 - 仅限管理员"""
    try:
        import_service = RecipeImportService(db)
        result = import_service.import_recipes_from_cook_repo(repo_url=url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/import-recipes-initial")
async def import_initial_recipes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """导入初始菜谱 - 仅限管理员"""
    try:
        from app.services.enhanced_recipe_import_service import check_and_import_initial_recipes
        result = check_and_import_initial_recipes(db, user_id=current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入初始菜谱失败: {str(e)}")


@router.post("/import-from-local-path")
async def import_from_local_path(
    request: LocalImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """从本地路径导入菜谱数据 - 仅限管理员"""
    try:
        from app.services.enhanced_recipe_import_service import EnhancedRecipeImportService
        service = EnhancedRecipeImportService(db, user_id=current_user.id)
        result = service.import_from_local_dir(request.local_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"从本地路径导入失败: {str(e)}")


# ==================== 动态配置 ====================

@router.get("/config")
async def get_admin_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取所有动态配置项 - 仅限管理员"""
    rows = db.query(SystemConfig).all()
    config: Dict[str, str] = {r.key: r.value for r in rows}
    return config


@router.put("/config", response_model=ConfigResponse)
async def update_admin_config(
    body: AdminConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """批量更新动态配置 - 仅限管理员"""
    if body.registration_require_invite_code is not None:
        row = db.query(SystemConfig).filter(
            SystemConfig.key == "registration_require_invite_code"
        ).first()
        val = "true" if body.registration_require_invite_code else "false"
        if row:
            row.value = val
        else:
            db.add(SystemConfig(key="registration_require_invite_code", value=val))
    db.commit()
    return ConfigResponse(
        registration_require_invite_code=body.registration_require_invite_code
        if body.registration_require_invite_code is not None
        else False
    )


# ==================== 图片管理 ====================

@router.get("/images/unused")
async def get_unused_images(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取未使用图片，按不再使用时间分组。

    分组（越老的越靠前，越安全）：
    - never_used: 从未引用（ref_count=0 AND last_used_at IS NULL）
    - 180d: 180 天以上
    - 90d: 90~180 天
    - 60d: 60~90 天
    - 30d: 30~60 天
    - recent: 30 天内
    """
    now = datetime.now(timezone.utc)
    used_keys = _collect_used_image_keys(db)
    storage = get_storage()

    rows = db.query(ImageTracking).filter(
        ImageTracking.ref_count == 0
    ).all()

    unused = [r for r in rows if r.key not in used_keys]

    def _ensure_utc(dt):
        if dt is not None and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _group_key(row):
        if row.last_used_at is None:
            return "never_used"
        last_used = _ensure_utc(row.last_used_at)
        days = (now - last_used).days
        if days >= 180:
            return "180d"
        if days >= 90:
            return "90d"
        if days >= 60:
            return "60d"
        if days >= 30:
            return "30d"
        return "recent"

    groups: dict[str, list[dict]] = {
        "never_used": [], "180d": [], "90d": [],
        "60d": [], "30d": [], "recent": [],
    }

    for row in unused:
        gk = _group_key(row)
        groups[gk].append({
            "key": row.key,
            "filename": row.key.split("/")[-1],
            "url": storage.url_for(row.key),
            "file_size": row.file_size,
            "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
        })

    group_order = ["never_used", "180d", "90d", "60d", "30d", "recent"]
    group_labels = {
        "never_used": "从未引用",
        "180d": "180 天以上不再使用",
        "90d": "90~180 天不再使用",
        "60d": "60~90 天不再使用",
        "30d": "30~60 天不再使用",
        "recent": "30 天内不再使用",
    }

    result_groups = []
    for gk in group_order:
        items = groups[gk]
        items.sort(key=lambda x: x.get("last_used_at") or "")
        result_groups.append({
            "key": gk,
            "label": group_labels[gk],
            "images": items,
            "count": len(items),
            "total_size": sum(item["file_size"] for item in items),
        })

    # 全量统计
    all_tracking = db.query(ImageTracking).all()
    total = len(all_tracking)
    used = sum(1 for r in all_tracking if r.ref_count > 0)
    unused_count = total - used
    used_size = sum(r.file_size for r in all_tracking if r.ref_count > 0)
    unused_size_t = sum(r.file_size for r in all_tracking if r.ref_count == 0 and r.key not in used_keys)

    return {
        "stats": {
            "total_images": total,
            "used_images": used,
            "unused_images": unused_count,
            "used_size": used_size,
            "unused_size": unused_size_t,
        },
        "groups": result_groups,
    }


@router.post("/images/scan")
async def scan_images(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """扫描存储后端，全量重建 image_tracking 表。

    每次系统启动时自动执行一次（lifespan 内调相同逻辑），
    也支持管理员手动调用刷新。失败不阻断启动。
    """
    from app.services.image_tracking import scan_all_images
    stats = scan_all_images(db)
    return {"stats": stats, "message": "扫描完成"}


@router.post("/images/unused/delete")
async def delete_unused_images(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """删除指定的未使用图片 - 仅限管理员

    接受 keys（完整 storage key 列表），直接调 storage.delete(key) 删除。
    不再硬编码 `recipes/` 前缀，支持所有子目录。
    """
    keys = body.get("keys", [])
    if not keys:
        raise HTTPException(status_code=400, detail="缺少 keys")

    storage = get_storage()
    deleted: list = []
    errors: list = []

    for key in keys:
        try:
            storage.delete(key)
            deleted.append(key)
        except Exception as e:
            errors.append(f"{key}: {str(e)}")

    return {"deleted": deleted, "errors": errors}