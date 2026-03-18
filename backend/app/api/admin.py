from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.product import ProductRecord
from app.models.recipe import Recipe
from app.models.merchant import Merchant
from app.models.map_config import MapConfiguration
from app.schemas.auth import UserResponse
from pydantic import BaseModel
from typing import Optional, List
from app.services.recipe_import_service import RecipeImportService


class TiandituConfig(BaseModel):
    token: str
    type: str = 'vec'


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
    current_user: UserResponse = Depends(get_current_user)
):
    """获取地图配置 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="仅限管理员访问"
        )

    stored_config = get_stored_map_config(db)
    return MapConfig(**stored_config.to_dict())


@router.put("/map-config", response_model=MapConfig)
async def update_map_config(
    config: MapConfig,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """更新地图配置 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="仅限管理员访问"
        )

    # 将 Pydantic 模型转换为字典并适配数据库字段
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
    current_user: UserResponse = Depends(get_current_user)
):
    """获取管理员统计信息 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="仅限管理员访问"
        )

    # 获取各种统计数据
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
    current_user: UserResponse = Depends(get_current_user)
):
    """从URL导入菜谱 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="仅限管理员访问"
        )

    try:
        import_service = RecipeImportService(db)
        result = import_service.import_recipes_from_cook_repo(repo_url=url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/import-recipes-initial")
async def import_initial_recipes(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """导入初始菜谱 - 仅限管理员"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="仅限管理员访问"
        )

    try:
        from app.services.recipe_import_service import check_and_import_initial_recipes
        result = check_and_import_initial_recipes(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入初始菜谱失败: {str(e)}")