"""导出集收集：full 全量 / mine 仅我的 + 可达性遍历。

mine 模式从「我的菜谱/价格记录/商品」出发，沿外键扩张集合到不动点，
确保引用到的管理员数据（食材/营养/单位等）一并纳入，避免导入后引用悬空。
"""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.recipe import Recipe, RecipeIngredient
from app.models.nutrition import Ingredient
from app.models.nutrition_data import NutritionData
from app.models.unit import Unit, UnitConversion
from app.models.ingredient_category import IngredientCategory
from app.models.ingredient_hierarchy import IngredientHierarchy
from app.models.entity_density import EntityDensity
from app.models.entity_unit_override import EntityUnitOverride
from app.models.product_entity import Product
from app.models.product_barcode import ProductBarcode
from app.models.product_ingredient_link import ProductIngredientLink
from app.models.product import ProductRecord
from app.models.merchant import Merchant
from app.models.user_place import UserPlace


@dataclass
class ExportSet:
    """各表待导出的 id 集合。None 表示「全部」（full 模式）。"""
    full_mode: bool = False
    recipe_ids: set = field(default_factory=set)
    ingredient_ids: set = field(default_factory=set)
    nutrition_ids: set = field(default_factory=set)
    unit_ids: set = field(default_factory=set)
    unit_conversion_ids: set = field(default_factory=set)
    category_ids: set = field(default_factory=set)
    hierarchy_ids: set = field(default_factory=set)
    entity_density_ids: set = field(default_factory=set)
    entity_unit_override_ids: set = field(default_factory=set)
    product_ids: set = field(default_factory=set)
    barcode_ids: set = field(default_factory=set)
    product_link_ids: set = field(default_factory=set)
    price_record_ids: set = field(default_factory=set)
    merchant_ids: set = field(default_factory=set)
    user_place_ids: set = field(default_factory=set)


def collect_full_set(db: Session) -> ExportSet:
    """full 模式：查询库内全部 id 填入集合（保留 full_mode 标记，供查询层参考）。

    注：packaging 的查询层对 full_mode 直接不加 id 过滤亦可；此处填充实集
    是为了让 caller（如测试、校验）能直接读取集合而无需再查库。
    """
    es = ExportSet(full_mode=True)
    # 食材及其闭包（营养/分类/单位/层级）
    seed = {i.id for i in db.query(Ingredient).all()}
    ingredients, ing_units, nutrition_ids, category_ids = _collect_ingredient_closure(db, seed)
    es.ingredient_ids = ingredients
    es.nutrition_ids = nutrition_ids
    # 注意：category_ids（来自食材闭包）会被下方全量覆盖，此处是死代码，故不赋值；
    # ingredients/nutrition 返回值仍在使用。
    es.unit_ids.update(ing_units)
    # 菜谱
    es.recipe_ids = {r.id for r in db.query(Recipe).all()}
    # 单位（含非食材引用的全量单位）+ 换算
    all_unit_ids = {u.id for u in db.query(Unit).all()}
    es.unit_ids.update(all_unit_ids)
    es.unit_conversion_ids = {c.id for c in db.query(UnitConversion).all()}
    # 分类/层级全量
    es.category_ids = {c.id for c in db.query(IngredientCategory).all()}
    es.hierarchy_ids = {h.id for h in db.query(IngredientHierarchy).all()}
    # 商品及其衍生（条码/关联/密度）
    es.product_ids = {p.id for p in db.query(Product).all()}
    if es.product_ids:
        es.barcode_ids = {
            b.id for b in db.query(ProductBarcode).filter(ProductBarcode.product_id.in_(es.product_ids)).all()
        }
        es.product_link_ids = {
            l.id for l in db.query(ProductIngredientLink).filter(ProductIngredientLink.product_id.in_(es.product_ids)).all()
        }
    # 密度（ingredient + product 全量，仅活跃数据）
    es.entity_density_ids = {d.id for d in db.query(EntityDensity).filter(EntityDensity.is_active.is_(True)).all()}
    # 自定义单位（ingredient + product 全量，仅活跃数据）
    es.entity_unit_override_ids = {o.id for o in db.query(EntityUnitOverride).filter(EntityUnitOverride.is_active.is_(True)).all()}
    # 价格记录 / 商家 / 收藏全量
    es.price_record_ids = {r.id for r in db.query(ProductRecord).all()}
    es.merchant_ids = {m.id for m in db.query(Merchant).all()}
    es.user_place_ids = {f.id for f in db.query(UserPlace).all()}
    return es


def _collect_ingredient_closure(db: Session, seed_ingredient_ids: set) -> tuple[set, set, set, set]:
    """从种子食材出发，扩张 ingredient / nutrition / category / unit / density / hierarchy 集合到不动点。

    返回 (ingredients, units, nutritions, categories)。
    """
    ingredients = set(seed_ingredient_ids)
    units = set()
    nutritions = set()
    categories = set()

    # 不动点迭代：层级关系会把更多食材拉进来
    while True:
        prev_size = len(ingredients)
        rows = db.query(Ingredient).filter(Ingredient.id.in_(ingredients)).all() if ingredients else []
        for ing in rows:
            if ing.nutrition_id:
                nutritions.add(ing.nutrition_id)
            if ing.category_id:
                categories.add(ing.category_id)
            for uid in (ing.piece_weight_unit_id, ing.serving_weight_unit_id):
                if uid:
                    units.add(uid)
            # 营养映射回链也可能指向更多 NutritionData
        # 层级关系双向扩张食材集合
        if ingredients:
            hier = db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id.in_(ingredients) |
                IngredientHierarchy.child_id.in_(ingredients)
            ).all()
            for h in hier:
                ingredients.add(h.parent_id)
                ingredients.add(h.child_id)
        if len(ingredients) == prev_size:
            break

    # nutrition_ids 由 ingredient 反查
    if ingredients:
        for ing in db.query(Ingredient).filter(Ingredient.id.in_(ingredients)).all():
            if ing.nutrition_id:
                nutritions.add(ing.nutrition_id)

    return ingredients, units, nutritions, categories  # type: ignore[return-value]


def collect_mine_set(db: Session, user_id: int) -> ExportSet:
    """mine 模式：我的直接数据 + 可达性扩张。"""
    es = ExportSet(full_mode=False)

    # 1) 我的菜谱 + 其 RecipeIngredient 引用的食材/单位
    my_recipes = db.query(Recipe).filter(Recipe.user_id == user_id).all()
    es.recipe_ids = {r.id for r in my_recipes}
    seed_ingredients = set()
    recipe_unit_ids = set()
    if es.recipe_ids:
        ris = db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id.in_(es.recipe_ids)).all()
        for ri in ris:
            if ri.ingredient_id:
                seed_ingredients.add(ri.ingredient_id)
            if ri.unit_id:
                recipe_unit_ids.add(ri.unit_id)
        # 成品关联
        for r in my_recipes:
            if r.result_ingredient_id:
                seed_ingredients.add(r.result_ingredient_id)

    # 2) 我的价格记录 → 商品/单位/商家
    my_records = db.query(ProductRecord).filter(ProductRecord.user_id == user_id).all()
    es.price_record_ids = {r.id for r in my_records}
    seed_products = set()
    record_unit_ids = set()
    merchant_ids = set()
    for r in my_records:
        if r.product_id:
            seed_products.add(r.product_id)
        if r.original_unit_id:
            record_unit_ids.add(r.original_unit_id)
        if r.standard_unit_id:
            record_unit_ids.add(r.standard_unit_id)
        if r.merchant_id:
            merchant_ids.add(r.merchant_id)

    # 3) 我创建的商品（全局库按 created_by）
    my_created_products = db.query(Product).filter(Product.created_by == user_id).all()
    seed_products.update(p.id for p in my_created_products)
    # 我创建的食材（全局库按 created_by）
    seed_ingredients.update(
        i.id for i in db.query(Ingredient).filter(Ingredient.created_by == user_id).all()
    )
    # 我创建的单位
    my_units = {u.id for u in db.query(Unit).filter(Unit.created_by == user_id).all()}
    es.unit_ids.update(my_units)

    # 4) 食材闭包扩张
    ingredients, ing_units, nutrition_ids, category_ids = _collect_ingredient_closure(db, seed_ingredients)
    es.ingredient_ids = ingredients
    es.nutrition_ids = nutrition_ids
    es.category_ids = category_ids
    es.unit_ids.update(ing_units)
    es.unit_ids.update(recipe_unit_ids)
    es.unit_ids.update(record_unit_ids)

    # 5) 商品闭包：商品引用的食材（已在 ingredients）、条码、关联
    if seed_products:
        products = db.query(Product).filter(Product.id.in_(seed_products)).all()
        es.product_ids = {p.id for p in products}
        extra_ing = {p.ingredient_id for p in products if p.ingredient_id}
        if extra_ing - es.ingredient_ids:
            merged, _, _, _ = _collect_ingredient_closure(db, extra_ing)
            es.ingredient_ids.update(merged)
        # 条码
        es.barcode_ids = {
            b.id for b in db.query(ProductBarcode).filter(ProductBarcode.product_id.in_(es.product_ids)).all()
        }
        # 关联
        es.product_link_ids = {
            l.id for l in db.query(ProductIngredientLink).filter(ProductIngredientLink.product_id.in_(es.product_ids)).all()
        }

    # 6) 商家（我的商家 + 价格记录引用的 + 我的收藏）
    # Merchant 为用户私有（user_id 归属），mine 模式需纳入所有归属我的商家，
    # 即使未为其记录过价格。
    my_merchant_ids = {m.id for m in db.query(Merchant).filter(Merchant.user_id == user_id).all()}
    es.merchant_ids = merchant_ids | my_merchant_ids
    es.user_place_ids = {
        f.id for f in db.query(UserPlace).filter(UserPlace.user_id == user_id).all()
    }

    # 7) 由 ingredient_ids / unit_ids 派生：密度、层级、换算、分类（闭包已含 category）
    if es.ingredient_ids:
        es.entity_density_ids = {
            d.id for d in db.query(EntityDensity).filter(
                EntityDensity.entity_type == "ingredient",
                EntityDensity.entity_id.in_(es.ingredient_ids),
                EntityDensity.is_active.is_(True),
            ).all()
        }
        es.entity_unit_override_ids = {
            o.id for o in db.query(EntityUnitOverride).filter(
                EntityUnitOverride.entity_type == "ingredient",
                EntityUnitOverride.entity_id.in_(es.ingredient_ids),
                EntityUnitOverride.is_active.is_(True),
            ).all()
        }
        es.hierarchy_ids = {
            h.id for h in db.query(IngredientHierarchy).filter(
                IngredientHierarchy.parent_id.in_(es.ingredient_ids) |
                IngredientHierarchy.child_id.in_(es.ingredient_ids)
            ).all()
        }
    if es.product_ids:
        es.entity_density_ids.update(
            d.id for d in db.query(EntityDensity).filter(
                EntityDensity.entity_type == "product",
                EntityDensity.entity_id.in_(es.product_ids),
                EntityDensity.is_active.is_(True),
            ).all()
        )
        es.entity_unit_override_ids.update(
            o.id for o in db.query(EntityUnitOverride).filter(
                EntityUnitOverride.entity_type == "product",
                EntityUnitOverride.entity_id.in_(es.product_ids),
                EntityUnitOverride.is_active.is_(True),
            ).all()
        )
    if es.unit_ids:
        es.unit_conversion_ids = {
            c.id for c in db.query(UnitConversion).filter(
                UnitConversion.from_unit_id.in_(es.unit_ids) |
                UnitConversion.to_unit_id.in_(es.unit_ids)
            ).all()
        }

    return es
