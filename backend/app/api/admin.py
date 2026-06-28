from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
from app.core.security import get_current_user, get_current_admin_user
from app.core.database import get_db
from app.models.user import User
from app.models.product import ProductRecord
from app.models.recipe import Recipe
from app.models.merchant import Merchant
from app.models.map_config import MapConfiguration
from app.models.system_config import SystemConfig
from app.schemas.auth import UserResponse, AdminConfigUpdate, ConfigResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.services.recipe_import_service import RecipeImportService


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
    """获取服务器上未被任何菜谱引用的图片列表 - 仅限管理员"""
    static_dir = Path(__file__).parent.parent.parent / "static" / "images" / "recipes"
    if not static_dir.exists():
        return {"images": []}

    # 获取所有菜谱引用的图片
    all_recipes = db.query(Recipe.images).all()
    used_names: set = set()
    for row in all_recipes:
        if row[0]:
            for img in row[0]:
                name = img.split("/")[-1] if "/" in img else img
                if name:
                    used_names.add(name)

    # 扫描目录
    unused = []
    if not static_dir.is_dir():
        return {"images": []}
    for f in sorted(static_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file() and f.name not in used_names:
            stat = f.stat()
            unused.append({
                "filename": f.name,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "url": f"/static/images/recipes/{f.name}",
            })

    return {"images": unused}


@router.post("/images/unused/delete")
async def delete_unused_images(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """删除指定的未使用图片 - 仅限管理员"""
    paths = body.get("paths", [])
    if not paths:
        raise HTTPException(status_code=400, detail="缺少 paths")

    static_dir = Path(__file__).parent.parent.parent / "static" / "images" / "recipes"
    deleted: list = []
    errors: list = []

    for filename in paths:
        file_path = static_dir / filename
        try:
            if file_path.exists():
                file_path.unlink()
                deleted.append(filename)
            else:
                errors.append(f"{filename}: 文件不存在")
        except Exception as e:
            errors.append(f"{filename}: {str(e)}")

    return {"deleted": deleted, "errors": errors}