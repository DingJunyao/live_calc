from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from app.schemas.common import PaginatedResponse
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, load_only, joinedload
from typing import List, Optional
import json
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData
from app.models.product_entity import Product
from app.models.product import ProductRecord
from app.schemas.nutrition import (
    IngredientResponse,
    NutritionDataResponse,
    NutritionMatchResponse,
    NutritionCorrectRequest,
    NutritionEditRequest,
    NutritionEditResponse
)
from pydantic import BaseModel, Field

router = APIRouter()


# ==================== 新增数据模型 ====================

class ImportRequest(BaseModel):
    """营养数据导入请求"""
    mode: str = Field(default="incremental", description="导入模式: incremental/full/force")
    force_update: bool = Field(default=False, description="是否强制更新已有数据")


class ImportResponse(BaseModel):
    """营养数据导入响应"""
    success: bool
    message: str
    total: int = 0
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: List[str] = []
    mode: str = "incremental"


class NutritionRequest(BaseModel):
    """营养计算请求"""
    quantity: float = Field(default=100.0, gt=0, description="数量")
    unit: str = Field(default="g", description="单位")


class NutritionResponse(BaseModel):
    """营养数据响应"""
    ingredient_id: int
    ingredient_name: Optional[str] = None
    quantity: float
    unit: str
    base_quantity: float
    nutrition: dict
    source: Optional[str] = None
    reference_amount: Optional[float] = None
    reference_unit: Optional[str] = None
    match_confidence: Optional[float] = None


class RecipeNutritionResponse(BaseModel):
    """菜谱营养响应"""
    recipe_id: int
    recipe_name: str
    total_nutrition: dict
    per_serving_nutrition: dict
    servings: int
    ingredient_details: List[dict]


class NutrientStatisticsResponse(BaseModel):
    """营养统计响应"""
    total_ingredients: int
    ingredients_with_nutrition: int
    coverage_percentage: float
    nutrient_coverage: dict


@router.get("/ingredients", response_model=PaginatedResponse[IngredientResponse])
async def get_ingredients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str = Query(None, alias="q"),
    sort_by: str = Query("price_records", enum=["name", "created_at", "price_records"], description="排序方式"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取原料列表"""
    try:
        # 构建基础查询
        base_query = db.query(Ingredient).options(
            load_only(
                Ingredient.id,
                Ingredient.name,
                Ingredient.aliases,
                Ingredient.default_unit_id,  # 添加外键以加载单位
                Ingredient.created_at,
                Ingredient.is_active
            )
        ).filter(Ingredient.is_active == True)

        if search is not None:
            base_query = base_query.filter(Ingredient.name.contains(search))

        # 根据排序方式进行查询
        if sort_by == "price_records":
            # 按价格记录数量排序
            subquery = db.query(
                Ingredient.id.label('ingredient_id'),
                func.coalesce(func.count(ProductRecord.id), 0).label('record_count')
            ).outerjoin(
                Product, Ingredient.id == Product.ingredient_id
            ).outerjoin(
                ProductRecord, Product.id == ProductRecord.product_id
            ).filter(Ingredient.is_active == True)

            # 显式检查search是否为None
            if search is not None:
                subquery = subquery.filter(Ingredient.name.contains(search))

            subquery = subquery.group_by(Ingredient.id).subquery()

            # 然后将此子查询与主查询连接，并按记录数量排序
            query = db.query(Ingredient).join(
                subquery, Ingredient.id == subquery.c.ingredient_id
            ).filter(Ingredient.is_active == True)

            # 显式检查search是否为None
            if search is not None:
                query = query.filter(Ingredient.name.contains(search))

            # 按价格记录数量降序排列，没有记录的排在后面，然后按ID确保一致性
            ingredients = query.order_by(
                subquery.c.record_count.desc(),  # 按记录数量降序排列
                Ingredient.id  # 按ID确保排序稳定性
            ).offset(skip).limit(limit).all()
        else:
            # 按名称或创建时间排序
            query = base_query
            if sort_by == "name":
                query = query.order_by(Ingredient.name)
            elif sort_by == "created_at":
                query = query.order_by(Ingredient.created_at.desc())

            ingredients = query.offset(skip).limit(limit).all()

        # 使用 Pydantic schema 序列化并返回分页响应
        total = len(ingredients)  # 由于我们使用了 limit，这里只是当前页的数量
        page = skip // limit + 1

        # 需要重新查询总数以获取真正的总数
        if sort_by == "price_records":
            # 为 price_records 排序方式查询总数量
            total_query = db.query(Ingredient.id).filter(Ingredient.is_active == True)
            if search is not None:
                total_query = total_query.filter(Ingredient.name.contains(search))
            total = total_query.count()
        else:
            # 为其他排序方式查询总数量
            total_query = base_query
            if search is not None:
                total_query = total_query.filter(Ingredient.name.contains(search))
            total = total_query.count()

        return PaginatedResponse.create(
            items=[IngredientResponse(
                id=ing.id,
                name=ing.name,
                aliases=ing.aliases or [],
                created_at=ing.created_at
            ) for ing in ingredients],
            total=total,
            page=page,
            page_size=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取原料列表失败: {str(e)}")


@router.get("/ingredients/{ingredient_id}", response_model=IngredientResponse)
async def get_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取原料详情"""
    try:
        # 明确只加载需要的字段，避免加载 relationship
        from app.models.unit import Unit
        ingredient = db.query(Ingredient).options(
            load_only(
                Ingredient.id,
                Ingredient.name,
                Ingredient.aliases,
                Ingredient.default_unit_id,
                Ingredient.created_at,
                Ingredient.updated_at,
                Ingredient.is_active
            )
        ).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="原料不存在")

        # 获取默认单位名称
        default_unit_name = None
        if ingredient.default_unit_id:
            unit = db.query(Unit).filter(Unit.id == ingredient.default_unit_id).first()
            if unit:
                default_unit_name = unit.name

        return IngredientResponse(
            id=ingredient.id,
            name=ingredient.name,
            aliases=ingredient.aliases or [],
            default_unit_id=ingredient.default_unit_id,
            default_unit_name=default_unit_name,
            created_at=ingredient.created_at,
            updated_at=ingredient.updated_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取原料详情失败: {str(e)}")


@router.post("/ingredients", response_model=dict)
async def create_ingredient(
    name: str = Body(..., min_length=1),
    aliases: str = Body(None),
    default_unit_id: int = Body(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建原料"""
    try:
        existing = db.query(Ingredient).filter(Ingredient.name == name).first()
        if existing:
            raise HTTPException(status_code=400, detail="原料已存在")

        aliases_list = []
        if aliases:
            aliases_list = [alias.strip() for alias in aliases.split(',') if alias.strip()]

        new_ingredient = Ingredient(
            name=name,
            aliases=aliases_list,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.add(new_ingredient)
        db.commit()
        db.refresh(new_ingredient)

        return {
            "id": new_ingredient.id,
            "name": new_ingredient.name,
            "aliases": new_ingredient.aliases or [],
            "created_at": new_ingredient.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建原料失败: {str(e)}")


@router.put("/ingredients/{ingredient_id}", response_model=dict)
async def update_ingredient(
    ingredient_id: int,
    name: Optional[str] = Body(None),
    aliases: Optional[List[str]] = Body(None),
    default_unit_id: Optional[int] = Body(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新原料 - nutrition.py 版本，不支持 nutrition 参数"""
    print(f"[DEBUG] === nutrition.py 的 update_ingredient 被调用 ===")
    print(f"[DEBUG] ingredient_id={ingredient_id}, 路径=/api/v1/nutrition/ingredients/{ingredient_id}")
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="原料不存在")

        if name and name != ingredient.name:
            existing = db.query(Ingredient).filter(Ingredient.name == name).first()
            if existing:
                raise HTTPException(status_code=400, detail="原料已存在")
            ingredient.name = name

        if aliases is not None:
            ingredient.aliases = [alias.strip() for alias in aliases if alias.strip()]

        if default_unit_id is not None:
            ingredient.default_unit_id = default_unit_id

        ingredient.updated_by = current_user.id

        db.commit()
        db.refresh(ingredient)

        return {
            "id": ingredient.id,
            "name": ingredient.name,
            "aliases": ingredient.aliases or [],
            "default_unit_id": ingredient.default_unit_id,
            "created_at": ingredient.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新原料失败: {str(e)}")


@router.delete("/ingredients/{ingredient_id}")
async def soft_delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """软删除原料 - 将is_active设置为False"""
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="原料不存在")

        ingredient.is_active = False
        ingredient.updated_by = current_user.id
        db.commit()

        return {"message": "原料已软删除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"软删除原料失败: {str(e)}")


@router.get("/search", response_model=List[NutritionDataResponse])
async def search_nutrition_data(
    query: str = Query(..., min_length=1),
    fuzzy: bool = Query(False),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """搜索营养数据"""
    try:
        from app.services.nutrition_service import search_nutrition
        results = await search_nutrition(query, fuzzy=fuzzy, limit=limit, db=db)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索营养数据失败: {str(e)}")


@router.post("/match", response_model=NutritionMatchResponse)
async def match_ingredient_nutrition(
    ingredient_name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """匹配食材到营养数据"""
    try:
        from app.services.nutrition_service import match_ingredient
        matches = await match_ingredient(ingredient_name, db=db)
        return NutritionMatchResponse(matches=matches)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"匹配食材失败: {str(e)}")


@router.post("/correct")
async def correct_nutrition_mapping(
    request: NutritionCorrectRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更正映射"""
    try:
        from app.services.nutrition_service import correct_mapping
        success = await correct_mapping(
            request.ingredient_name,
            request.nutrition_id,
            db=db
        )
        if not success:
            raise HTTPException(status_code=404, detail="更正失败")
        return {"success": True, "message": "更正成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更正失败: {str(e)}")


# ==================== 营养数据导入端点（新增） ====================

@router.post("/import", response_model=ImportResponse)
async def import_nutrition_data(
    request: ImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    导入营养数据

    从 HowToCook_json 仓库的 out/nutritions.json 导入 USDA 标准化营养数据

    - **mode**: 导入模式
      - `incremental`: 仅导入新食材的营养数据（默认）
      - `full`: 导入所有食材的营养数据，更新已存在的
      - `force`: 强制重新导入所有数据

    - **force_update**: 是否强制更新已有数据
    """
    # 检查权限（仅管理员可以导入）
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅限管理员访问")

    try:
        from app.services.nutrition_import_service import NutritionImportService
        service = NutritionImportService(db)
        result = service.import_all(mode=request.mode, force_update=request.force_update)

        return ImportResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.post("/import-auto", response_model=ImportResponse)
async def auto_import_nutrition_data(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    自动导入营养数据（智能模式）

    自动检测并导入营养数据，首次使用时导入，后续仅更新新增食材
    """
    # 检查权限（仅管理员可以导入）
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅限管理员访问")

    try:
        from app.services.nutrition_import_service import check_and_import_nutrition
        result = check_and_import_nutrition(db, mode="incremental", force_update=False)
        return ImportResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/statistics", response_model=NutrientStatisticsResponse)
async def get_nutrition_statistics(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取营养数据统计信息

    返回营养数据的覆盖率和详细统计
    """
    try:
        from app.services.nutrition_import_service import NutritionImportService
        service = NutritionImportService(db)
        stats = service.get_nutrient_statistics()
        return NutrientStatisticsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


# ==================== 营养计算端点（新增） ====================

@router.get("/ingredients/{ingredient_id}/nutrition", response_model=NutritionResponse)
async def get_ingredient_nutrition(
    ingredient_id: int,
    quantity: float = Query(default=100.0, gt=0, description="数量"),
    unit: str = Query(default="g", description="单位"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取指定食材的营养成分（支持自定义数量）

    - **quantity**: 目标数量（默认 100g）
    - **unit**: 目标单位（默认 g）
    """
    try:
        from app.services.nutrition_calculator import NutritionCalculator
        from app.models.nutrition_data import NutritionData
        from app.models.nutrition import Ingredient

        calculator = NutritionCalculator(db)
        result = calculator.calculate_ingredient_nutrition(ingredient_id, quantity, unit)

        if not result:
            print(f"[营养查询] 食材 {ingredient_id} 营养数据不存在")
            print(f"[营养查询] 调用参数: ingredient_id={ingredient_id}, quantity={quantity}, unit={unit}")
            raise HTTPException(status_code=404, detail="食材营养数据不存在")

        # 查询原料名称
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if ingredient:
            result["ingredient_name"] = ingredient.name

        # 查询营养数据源信息
        nutrition_data = db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id
        ).first()

        if nutrition_data:
            result["source"] = nutrition_data.source
            result["reference_amount"] = nutrition_data.reference_amount
            result["reference_unit"] = nutrition_data.reference_unit
            result["match_confidence"] = nutrition_data.match_confidence

        # print(f"[营养查询] 返回结果: {result}")
        return NutritionResponse(**result)
    except HTTPException as he:
        print(f"[营养查询] HTTP 错误: {he.status_code} - {he.detail}")
        print(f"[营养查询] 调用参数: ingredient_id={ingredient_id}, quantity={quantity}, unit={unit}")
        raise
    except Exception as e:
        print(f"[营养查询] 异常: {type(e).__name__}: {str(e)}")
        print(f"[营养查询] 调用参数: ingredient_id={ingredient_id}, quantity={quantity}, unit={unit}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/ingredients/{ingredient_id}/nutrition/base")
async def get_ingredient_nutrition_base(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取指定食材的基准营养数据（每100g）

    返回原始的营养数据，不进行数量缩放
    """
    try:
        from app.models.nutrition_data import NutritionData

        nutrition = db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id,
            NutritionData.is_verified == True
        ).first()

        if not nutrition:
            raise HTTPException(status_code=404, detail="食材营养数据不存在")

        return {
            "ingredient_id": ingredient_id,
            "source": nutrition.source,
            "usda_id": nutrition.usda_id,
            "usda_name": nutrition.usda_name,
            "nutrients": nutrition.nutrients,
            "reference_amount": nutrition.reference_amount,
            "reference_unit": nutrition.reference_unit,
            "match_confidence": nutrition.match_confidence,
            "is_verified": nutrition.is_verified
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/ingredients/{ingredient_id}/recipes")
async def get_ingredient_recipes(
    ingredient_id: int,
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(50, ge=1, le=100, description="每页记录数"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取包含指定食材的菜谱列表

    - **ingredient_id**: 食材ID
    - **skip**: 跳过记录数（分页）
    - **limit**: 每页记录数
    """
    try:
        from app.models.recipe import Recipe, RecipeIngredient

        # 查询包含该食材的菜谱ID
        recipe_ingredients_query = db.query(RecipeIngredient).filter(
            RecipeIngredient.ingredient_id == ingredient_id
        )

        total = recipe_ingredients_query.count()

        # 分页查询
        recipe_ingredients = recipe_ingredients_query.offset(skip).limit(limit).all()

        # 提取菜谱ID列表
        recipe_ids = [ri.recipe_id for ri in recipe_ingredients]

        if not recipe_ids:
            return {
                "items": [],
                "total": 0,
                "page": skip // limit + 1,
                "page_size": limit
            }

        # 查询菜谱详情（当前用户的菜谱和公共导入的菜谱）
        recipes = db.query(Recipe).filter(
            Recipe.id.in_(recipe_ids),
            or_(
                Recipe.user_id == current_user.id,
                Recipe.source != None
            )
        ).all()

        # 构建返回数据
        items = []
        for recipe in recipes:
            items.append({
                "id": recipe.id,
                "name": recipe.name,
                "source": recipe.source,
                "category": recipe.category,
                "servings": recipe.servings,
                "total_time_minutes": recipe.total_time_minutes,
                "difficulty": recipe.difficulty,
                "tags": recipe.tags or [],
                "created_at": recipe.created_at,
                "updated_at": recipe.updated_at
            })

        return {
            "items": items,
            "total": total,
            "page": skip // limit + 1,
            "page_size": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取关联菜谱失败: {str(e)}")


@router.get("/ingredients/{ingredient_id}/latest-price")
async def get_ingredient_latest_price(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取原料的最近一天平均价格

    - **ingredient_id**: 食材ID

    返回该原料关联商品在最近一天的平均价格（基于原料的默认单位）
    """
    try:
        from app.models.product import ProductRecord
        from app.services.unit_conversion_service import UnitConversionService
        from datetime import datetime, timedelta

        # 查询原料及其默认单位
        ingredient = db.query(Ingredient).filter(
            Ingredient.id == ingredient_id
        ).first()

        if not ingredient:
            print(f"[DEBUG] 原料 {ingredient_id} 不存在")
            return {"average_price": None, "unit": None}

        print(f"[DEBUG] 原料: {ingredient.name}, 默认单位: {ingredient.default_unit.abbreviation if ingredient.default_unit else None}")

        # 查询该原料关联的商品
        products = db.query(Product).filter(
            Product.ingredient_id == ingredient_id
        ).all()

        if not products:
            print(f"[DEBUG] 原料 {ingredient_id} 没有关联商品")
            return {"average_price": None, "unit": None}

        print(f"[DEBUG] 找到 {len(products)} 个关联商品")

        product_ids = [p.id for p in products]

        # 首先尝试获取最近24小时内的记录
        from sqlalchemy import func
        now = datetime.utcnow()
        one_day_ago = now - timedelta(days=1)

        recent_records = db.query(ProductRecord).options(
            joinedload(ProductRecord.original_unit)
        ).filter(
            ProductRecord.product_id.in_(product_ids),
            ProductRecord.recorded_at >= one_day_ago
        ).order_by(ProductRecord.recorded_at.desc()).all()

        # 如果最近24小时内没有记录，则查找最近一次记录的那一天的所有记录
        if not recent_records:
            print(f"[DEBUG] 最近24小时内没有记录，查找最近一次记录")
            # 查找最近一次记录
            latest_record = db.query(ProductRecord).filter(
                ProductRecord.product_id.in_(product_ids)
            ).order_by(ProductRecord.recorded_at.desc()).first()

            if not latest_record:
                print(f"[DEBUG] 没有找到任何价格记录")
                return {"average_price": None, "unit": None}

            # 获取与最近记录同一天的所有记录
            latest_date = latest_record.recorded_at.date()
            print(f"[DEBUG] 最近记录日期: {latest_date}")
            recent_records = db.query(ProductRecord).options(
                joinedload(ProductRecord.original_unit)
            ).filter(
                ProductRecord.product_id.in_(product_ids),
                func.date(ProductRecord.recorded_at) == latest_date
            ).all()

        print(f"[DEBUG] 找到 {len(recent_records)} 条价格记录")

        if not recent_records:
            return {"average_price": None, "unit": None}

        # 初始化单位转换服务
        unit_service = UnitConversionService(db)

        # 获取原料的默认单位缩写
        target_unit_abbr = None
        if ingredient.default_unit:
            target_unit_abbr = ingredient.default_unit.abbreviation

        print(f"[DEBUG] 目标单位: {target_unit_abbr}")

        # 计算平均价格 - 转换到原料的默认单位
        unit_prices = []
        for i, record in enumerate(recent_records):
            print(f"[DEBUG] 记录 {i+1}: price={record.price}, quantity={record.original_quantity}, unit={record.original_unit.abbreviation if record.original_unit else None}")
            if record.price is not None and record.original_quantity is not None and record.original_quantity > 0 and record.original_unit:
                total_price = float(record.price)
                original_quantity = float(record.original_quantity)
                original_unit_abbr = record.original_unit.abbreviation

                # 如果原料有默认单位，且与记录单位不同，则转换数量到目标单位
                if target_unit_abbr and original_unit_abbr != target_unit_abbr:
                    # 转换数量到目标单位
                    print(f"[DEBUG]   转换数量: {original_quantity} {original_unit_abbr} -> {target_unit_abbr}")
                    converted_quantity = unit_service.convert(
                        original_quantity,
                        original_unit_abbr,
                        target_unit_abbr,
                        ingredient.name
                    )
                    print(f"[DEBUG]   转换后数量: {converted_quantity} {target_unit_abbr}")

                    if converted_quantity is not None and converted_quantity > 0:
                        # 用总价除以转换后的数量，得到目标单位的单价
                        unit_price = total_price / converted_quantity
                        print(f"[DEBUG]   目标单位单价: {unit_price} {target_unit_abbr}")
                        unit_prices.append(unit_price)
                    else:
                        # 转换失败，跳过此记录
                        print(f"[DEBUG]   转换失败，跳过此记录")
                        continue
                else:
                    # 单位相同或原料没有默认单位，直接计算单价
                    unit_price = total_price / original_quantity
                    print(f"[DEBUG]   单价: {unit_price} {original_unit_abbr}")
                    unit_prices.append(unit_price)

        print(f"[DEBUG] 有效单价列表: {unit_prices}")

        if not unit_prices:
            return {"average_price": None, "unit": None}

        average_price = sum(unit_prices) / len(unit_prices)

        print(f"[DEBUG] 平均价格: {average_price}")

        # 返回原料的默认单位（如果有）
        result = {
            "average_price": round(average_price, 2),
            "unit": target_unit_abbr
        }
        print(f"[DEBUG] 返回结果: {result}")
        return result
    except Exception as e:
        import traceback
        print(f"[ERROR] 获取最近价格失败: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取最近价格失败: {str(e)}")


@router.get("/recipes/{recipe_id}/nutrition", response_model=RecipeNutritionResponse)
async def get_recipe_nutrition(
    recipe_id: int,
    servings: Optional[int] = Query(default=None, gt=0, description="份数"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    计算菜谱的营养成分

    - **servings**: 份数（如为 None 则使用菜谱默认份数）

    返回菜谱总营养和每份营养数据
    """
    try:
        from app.services.nutrition_calculator import calculate_recipe_nutrition
        result = await calculate_recipe_nutrition(recipe_id, db, servings)

        if not result:
            raise HTTPException(status_code=404, detail="菜谱不存在或营养数据不足")

        return RecipeNutritionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")


@router.get("/recipes/{recipe_id}/nutrition/summary")
async def get_recipe_nutrition_summary(
    recipe_id: int,
    servings: Optional[int] = Query(default=None, gt=0, description="份数"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取菜谱营养摘要（简化版）

    返回核心营养素的简要信息，用于列表展示
    """
    try:
        from app.services.nutrition_calculator import calculate_recipe_nutrition
        result = await calculate_recipe_nutrition(recipe_id, db, servings)

        if not result:
            raise HTTPException(status_code=404, detail="菜谱不存在或营养数据不足")

        # 提取核心营养素用于摘要
        core_nutrients = result.get("per_serving_nutrition", {}).get("core_nutrients", {})

        return {
            "recipe_id": recipe_id,
            "servings": result.get("servings", 1),
            "summary": {
                "energy": core_nutrients.get("能量", {}).get("value", 0),
                "protein": core_nutrients.get("蛋白质", {}).get("value", 0),
                "fat": core_nutrients.get("脂肪", {}).get("value", 0),
                "carbohydrate": core_nutrients.get("碳水化合物", {}).get("value", 0),
            },
            "nrp_summary": {
                "energy": core_nutrients.get("能量", {}).get("nrp_pct", 0),
                "protein": core_nutrients.get("蛋白质", {}).get("nrp_pct", 0),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算失败: {str(e)}")


@router.get("/products/{product_id}/nutrition")
async def get_product_nutrition(
    product_id: int,
    quantity: Optional[float] = Query(default=None, gt=0, description="数量"),
    unit: Optional[str] = Query(default=None, description="单位"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取商品的营养成分

    优先使用商品自定义营养数据，其次使用关联食材的 USDA 数据
    """
    try:
        from app.services.nutrition_calculator import NutritionCalculator
        calculator = NutritionCalculator(db)
        result = calculator.calculate_product_nutrition(product_id, quantity, unit)

        if not result:
            raise HTTPException(status_code=404, detail="商品营养数据不存在")

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")




# ==================== 营养编辑端点 ====================

@router.post("/ingredients/{ingredient_id}/nutrition", response_model=NutritionEditResponse)
async def edit_ingredient_nutrition(
    ingredient_id: int,
    request: NutritionEditRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    编辑原料营养数据

    创建或更新原料的营养数据
    """
    try:
        # 验证原料是否存在
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="原料不存在")

        # 构建营养数据字典
        nutrients_dict = {}
        for nutrient in request.nutrients:
            nutrients_dict[nutrient.name] = {
                "value": nutrient.value,
                "unit": nutrient.unit,
                "key": nutrient.key
            }

        # 查找或创建营养数据
        nutrition_data = db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id
        ).first()

        if nutrition_data:
            # 更新现有数据
            nutrition_data.nutrients = nutrients_dict
            nutrition_data.reference_amount = request.base_quantity
            nutrition_data.reference_unit = request.base_unit
            nutrition_data.source = request.source
            nutrition_data.is_verified = True
        else:
            # 创建新数据
            nutrition_data = NutritionData(
                ingredient_id=ingredient_id,
                nutrients=nutrients_dict,
                reference_amount=request.base_quantity,
                reference_unit=request.base_unit,
                source=request.source,
                is_verified=True,
                match_confidence=100.0  # 用户自定义数据，置信度100%
            )
            db.add(nutrition_data)

        db.commit()
        db.refresh(nutrition_data)

        return NutritionEditResponse(
            success=True,
            message="营养数据保存成功",
            ingredient_id=ingredient_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.post("/products/{product_id}/nutrition", response_model=NutritionEditResponse)
async def edit_product_nutrition(
    product_id: int,
    request: NutritionEditRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    编辑商品营养数据

    创建或更新商品的自定义营养数据
    """
    try:
        # 验证商品是否存在
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        # 构建营养数据字典
        nutrients_dict = {}
        for nutrient in request.nutrients:
            nutrients_dict[nutrient.name] = {
                "value": nutrient.value,
                "unit": nutrient.unit,
                "key": nutrient.key
            }

        # 更新商品的自定义营养数据
        product.custom_nutrition_data = nutrients_dict
        product.custom_nutrition_source = request.source
        product.updated_by = current_user.id

        db.commit()
        db.refresh(product)

        return NutritionEditResponse(
            success=True,
            message="商品营养数据保存成功",
            product_id=product_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")
