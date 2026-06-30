"""打包服务：按 ExportSet 查询→序列化→收集图片→写入 zip。

对外暴露 build_export_zip(db, user, scope) -> (zip_bytes, manifest_dict)。
"""
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

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
from app.models.blacklist_group import BlacklistGroup, BlacklistGroupIngredient
from app.models.user_ingredient_blacklist import UserIngredientBlacklist
from app.models.blacklist_group_subscription import BlacklistGroupSubscription

from .reachability import ExportSet, collect_full_set, collect_mine_set
from . import serializers as S

STATIC_DIR = Path(__file__).resolve().parents[3] / "static"  # backend/static

_UNSAFE_FILENAME = re.compile(r'[/\\:*?"<>|]')


def _safe_filename(name: str, fallback_id: int) -> str:
    cleaned = _UNSAFE_FILENAME.sub("_", name or "").strip()[:80]
    return cleaned or f"recipe_{fallback_id}"


def _unit_name_map(db: Session, unit_ids: set | None) -> dict:
    q = db.query(Unit)
    if unit_ids is not None:
        q = q.filter(Unit.id.in_(unit_ids)) if unit_ids else q.filter(False)
    return {u.id: u.name for u in q.all()}


def _ingredient_name_map(db: Session, ing_ids: set | None) -> dict:
    q = db.query(Ingredient)
    if ing_ids is not None:
        q = q.filter(Ingredient.id.in_(ing_ids)) if ing_ids else q.filter(False)
    return {i.id: i.name for i in q.all()}


def _collect_image_files(manifest: dict, recipes_payload: list, products_payload: list) -> list:
    """扫描已序列化的图片相对路径，返回 [(zip内路径, 物理绝对路径)]。

    外链 http(s):// 跳过并计入 manifest.notes。
    """
    files = []
    skipped = 0
    seen = set()

    def _handle(rel: str | None):
        nonlocal skipped
        if not rel:
            return
        if rel.startswith("http://") or rel.startswith("https://"):
            skipped += 1
            return
        phys = STATIC_DIR / rel
        if not phys.exists():
            skipped += 1
            return
        if rel in seen:
            return
        seen.add(rel)
        files.append((rel, phys))

    for r in recipes_payload:
        for img in r.get("images", []):
            _handle(img)
    for p in products_payload:
        _handle(p.get("image_url"))

    if skipped:
        manifest.setdefault("notes", []).append(f"{skipped} 个图片为外链或缺失，未打包")
    manifest.setdefault("image_summary", {})["skipped_remote"] = skipped
    return files


def build_export_zip(db: Session, user, scope: str) -> tuple[bytes, dict]:
    """主编排：返回 (zip_bytes, manifest)。"""
    es: ExportSet = collect_full_set(db) if scope == "full" else collect_mine_set(db, user.id)

    # ---- 查询（full 不加 id 过滤；mine 按 ExportSet 过滤）----
    def _query(model, id_set):
        q = db.query(model)
        # entity_densities / entity_unit_overrides 软删行（is_active=False）
        # 即使 full 模式也不导出，避免幽灵数据。
        if model in (EntityDensity, EntityUnitOverride):
            q = q.filter(model.is_active.is_(True))
        if not es.full_mode:
            if id_set:
                q = q.filter(model.id.in_(id_set))
            else:
                q = q.filter(False)
        return q.all()

    recipes = _query(Recipe, es.recipe_ids)
    ingredients = _query(Ingredient, es.ingredient_ids)
    nutritions = _query(NutritionData, es.nutrition_ids)
    units = _query(Unit, es.unit_ids)
    conversions = _query(UnitConversion, es.unit_conversion_ids)
    categories = _query(IngredientCategory, es.category_ids)
    hierarchies = _query(IngredientHierarchy, es.hierarchy_ids)
    densities = _query(EntityDensity, es.entity_density_ids)
    unit_overrides = _query(EntityUnitOverride, es.entity_unit_override_ids)
    products = _query(Product, es.product_ids)
    barcodes = _query(ProductBarcode, es.barcode_ids)
    links = _query(ProductIngredientLink, es.product_link_ids)
    records = _query(ProductRecord, es.price_record_ids)
    merchants = _query(Merchant, es.merchant_ids)
    places = _query(UserPlace, es.user_place_ids)

    # ---- 名字映射 ----
    unit_names = _unit_name_map(db, es.unit_ids if not es.full_mode else None)
    ing_names = _ingredient_name_map(db, es.ingredient_ids if not es.full_mode else None)
    cat_names = {c.id: c.display_name for c in categories}
    # 食材→usda_id：从 nutrition 反查
    ing_to_usda = {}
    for nd in nutritions:
        ing_to_usda[nd.ingredient_id] = nd.usda_id

    # ---- 序列化 ----
    errors: list = []

    def _safe_build(label: str, fn):
        """构建一个 payload；失败时记入 errors 并返回 []，不中断整体导出。"""
        try:
            return fn()
        except Exception as e:
            errors.append({"table": label, "error": str(e)})
            return []

    # 密度→product name 批量预取（避免 N+1）
    prod_density_ids = {
        d.entity_id for d in densities
        if d.entity_type == "product" and d.entity_id is not None
    }
    prod_density_name_map = (
        {p.id: p.name for p in db.query(Product).filter(Product.id.in_(prod_density_ids)).all()}
        if prod_density_ids else {}
    )

    units_payload = _safe_build("units", lambda: [S.serialize_unit(u) for u in units])
    ingredients_payload = _safe_build(
        "ingredients",
        lambda: [
            S.serialize_ingredient(
                ing,
                category_display_name=cat_names.get(ing.category_id),
                usda_id=ing_to_usda.get(ing.id),
            )
            for ing in ingredients
        ],
    )
    ingredients_doc = {p["name"]: p for p in ingredients_payload}

    nutritions_payload = _safe_build(
        "nutritions",
        lambda: [
            S.serialize_nutrition(nd, ingredient_name=ing_names.get(nd.ingredient_id, ""))
            for nd in nutritions
        ],
    )

    conversions_payload = _safe_build(
        "unit_conversions",
        lambda: [
            S.serialize_unit_conversion(c, unit_names.get(c.from_unit_id), unit_names.get(c.to_unit_id))
            for c in conversions
        ],
    )
    categories_payload = _safe_build(
        "ingredient_categories", lambda: [S.serialize_category(c) for c in categories]
    )
    hierarchy_payload = _safe_build(
        "ingredient_hierarchy",
        lambda: [
            S.serialize_hierarchy(h, ing_names.get(h.parent_id), ing_names.get(h.child_id))
            for h in hierarchies
        ],
    )
    densities_payload = _safe_build(
        "entity_densities",
        lambda: [
            S.serialize_entity_density(
                d,
                ing_names.get(d.entity_id) if d.entity_type == "ingredient"
                else prod_density_name_map.get(d.entity_id),
            )
            for d in densities
        ],
    )

    # 自定义单位→name 预取
    prod_id_to_name = {p.id: p.name for p in products}
    unit_override_unit_ids = set()
    for o in unit_overrides:
        if o.base_unit_id:
            unit_override_unit_ids.add(o.base_unit_id)
        if o.weight_unit_id:
            unit_override_unit_ids.add(o.weight_unit_id)
    unit_override_unit_names = _unit_name_map(db, unit_override_unit_ids or None)

    unit_overrides_payload = _safe_build(
        "entity_unit_overrides",
        lambda: [
            S.serialize_entity_unit_override(
                o,
                entity_name=ing_names.get(o.entity_id) if o.entity_type == "ingredient"
                else prod_id_to_name.get(o.entity_id),
                base_unit_name=unit_override_unit_names.get(o.base_unit_id),
                weight_unit_name=unit_override_unit_names.get(o.weight_unit_id),
            )
            for o in unit_overrides
        ],
    )

    # 商品/条码/关联
    barcode_primary = {}
    for b in barcodes:
        if b.is_primary:
            barcode_primary[b.product_id] = b.barcode
    products_payload = _safe_build(
        "products",
        lambda: [
            S.serialize_product(p, ing_names.get(p.ingredient_id), barcode_primary.get(p.id))
            for p in products
        ],
    )
    barcodes_payload = _safe_build(
        "product_barcodes",
        lambda: [S.serialize_barcode(b, prod_id_to_name.get(b.product_id)) for b in barcodes],
    )
    links_payload = _safe_build(
        "product_ingredient_links",
        lambda: [
            S.serialize_product_link(l, prod_id_to_name.get(l.product_id), ing_names.get(l.ingredient_id))
            for l in links
        ],
    )

    # 菜谱（含 RecipeIngredient）
    recipe_ri_map = {}
    if recipes:
        ri_rows = db.query(RecipeIngredient).filter(
            RecipeIngredient.recipe_id.in_([r.id for r in recipes])
        ).all()
        for ri in ri_rows:
            recipe_ri_map.setdefault(ri.recipe_id, []).append(ri)

    def _build_recipes():
        payloads = []
        file_index = []
        used_names = set()
        for r in recipes:
            payload = S.serialize_recipe(
                r, recipe_ri_map.get(r.id, []),
                ingredient_map=ing_names, unit_map=unit_names,
            )
            fname = _safe_filename(r.name, r.id)
            if fname in used_names:
                fname = f"{fname}_{r.id}"
            used_names.add(fname)
            file_index.append((f"recipes/{fname}.json", payload))
            payloads.append(payload)
        return payloads, file_index

    # recipes 需要同时返回 payload 与 file_index，单独 try
    try:
        recipes_payload, recipe_file_index = _build_recipes()
    except Exception as e:
        errors.append({"table": "recipes", "error": str(e)})
        recipes_payload, recipe_file_index = [], []

    # 商家/价格记录/收藏
    merchant_id_to_name = {m.id: m.name for m in merchants}
    records_payload = _safe_build(
        "price_records",
        lambda: [
            S.serialize_price_record(
                pr,
                pr.product_name,
                merchant_id_to_name.get(pr.merchant_id),
                unit_names.get(pr.original_unit_id),
                unit_names.get(pr.standard_unit_id),
            )
            for pr in records
        ],
    )
    merchants_payload = _safe_build(
        "merchants", lambda: [S.serialize_merchant(m) for m in merchants]
    )
    places_payload = _safe_build(
        "user_places", lambda: [S.serialize_user_place(p) for p in places]
    )

    # ---- 黑名单 ----
    # 黑名单分组（full 全量；mine 只导出用户已订阅的分组）
    if scope == "full":
        bl_groups = db.query(BlacklistGroup).all()
    else:
        subscribed_group_ids = [
            r[0] for r in db.query(BlacklistGroupSubscription.blacklist_group_id).filter(
                BlacklistGroupSubscription.user_id == user.id,
                BlacklistGroupSubscription.is_active == True,
            ).all()
        ]
        bl_groups = (
            db.query(BlacklistGroup).filter(BlacklistGroup.id.in_(subscribed_group_ids)).all()
            if subscribed_group_ids else []
        )

    def _build_blacklist_groups():
        group_ids = [g.id for g in bl_groups]
        if not group_ids:
            return []
        bgis = db.query(BlacklistGroupIngredient).filter(
            BlacklistGroupIngredient.group_id.in_(group_ids),
        ).all()
        ing_ids = {bgi.ingredient_id for bgi in bgis}
        ing_map = _ingredient_name_map(db, ing_ids) if ing_ids else {}
        group_ing_map: dict[int, list[dict]] = {}
        for bgi in bgis:
            group_ing_map.setdefault(bgi.group_id, []).append({
                "ingredient_id": bgi.ingredient_id,
                "ingredient_name": ing_map.get(bgi.ingredient_id),
                "is_ai_matched": bool(bgi.is_ai_matched),
            })
        return [
            S.serialize_blacklist_group(g, group_ing_map.get(g.id, []))
            for g in bl_groups
        ]

    bl_groups_payload = _safe_build("blacklist_groups", _build_blacklist_groups)

    # 用户个人黑名单条目
    bl_entries = db.query(UserIngredientBlacklist).filter(
        UserIngredientBlacklist.user_id == user.id,
        UserIngredientBlacklist.is_active == True,
    ).all()
    bl_entry_ing_ids = {e.ingredient_id for e in bl_entries}
    bl_entry_ing_map = _ingredient_name_map(db, bl_entry_ing_ids) if bl_entry_ing_ids else {}

    bl_entries_payload = _safe_build(
        "user_ingredient_blacklist",
        lambda: [
            S.serialize_blacklist_entry(e, bl_entry_ing_map.get(e.ingredient_id))
            for e in bl_entries
        ],
    )

    # 用户黑名单分组订阅
    bl_subs = db.query(BlacklistGroupSubscription).filter(
        BlacklistGroupSubscription.user_id == user.id,
        BlacklistGroupSubscription.is_active == True,
    ).all()
    bl_sub_group_ids = {s.blacklist_group_id for s in bl_subs}
    bl_sub_group_map = {g.id: g.name for g in db.query(BlacklistGroup).filter(
        BlacklistGroup.id.in_(bl_sub_group_ids),
    ).all()} if bl_sub_group_ids else {}

    bl_subs_payload = _safe_build(
        "blacklist_group_subscriptions",
        lambda: [
            S.serialize_blacklist_subscription(s, bl_sub_group_map.get(s.blacklist_group_id))
            for s in bl_subs
        ],
    )

    # ---- manifest ----
    manifest = {
        "format_version": "1.0",
        "app": "生计 - 生活成本计算器",
        "app_version": "0.2.0",
        "exported_at": datetime.now().astimezone().isoformat(),
        "scope": scope,
        "exported_by_user_id": getattr(user, "id", None),
        "schema": {
            "howto_cook_compatible": ["recipes", "ingredients", "nutritions", "units"],
            "extended": ["unit_conversions", "ingredient_categories", "ingredient_hierarchy",
                         "entity_densities", "entity_unit_overrides", "products",
                         "product_barcodes", "product_ingredient_links", "price_records",
                         "merchants", "user_places",
                         "blacklist_groups", "user_ingredient_blacklist",
                         "blacklist_group_subscriptions"],
        },
        "counts": {
            "recipes": len(recipes_payload),
            "ingredients": len(ingredients_payload),
            "nutritions": len(nutritions_payload),
            "units": len(units_payload),
            "unit_conversions": len(conversions_payload),
            "ingredient_categories": len(categories_payload),
            "ingredient_hierarchy": len(hierarchy_payload),
            "entity_densities": len(densities_payload),
            "entity_unit_overrides": len(unit_overrides_payload),
            "products": len(products_payload),
            "product_barcodes": len(barcodes_payload),
            "product_ingredient_links": len(links_payload),
            "price_records": len(records_payload),
            "merchants": len(merchants_payload),
            "user_places": len(places_payload),
            "blacklist_groups": len(bl_groups_payload),
            "user_ingredient_blacklist": len(bl_entries_payload),
            "blacklist_group_subscriptions": len(bl_subs_payload),
        },
        "image_summary": {},
        "errors": errors,
        "notes": [],
    }

    # ---- 图片收集（image_summary 统计统一由 _collect_image_files 负责）----
    image_files = _collect_image_files(manifest, recipes_payload, products_payload)

    # ---- 写 zip ----
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for fname, payload in recipe_file_index:
            zf.writestr(fname, json.dumps(payload, ensure_ascii=False, indent=2))
        zf.writestr("ingredients.json", json.dumps(ingredients_doc, ensure_ascii=False, indent=2))
        zf.writestr("nutritions.json", json.dumps(nutritions_payload, ensure_ascii=False, indent=2))
        zf.writestr("units.json", json.dumps(units_payload, ensure_ascii=False, indent=2))
        zf.writestr("unit_conversions.json", json.dumps(conversions_payload, ensure_ascii=False, indent=2))
        zf.writestr("ingredient_categories.json", json.dumps(categories_payload, ensure_ascii=False, indent=2))
        zf.writestr("ingredient_hierarchy.json", json.dumps(hierarchy_payload, ensure_ascii=False, indent=2))
        zf.writestr("entity_densities.json", json.dumps(densities_payload, ensure_ascii=False, indent=2))
        zf.writestr("entity_unit_overrides.json", json.dumps(unit_overrides_payload, ensure_ascii=False, indent=2))
        zf.writestr("products.json", json.dumps(products_payload, ensure_ascii=False, indent=2))
        zf.writestr("product_barcodes.json", json.dumps(barcodes_payload, ensure_ascii=False, indent=2))
        zf.writestr("product_ingredient_links.json", json.dumps(links_payload, ensure_ascii=False, indent=2))
        zf.writestr("price_records.json", json.dumps(records_payload, ensure_ascii=False, indent=2))
        zf.writestr("merchants.json", json.dumps(merchants_payload, ensure_ascii=False, indent=2))
        zf.writestr("user_places.json", json.dumps(places_payload, ensure_ascii=False, indent=2))
        zf.writestr("blacklist_groups.json", json.dumps(bl_groups_payload, ensure_ascii=False, indent=2))
        zf.writestr("user_ingredient_blacklist.json", json.dumps(bl_entries_payload, ensure_ascii=False, indent=2))
        zf.writestr("blacklist_group_subscriptions.json", json.dumps(bl_subs_payload, ensure_ascii=False, indent=2))
        for rel, phys in image_files:
            zf.write(phys, rel)

    return buf.getvalue(), manifest
