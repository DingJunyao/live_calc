from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session, load_only
import os
from sqlalchemy import or_, and_
from typing import List, Optional
from decimal import Decimal
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.recipe import Recipe, RecipeIngredient, RecipeCostHistory
from app.models.nutrition import Ingredient
from app.models.unit import Unit
from app.schemas.recipe import (
    RecipeCreate,
    RecipeUpdate,
    RecipeResponse,
    RecipeDetailResponse,
    RecipeCostResponse,
    RecipeNutritionResponse,
    RecipeIngredientDetail,
    RecipeCostHistoryResponse,
    RecipeCostRangeResponse,
    RecipeMerchantCostResponse,
    MerchantCostItem
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


def _apply_recipe_special_conditions(query, has_unpriced_ingredient, has_unnourished_ingredient):
    """Apply special condition filters to a Recipe query."""
    from app.models.product_entity import Product
    from app.models.product import ProductRecord
    from app.models.nutrition_data import NutritionData
    from sqlalchemy import exists, and_

    if has_unpriced_ingredient:
        # EXISTS ingredient in recipe with active product but no price records
        query = query.filter(
            exists().where(
                and_(
                    RecipeIngredient.recipe_id == Recipe.id,
                    exists().where(
                        and_(
                            Product.ingredient_id == RecipeIngredient.ingredient_id,
                            Product.is_active == True,
                            ~exists().where(ProductRecord.product_id == Product.id)
                        )
                    )
                )
            )
        )

    if has_unnourished_ingredient:
        # EXISTS ingredient in recipe with no verified nutrition data
        query = query.filter(
            exists().where(
                and_(
                    RecipeIngredient.recipe_id == Recipe.id,
                    ~exists().where(
                        and_(
                            NutritionData.ingredient_id == RecipeIngredient.ingredient_id,
                            NutritionData.is_verified == True
                        )
                    )
                )
            )
        )

    return query


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
    search: Optional[str] = Query(None, description="搜索菜谱名称"),
    categories: Optional[str] = Query(None, description="菜谱分类列表，逗号分隔"),
    difficulties: Optional[str] = Query(None, description="难度列表，逗号分隔"),
    ingredient_ids: Optional[str] = Query(None, description="食材ID列表，逗号分隔（筛选包含任意该食材的菜谱，包括可选食材）"),
    has_unpriced_ingredient: bool = Query(False, description="筛选存在原料没有维护价格的菜谱"),
    has_unnourished_ingredient: bool = Query(False, description="筛选存在原料没有维护营养成分的菜谱"),
    include_cost: bool = Query(False, description="是否包含成本和营养信息（列表页默认不计算，通过 batch-cost 懒加载）"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱列表（分页）"""
    try:
        # 获取当前用户的菜谱（允许编辑，排除软删除）
        user_recipes = db.query(Recipe).filter(
            Recipe.user_id == current_user.id,
            Recipe.is_active == True
        )

        # 获取公共导入的菜谱（非当前用户所有，但有来源标识，排除软删除）
        public_imported_recipes = db.query(Recipe).filter(
            Recipe.source != None,
            Recipe.is_active == True
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

        # 应用分类筛选
        if categories:
            cat_list = [c.strip() for c in categories.split(',') if c.strip()]
            if cat_list:
                all_recipes_query = all_recipes_query.filter(Recipe.category.in_(cat_list))

        # 应用难度筛选
        if difficulties:
            diff_list = [d.strip() for d in difficulties.split(',') if d.strip()]
            if diff_list:
                all_recipes_query = all_recipes_query.filter(Recipe.difficulty.in_(diff_list))

        # 应用食材筛选（包含任意指定食材的菜谱，包括可选食材）
        if ingredient_ids:
            ing_id_list = [int(i.strip()) for i in ingredient_ids.split(',') if i.strip()]
            if ing_id_list:
                recipe_ids_subq = db.query(RecipeIngredient.recipe_id).filter(
                    RecipeIngredient.ingredient_id.in_(ing_id_list)
                ).distinct().subquery()
                all_recipes_query = all_recipes_query.filter(Recipe.id.in_(recipe_ids_subq))

        # 应用特殊条件过滤
        all_recipes_query = _apply_recipe_special_conditions(
            all_recipes_query, has_unpriced_ingredient, has_unnourished_ingredient
        )

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
                    description=recipe.description,
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
                    description=recipe.description,
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


@router.post("/batch-cost")
async def get_recipes_batch_cost(
    request: dict,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """批量获取菜谱的成本和卡路里（用于列表页懒加载）"""
    recipe_ids = request.get("ids", [])
    if not recipe_ids:
        return {}

    from app.services.recipe_service import batch_calculate_recipes_cost_nutrition
    batch_results = await batch_calculate_recipes_cost_nutrition(recipe_ids, current_user.id, db)

    result = {}
    for recipe_id, data in batch_results.items():
        cost = data.get("cost")
        nutrition = data.get("nutrition")
        result[str(recipe_id)] = {
            "estimated_cost": float(cost["total_cost"]) if cost and cost.get("total_cost") is not None else None,
            "calories": int(nutrition["total_calories"]) if nutrition and nutrition.get("total_calories") else None,
        }
    return result


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
            description=recipe.description,
            images=recipe.images or [],
            created_at=recipe.created_at,
            updated_at=recipe.updated_at,
            ingredients=ingredients_detail
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取菜谱详情失败: {str(e)}")


@router.put("/{recipe_id}", response_model=RecipeDetailResponse)
async def update_recipe(
    recipe_id: int,
    update_data: RecipeUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新菜谱（部分更新，仅修改传入的字段）

    管理员可修改任意菜谱，普通用户只能修改自己创建的菜谱。
    """
    try:
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        if recipe.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="无权修改此菜谱")

        exclude_unset = update_data.model_dump(exclude_unset=True)

        # 处理 ingredients 全量替换
        if "ingredients" in exclude_unset:
            # 删除旧的原料关联
            db.query(RecipeIngredient).filter(
                RecipeIngredient.recipe_id == recipe_id
            ).delete()

            # 创建新的原料关联
            for ing_data in update_data.ingredients:
                ingredient = db.query(Ingredient).options(
                    load_only(Ingredient.id, Ingredient.name, Ingredient.is_active)
                ).filter(Ingredient.name == ing_data.ingredient_name).first()
                if not ingredient:
                    continue

                db_ri = RecipeIngredient(
                    recipe_id=recipe_id,
                    ingredient_id=ingredient.id,
                    quantity=ing_data.quantity,
                    quantity_range=ing_data.quantity_range,
                    unit_id=ing_data.unit_id,
                    is_optional=ing_data.is_optional,
                    note=ing_data.note,
                    original_quantity=ing_data.original_quantity
                )
                db.add(db_ri)

            # 从 update dict 中移除 ingredients，避免直接设置到 Recipe 模型
            exclude_unset.pop("ingredients")

        # 更新标量字段（只更新传入的字段）
        for field, value in exclude_unset.items():
            if hasattr(recipe, field):
                setattr(recipe, field, value)

        # 显式标记 updated_at
        from datetime import datetime, timezone
        recipe.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(recipe)

        # 返回完整的详情数据（复用 detail 响应构建逻辑）
        return _build_recipe_detail_response(recipe, db)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新菜谱失败: {str(e)}")


def _build_recipe_detail_response(recipe: Recipe, db: Session) -> RecipeDetailResponse:
    """构建菜谱详情响应（辅助函数，避免重复代码）"""
    recipe_ingredients = db.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == recipe.id
    ).all()

    ingredients_detail = []
    for ri in recipe_ingredients:
        ingredient = db.query(Ingredient).options(
            load_only(Ingredient.id, Ingredient.name, Ingredient.is_active)
        ).filter(Ingredient.id == ri.ingredient_id).first()
        if ingredient is None:
            continue
        ingredients_detail.append(RecipeIngredientDetail(
            id=ri.id,
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
        description=recipe.description,
        images=recipe.images or [],
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
        ingredients=ingredients_detail
    )


@router.delete("/{recipe_id}")
async def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """软删除菜谱

    管理员可删除任意菜谱，普通用户只能删除自己创建的菜谱。
    """
    try:
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        if recipe.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="无权删除此菜谱")

        recipe.is_active = False
        db.commit()
        return {"detail": "菜谱已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除菜谱失败: {str(e)}")


@router.post("/{recipe_id}/images")
async def upload_recipe_image(
    recipe_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """上传菜谱配图"""
    try:
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        if recipe.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="无权修改此菜谱")

        # 验证文件类型
        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if file.content_type and file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="仅支持 JPEG、PNG、GIF、WebP 格式的图片")

        # 确保存储目录存在
        from pathlib import Path
        static_images_dir = Path(__file__).parent.parent.parent / "static" / "images" / "recipes"
        static_images_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        import uuid
        ext = os.path.splitext(file.filename or "image.jpg")[1] or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = static_images_dir / filename

        # 保存文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # 更新菜谱的 images 列表
        image_rel_path = f"/static/images/recipes/{filename}"
        current_images = recipe.images or []
        current_images.append(image_rel_path)
        recipe.images = current_images

        from datetime import datetime, timezone
        recipe.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {"image_path": image_rel_path, "image_url": f"/api/v1{image_rel_path}"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"上传图片失败: {str(e)}")


@router.delete("/{recipe_id}/images/{filename}")
async def delete_recipe_image(
    recipe_id: int,
    filename: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """删除菜谱配图"""
    try:
        recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        if recipe.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="无权修改此菜谱")

        # 从 images 列表中移除
        current_images = recipe.images or []
        target_path = f"/static/images/recipes/{filename}"
        if target_path not in current_images:
            raise HTTPException(status_code=404, detail="图片不存在")

        current_images.remove(target_path)
        recipe.images = current_images

        from datetime import datetime, timezone
        recipe.updated_at = datetime.now(timezone.utc)
        db.commit()

        # 删除物理文件（不阻止成功响应）
        from pathlib import Path
        file_path = Path(__file__).parent.parent.parent / "static" / "images" / "recipes" / filename
        if file_path.exists():
            file_path.unlink()

        return {"detail": "图片已删除"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除图片失败: {str(e)}")


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


@router.get("/{recipe_id}/merchant-costs", response_model=RecipeMerchantCostResponse)
async def get_recipe_merchant_costs(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """计算菜谱按商家购买的总成本估算"""
    try:
        recipe = db.query(Recipe).filter(
            Recipe.id == recipe_id,
            or_(Recipe.user_id == current_user.id, Recipe.source != None)
        ).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        recipe_ingredients = db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id == recipe_id
        ).all()

        if not recipe_ingredients:
            return RecipeMerchantCostResponse(merchants=[])

        from app.models.product_entity import Product
        from app.models.product import ProductRecord
        from app.models.merchant import Merchant
        from app.services.unit_conversion_service import UnitConversionService
        from sqlalchemy.orm import joinedload

        unit_service = UnitConversionService(db)
        total_ingredients = len(recipe_ingredients)

        merchant_data: dict = {}

        for ri in recipe_ingredients:
            ingredient = ri.ingredient
            if not ingredient or not ingredient.is_active:
                continue

            target_unit = ingredient.default_unit.abbreviation if ingredient.default_unit else None

            products = db.query(Product).filter(
                Product.ingredient_id == ingredient.id,
                Product.is_active == True
            ).all()

            product_ids = [p.id for p in products if p.id]
            if not product_ids:
                continue

            records = db.query(ProductRecord).options(
                joinedload(ProductRecord.original_unit),
                joinedload(ProductRecord.merchant)
            ).join(
                Merchant, ProductRecord.merchant_id == Merchant.id
            ).filter(
                ProductRecord.product_id.in_(product_ids),
                ProductRecord.merchant_id.isnot(None),
                ProductRecord.is_active == True,
                Merchant.is_open == True
            ).order_by(ProductRecord.recorded_at.desc()).all()

            merchant_latest: dict = {}
            for record in records:
                mid = record.merchant_id
                if mid not in merchant_latest:
                    merchant_latest[mid] = record

            for mid, record in merchant_latest.items():
                if record.price is None or record.original_quantity is None or record.original_quantity <= 0 or not record.original_unit:
                    continue

                unit_price = None
                total_price = Decimal(str(record.price))
                orig_qty = float(record.original_quantity)
                orig_unit_abbr = record.original_unit.abbreviation

                if target_unit and orig_unit_abbr != target_unit:
                    convert_result = unit_service.convert(
                        orig_qty, orig_unit_abbr, target_unit,
                        entity_type="ingredient",
                        entity_id=ingredient.id
                    )
                    if convert_result is not None:
                        converted_qty, _ = convert_result
                        if converted_qty and float(converted_qty) > 0:
                            unit_price = total_price / Decimal(str(converted_qty))
                else:
                    unit_price = total_price / Decimal(str(orig_qty)) if orig_qty > 0 else None

                if unit_price is None or unit_price <= 0:
                    continue

                ingredient_qty = 0
                if ri.quantity:
                    try:
                        ingredient_qty = float(ri.quantity)
                    except (ValueError, TypeError):
                        pass
                elif ri.quantity_range:
                    qr = ri.quantity_range
                    if isinstance(qr, dict):
                        q_min = float(qr.get("min", 0) or 0)
                        q_max = float(qr.get("max", 0) or 0)
                        ingredient_qty = (q_min + q_max) / 2

                ingredient_cost = unit_price * Decimal(str(ingredient_qty))

                merchant_name = record.merchant.name if record.merchant else f"商家{mid}"
                if mid not in merchant_data:
                    merchant_data[mid] = {
                        "merchant_name": merchant_name,
                        "total_cost": Decimal("0"),
                        "covered_set": set(),
                    }
                merchant_data[mid]["total_cost"] += ingredient_cost
                merchant_data[mid]["covered_set"].add(ri.id)

        merchants_list = []
        for mid, data in merchant_data.items():
            missing_names = []
            for ri in recipe_ingredients:
                if ri.id not in data["covered_set"]:
                    missing_names.append(ri.ingredient.name if ri.ingredient else "未知食材")

            merchants_list.append(MerchantCostItem(
                merchant_id=mid,
                merchant_name=data["merchant_name"],
                total_cost=float(round(data["total_cost"], 2)),
                covered_count=len(data["covered_set"]),
                total_ingredients=total_ingredients,
                missing_ingredients=missing_names,
                is_recommended=False,
            ))

        if merchants_list:
            merchants_list.sort(key=lambda m: (-m.covered_count, m.total_cost))
            if merchants_list:
                merchants_list[0].is_recommended = True

        return RecipeMerchantCostResponse(merchants=merchants_list)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算商家成本失败: {str(e)}")


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
        from app.services.enhanced_recipe_import_service import check_and_import_initial_recipes
        result = check_and_import_initial_recipes(db, user_id=current_user.id)
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

        # 将相对路径转换为完整的远程 URL
        image_urls = []
        repo_url = os.getenv("DATA_REPO_URL", "https://github.com/DingJunyao/HowToCook_json.git").rstrip("/").removesuffix(".git")
        branch = os.getenv("DATA_REPO_BRANCH", "corr")
        data_dir = os.getenv("DATA_REPO_DIR", "out")
        repo_path = repo_url.split("github.com/")[-1]
        for image_path in recipe.images:
            full_url = f"https://raw.githubusercontent.com/{repo_path}/{branch}/{data_dir}/{image_path}"
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
    offset_days: int = Query(0, ge=0, description="偏移天数（从 offset_days 天前开始算）"),
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

    offset_days 用于分批加载。例如 days=30, offset_days=0 为近30天；
    days=60, offset_days=30 为第31天至第90天。

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
        cost_range_trend = calculate_recipe_cost_range_trend(recipe_id, current_user.id, db, days, offset_days)

        # 转换为响应模型（按时间顺序）
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
            for i, item in enumerate(cost_range_trend)
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取成本区间历史失败：{str(e)}")
