from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.product import ProductRecord
from app.models.recipe import Recipe
from app.models.merchant import Merchant
from app.schemas.auth import UserResponse
from pydantic import BaseModel
from typing import Optional, Dict, List
from app.services.recipe_import_service import RecipeImportService


class TiandituConfig(BaseModel):
    token: str
    type: str = 'vec'


class MapApiKeys(BaseModel):
    amap: Optional[str] = None
    baidu: Optional[str] = None
    tencent: Optional[str] = None
    tianditu: Optional[TiandituConfig] = None


class GeocodingApiKeys(BaseModel):
    amap: Optional[str] = None
    baidu: Optional[str] = None
    tencent: Optional[str] = None


class GeocodingConfig(BaseModel):
    enabled_service: str = 'amap'
    api_keys: GeocodingApiKeys = GeocodingApiKeys()
    nominatim_url: str = ''


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

# 地图配置存储（实际项目中应该存储到数据库）
_map_config: Optional[MapConfig] = None


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

    global _map_config
    if _map_config is None:
        _map_config = MapConfig()

    return _map_config


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

    global _map_config
    _map_config = config

    return _map_config


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