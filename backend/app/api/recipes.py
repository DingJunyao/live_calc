from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session, load_only
from sqlalchemy import or_, and_
from typing import List, Optional
from decimal import Decimal
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.recipe import Recipe, RecipeIngredient, RecipeCostHistory
from app.models.nutrition import Ingredient
from app.schemas.recipe import (
    RecipeCreate,
    RecipeResponse,
    RecipeDetailResponse,
    RecipeCostResponse,
    RecipeNutritionResponse,
    RecipeIngredientDetail,
    RecipeCostHistoryResponse,
    RecipeCostRangeResponse
)
from app.schemas.common import PaginatedResponse
from app.services.recipe_service import (
    calculate_recipe_cost,
    calculate_recipe_nutrition,
    calculate_recipe_cost_trend,
    calculate_recipe_cost_range_trend
)
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
            ingredient = db.query(Ingredient).options(
                load_only(
                    Ingredient.id,
                    Ingredient.name,
                    Ingredient.is_active
                )
            ).filter(
                Ingredient.name == ingredient_data.ingredient_name
            ).first()
            if not ingredient:
                continue

            recipe_ingredient = RecipeIngredient(
                recipe_id=db_recipe.id,
                ingredient_id=ingredient.id,
                quantity=ingredient_data.quantity,
                quantity_range=ingredient_data.quantity_range,
                unit_id=ingredient_data.unit_id,
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


@router.get("", response_model=PaginatedResponse)
@router.get("/", response_model=PaginatedResponse)
async def get_recipes(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    tag: Optional[str] = Query(None, description="标签过滤"),
    search: Optional[str] = Query(None, alias="q", description="搜索菜谱名称"),
    include_cost: bool = Query(True, description="是否包含成本和营养信息"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱列表（分页）"""
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

        # 应用搜索过滤（如果指定了搜索关键词）
        if search:
            all_recipes_query = all_recipes_query.filter(Recipe.name.contains(search))

        total = all_recipes_query.count()
        recipes = all_recipes_query.order_by(Recipe.created_at.desc()).offset(skip).limit(limit).all()
        page = skip // limit + 1

        # 手动构造响应对象列表
        items = []

        # 如果需要包含成本和营养信息，批量计算它们
        if include_cost:
            from app.services.recipe_service import batch_calculate_recipes_cost_nutrition

            recipe_ids = [recipe.id for recipe in recipes]
            batch_results = await batch_calculate_recipes_cost_nutrition(recipe_ids, current_user.id, db)

            # 为每个菜谱构建响应
            for recipe in recipes:
                # 确保 JSON 字段不为 None
                tags_list = recipe.tags if isinstance(recipe.tags, list) else []
                cooking_steps_list = recipe.cooking_steps if isinstance(recipe.cooking_steps, list) else []
                tips_list = recipe.tips if isinstance(recipe.tips, list) else []
                images_list = recipe.images if isinstance(recipe.images, list) else []

                # 从批量结果中获取成本和营养信息
                recipe_result = batch_results.get(recipe.id, {})
                cost_result = recipe_result.get('cost')
                nutrition_result = recipe_result.get('nutrition')

                # 从成本结果提取数据
                estimated_cost = None
                if cost_result and 'total_cost' in cost_result:
                    estimated_cost = cost_result['total_cost']

                # 从营养结果提取数据
                calories = None
                protein = None
                if nutrition_result:
                    calories = nutrition_result.get('total_calories')
                    protein = nutrition_result.get('total_protein')

                items.append(RecipeResponse(
                    id=recipe.id,
                    name=recipe.name,
                    source=recipe.source or "",
                    category=recipe.category,
                    tags=tags_list,
                    cooking_steps=cooking_steps_list,
                    total_time_minutes=recipe.total_time_minutes,
                    difficulty=recipe.difficulty,
                    servings=recipe.servings,
                    tips=tips_list,
                    images=images_list,
                    result_ingredient_id=recipe.result_ingredient_id,
                    created_at=recipe.created_at,
                    updated_at=recipe.updated_at,
                    estimated_cost=estimated_cost,
                    calories=int(calories) if calories is not None else None,
                    protein=protein
                ))
        else:
            # 不需要成本和营养信息时，直接构建响应
            for recipe in recipes:
                # 确保 JSON 字段不为 None
                tags_list = recipe.tags if isinstance(recipe.tags, list) else []
                cooking_steps_list = recipe.cooking_steps if isinstance(recipe.cooking_steps, list) else []
                tips_list = recipe.tips if isinstance(recipe.tips, list) else []
                images_list = recipe.images if isinstance(recipe.images, list) else []

                items.append(RecipeResponse(
                    id=recipe.id,
                    name=recipe.name,
                    source=recipe.source or "",
                    category=recipe.category,
                    tags=tags_list,
                    cooking_steps=cooking_steps_list,
                    total_time_minutes=recipe.total_time_minutes,
                    difficulty=recipe.difficulty,
                    servings=recipe.servings,
                    tips=tips_list,
                    images=images_list,
                    result_ingredient_id=recipe.result_ingredient_id,
                    created_at=recipe.created_at,
                    updated_at=recipe.updated_at,
                    estimated_cost=None,
                    calories=None,
                    protein=None
                ))

        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=limit
        )
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
            ingredient = db.query(Ingredient).options(
                load_only(
                    Ingredient.id,
                    Ingredient.name,
                    Ingredient.is_active
                )
            ).filter(Ingredient.id == ri.ingredient_id).first()
            if ingredient is None:
                continue
            ingredients_detail.append(RecipeIngredientDetail(
                id=ri.id,  # 添加recipe_ingredient的ID
                ingredient_id=ingredient.id,
                name=ingredient.name,
                quantity=ri.quantity or "",
                quantity_range=ri.quantity_range,
                unit=ri.unit.abbreviation if ri.unit else None,
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
        result = check_and_import_from_json_repo(db, user_id=current_user.id)
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
        raise HTTPException(status_code=500, detail=f"获取图片失败：{str(e)}")


@router.get("/{recipe_id}/cost-history", response_model=List[RecipeCostHistoryResponse])
async def get_recipe_cost_history(
    recipe_id: int,
    days: int = Query(90, ge=7, le=365, description="查询天数"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱成本趋势

    根据菜谱中食材的历史价格，计算每一天的菜谱成本。
    如果某天某食材没有价格数据，则向前找食材价格；
    如果没有食材价格，则以时间最早的为准。
    """
    try:
        # 验证菜谱存在且属于当前用户
        recipe = db.query(Recipe).filter(
            Recipe.id == recipe_id,
            Recipe.user_id == current_user.id
        ).first()

        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        # 实时计算成本趋势
        cost_trend = calculate_recipe_cost_trend(recipe_id, current_user.id, db, days)

        # 转换为响应模型（按时间倒序）
        return [
            RecipeCostHistoryResponse(
                id=i,  # 使用索引作为临时 ID
                recipe_id=recipe_id,
                recipe_name=recipe.name,
                total_cost=item["total_cost"],
                recorded_at=item["recorded_at"],
                exchange_rate=100  # 默认无汇率转换
            )
            for i, item in enumerate(reversed(cost_trend))
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取成本历史失败：{str(e)}")


@router.get("/{recipe_id}/cost-history-range", response_model=List[RecipeCostRangeResponse])
async def get_recipe_cost_history_range(
    recipe_id: int,
    days: int = Query(90, ge=7, le=365, description="查询天数"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱成本区间趋势

    返回菜谱在指定日期范围内的成本区间数据（最小值、最大值、平均值）。
    反映当天不同商家价格波动对菜谱总成本的影响。

    计算规则：
    - 区间最大值：每道食材在当天的最高价格之和
    - 区间最小值：每道食材在当天的最低价格之和
    - 平均值：每道食材在当天的平均价格之和

    使用前向填充机制处理缺失的价格记录。
    """
    try:
        # 验证菜谱存在且属于当前用户
        recipe = db.query(Recipe).filter(
            Recipe.id == recipe_id,
            Recipe.user_id == current_user.id
        ).first()

        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        # 计算成本区间趋势
        cost_range_trend = calculate_recipe_cost_range_trend(recipe_id, current_user.id, db, days)

        # 转换为响应模型（按时间倒序）
        return [
            RecipeCostRangeResponse(
                id=i,  # 使用索引作为临时 ID
                recipe_id=recipe_id,
                recipe_name=recipe.name,
                min_cost=item["min_cost"],
                max_cost=item["max_cost"],
                avg_cost=item["avg_cost"],
                date=item["date"],
                recorded_at=item["recorded_at"]
            )
            for i, item in enumerate(reversed(cost_range_trend))
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取成本区间历史失败：{str(e)}")
