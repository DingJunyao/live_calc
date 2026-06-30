# 食材扩展 API - 支持别名搜索（最后修改: 2026-03-27 23:35）
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, load_only, joinedload
from sqlalchemy import func
from typing import List, Optional
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.services.unit_conversion_service import UnitConversionService
from app.services.ingredient_matcher import IngredientMatcher
from app.utils.database_helpers import json_text_contains
from app.models.ingredient_category import IngredientCategory
from app.models.unit import Unit
from app.models.nutrition import Ingredient
from app.schemas.common import PaginatedResponse
from app.services.proposals import service as proposal_service

router = APIRouter()


def _apply_ingredient_special_conditions(query, no_nutrition, no_price, single_price, single_merchant, no_recipe, no_product):
    """Apply special condition filters to an Ingredient query."""
    from app.models.nutrition_data import NutritionData
    from app.models.product_entity import Product
    from app.models.product import ProductRecord
    from app.models.recipe import RecipeIngredient
    from sqlalchemy import exists, select

    if no_nutrition:
        from sqlalchemy import or_
        query = query.filter(
            ~exists().where(
                NutritionData.ingredient_id == Ingredient.id,
                or_(
                    NutritionData.source.in_(['custom', 'usda_import', 'usda_manual_match']),
                    NutritionData.is_verified == True
                )
            )
        )

    if no_price:
        query = query.filter(
            ~exists().where(
                Product.ingredient_id == Ingredient.id,
                Product.is_active == True,
                ProductRecord.product_id == Product.id
            )
        )

    if single_price:
        subq = (
            select(func.count())
            .select_from(ProductRecord)
            .join(Product, Product.id == ProductRecord.product_id)
            .where(Product.ingredient_id == Ingredient.id, Product.is_active == True)
            .correlate(Ingredient)
            .scalar_subquery()
        )
        query = query.filter(subq == 1)

    if single_merchant:
        subq = (
            select(func.count(func.distinct(ProductRecord.merchant_id)))
            .select_from(ProductRecord)
            .join(Product, Product.id == ProductRecord.product_id)
            .where(Product.ingredient_id == Ingredient.id, Product.is_active == True)
            .correlate(Ingredient)
            .scalar_subquery()
        )
        query = query.filter(subq == 1)

    if no_recipe:
        query = query.filter(
            ~exists().where(RecipeIngredient.ingredient_id == Ingredient.id)
        )

    if no_product:
        query = query.filter(
            ~exists().where(
                Product.ingredient_id == Ingredient.id,
                Product.is_active == True
            )
        )

    return query


@router.get("/units", response_model=PaginatedResponse[dict])
async def get_units(
    unit_type: Optional[str] = Query(None, description="单位类型，如mass, volume, length"),
    is_common: Optional[bool] = Query(None, description="是否为常用单位"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取单位列表（分页）"""
    try:
        query = db.query(Unit).filter(Unit.is_active == True)

        if unit_type:
            query = query.filter(Unit.unit_type == unit_type)
        if is_common is not None:
            query = query.filter(Unit.is_common == is_common)

        # 获取总数
        total = query.count()

        # 获取分页数据
        units = query.offset(skip).limit(limit).all()

        items = [{
            "id": unit.id,
            "name": unit.name,
            "abbreviation": unit.abbreviation,
            "plural_form": unit.plural_form,
            "unit_type": unit.unit_type,
            "si_factor": unit.si_factor,
            "is_si_base": unit.is_si_base,
            "is_common": unit.is_common,
            "display_order": unit.display_order
        } for unit in units]

        page = skip // limit + 1
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取单位列表失败: {str(e)}")


@router.get("/unit-conversion/{value}/{from_unit}/{to_unit}", response_model=Optional[float])
async def convert_units(
    value: float,
    from_unit: str,
    to_unit: str,
    ingredient_name: Optional[str] = Query(None, description="食材名称，用于体积重量转换"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """单位转换"""
    try:
        service = UnitConversionService(db)

        if ingredient_name:
            if from_unit.lower() in ['ml', 'l', 'cup', 'tbsp', 'tsp'] and to_unit.lower() in ['g', 'kg', 'lb', 'oz', 'jin']:
                result = service.convert_volume_to_weight(value, from_unit, ingredient_name)
                if result:
                    converted_value, _ = result
                    final_result = service.convert(converted_value, "g", to_unit)
                    return final_result
            elif from_unit.lower() in ['g', 'kg', 'lb', 'oz', 'jin'] and to_unit.lower() in ['ml', 'l', 'cup', 'tbsp', 'tsp']:
                result = service.convert_weight_to_volume(value, from_unit, ingredient_name)
                if result:
                    converted_value, _ = result
                    final_result = service.convert(converted_value, "ml", to_unit)
                    return final_result

        result = service.convert(value, from_unit, to_unit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"单位转换失败: {str(e)}")


@router.get("/search-by-name/{name}", response_model=List[dict])
async def search_ingredients_by_name(
    name: str,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """按名称搜索食材"""
    try:
        matcher = IngredientMatcher(db)
        matches = matcher.match_product_to_ingredient(name)[:limit]

        results = []
        for ingredient, confidence in matches:
            if ingredient.is_active:
                # 显式加载 default_unit 关系以获取单位信息
                ingredient_with_unit = db.query(Ingredient).options(
                    joinedload(Ingredient.default_unit),
                    joinedload(Ingredient.category_obj)
                ).filter(Ingredient.id == ingredient.id).first()

                default_unit = ingredient_with_unit.default_unit.abbreviation if ingredient_with_unit.default_unit else None

                results.append({
                    "id": ingredient.id,
                    "name": ingredient.name,
                    "category_id": ingredient.category_id,
                    "category": ingredient_with_unit.category_obj.display_name if ingredient_with_unit.category_obj else None,
                    "density": ingredient.density,
                    "default_unit": default_unit,
                    "aliases": ingredient.aliases or [],
                    "confidence": float(confidence)
                })

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索食材失败: {str(e)}")


@router.get("/hierarchy/{ingredient_id}", response_model=dict)
async def get_ingredient_hierarchy(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取食材的层级关系"""
    try:
        from app.models.ingredient_hierarchy import IngredientHierarchy

        ingredient = db.query(Ingredient).options(
            joinedload(Ingredient.default_unit),
            joinedload(Ingredient.category_obj)
        ).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        parent_relations = db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == ingredient_id
        ).all()

        parents = []
        for rel in parent_relations:
            parent_ing = db.query(Ingredient).filter(Ingredient.id == rel.parent_id, Ingredient.is_active == True).first()
            if parent_ing:
                parents.append({
                    "id": parent_ing.id,
                    "name": parent_ing.name,
                    "relationship_type": rel.relationship_type,
                    "confidence": float(rel.confidence) if rel.confidence else 1.0
                })

        child_relations = db.query(IngredientHierarchy).filter(
            IngredientHierarchy.parent_id == ingredient_id
        ).all()

        children = []
        for rel in child_relations:
            child_ing = db.query(Ingredient).options(
                joinedload(Ingredient.default_unit)
            ).filter(Ingredient.id == rel.child_id, Ingredient.is_active == True).first()
            if child_ing:
                children.append({
                    "id": child_ing.id,
                    "name": child_ing.name,
                    "relationship_type": rel.relationship_type,
                    "default_unit": child_ing.default_unit.abbreviation if child_ing.default_unit else None,
                    "confidence": float(rel.confidence) if rel.confidence else 1.0
                })

        return {
            "ingredient": {
                "id": ingredient.id,
                "name": ingredient.name,
                "category_id": ingredient.category_id,
                "category": ingredient.category_obj.display_name if ingredient.category_obj else None,
                "density": ingredient.density,
                "default_unit": ingredient.default_unit.abbreviation if ingredient.default_unit else None,
                "aliases": ingredient.aliases or []
            },
            "parents": parents,
            "children": children
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取层级关系失败: {str(e)}")


@router.get("/categories", response_model=List[dict])
async def get_ingredient_categories(
    parent_id: Optional[int] = Query(None, description="父类别ID，为None时返回顶级类别"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取食材分类列表"""
    try:
        query = db.query(IngredientCategory).filter(IngredientCategory.is_active == True)

        if parent_id is not None:
            query = query.filter(IngredientCategory.parent_category_id == parent_id)
        else:
            query = query.filter(IngredientCategory.parent_category_id.is_(None))

        categories = query.all()

        return [{
            "id": cat.id,
            "name": cat.name,
            "display_name": cat.display_name,
            "parent_category_id": cat.parent_category_id,
            "sort_order": cat.sort_order,
            "description": cat.description
        } for cat in categories]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类列表失败: {str(e)}")


@router.post("/resolve-hierarchy", response_model=Optional[dict])
async def resolve_ingredient_hierarchy(
    base_ingredient: str = Query(..., description="基础食材名称"),
    grade_requirement: Optional[str] = Query(None, description="等级要求，如高筋、中筋等"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """解析食材层级关系"""
    try:
        matcher = IngredientMatcher(db)
        ingredient = matcher.resolve_ingredient_hierarchy(base_ingredient, grade_requirement)

        if ingredient:
            # 重新查询以加载 default_unit 关系
            ingredient_with_unit = db.query(Ingredient).options(
                joinedload(Ingredient.default_unit),
                joinedload(Ingredient.category_obj)
            ).filter(Ingredient.id == ingredient.id).first()

            return {
                "id": ingredient.id,
                "name": ingredient.name,
                "category_id": ingredient.category_id,
                "category": ingredient_with_unit.category_obj.display_name if ingredient_with_unit.category_obj else None,
                "density": ingredient.density,
                "default_unit": ingredient_with_unit.default_unit.abbreviation if ingredient_with_unit.default_unit else None,
                "aliases": ingredient.aliases or []
            }
        else:
            return None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析层级关系失败: {str(e)}")


@router.get("/alternatives/{ingredient_id}", response_model=List[dict])
async def get_ingredient_alternatives(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取食材替代选项"""
    try:
        ingredient = db.query(Ingredient).options(
            joinedload(Ingredient.default_unit),
            joinedload(Ingredient.category_obj)
        ).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        matcher = IngredientMatcher(db)
        alternatives = matcher.suggest_alternatives(ingredient)

        return [{
            "id": alt.id,
            "name": alt.name,
            "category_id": alt.category_id,
            "category": alt.category_obj.display_name if alt.category_obj else None,
            "density": alt.density,
            "default_unit": alt.default_unit.abbreviation if alt.default_unit else None,
            "aliases": alt.aliases or []
        } for alt in alternatives]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取替代选项失败: {str(e)}")


def _get_default_mass_unit_id(db: Session) -> Optional[int]:
    """获取默认质量单位（斤）的 ID"""
    jin_unit = db.query(Unit).filter(Unit.abbreviation == "斤").first()
    if jin_unit:
        return jin_unit.id
    # 回退：查找 kg 或 g
    kg_unit = db.query(Unit).filter(Unit.abbreviation == "kg").first()
    return kg_unit.id if kg_unit else None


@router.post("", response_model=dict)
async def create_ingredient(
    name: str = Body(..., min_length=1),
    category_id: Optional[int] = Body(None),
    aliases: Optional[List[str]] = Body(None),
    density: Optional[float] = Body(None),
    default_unit: Optional[str] = Body(None),
    nutrition: Optional[dict] = Body(None, description="营养素数据，如 {protein: 10, fat: 5}"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """创建食材"""
    try:
        existing = db.query(Ingredient).filter(Ingredient.name == name, Ingredient.is_active == True).first()
        if existing:
            raise HTTPException(status_code=400, detail="食材已存在")

        # 使用单位匹配器获取单位 ID，未指定时默认为斤
        unit_id = None
        if default_unit:
            from app.services.unit_matcher import UnitMatcher
            matcher = UnitMatcher(db)
            unit_obj = matcher.match_or_create_unit(default_unit)
            unit_id = unit_obj.id if unit_obj else None
        else:
            unit_id = _get_default_mass_unit_id(db)

        new_ingredient = Ingredient(
            name=name,
            category_id=category_id,
            aliases=aliases or [],
            density=density,
            default_unit_id=unit_id,
            created_by=current_user.id
        )
        db.add(new_ingredient)
        db.commit()
        db.refresh(new_ingredient)

        # 处理营养素数据
        if nutrition:
            try:
                from app.models.nutrition_data import NutritionData

                # 构建营养素数据结构
                core_nutrients = {}
                all_nutrients = {}

                # 营养素映射（中文 -> 英文键名）
                nutrient_map = {
                    'energy': ('能量', 'kcal'),
                    'protein': ('蛋白质', 'g'),
                    'fat': ('脂肪', 'g'),
                    'carbohydrates': ('碳水化合物', 'g'),
                    'dietary_fiber': ('膳食纤维', 'g'),
                    'calcium': ('钙', 'mg'),
                    'iron': ('铁', 'mg'),
                    'sodium': ('钠', 'mg'),
                    'potassium': ('钾', 'mg'),
                }

                for eng_name, (zh_name, unit) in nutrient_map.items():
                    if nutrition.get(eng_name) is not None:
                        value = float(nutrition[eng_name])
                        if value > 0:
                            # 核心（中文键名）
                            core_nutrients[zh_name] = {
                                'value': value,
                                'unit': unit,
                                'key': eng_name,
                                'standard': '中国GB标准'
                            }
                            # 全部（英文键名）
                            all_nutrients[eng_name] = {
                                'value': value,
                                'unit': unit,
                                'standard': '中国GB标准'
                            }

                if core_nutrients:
                    nutrition_data = NutritionData(
                        ingredient_id=new_ingredient.id,
                        source='custom',
                        nutrients={
                            'core_nutrients': core_nutrients,
                            'all_nutrients': all_nutrients
                        },
                        reference_amount=100.0,
                        reference_unit='g',
                        match_confidence=1.0,
                        is_verified=False,
                        created_by=current_user.id,
                        updated_by=current_user.id
                    )
                    db.add(nutrition_data)
                    db.commit()
            except Exception as e:
                # 营养素数据创建失败不影响原料创建
                print(f"Warning: Failed to create nutrition data for {name}: {str(e)}")

        # 自动创建对应的同名商品
        try:
            from app.models.product_entity import Product

            # 检查是否已存在同名商品
            existing_product = db.query(Product).filter(
                Product.name == new_ingredient.name,
                Product.is_active == True
            ).first()

            if not existing_product:
                # 创建商品
                new_product = Product(
                    name=new_ingredient.name,
                    ingredient_id=new_ingredient.id,
                    created_by=current_user.id,
                    updated_by=current_user.id,
                    is_active=True
                )
                db.add(new_product)
                db.commit()
        except Exception as e:
            # 创建商品失败不影响原料创建
            print(f"Warning: Failed to create product for ingredient {new_ingredient.name}: {str(e)}")

        # 重新查询以加载 default_unit 和 category_obj 关系
        ingredient_with_unit = db.query(Ingredient).options(
            joinedload(Ingredient.default_unit),
            joinedload(Ingredient.category_obj)
        ).filter(Ingredient.id == new_ingredient.id).first()

        return {
            "id": new_ingredient.id,
            "name": new_ingredient.name,
            "category_id": new_ingredient.category_id,
            "category": ingredient_with_unit.category_obj.display_name if ingredient_with_unit.category_obj else None,
            "density": new_ingredient.density,
            "default_unit": ingredient_with_unit.default_unit.abbreviation if ingredient_with_unit.default_unit else None,
            "aliases": new_ingredient.aliases or [],
            "created_at": new_ingredient.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建食材失败: {str(e)}")


@router.put("/{ingredient_id}", response_model=dict)
async def update_ingredient(
    ingredient_id: int,
    name: Optional[str] = Body(None),
    category_id: Optional[int] = Body(None),
    aliases: Optional[List[str]] = Body(None),
    density: Optional[float] = Body(None),
    default_unit: Optional[str] = Body(None),
    default_unit_id: Optional[int] = Body(None),
    serving_weight: Optional[float] = Body(None, description="成品基准量（每份多重），用于制作菜谱成本换算"),
    serving_weight_unit_id: Optional[int] = Body(None, description="成品基准量单位ID"),
    nutrition: Optional[dict] = Body(None, description="营养素数据，如 {protein: 10, fat: 5}"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """更新食材 - 这是 ingredient_extended.py 中支持 nutrition 参数的版本"""
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        # 构造基本信息 payload（不含 nutrition——前端基本信息编辑不传 nutrition）
        payload = {}
        if name is not None and name != ingredient.name:
            existing = db.query(Ingredient).filter(
                Ingredient.name == name, Ingredient.is_active == True
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="食材已存在")
            payload["name"] = name
        if category_id is not None:
            payload["category_id"] = category_id
        if aliases is not None:
            payload["aliases"] = aliases
        if density is not None:
            payload["density"] = density
        if default_unit_id is not None:
            payload["default_unit_id"] = default_unit_id if default_unit_id > 0 else None
        elif default_unit is not None:
            from app.services.unit_matcher import UnitMatcher
            matcher = UnitMatcher(db)
            unit_obj = matcher.match_or_create_unit(default_unit)
            payload["default_unit_id"] = unit_obj.id if unit_obj else None
        if serving_weight is not None:
            payload["serving_weight"] = serving_weight if serving_weight > 0 else None
        if serving_weight_unit_id is not None:
            payload["serving_weight_unit_id"] = serving_weight_unit_id if serving_weight_unit_id > 0 else None

        # 分流：管理员直写 / 普通用户提议（全 manual）。放开 created_by 限制。
        if payload:
            payload["updated_by"] = current_user.id
            if current_user.is_admin:
                proposal_service.apply_as_admin(
                    db, entity_type="ingredient", entity_id=ingredient_id,
                    action="update", payload=payload, admin=current_user,
                )
            else:
                proposal_service.submit(
                    db, entity_type="ingredient", entity_id=ingredient_id,
                    action="update", payload=payload, proposer=current_user,
                )
            db.commit()
            db.refresh(ingredient)

        # 处理营养素数据
        if nutrition:
            try:
                print(f"[更新原料] 开始处理营养素数据: ingredient_id={ingredient_id}, nutrition={nutrition}")
                from app.models.nutrition_data import NutritionData

                # 构建营养素数据结构
                core_nutrients = {}
                all_nutrients = {}

                # 营养素映射（中文 -> 英文键名）
                nutrient_map = {
                    'energy': ('能量', 'kcal'),
                    'protein': ('蛋白质', 'g'),
                    'fat': ('脂肪', 'g'),
                    'carbohydrates': ('碳水化合物', 'g'),
                    'dietary_fiber': ('膳食纤维', 'g'),
                    'calcium': ('钙', 'mg'),
                    'iron': ('铁', 'mg'),
                    'sodium': ('钠', 'mg'),
                    'potassium': ('钾', 'mg'),
                }

                for eng_name, (zh_name, unit) in nutrient_map.items():
                    if nutrition.get(eng_name) is not None:
                        value = float(nutrition[eng_name])
                        print(f"[更新原料] 处理营养素 {eng_name}: value={value}")
                        if value > 0:
                            # 核心（中文键名）
                            core_nutrients[zh_name] = {
                                'value': value,
                                'unit': unit,
                                'key': eng_name,
                                'standard': '中国GB标准'
                            }
                            # 全部（英文键名）
                            all_nutrients[eng_name] = {
                                'value': value,
                                'unit': unit,
                                'standard': '中国GB标准'
                            }

                print(f"[更新原料] 构建完成: core_nutrients={list(core_nutrients.keys())}, all_nutrients={list(all_nutrients.keys())}")

                if core_nutrients:
                    # 查找是否已存在自定义营养数据
                    existing_nutrition = db.query(NutritionData).filter(
                        NutritionData.ingredient_id == ingredient_id,
                        NutritionData.source == 'custom'
                    ).first()

                    print(f"[更新原料] 查询现有营养数据: existing={existing_nutrition is not None}")

                    if existing_nutrition:
                        # 更新现有营养数据
                        print(f"[更新原料] 更新现有营养数据 id={existing_nutrition.id}")
                        existing_nutrition.nutrients = {
                            'core_nutrients': core_nutrients,
                            'all_nutrients': all_nutrients,
                            'nutrient_details': {**all_nutrients}
                        }
                        existing_nutrition.updated_by = current_user.id
                    else:
                        # 创建新的营养数据
                        print(f"[更新原料] 创建新的营养数据")
                        nutrition_data = NutritionData(
                            ingredient_id=ingredient_id,
                            source='custom',
                            nutrients={
                                'core_nutrients': core_nutrients,
                                'all_nutrients': all_nutrients,
                                'nutrient_details': {**all_nutrients}
                            },
                            reference_amount=100.0,
                            reference_unit='g',
                            match_confidence=1.0,
                            is_verified=False,
                            created_by=current_user.id,
                            updated_by=current_user.id
                        )
                        db.add(nutrition_data)

                    db.commit()
                    print(f"[更新原料] 营养数据保存成功")
                else:
                    print(f"[更新原料] core_nutrients 为空，跳过营养数据更新")
            except Exception as e:
                # 营养素数据更新失败不影响原料更新
                import traceback
                print(f"Warning: Failed to update nutrition data for {ingredient.name}: {str(e)}")
                print(f"Traceback: {traceback.format_exc()}")
        else:
            print(f"[更新原料] 未提供营养素数据")

        # 重新查询以加载 default_unit 和 category_obj 关系
        ingredient_with_unit = db.query(Ingredient).options(
            joinedload(Ingredient.default_unit),
            joinedload(Ingredient.category_obj),
            joinedload(Ingredient.serving_weight_unit)
        ).filter(Ingredient.id == ingredient.id).first()

        return {
            "id": ingredient.id,
            "name": ingredient.name,
            "category_id": ingredient.category_id,
            "category": ingredient_with_unit.category_obj.display_name if ingredient_with_unit.category_obj else None,
            "density": ingredient.density,
            "default_unit_id": ingredient.default_unit_id,
            "default_unit_name": ingredient_with_unit.default_unit.abbreviation if ingredient_with_unit.default_unit else None,
            "serving_weight": float(ingredient.serving_weight) if ingredient.serving_weight is not None else None,
            "serving_weight_unit_id": ingredient.serving_weight_unit_id,
            "serving_weight_unit_name": ingredient_with_unit.serving_weight_unit.abbreviation if ingredient_with_unit.serving_weight_unit else None,
            "aliases": ingredient.aliases or [],
            "is_imported": ingredient.is_imported,
            "created_at": ingredient.created_at,
            "updated_at": ingredient.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新食材失败: {str(e)}")


@router.delete("/{ingredient_id}/hard")
async def hard_delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """硬删除食材 - 永久删除"""
    try:
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        db.delete(ingredient)
        db.commit()

        return {"message": "食材已永久删除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"硬删除食材失败: {str(e)}")


@router.get("", response_model=PaginatedResponse[dict])
async def get_ingredients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str = Query(None, alias="q"),
    category_id: Optional[int] = Query(None),
    category_ids: Optional[str] = Query(None, description="逗号分隔的分类ID列表，与 category_id 互斥"),
    sort_by: str = Query("created_at", enum=["name", "created_at", "price_records"], description="排序方式"),
    no_nutrition: bool = Query(False, description="筛选未配置营养成分的原料"),
    no_price: bool = Query(False, description="筛选没有维护过价格的原料"),
    single_price: bool = Query(False, description="筛选仅有一条价格记录的原料"),
    single_merchant: bool = Query(False, description="筛选仅有一家商家有其价格记录的原料"),
    no_recipe: bool = Query(False, description="筛选无相关菜谱的原料"),
    no_product: bool = Query(False, description="筛选无下属商品的原料"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取食材列表（分页）"""
    try:
        from app.models.product_entity import Product
        from app.models.product import ProductRecord
        from sqlalchemy import func

        # 合并 category_id（单值）和 category_ids（逗号分隔多值）
        _category_filter_ids: list[int] = []
        if category_id is not None:
            _category_filter_ids.append(category_id)
        if category_ids:
            for cid in category_ids.split(','):
                cid = cid.strip()
                if cid:
                    _category_filter_ids.append(int(cid))

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

            if search is not None:
                # 搜索名称、原料别名或商品别名
                subquery = subquery.filter(
                    (Ingredient.name.contains(search)) |
                    json_text_contains(Ingredient.aliases, search) |
                    (Ingredient.products.any(Product.name.contains(search))) |
                    (Ingredient.products.any(json_text_contains(Product.aliases, search)))
                )

            if _category_filter_ids:
                subquery = subquery.filter(Ingredient.category_id.in_(_category_filter_ids))

            subquery = subquery.group_by(Ingredient.id).subquery()

            # 然后将此子查询与主查询连接，并按记录数量排序
            query = db.query(Ingredient).options(
                joinedload(Ingredient.default_unit),
                joinedload(Ingredient.category_obj)
            ).join(
                subquery, Ingredient.id == subquery.c.ingredient_id
            ).filter(Ingredient.is_active == True)

            if search is not None:
                # 搜索名称、原料别名或商品别名
                query = query.filter(
                    (Ingredient.name.contains(search)) |
                    json_text_contains(Ingredient.aliases, search) |
                    (Ingredient.products.any(Product.name.contains(search))) |
                    (Ingredient.products.any(json_text_contains(Product.aliases, search)))
                )

            if _category_filter_ids:
                query = query.filter(Ingredient.category_id.in_(_category_filter_ids))

            # 应用特殊条件过滤
            query = _apply_ingredient_special_conditions(
                query, no_nutrition, no_price, single_price, single_merchant, no_recipe, no_product
            )

            # 按价格记录数量降序排列
            ingredients = query.order_by(
                subquery.c.record_count.desc(),  # 按记录数量降序排列
                Ingredient.id  # 按ID确保排序稳定性
            ).offset(skip).limit(limit).all()

            # 需要单独查询总数
            total_query = db.query(Ingredient.id).join(
                subquery, Ingredient.id == subquery.c.ingredient_id
            ).filter(Ingredient.is_active == True)

            if search is not None:
                # 搜索名称、原料别名或商品别名
                total_query = total_query.filter(
                    (Ingredient.name.contains(search)) |
                    json_text_contains(Ingredient.aliases, search) |
                    (Ingredient.products.any(Product.name.contains(search))) |
                    (Ingredient.products.any(json_text_contains(Product.aliases, search)))
                )

            if _category_filter_ids:
                total_query = total_query.filter(Ingredient.category_id.in_(_category_filter_ids))

            # 应用特殊条件过滤
            total_query = _apply_ingredient_special_conditions(
                total_query, no_nutrition, no_price, single_price, single_merchant, no_recipe, no_product
            )

            total = total_query.count()
        else:
            # 按名称或创建时间排序
            query = db.query(Ingredient).options(
                joinedload(Ingredient.default_unit),
                joinedload(Ingredient.category_obj)
            ).filter(Ingredient.is_active == True)

            if search is not None:
                # 搜索名称、原料别名或商品别名
                query = query.filter(
                    (Ingredient.name.contains(search)) |
                    json_text_contains(Ingredient.aliases, search) |
                    (Ingredient.products.any(Product.name.contains(search))) |
                    (Ingredient.products.any(json_text_contains(Product.aliases, search)))
                )

            if _category_filter_ids:
                query = query.filter(Ingredient.category_id.in_(_category_filter_ids))

            # 应用特殊条件过滤
            query = _apply_ingredient_special_conditions(
                query, no_nutrition, no_price, single_price, single_merchant, no_recipe, no_product
            )

            # 按指定字段排序
            if sort_by == "name":
                query = query.order_by(Ingredient.name)
            elif sort_by == "created_at":
                query = query.order_by(Ingredient.created_at.desc())

            # 获取总数
            total = query.count()

            # 获取分页数据
            ingredients = query.offset(skip).limit(limit).all()

        items = [{
            "id": ing.id,
            "name": ing.name,
            "category_id": ing.category_id,
            "category": ing.category_obj.display_name if ing.category_obj else None,
            "density": ing.density,
            "default_unit": ing.default_unit.abbreviation if ing.default_unit else None,
            "aliases": ing.aliases or [],
            "created_at": ing.created_at
        } for ing in ingredients]

        page = skip // limit + 1
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取食材列表失败: {str(e)}")


@router.get("/{ingredient_id}", response_model=dict)
async def get_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取食材详情"""
    try:
        ingredient = db.query(Ingredient).options(
            joinedload(Ingredient.default_unit),
            joinedload(Ingredient.category_obj),
            joinedload(Ingredient.serving_weight_unit)
        ).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        # 反查制作菜谱（哪个菜谱把我当成品产出）
        from app.models.recipe import Recipe
        making_recipe = db.query(Recipe).filter(
            Recipe.result_ingredient_id == ingredient_id,
            Recipe.is_active == True
        ).first()

        return {
            "id": ingredient.id,
            "name": ingredient.name,
            "category_id": ingredient.category_id,
            "category": ingredient.category_obj.display_name if ingredient.category_obj else None,
            "density": ingredient.density,
            "default_unit": ingredient.default_unit.abbreviation if ingredient.default_unit else None,
            "serving_weight": float(ingredient.serving_weight) if ingredient.serving_weight is not None else None,
            "serving_weight_unit_id": ingredient.serving_weight_unit_id,
            "serving_weight_unit_name": ingredient.serving_weight_unit.abbreviation if ingredient.serving_weight_unit else None,
            "making_recipe_id": making_recipe.id if making_recipe else None,
            "making_recipe_name": making_recipe.name if making_recipe else None,
            "aliases": ingredient.aliases or [],
            "created_at": ingredient.created_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取食材详情失败: {str(e)}")


@router.delete("/{ingredient_id}")
async def soft_delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """软删除食材

    仅当原料未关联任何菜谱时可删除。删除时级联软删除其下的商品和关联关系。
    管理员可删除任意食材（直写即时生效），普通用户提交删除提议（manual 待审）。
    级联软删商品/层级关系由 IngredientExecutor._apply_delete 完成。
    """
    try:
        from app.models.recipe import RecipeIngredient

        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id, Ingredient.is_active == True).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="食材不存在")

        # 菜谱引用检查（端点提交时；执行器 apply 时再查一次）
        recipe_count = db.query(RecipeIngredient).filter(
            RecipeIngredient.ingredient_id == ingredient_id
        ).count()
        if recipe_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"该食材已被 {recipe_count} 个菜谱引用，无法删除。请先移除菜谱中的该食材。"
            )

        # 分流：管理员直写（级联软删商品+层级在执行器）/ 普通用户提议待审
        if current_user.is_admin:
            proposal_service.apply_as_admin(
                db, entity_type="ingredient", entity_id=ingredient_id,
                action="delete", payload={}, admin=current_user,
            )
            db.commit()
            return {"message": "原料已删除（管理员直写，级联软删商品和层级关系）"}

        p = proposal_service.submit(
            db, entity_type="ingredient", entity_id=ingredient_id,
            action="delete", payload={}, proposer=current_user,
        )
        db.commit()
        return {"message": f"删除提议已提交（proposal_id={p.id}, status={p.status}）"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除原料失败: {str(e)}")


def _flatten_nutrients(nutrients_dict: dict) -> dict:
    """将嵌套格式的营养数据（core_nutrients + all_nutrients）扁平化为单一字典

    返回扁平化的 {nutrient_key: {value, unit, ...}} 字典，
    其中 core_nutrients 使用中文键名，all_nutrients 使用英文键名。
    """
    if not nutrients_dict or not isinstance(nutrients_dict, dict):
        return {}

    flat = {}

    # 提取 core_nutrients（中文键名优先）
    core = nutrients_dict.get("core_nutrients", {})
    if isinstance(core, dict):
        for k, v in core.items():
            if isinstance(v, dict) and "value" in v:
                flat[k] = dict(v)

    # 提取 all_nutrients（英文键名，补充不在 core 中的）
    all_nut = nutrients_dict.get("all_nutrients", {})
    if isinstance(all_nut, dict):
        # 收集 core 中的英文 key 以避免重复
        core_english_keys = {
            v.get("key") for v in core.values()
            if isinstance(v, dict) and "key" in v
        }
        for k, v in all_nut.items():
            if isinstance(v, dict) and "value" in v and k not in core_english_keys:
                flat[k] = dict(v)

    # 兼容扁平格式：直接包含 nutrient key
    for k, v in nutrients_dict.items():
        if k in ("core_nutrients", "all_nutrients", "nutrient_details"):
            continue
        if isinstance(v, dict) and "value" in v:
            if k not in flat:
                flat[k] = dict(v)

    return flat


def _mix_custom_nutrition(base: dict, overlay: dict) -> dict:
    """合并两个扁平化的营养数据字典，overlay 的值覆盖 base

    返回嵌套格式 {core_nutrients: {...}, all_nutrients: {...}}，
    兼容 NutritionMixin.merge_nutrition_data 的处理方式（扁平格式）。
    由于 merge_nutrition_data 支持扁平格式，直接返回扁平字典即可。
    """
    if not overlay:
        return base
    if not base:
        return overlay

    result = dict(base)
    for k, v in overlay.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            merged = dict(result[k])
            merged.update(v)
            result[k] = merged
        else:
            result[k] = v
    return result


def _get_ingredient_nutrition_flat(db: Session, ingredient_id: int) -> dict:
    """获取原料的营养数据并返回扁平化格式"""
    from app.models.nutrition_data import NutritionData

    from app.models.mixins import NutritionMixin
    nutrition_data = NutritionMixin.get_best_nutrition_data(db, ingredient_id)

    if nutrition_data and nutrition_data.nutrients:
        return _flatten_nutrients(nutrition_data.nutrients)
    return {}


@router.post("/merge", response_model=dict)
async def merge_ingredients(
    source_id: int = Body(..., embed=False),
    target_id: int = Body(..., embed=False),
    merge_same_name_products: bool = Body(True, embed=False),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """合并原料，将源原料合并到目标原料，源原料会被软删除

    权限控制：
    - 管理员可以合并所有原料
    - 普通用户只能合并自己添加的原料

    合并操作：
    1. 菜谱中的原料引用更新为目标原料
    2. 商品处理（受 merge_same_name_products 参数控制）：
       - merge_same_name_products=True: 同名商品合并（价格记录迁移、营养数据 mixin、源商品软删除）
       - merge_same_name_products=False: 同名商品保留为独立商品（移到目标原料下，原料营养→商品自定义营养 mixin）
    3. 别名合并：源原料的名称和别名添加到目标原料的别名中（去重）
    4. 软删除源原料并标记为已合并
    """
    from app.models.recipe import RecipeIngredient
    from app.models.product_entity import Product
    from app.models.product import ProductRecord
    from app.models.nutrition_data import NutritionData

    try:
        # 获取源原料和目标原料
        source_ingredient = db.query(Ingredient).filter(Ingredient.id == source_id, Ingredient.is_active == True).first()
        target_ingredient = db.query(Ingredient).filter(Ingredient.id == target_id, Ingredient.is_active == True).first()

        if not source_ingredient:
            raise HTTPException(status_code=404, detail="源原料不存在")
        if not target_ingredient:
            raise HTTPException(status_code=404, detail="目标原料不存在")

        if source_id == target_id:
            raise HTTPException(status_code=400, detail="不能将原料合并到自身")

        # 权限检查
        if not current_user.is_admin:
            # 普通用户只能合并自己添加的原料
            if source_ingredient.created_by != current_user.id:
                raise HTTPException(status_code=403, detail="只能合并自己添加的原料")

        # 1. 更新菜谱中的原料引用
        recipe_ingredients = db.query(RecipeIngredient).filter(RecipeIngredient.ingredient_id == source_id).all()
        recipe_count = len(recipe_ingredients)
        for ri in recipe_ingredients:
            ri.ingredient_id = target_id

        # 2. 处理商品
        product_migrated_count = 0
        price_migrated_count = 0
        product_merged_count = 0  # 同名商品合并数量

        # 获取源原料下的所有商品
        source_products = db.query(Product).filter(
            Product.ingredient_id == source_id,
            Product.is_active == True
        ).all()

        # 获取目标原料下的所有商品（构建名称索引）
        target_products = db.query(Product).filter(
            Product.ingredient_id == target_id,
            Product.is_active == True
        ).all()
        target_product_names = {p.name: p for p in target_products}

        # 如果不合并同名商品，预先获取源原料的扁平化营养数据
        source_ingredient_nutrition_flat = None
        if not merge_same_name_products:
            source_ingredient_nutrition_flat = _get_ingredient_nutrition_flat(db, source_id)

        for source_product in source_products:
            is_same_name = source_product.name in target_product_names

            if merge_same_name_products and is_same_name:
                # 【合并同名商品】将源商品合并到目标同名商品
                target_product = target_product_names[source_product.name]

                # 迁移价格记录
                price_records = db.query(ProductRecord).filter(
                    ProductRecord.product_id == source_product.id
                ).all()
                for pr in price_records:
                    pr.product_id = target_product.id
                    price_migrated_count += 1

                # Mixin 源商品的自定义营养到目标商品
                if source_product.custom_nutrition_data:
                    source_custom_flat = _flatten_nutrients(source_product.custom_nutrition_data)
                    if source_custom_flat:
                        target_custom_flat = _flatten_nutrients(target_product.custom_nutrition_data or {})
                        mixed = _mix_custom_nutrition(target_custom_flat, source_custom_flat)
                        target_product.custom_nutrition_data = mixed

                # 软删除源商品
                source_product.is_active = False
                product_merged_count += 1
            else:
                # 【保留独立商品】将商品移到目标原料下
                source_product.ingredient_id = target_id
                product_migrated_count += 1

                if not merge_same_name_products and source_ingredient_nutrition_flat:
                    # 将原料营养数据 mixin 到商品自定义营养数据
                    product_custom_flat = _flatten_nutrients(source_product.custom_nutrition_data or {})
                    # 原料营养为基础，商品自定义优先覆盖
                    mixed = _mix_custom_nutrition(source_ingredient_nutrition_flat, product_custom_flat)
                    source_product.custom_nutrition_data = mixed

        # 3. 合并别名
        target_aliases = set(target_ingredient.aliases or [])
        source_name = source_ingredient.name
        source_aliases = set(source_ingredient.aliases or [])

        # 添加源原料名称（如果不与目标原料名称相同）
        if source_name != target_ingredient.name:
            target_aliases.add(source_name)

        # 添加源原料别名（去重）
        for alias in source_aliases:
            if alias != target_ingredient.name:
                target_aliases.add(alias)

        # 更新目标原料的别名
        target_ingredient.aliases = list(target_aliases) if target_aliases else None

        # 4. 从 IngredientNutritionMapping 表更新引用
        from app.models.nutrition import IngredientNutritionMapping
        mappings = db.query(IngredientNutritionMapping).filter(
            IngredientNutritionMapping.ingredient_id == source_id
        ).all()
        for mapping in mappings:
            # 检查是否已存在相同的映射
            existing = db.query(IngredientNutritionMapping).filter(
                IngredientNutritionMapping.ingredient_id == target_id,
                IngredientNutritionMapping.nutrition_id == mapping.nutrition_id
            ).first()
            if not existing:
                mapping.ingredient_id = target_id
            else:
                # 已存在相同映射，删除重复的
                db.delete(mapping)

        # 4.5 迁移 NutritionData 记录（原料级营养数据）
        nutrition_data_migrated_count = 0
        source_nutrition_records = db.query(NutritionData).filter(
            NutritionData.ingredient_id == source_id
        ).all()
        for nd in source_nutrition_records:
            # 检查目标原料是否已有营养数据
            existing = db.query(NutritionData).filter(
                NutritionData.ingredient_id == target_id
            ).first()
            if not existing:
                nd.ingredient_id = target_id
                nutrition_data_migrated_count += 1
            # 如果目标已有营养数据，源营养数据保留（随原料软删除而不再活跃）

        # 4.6 更新 ProductIngredientLink 引用
        from app.models.product_ingredient_link import ProductIngredientLink
        product_links_updated = 0
        source_product_links = db.query(ProductIngredientLink).filter(
            ProductIngredientLink.ingredient_id == source_id
        ).all()
        for link in source_product_links:
            existing = db.query(ProductIngredientLink).filter(
                ProductIngredientLink.product_id == link.product_id,
                ProductIngredientLink.ingredient_id == target_id
            ).first()
            if not existing:
                link.ingredient_id = target_id
                product_links_updated += 1
            else:
                db.delete(link)

        # 5. 处理层级关系
        from app.models.ingredient_hierarchy import IngredientHierarchy

        hierarchy_updated_count = 0

        # 5.1 源食材作为父级的关系：目标食材继承源食材的子级
        child_relations = db.query(IngredientHierarchy).filter(
            IngredientHierarchy.parent_id == source_id
        ).all()

        for relation in child_relations:
            # 检查是否已存在相同的关系
            existing = db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id == target_id,
                IngredientHierarchy.child_id == relation.child_id,
                IngredientHierarchy.relation_type == relation.relation_type
            ).first()

            if not existing:
                # 转移关系到目标食材
                relation.parent_id = target_id
                hierarchy_updated_count += 1
            else:
                # 已存在相同关系，软删除重复的关系
                relation.is_active = False

        # 5.2 源食材作为子级的关系：目标食材继承源食材的父级
        parent_relations = db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == source_id
        ).all()

        for relation in parent_relations:
            # 检查是否已存在相同的关系
            existing = db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id == relation.parent_id,
                IngredientHierarchy.child_id == target_id,
                IngredientHierarchy.relation_type == relation.relation_type
            ).first()

            if not existing:
                # 转移关系到目标食材
                relation.child_id = target_id
                hierarchy_updated_count += 1
            else:
                # 已存在相同关系，软删除重复的关系
                relation.is_active = False

        # 6. 软删除源原料并标记为已合并
        source_ingredient.is_active = False
        source_ingredient.is_merged = True
        source_ingredient.merged_into_id = target_id
        source_ingredient.updated_by = current_user.id

        db.commit()

        return {
            "message": f"成功将原料 '{source_ingredient.name}' 合并到 '{target_ingredient.name}'",
            "source_id": source_id,
            "target_id": target_id,
            "recipe_count": recipe_count,
            "product_migrated_count": product_migrated_count,
            "price_migrated_count": price_migrated_count,
            "product_merged_count": product_merged_count,
            "hierarchy_updated_count": hierarchy_updated_count,
            "nutrition_data_migrated_count": nutrition_data_migrated_count,
            "merge_same_name_products": merge_same_name_products
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"合并原料失败: {str(e)}")


@router.post("/batch-create-products", response_model=dict)
async def batch_create_products(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """为所有没有对应商品的原料批量创建商品"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅限管理员访问")

    try:
        from app.models.product_entity import Product

        # 获取所有原料
        ingredients = db.query(Ingredient).filter(Ingredient.is_active == True).all()

        created_count = 0
        skipped_count = 0
        failed_count = 0

        for ingredient in ingredients:
            try:
                # 检查是否已存在同名商品
                existing_product = db.query(Product).filter(
                    Product.name == ingredient.name,
                    Product.is_active == True
                ).first()

                if existing_product:
                    skipped_count += 1
                    continue

                # 创建商品
                new_product = Product(
                    name=ingredient.name,
                    ingredient_id=ingredient.id,
                    created_by=current_user.id,
                    updated_by=current_user.id,
                    is_active=True
                )
                db.add(new_product)
                created_count += 1
                print(f"创建商品: {ingredient.name}")

            except Exception as e:
                failed_count += 1
                print(f"创建商品失败 {ingredient.name}: {str(e)}")

        db.commit()

        return {
            "message": f"批量创建商品完成：创建 {created_count}，跳过 {skipped_count}，失败 {failed_count}",
            "created": created_count,
            "skipped": skipped_count,
            "failed": failed_count
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量创建商品失败: {str(e)}")