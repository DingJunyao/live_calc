from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.product import ProductRecord
from app.models.recipe import Recipe
from app.models.location import Location
from app.schemas.auth import UserResponse
from pydantic import BaseModel
from app.services.recipe_import_service import RecipeImportService


class AdminStatsResponse(BaseModel):
    users: int
    products: int
    recipes: int
    locations: int


router = APIRouter()


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
    locations_count = db.query(Location).count()

    return AdminStatsResponse(
        users=users_count,
        products=products_count,
        recipes=recipes_count,
        locations=locations_count
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