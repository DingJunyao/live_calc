from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.schemas.recipe import (
    RecipeCreate,
    RecipeResponse,
    RecipeDetailResponse,
    RecipeCostResponse,
    RecipeNutritionResponse,
    RecipeIngredientDetail
)
from app.services.recipe_service import calculate_recipe_cost, calculate_recipe_nutrition
from app.services.recipe_import_service import RecipeImportService
import shutil
import tempfile

router = APIRouter()


@router.post("", response_model=RecipeResponse)
async def create_recipe(
    recipe: RecipeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建菜谱"""
    try:
        db_recipe = Recipe(
            name=recipe.name,
            source=recipe.source,
            category=recipe.category,
            user_id=current_user.id,
            tags=recipe.tags,
            cooking_steps=[s.model_dump() for s in recipe.cooking_steps],
            total_time_minutes=recipe.total_time_minutes,
            difficulty=recipe.difficulty,
            servings=recipe.servings,
            tips=recipe.tips,
            images=recipe.images or []
        )
        db.add(db_recipe)
        db.flush()

        for ingredient_data in recipe.ingredients:
            # 查找食材
            ingredient = db.query(Ingredient).filter(
                Ingredient.name == ingredient_data.ingredient_name
            ).first()
            if not ingredient:
                continue

            recipe_ingredient = RecipeIngredient(
                recipe_id=db_recipe.id,
                ingredient_id=ingredient.id,
                quantity=ingredient_data.quantity,
                quantity_range=ingredient_data.quantity_range,
                unit=ingredient_data.unit,
                is_optional=ingredient_data.is_optional,
                note=ingredient_data.note,
                original_quantity=ingredient_data.original_quantity
            )
            db.add(recipe_ingredient)

        db.commit()
        db.refresh(db_recipe)
        return db_recipe
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建菜谱失败: {str(e)}")


@router.get("", response_model=List[RecipeResponse])
async def get_recipes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tag: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱列表"""
    try:
        # 获取当前用户的菜谱（允许编辑）
        user_recipes = db.query(Recipe).filter(Recipe.user_id == current_user.id)

        # 获取公共导入的菜谱（非当前用户所有，但有来源标识，通常是"howtocook"或其他标识）
        public_imported_recipes = db.query(Recipe).filter(
            Recipe.source != None
        )

        # 合并查询结果，去重
        all_recipes_query = user_recipes.union(public_imported_recipes)

        # 应用标签过滤（如果指定了标签）
        if tag:
            user_recipes = user_recipes.filter(Recipe.tags.contains([tag]))
            public_imported_recipes = public_imported_recipes.filter(Recipe.tags.contains([tag]))
            all_recipes_query = user_recipes.union(public_imported_recipes)

        recipes = all_recipes_query.order_by(Recipe.created_at.desc()).offset(skip).limit(limit).all()
        return recipes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取菜谱列表失败: {str(e)}")


@router.get("/{recipe_id}", response_model=RecipeDetailResponse)
async def get_recipe_detail(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱详情"""
    try:
        # 查询当前用户的菜谱或公共导入的菜谱
        recipe = db.query(Recipe).filter(
            Recipe.id == recipe_id,
            or_(
                Recipe.user_id == current_user.id,
                Recipe.source != None
            )
        ).first()

        # 如果没有找到，尝试只通过 source 查询（公共菜谱）
        if not recipe:
            recipe = db.query(Recipe).filter(
                Recipe.id == recipe_id,
                Recipe.source != None
            ).first()

        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        # 单独查询原料和食材信息
        recipe_ingredients = db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).all()

        # 获取原料详情，处理可能的空关联
        ingredients_detail = []
        for ri in recipe_ingredients:
            ingredient = db.query(Ingredient).filter(Ingredient.id == ri.ingredient_id).first()
            if ingredient is None:
                continue
            ingredients_detail.append(RecipeIngredientDetail(
                ingredient_id=ingredient.id,
                name=ingredient.name,
                quantity=ri.quantity or "",
                quantity_range=ri.quantity_range,
                unit=ri.unit,
                is_optional=ri.is_optional or False,
                note=ri.note,
                original_quantity=ri.original_quantity,
                nutrition_info=None
            ))

        return RecipeDetailResponse(
            id=recipe.id,
            name=recipe.name,
            source=recipe.source,
            category=recipe.category,
            tags=recipe.tags or [],
            cooking_steps=recipe.cooking_steps or [],
            total_time_minutes=recipe.total_time_minutes,
            difficulty=recipe.difficulty,
            servings=recipe.servings,
            tips=recipe.tips,
            images=recipe.images or [],
            created_at=recipe.created_at,
            updated_at=recipe.updated_at,
            ingredients=ingredients_detail
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取菜谱详情失败: {str(e)}")


@router.get("/{recipe_id}/cost", response_model=RecipeCostResponse)
async def get_recipe_cost(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算菜谱成本"""
    try:
        result = await calculate_recipe_cost(recipe_id, current_user.id, db=db)
        if not result:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        return RecipeCostResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算成本失败: {str(e)}")


@router.get("/{recipe_id}/nutrition", response_model=RecipeNutritionResponse)
async def get_recipe_nutrition(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算菜谱营养"""
    try:
        result = await calculate_recipe_nutrition(recipe_id, db=db)
        if not result:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        return RecipeNutritionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算营养失败: {str(e)}")


@router.post("/import-from-url")
async def import_recipes_from_url(
    url: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """从URL导入菜谱"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅限管理员访问")

    try:
        import_service = RecipeImportService(db)
        result = import_service.import_recipes_from_cook_repo(repo_url=url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/import-from-upload")
async def import_recipes_from_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """从上传的文件导入菜谱"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅限管理员访问")

    try:
        # 检查文件类型
        if not file.filename.endswith(('.zip', '.json', '.tar.gz')):
            raise HTTPException(status_code=400, detail="仅支持 .zip, .json, .tar.gz 文件")

        # 创建临时文件
        temp_file_path = tempfile.mktemp(suffix='.' + file.filename.split('.')[-1])

        # 保存上传的文件
        with open(temp_file_path, 'wb') as temp_file:
            shutil.copyfileobj(file.file, temp_file)

        try:
            import_service = RecipeImportService(db)
            result = import_service.import_recipes_from_zip_file(temp_file_path)
            return result
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/import-initial")
async def import_initial_recipes(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """导入初始菜谱（通常在首次启动时使用）"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅限管理员访问")

    try:
        from app.services.recipe_import_service import check_and_import_initial_recipes
        result = check_and_import_initial_recipes(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入初始菜谱失败: {str(e)}")


@router.post("/import-json-repo")
async def import_from_json_repo(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """从 JSON 仓库导入菜谱和原料"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅限管理员访问")

    try:
        from app.services.json_recipe_import_service import check_and_import_from_json_repo
        result = check_and_import_from_json_repo(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"从 JSON 仓库导入失败: {str(e)}")


@router.get("/{recipe_id}/images")
async def get_recipe_images(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱图片的完整 URL 列表"""
    try:
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        if not recipe.images:
            return {"images": []}

        # 将相对路径转换为完整的 GitHub raw URL
        image_urls = []
        for image_path in recipe.images:
            # 使用 GitHub raw URL
            full_url = f"https://raw.githubusercontent.com/DingJunyao/HowToCook_json/main/out/{image_path}"
            image_urls.append(full_url)

        return {"images": image_urls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图片失败: {str(e)}")
