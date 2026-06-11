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


def _compute_sparkline_for_entity(
    db: Session,
    product_ids: List[int],
    days: int = 90,
) -> List[float]:
    """计算指定商品列表的近N天每日平均价格（聚合所有商品）

    返回按日期升序排列的每日平均价格列表，用于迷你图展示。
    """
    from datetime import datetime, timedelta
    from collections import defaultdict

    if not product_ids:
        return []

    cutoff = datetime.utcnow() - timedelta(days=days)
    records = db.query(ProductRecord).filter(
        ProductRecord.product_id.in_(product_ids),
        ProductRecord.recorded_at >= cutoff,
        ProductRecord.price.isnot(None),
    ).all()

    # 按日期分组计算日均价
    daily_totals: dict = defaultdict(lambda: {"sum": 0.0, "count": 0})
    for r in records:
        std_qty = float(r.standard_quantity) if r.standard_quantity and float(r.standard_quantity) > 0 else 500.0
        # 归一化到 ¥/斤 (1斤=500g), 使用 standard_quantity 确保跨单位可比较
        unit_price = float(r.price) * 500.0 / std_qty
        date_key = r.recorded_at.strftime("%Y-%m-%d")
        daily_totals[date_key]["sum"] += unit_price
        daily_totals[date_key]["count"] += 1

    # 按日期排序返回平均值列表
    sorted_dates = sorted(daily_totals.keys())
    return [
        round(daily_totals[d]["sum"] / daily_totals[d]["count"], 2)
        for d in sorted_dates
    ]


def _inject_ingredient_sparklines(
    items: list,
    db: Session,
    days: int = 90,
) -> None:
    """为原料列表批量注入迷你图数据"""
    from collections import defaultdict

    ingredient_ids = [item.id for item in items]

    # 批量查询所有原料关联的商品
    products = db.query(Product.id, Product.ingredient_id).filter(
        Product.ingredient_id.in_(ingredient_ids),
        Product.is_active == True,
    ).all()

    if not products:
        return

    # 构建 ingredient_id -> [product_ids] 映射
    ing_to_products: dict = defaultdict(list)
    all_product_ids = []
    for prod_id, ing_id in products:
        ing_to_products[ing_id].append(prod_id)
        all_product_ids.append(prod_id)

    # 批量查询所有价格记录
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    records = db.query(
        ProductRecord.product_id,
        ProductRecord.price,
        ProductRecord.standard_quantity,
        ProductRecord.recorded_at,
    ).filter(
        ProductRecord.product_id.in_(all_product_ids),
        ProductRecord.recorded_at >= cutoff,
        ProductRecord.price.isnot(None),
    ).all()

    # 按 (ingredient_id, date) 分组
    ing_date_prices: dict = defaultdict(lambda: defaultdict(lambda: {"sum": 0.0, "count": 0}))
    # 反向映射 product_id -> ingredient_id
    prod_to_ing = {prod_id: ing_id for prod_id, ing_id in products}

    for prod_id, price, std_qty, recorded_at in records:
        ing_id = prod_to_ing.get(prod_id)
        if ing_id is None:
            continue
        std_qty_f = float(std_qty) if std_qty and float(std_qty) > 0 else 500.0
        # 归一化到 ¥/斤 (1斤=500g), 使用 standard_quantity 确保跨单位可比较
        unit_price = float(price) * 500.0 / std_qty_f
        date_key = recorded_at.strftime("%Y-%m-%d")
        ing_date_prices[ing_id][date_key]["sum"] += unit_price
        ing_date_prices[ing_id][date_key]["count"] += 1

    # 注入到每个 response item
    for item in items:
        date_data = ing_date_prices.get(item.id, {})
        if date_data:
            sorted_dates = sorted(date_data.keys())
            item.sparkline_data = [
                round(date_data[d]["sum"] / date_data[d]["count"], 2)
                for d in sorted_dates
            ]


def _inject_merchant_sparklines(
    results: list,
    product_ids: List[int],
    db: Session,
    days: int = 90,
) -> None:
    """为商家价格列表批量注入迷你图数据（每个商家近N天每日均价）"""
    from collections import defaultdict
    from datetime import datetime, timedelta

    if not results or not product_ids:
        return

    merchant_ids = [r["merchant_id"] for r in results]
    cutoff = datetime.utcnow() - timedelta(days=days)

    records = db.query(
        ProductRecord.merchant_id,
        ProductRecord.price,
        ProductRecord.standard_quantity,
        ProductRecord.recorded_at,
    ).filter(
        ProductRecord.product_id.in_(product_ids),
        ProductRecord.merchant_id.in_(merchant_ids),
        ProductRecord.recorded_at >= cutoff,
        ProductRecord.price.isnot(None),
    ).all()

    # 按 (merchant_id, date) 分组
    merchant_date_prices: dict = defaultdict(lambda: defaultdict(lambda: {"sum": 0.0, "count": 0}))
    for mid, price, std_qty, recorded_at in records:
        std_qty_f = float(std_qty) if std_qty and float(std_qty) > 0 else 500.0
        # 归一化到 ¥/斤 (1斤=500g), 使用 standard_quantity 确保跨单位可比较
        unit_price = float(price) * 500.0 / std_qty_f
        date_key = recorded_at.strftime("%Y-%m-%d")
        merchant_date_prices[mid][date_key]["sum"] += unit_price
        merchant_date_prices[mid][date_key]["count"] += 1

    for r in results:
        date_data = merchant_date_prices.get(r["merchant_id"], {})
        if date_data:
            sorted_dates = sorted(date_data.keys())
            r["sparkline_data"] = [
                round(date_data[d]["sum"] / date_data[d]["count"], 2)
                for d in sorted_dates
            ]
        else:
            r["sparkline_data"] = None


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
    category_ids: Optional[str] = Query(None, description="原料分类ID列表，逗号分隔"),
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

        if category_ids:
            ids = [int(x.strip()) for x in category_ids.split(',') if x.strip()]
            if ids:
                base_query = base_query.filter(Ingredient.category_id.in_(ids))

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

            if category_ids:
                ids = [int(x.strip()) for x in category_ids.split(',') if x.strip()]
                if ids:
                    subquery = subquery.filter(Ingredient.category_id.in_(ids))

            subquery = subquery.group_by(Ingredient.id).subquery()

            # 然后将此子查询与主查询连接，并按记录数量排序
            query = db.query(Ingredient).join(
                subquery, Ingredient.id == subquery.c.ingredient_id
            ).filter(Ingredient.is_active == True)

            # 显式检查search是否为None
            if search is not None:
                query = query.filter(Ingredient.name.contains(search))

            if category_ids:
                ids = [int(x.strip()) for x in category_ids.split(',') if x.strip()]
                if ids:
                    query = query.filter(Ingredient.category_id.in_(ids))

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
            if category_ids:
                ids = [int(x.strip()) for x in category_ids.split(',') if x.strip()]
                if ids:
                    total_query = total_query.filter(Ingredient.category_id.in_(ids))
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

        # 未指定默认单位时默认为斤
        unit_id = default_unit_id
        if unit_id is None:
            from app.models.unit import Unit
            jin_unit = db.query(Unit).filter(Unit.abbreviation == "斤").first()
            if jin_unit:
                unit_id = jin_unit.id

        new_ingredient = Ingredient(
            name=name,
            aliases=aliases_list,
            default_unit_id=unit_id,
            created_by=current_user.id,
            updated_by=current_user.id
        )
        db.add(new_ingredient)
        db.commit()
        db.refresh(new_ingredient)

        default_unit_name = None
        if new_ingredient.default_unit_id:
            from app.models.unit import Unit
            unit = db.query(Unit).filter(Unit.id == new_ingredient.default_unit_id).first()
            if unit:
                default_unit_name = unit.name

        return {
            "id": new_ingredient.id,
            "name": new_ingredient.name,
            "aliases": new_ingredient.aliases or [],
            "default_unit_id": new_ingredient.default_unit_id,
            "default_unit_name": default_unit_name,
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
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="原料不存在")

        # 权限检查：管理员可修改任意原料，普通用户只能修改自己创建的
        if ingredient.created_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="无权修改此原料")

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
    """软删除原料

    仅当原料未关联任何菜谱时可删除。删除时级联软删除其下的商品和关联关系。
    管理员可删除任意原料，普通用户只能删除自己创建的原料。
    """
    try:
        from app.models.recipe import RecipeIngredient

        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="原料不存在")

        # 检查是否有关联菜谱
        recipe_count = db.query(RecipeIngredient).filter(
            RecipeIngredient.ingredient_id == ingredient_id
        ).count()
        if recipe_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"该原料已被 {recipe_count} 个菜谱引用，无法删除。请先移除菜谱中的该原料。"
            )

        # 权限检查
        if ingredient.created_by != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=403, detail="无权删除此原料")

        # 级联软删除关联的商品
        db.query(Product).filter(
            Product.ingredient_id == ingredient_id,
            Product.is_active == True
        ).update({"is_active": False}, synchronization_session=False)

        ingredient.is_active = False
        ingredient.updated_by = current_user.id
        db.commit()

        return {"message": "原料已删除，关联商品也已软删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除原料失败: {str(e)}")


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
            return {"average_price": None, "unit": None}


        # 查询该原料关联的商品
        products = db.query(Product).filter(
            Product.ingredient_id == ingredient_id
        ).all()

        if not products:
            return {"average_price": None, "unit": None}


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
            # 查找最近一次记录
            latest_record = db.query(ProductRecord).filter(
                ProductRecord.product_id.in_(product_ids)
            ).order_by(ProductRecord.recorded_at.desc()).first()

            if not latest_record:
                return {"average_price": None, "unit": None}

            # 获取与最近记录同一天的所有记录
            latest_date = latest_record.recorded_at.date()
            recent_records = db.query(ProductRecord).options(
                joinedload(ProductRecord.original_unit)
            ).filter(
                ProductRecord.product_id.in_(product_ids),
                func.date(ProductRecord.recorded_at) == latest_date
            ).all()


        if not recent_records:
            return {"average_price": None, "unit": None}

        # 初始化单位转换服务
        unit_service = UnitConversionService(db)

        # 获取原料的默认单位缩写
        target_unit_abbr = None
        if ingredient.default_unit:
            target_unit_abbr = ingredient.default_unit.abbreviation


        # 计算平均价格 - 转换到原料的默认单位
        unit_prices = []
        for i, record in enumerate(recent_records):
            if record.price is not None and record.original_quantity is not None and record.original_quantity > 0 and record.original_unit:
                total_price = float(record.price)
                original_quantity = float(record.original_quantity)
                original_unit_abbr = record.original_unit.abbreviation

                # 如果原料有默认单位，且与记录单位不同，则转换数量到目标单位
                if target_unit_abbr and original_unit_abbr != target_unit_abbr:
                    # 转换数量到目标单位
                    convert_result = unit_service.convert(
                        original_quantity,
                        original_unit_abbr,
                        target_unit_abbr,
                        entity_type="ingredient",
                        entity_id=ingredient_id,
                    )
                    if convert_result is not None:
                        converted_quantity, _ = convert_result
                    else:
                        converted_quantity = None

                    if converted_quantity is not None and converted_quantity > 0:
                        # 用总价除以转换后的数量，得到目标单位的单价
                        unit_price = float(total_price) / float(converted_quantity)
                        unit_prices.append(unit_price)
                    else:
                        # 转换失败，跳过此记录
                        continue
                else:
                    # 单位相同或原料没有默认单位，直接计算单价
                    unit_price = total_price / original_quantity
                    unit_prices.append(unit_price)


        if not unit_prices:
            return {"average_price": None, "unit": None}

        average_price = sum(unit_prices) / len(unit_prices)


        # 返回原料的默认单位（如果有）
        latest_date = max(r.recorded_at for r in recent_records)
        result = {
            "average_price": round(average_price, 2),
            "unit": target_unit_abbr,
            "latest_date": latest_date.isoformat() if latest_date else None,
        }
        return result
    except Exception as e:
        import traceback
        print(f"[ERROR] 获取最近价格失败: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取最近价格失败: {str(e)}")


@router.get("/ingredients/{ingredient_id}/latest-price-by-merchant")
async def get_ingredient_latest_price_by_merchant(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取原料按商家分组的最新价格

    返回每个商家的最新一条价格记录（已转换为原料默认单位）。
    按价格从低到高排序，并标注最低价。
    """
    try:
        from app.models.merchant import Merchant
        from app.services.unit_conversion_service import UnitConversionService
        from datetime import datetime, timedelta
        from decimal import Decimal

        ingredient = db.query(Ingredient).filter(
            Ingredient.id == ingredient_id
        ).first()

        if not ingredient:
            return {"prices": [], "unit": None}

        products = db.query(Product).filter(
            Product.ingredient_id == ingredient_id
        ).all()

        if not products:
            return {"prices": [], "unit": None}

        product_ids = [p.id for p in products]

        # 获取原料的默认单位
        target_unit_abbr = None
        if ingredient.default_unit:
            target_unit_abbr = ingredient.default_unit.abbreviation

        unit_service = UnitConversionService(db)

        # 查询所有价格记录，按商家分组，每组取最新一条（仅营业中商家）
        records = db.query(ProductRecord).options(
            joinedload(ProductRecord.original_unit),
            joinedload(ProductRecord.merchant)
        ).join(
            Merchant, ProductRecord.merchant_id == Merchant.id
        ).filter(
            ProductRecord.product_id.in_(product_ids),
            ProductRecord.merchant_id.isnot(None),
            Merchant.is_open == True
        ).order_by(ProductRecord.recorded_at.desc()).all()

        # 按商家分组，每组只保留最新一条
        merchant_latest: dict = {}
        for record in records:
            mid = record.merchant_id
            if mid not in merchant_latest:
                merchant_latest[mid] = record

        # 计算每个商家的单价（转换为原料默认单位）
        results = []
        for mid, record in merchant_latest.items():
            if record.price is None or record.original_quantity is None or record.original_quantity <= 0 or not record.original_unit:
                continue

            total_price = float(record.price)
            original_quantity = float(record.original_quantity)
            original_unit_abbr = record.original_unit.abbreviation

            unit_price = None
            if target_unit_abbr and original_unit_abbr != target_unit_abbr:
                convert_result = unit_service.convert(
                    original_quantity,
                    original_unit_abbr,
                    target_unit_abbr,
                    entity_type="ingredient",
                    entity_id=ingredient_id,
                )
                if convert_result is not None:
                    converted_quantity, _ = convert_result
                    if converted_quantity and float(converted_quantity) > 0:
                        unit_price = total_price / float(converted_quantity)

            if unit_price is None:
                unit_price = total_price / original_quantity

            results.append({
                "merchant_id": mid,
                "merchant_name": record.merchant.name if record.merchant else f"商家#{mid}",
                "price": round(unit_price, 2),
                "unit": target_unit_abbr or original_unit_abbr,
                "recorded_at": record.recorded_at.isoformat() if record.recorded_at else None,
                "product_name": record.product_name,
            })

        # 按价格从低到高排序
        results.sort(key=lambda x: x["price"])

        # 标注最低价
        if results:
            results[0]["is_lowest"] = True
            for r in results[1:]:
                r["is_lowest"] = False

            # 为每个商家注入近90天价格趋势迷你图数据
            _inject_merchant_sparklines(results, product_ids, db)

        return {"prices": results, "unit": target_unit_abbr}

    except Exception as e:
        import traceback
        print(f"[ERROR] 获取商家价格失败: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取商家价格失败: {str(e)}")


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

        # 构建结构化营养数据字典（与 import 格式一致）
        # 格式: { core_nutrients: {...}, all_nutrients: {...}, nutrient_details: {...} }
        from app.services.nutrition_import_service import NutritionImportService
        core_display_map = NutritionImportService.CORE_DISPLAY_MAP

        # NRV 参考值（中国GB标准，成人每日推荐摄入量）
        NRV_REF = {
            "能量": (2000, "kcal"),
            "蛋白质": (60, "g"),
            "脂肪": (60, "g"),
            "碳水化合物": (300, "g"),
            "膳食纤维": (25, "g"),
            "钙": (800, "mg"),
            "铁": (15, "mg"),
            "钠": (2000, "mg"),
            "钾": (2000, "mg"),
            "维生素A": (800, "μg"),
            "维生素C": (100, "mg"),
            "维生素B1": (1.2, "mg"),
            "维生素B2": (1.4, "mg"),
            "维生素B12": (2.4, "μg"),
            "维生素D": (5, "μg"),
            "维生素E": (14, "mg"),
            "维生素K": (80, "μg"),
        }
        NRV_UNIT_FACTOR = {
            ("kJ", "kcal"): 1.0 / 4.184,
            ("mg", "g"): 0.001,
            ("μg", "g"): 0.000001,
            ("g", "mg"): 1000,
            ("μg", "mg"): 0.001,
            ("g", "μg"): 1000000,
            ("mg", "μg"): 1000,
        }

        def _calc_nrp(display_name: str, value: float, unit: str) -> float:
            """根据 NRV 标准计算百分比"""
            ref = NRV_REF.get(display_name)
            if not ref or value <= 0:
                return 0
            nrv_value, nrv_unit = ref
            if unit != nrv_unit:
                factor = NRV_UNIT_FACTOR.get((unit, nrv_unit))
                if factor:
                    value = value * factor
                else:
                    return 0
            if nrv_value <= 0:
                return 0
            return round((value / nrv_value) * 100, 2)

        structured_nutrients = {
            "core_nutrients": {},
            "all_nutrients": {},
            "nutrient_details": {}
        }

        for nutrient in request.nutrients:
            key = nutrient.key or nutrient.name
            info = {
                "value": nutrient.value,
                "unit": nutrient.unit,
                "key": key
            }

            # 计算 NRV 百分比
            display_name = core_display_map.get(nutrient.name)
            if display_name:
                nrp = _calc_nrp(display_name, float(nutrient.value), nutrient.unit)
                if nrp > 0:
                    info["nrp_pct"] = nrp
                    info["standard"] = "中国GB标准"

            structured_nutrients["all_nutrients"][key] = info
            structured_nutrients["nutrient_details"][key] = info

            if display_name:
                structured_nutrients["core_nutrients"][display_name] = {
                    **info, "key": key
                }

        # 查找或创建营养数据
        nutrition_data = db.query(NutritionData).filter(
            NutritionData.ingredient_id == ingredient_id
        ).first()

        if nutrition_data:
            # 更新现有数据
            nutrition_data.nutrients = structured_nutrients
            nutrition_data.reference_amount = request.base_quantity
            nutrition_data.reference_unit = request.base_unit
            nutrition_data.source = request.source
            nutrition_data.is_verified = True
        else:
            # 创建新数据
            nutrition_data = NutritionData(
                ingredient_id=ingredient_id,
                nutrients=structured_nutrients,
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

        # 构建结构化营养数据字典（与 import 格式一致）
        from app.services.nutrition_import_service import NutritionImportService
        core_display_map = NutritionImportService.CORE_DISPLAY_MAP

        # NRV 参考值
        NRV_REF = {
            "能量": (2000, "kcal"),
            "蛋白质": (60, "g"),
            "脂肪": (60, "g"),
            "碳水化合物": (300, "g"),
            "膳食纤维": (25, "g"),
            "钙": (800, "mg"),
            "铁": (15, "mg"),
            "钠": (2000, "mg"),
            "钾": (2000, "mg"),
            "维生素A": (800, "μg"),
            "维生素C": (100, "mg"),
            "维生素B1": (1.2, "mg"),
            "维生素B2": (1.4, "mg"),
            "维生素B12": (2.4, "μg"),
            "维生素D": (5, "μg"),
            "维生素E": (14, "mg"),
            "维生素K": (80, "μg"),
        }
        NRV_UNIT_FACTOR = {
            ("kJ", "kcal"): 1.0 / 4.184,
            ("mg", "g"): 0.001,
            ("μg", "g"): 0.000001,
            ("g", "mg"): 1000,
            ("μg", "mg"): 0.001,
            ("g", "μg"): 1000000,
            ("mg", "μg"): 1000,
        }

        def _calc_nrp(display_name: str, value: float, unit: str) -> float:
            ref = NRV_REF.get(display_name)
            if not ref or value <= 0:
                return 0
            nrv_value, nrv_unit = ref
            if unit != nrv_unit:
                factor = NRV_UNIT_FACTOR.get((unit, nrv_unit))
                if factor:
                    value = value * factor
                else:
                    return 0
            if nrv_value <= 0:
                return 0
            return round((value / nrv_value) * 100, 2)

        structured_nutrients = {
            "core_nutrients": {},
            "all_nutrients": {},
            "nutrient_details": {}
        }

        for nutrient in request.nutrients:
            key = nutrient.key or nutrient.name
            info = {
                "value": nutrient.value,
                "unit": nutrient.unit,
                "key": key
            }
            display_name = core_display_map.get(nutrient.name)
            if display_name:
                nrp = _calc_nrp(display_name, float(nutrient.value), nutrient.unit)
                if nrp > 0:
                    info["nrp_pct"] = nrp
                    info["standard"] = "中国GB标准"
                structured_nutrients["core_nutrients"][display_name] = {
                    **info, "key": key
                }
            structured_nutrients["all_nutrients"][key] = info
            structured_nutrients["nutrient_details"][key] = info

        # 更新商品的自定义营养数据
        product.custom_nutrition_data = structured_nutrients
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
