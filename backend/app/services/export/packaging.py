"""打包服务：按 ExportSet 查询→序列化→收集图片→写入 zip。

对外暴露 build_export_zip(db, user, scope) -> (zip_bytes, manifest_dict)。
"""
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor

import requests
from sqlalchemy.orm import Session

from app import APP_INFO, __version__
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
from app.services.storage.factory import get_storage

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


def _download_remote_images(image_urls: list, is_admin: bool,
                            max_workers: int = 8, timeout: int = 30):
    """并发下载外链图到临时目录。

    - is_admin=True：去掉 URL query（下原图）；否则原样（瘦身图）。
    返回 (downloaded, failed, tmpdir_path)：
      downloaded: {原 url: (zip 内相对路径, 临时文件绝对路径)}
      failed: 下载失败数
      tmpdir_path: 临时目录（调用方负责清理）
    """
    tmpdir = tempfile.mkdtemp(prefix="export_img_")

    def fetch(url):
        fetch_url = url.split("?", 1)[0] if is_admin else url
        try:
            resp = requests.get(fetch_url, timeout=timeout)
            resp.raise_for_status()
        except Exception:
            return None
        # 提取 basename 时统一去掉 query
        clean_url = url.split("?", 1)[0]
        base = clean_url.rsplit("/", 1)[-1] or "image"
        base = _UNSAFE_FILENAME.sub("_", base).strip() or "image"
        return url, base, resp.content

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(fetch, image_urls))

    downloaded = {}
    used_rels = set()
    failed = 0
    for r in results:
        if r is None:
            failed += 1
            continue
        url, base, content = r

        # 去重：在扩展名前加 _2, _3 等
        name, ext = base.rsplit(".", 1) if "." in base else (base, "")
        rel = f"images/{name}.{ext}" if ext else f"images/{name}"
        n = 2
        while rel in used_rels:
            rel = f"images/{name}_{n}.{ext}" if ext else f"images/{name}_{n}"
            n += 1
        used_rels.add(rel)

        tmp_path = Path(tmpdir) / base
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(content)
        downloaded[url] = (rel, str(tmp_path))

    return downloaded, failed, tmpdir


def _collect_image_files(manifest: dict, recipes_payload: list, products_payload: list,
                         user=None) -> tuple:
    """扫描图片，返回 (files, tmpdir_to_clean)。

    三类图：
    - http(s) 外链：下载（admin 去 query 下原图）；成功改写 JSON 为 images/<basename>、失败保留外链。
    - 本地图（STATIC_DIR 存在）：直接打包。
    - storage key 图（recipes/xxx 等，本地缺失但图在 S3）：storage.get(key) 读 S3 打包到原 key，JSON 不改写。

    管理员（user.is_admin）仅影响 http 外链下载（去 query）；storage.get 直读 S3 原图，无 query 问题。
    """
    files = []
    seen = set()
    skipped_local_missing = 0
    s3_downloaded = 0
    s3_missing = 0

    # 预加载 storage：本地图缺失时从 S3 读（图物理在 S3、DB 存 storage key）
    try:
        storage = get_storage()
    except Exception:
        storage = None

    # 1) 收集去重的外链 URL
    remote_urls: list = []
    seen_urls: set = set()

    def _is_remote(rel):
        return rel and (rel.startswith("http://") or rel.startswith("https://"))

    for r in recipes_payload:
        for img in r.get("images", []):
            if _is_remote(img) and img not in seen_urls:
                seen_urls.add(img)
                remote_urls.append(img)
    for p in products_payload:
        url = p.get("image_url")
        if _is_remote(url) and url not in seen_urls:
            seen_urls.add(url)
            remote_urls.append(url)

    # 2) 下载外链
    is_admin = bool(getattr(user, "is_admin", False))
    downloaded, dl_failed, tmpdir = _download_remote_images(remote_urls, is_admin)

    # 3) 遍历 payload：改写外链 + 收集打包（本地图 / storage key）
    def _handle(rel, payload_obj, key, idx=None):
        nonlocal skipped_local_missing, s3_downloaded, s3_missing
        if not rel:
            return
        if _is_remote(rel):
            if rel not in downloaded:
                return  # 失败：保留外链，不打包
            pack_rel, phys = downloaded[rel]
            if idx is not None:
                payload_obj[key][idx] = pack_rel
            else:
                payload_obj[key] = pack_rel
        else:
            phys = STATIC_DIR / rel
            if phys.exists():
                pack_rel = rel
            elif storage is not None:
                # storage key 图：图在 S3、DB 存 key。直读 S3 bytes（不经 CDN，无 UA/query 问题）。
                # 统一打包到 images/<key>（与本地图片模式一致，避免与 recipes/*.json 混杂），JSON 改写。
                try:
                    data = storage.get(rel)
                except Exception:
                    s3_missing += 1
                    return
                tmp_name = _UNSAFE_FILENAME.sub("_", rel.replace("/", "_"))
                tmp_path = Path(tmpdir) / tmp_name
                tmp_path.write_bytes(data)
                phys = tmp_path
                pack_rel = "images/" + rel
                if idx is not None:
                    payload_obj[key][idx] = pack_rel
                else:
                    payload_obj[key] = pack_rel
                s3_downloaded += 1
            else:
                skipped_local_missing += 1
                return
        if pack_rel in seen:
            return
        seen.add(pack_rel)
        files.append((pack_rel, str(phys)))

    for r in recipes_payload:
        for i, img in enumerate(r.get("images", [])):
            _handle(img, r, "images", i)
    for p in products_payload:
        _handle(p.get("image_url"), p, "image_url")

    # 4) manifest 统计
    summary = manifest.setdefault("image_summary", {})
    summary["downloaded"] = len(downloaded)
    summary["failed"] = dl_failed
    summary["s3_downloaded"] = s3_downloaded
    summary["s3_missing"] = s3_missing
    summary["skipped_local_missing"] = skipped_local_missing
    summary["skipped_remote"] = dl_failed  # 向后兼容旧字段
    if downloaded or dl_failed or s3_downloaded or s3_missing:
        manifest.setdefault("notes", []).append(
            f"{len(downloaded)} 个外链图下载打包、{dl_failed} 个外链失败，"
            f"{s3_downloaded} 个 S3 图读取打包、{s3_missing} 个 S3 缺失"
        )

    return files, tmpdir


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
        "app": APP_INFO["name"],
        "app_version": __version__,
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

    # ---- 图片收集（外链图下载打包；image_summary 由 _collect_image_files 统一维护）----
    image_files, img_tmpdir = _collect_image_files(manifest, recipes_payload, products_payload, user)

    # ---- 写 zip ----
    buf = io.BytesIO()
    try:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # ↓↓↓ 以下所有 zf.writestr(...) 与现有完全一致（逐行对照，勿漏勿改序）↓↓↓
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
    finally:
        if img_tmpdir:
            shutil.rmtree(img_tmpdir, ignore_errors=True)
