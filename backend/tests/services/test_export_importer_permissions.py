"""ExportImporter 权限分流测试。

验证普通用户导入 full/mine 包时遵守多用户权限边界：
- admin-only 数据（黑名单分组 / 单位换算 / 商品条码）跳过
- 菜谱 full 强制私有、mine 恢复原值
- 个人行为数据 full 跳过、mine 恢复
- 营养 is_verified 普通用户降级
- 管理员导入维持现状

设计：用 conftest 的内存库 db_session；autouse fixture 每测前清表隔离
（内存库 StaticPool 跨测试共享，不清理会残留）；make_collection 工厂在
tmp_path 下写 export 包结构。
"""
import json
import os

import pytest

from app.core.database import Base
from app.services.importer.importers.export import ExportImporter
from app.services.importer.models import DataFile, FileCollection, ImportResult


# ---------- 测试基建 ----------

@pytest.fixture(autouse=True)
def _clear_tables(db_session):
    """每测前清空所有表，隔离内存库共享数据。"""
    for table in reversed(Base.metadata.sorted_tables):
        db_session.execute(table.delete())
    db_session.commit()
    yield


@pytest.fixture
def make_collection(tmp_path):
    """工厂：在 tmp_path 下写 export 包文件，返回 FileCollection。

    用法：
        coll = make_collection({"blacklist_groups.json": [...]}, scope="full")
        coll = make_collection({"units.json": []}, scope=None)  # 不写 manifest
    """
    base = str(tmp_path)

    def _build(files: dict, scope="full"):
        coll = FileCollection()
        all_files = dict(files)
        if scope is not None:
            all_files["manifest.json"] = {"scope": scope, "version": "1"}
        for rel, content in all_files.items():
            full = os.path.join(base, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False)
            coll.files.append(DataFile(relative_path=rel, absolute_path=full, size=0))
        return coll

    return _build


# ---------- Task 1: 基础设施 is_admin + skipped ----------

def test_export_importer_accepts_is_admin(db_session):
    """ExportImporter 接收 is_admin 并保存。"""
    importer = ExportImporter(db_session, user_id=1, is_admin=False)
    assert importer.is_admin is False


def test_export_importer_is_admin_true(db_session):
    """管理员构造时 is_admin=True。"""
    importer = ExportImporter(db_session, user_id=1, is_admin=True)
    assert importer.is_admin is True


def test_import_result_has_skipped():
    """ImportResult 带 skipped 字典。"""
    r = ImportResult()
    assert r.skipped == {}
    r.skipped["blacklist_groups"] = 3
    assert r.skipped["blacklist_groups"] == 3


# ---------- Task 2: scope 读取 ----------

def test_import_all_reads_scope_from_manifest(db_session, make_collection):
    """import_all 从 manifest.json 读 scope。"""
    coll = make_collection({"units.json": []}, scope="mine")
    importer = ExportImporter(db_session, user_id=1, is_admin=False)
    importer.import_all(coll)
    assert importer.scope == "mine"


def test_import_all_defaults_full_when_no_manifest(db_session, make_collection):
    """无 manifest 时 scope 默认 full（最严）。"""
    coll = make_collection({"units.json": []}, scope=None)
    importer = ExportImporter(db_session, user_id=1, is_admin=False)
    importer.import_all(coll)
    assert importer.scope == "full"


# ---------- Task 3: admin-only 跳过 ----------

def test_normal_user_skips_blacklist_groups(db_session, make_collection):
    """普通用户：黑名单分组不新建，计入 skipped。"""
    coll = make_collection({"blacklist_groups.json": [
        {"id": 1, "name": "花生组", "display_order": 1, "ingredients": []},
    ]}, scope="full")
    importer = ExportImporter(db_session, user_id=1, is_admin=False)
    result = importer.import_all(coll)
    from app.models.blacklist_group import BlacklistGroup
    assert db_session.query(BlacklistGroup).count() == 0
    assert result.skipped.get("blacklist_groups", 0) == 1


def test_admin_imports_blacklist_groups(db_session, make_collection):
    """管理员：黑名单分组正常新建。"""
    coll = make_collection({"blacklist_groups.json": [
        {"id": 1, "name": "花生组", "display_order": 1, "ingredients": []},
    ]}, scope="full")
    importer = ExportImporter(db_session, user_id=1, is_admin=True)
    importer.import_all(coll)
    from app.models.blacklist_group import BlacklistGroup
    assert db_session.query(BlacklistGroup).count() == 1


def test_normal_user_skips_unit_conversions_and_barcodes(db_session, make_collection):
    """普通用户：单位换算与商品条码跳过。"""
    coll = make_collection({
        "unit_conversions.json": [{"from_unit_id": 1, "to_unit_id": 2, "conversion_factor": 1000}],
        "product_barcodes.json": [{"product_id": 1, "barcode": "6901234567890"}],
    }, scope="full")
    importer = ExportImporter(db_session, user_id=1, is_admin=False)
    result = importer.import_all(coll)
    assert result.skipped.get("unit_conversions", 0) == 1
    assert result.skipped.get("product_barcodes", 0) == 1


def _seed_ingredient(db_session, name):
    """造一个活跃原料，返回 ORM 对象。"""
    from app.models.nutrition import Ingredient
    ing = Ingredient(name=name, is_active=True)
    db_session.add(ing)
    db_session.flush()
    return ing


# ---------- Task 4: 营养 is_verified 普通用户降级 ----------

def test_normal_user_nutritions_not_verified(db_session, make_collection):
    """普通用户导入营养：is_verified 强制 False，即使包里是 True。"""
    _seed_ingredient(db_session, name="鸡蛋")
    coll = make_collection({
        "ingredients.json": [{"id": 99, "name": "鸡蛋"}],
        "nutritions.json": [{"ingredient_id": 99, "nutrients": {"energy": 100}, "is_verified": True}],
    }, scope="full")
    importer = ExportImporter(db_session, user_id=1, is_admin=False)
    importer.import_all(coll)
    from app.models.nutrition_data import NutritionData
    nd = db_session.query(NutritionData).first()
    assert nd is not None
    assert nd.is_verified is False


def test_admin_nutritions_keep_verified(db_session, make_collection):
    """管理员导入：is_verified 保留原值。"""
    _seed_ingredient(db_session, name="鸡蛋")
    coll = make_collection({
        "ingredients.json": [{"id": 99, "name": "鸡蛋"}],
        "nutritions.json": [{"ingredient_id": 99, "nutrients": {"energy": 100}, "is_verified": True}],
    }, scope="full")
    importer = ExportImporter(db_session, user_id=1, is_admin=True)
    importer.import_all(coll)
    from app.models.nutrition_data import NutritionData
    nd = db_session.query(NutritionData).first()
    assert nd is not None
    assert nd.is_verified is True


# ---------- Task 5: 菜谱 is_public 分 scope ----------

def _recipe_pkg(make_collection, scope, is_public=True):
    return make_collection({"recipes/番茄炒蛋.json": {
        "id": 1, "name": "番茄炒蛋", "is_public": is_public, "ingredients": [],
    }}, scope=scope)


def test_normal_user_full_recipe_is_private(db_session, make_collection):
    """普通用户 full 包：菜谱强制私有。"""
    coll = _recipe_pkg(make_collection, scope="full", is_public=True)
    ExportImporter(db_session, user_id=1, is_admin=False).import_all(coll)
    from app.models.recipe import Recipe
    r = db_session.query(Recipe).first()
    assert r is not None
    assert r.is_public is False


def test_normal_user_mine_recipe_keeps_public(db_session, make_collection):
    """普通用户 mine 包：菜谱恢复原 is_public。"""
    coll = _recipe_pkg(make_collection, scope="mine", is_public=True)
    ExportImporter(db_session, user_id=1, is_admin=False).import_all(coll)
    from app.models.recipe import Recipe
    r = db_session.query(Recipe).first()
    assert r is not None
    assert r.is_public is True


def test_admin_recipe_keeps_public(db_session, make_collection):
    """管理员导入：菜谱 is_public 保留原值。"""
    coll = _recipe_pkg(make_collection, scope="full", is_public=True)
    ExportImporter(db_session, user_id=1, is_admin=True).import_all(coll)
    from app.models.recipe import Recipe
    r = db_session.query(Recipe).first()
    assert r is not None
    assert r.is_public is True


# ---------- Task 6: 个人行为数据 full 包跳过 ----------

def test_normal_user_full_skips_personal_data(db_session, make_collection):
    """普通用户 full 包：地点/个人黑名单/订阅跳过（价格记录单独测）。"""
    coll = make_collection({
        "user_places.json": [{"name": "家", "kind": "home"}],
        "user_ingredient_blacklist.json": [{"ingredient_id": 99, "ingredient_name": "鸡蛋"}],
        "blacklist_group_subscriptions.json": [{"blacklist_group_id": 1}],
    }, scope="full")
    importer = ExportImporter(db_session, user_id=1, is_admin=False)
    result = importer.import_all(coll)
    from app.models.user_place import UserPlace
    from app.models.user_ingredient_blacklist import UserIngredientBlacklist
    from app.models.blacklist_group_subscription import BlacklistGroupSubscription
    assert db_session.query(UserPlace).count() == 0
    assert db_session.query(UserIngredientBlacklist).count() == 0
    assert db_session.query(BlacklistGroupSubscription).count() == 0
    assert result.skipped.get("user_places", 0) == 1
    assert result.skipped.get("user_ingredient_blacklist", 0) == 1


def test_normal_user_mine_imports_personal_data(db_session, make_collection):
    """普通用户 mine 包：个人数据恢复（改归属）。"""
    coll = make_collection({"user_places.json": [{"name": "家", "kind": "home"}]}, scope="mine")
    ExportImporter(db_session, user_id=1, is_admin=False).import_all(coll)
    from app.models.user_place import UserPlace
    assert db_session.query(UserPlace).count() == 1


def test_admin_full_imports_personal_data(db_session, make_collection):
    """管理员 full 包：个人数据正常导入。"""
    coll = make_collection({"user_places.json": [{"name": "家", "kind": "home"}]}, scope="full")
    ExportImporter(db_session, user_id=1, is_admin=True).import_all(coll)
    from app.models.user_place import UserPlace
    assert db_session.query(UserPlace).count() == 1


# ---------- Task 7: 商品字段补全 ----------

def test_product_imports_full_fields(db_session, make_collection):
    """商品补读 barcode/image_url/custom_nutrition_data/custom_nutrition_source。"""
    _seed_ingredient(db_session, name="番茄")
    coll = make_collection({
        "ingredients.json": [{"id": 99, "name": "番茄"}],
        "products.json": [{
            "id": 1, "name": "番茄A", "ingredient_id": 99,
            "barcode": "6901234567890",
            "image_url": "/static/images/tomato.jpg",
            "custom_nutrition_data": {"energy": 50},
            "custom_nutrition_source": "ai_match",
        }],
    }, scope="full")
    ExportImporter(db_session, user_id=1, is_admin=True).import_all(coll)
    from app.models.product_entity import Product
    p = db_session.query(Product).filter(Product.name == "番茄A").first()
    assert p.barcode == "6901234567890"
    assert p.image_url == "/static/images/tomato.jpg"
    assert p.custom_nutrition_data == {"energy": 50}
    assert p.custom_nutrition_source == "ai_match"


def test_normal_user_product_custom_nutrition_marked_import(db_session, make_collection):
    """普通用户导入：商品 custom_nutrition_source 标 import（与营养降级口径一致）。"""
    _seed_ingredient(db_session, name="番茄")
    coll = make_collection({
        "ingredients.json": [{"id": 99, "name": "番茄"}],
        "products.json": [{
            "id": 1, "name": "番茄B", "ingredient_id": 99,
            "custom_nutrition_data": {"energy": 50},
            "custom_nutrition_source": "ai_match",
        }],
    }, scope="full")
    ExportImporter(db_session, user_id=1, is_admin=False).import_all(coll)
    from app.models.product_entity import Product
    p = db_session.query(Product).filter(Product.name == "番茄B").first()
    assert p is not None
    assert p.custom_nutrition_source == "import"


# ---------- Task 8: entity_unit_overrides 导入 ----------

def test_imports_entity_unit_overrides(db_session, make_collection):
    """entity_unit_overrides 正常导入（按 entity_type+entity_id+unit_name 去重）。"""
    _seed_ingredient(db_session, name="土豆")
    coll = make_collection({
        "ingredients.json": [{"id": 99, "name": "土豆"}],
        "entity_unit_overrides.json": [{
            "id": 1, "entity_type": "ingredient", "entity_id": 99,
            "unit_name": "盒(12个)", "conversion_factor": 12, "is_default": True,
            "source": "manual",
        }],
    }, scope="full")
    result = ExportImporter(db_session, user_id=1, is_admin=True).import_all(coll)
    from app.models.entity_unit_override import EntityUnitOverride
    assert db_session.query(EntityUnitOverride).count() == 1
    assert result.stats.get("entity_unit_overrides", 0) == 1
    euo = db_session.query(EntityUnitOverride).first()
    assert euo.unit_name == "盒(12个)"
    assert float(euo.conversion_factor) == 12


# ---------- Task 10: 端到端综合（full 包普通用户一次导入，所有越权点）----------

def test_e2e_normal_user_full_no_overreach(db_session, make_collection):
    """端到端：普通用户导入含多种数据的 full 包，所有越权点都被堵住。"""
    _seed_ingredient(db_session, name="鸡蛋")
    coll = make_collection({
        "ingredients.json": [{"id": 99, "name": "鸡蛋"}],
        "blacklist_groups.json": [{"id": 1, "name": "花生组", "ingredients": []}],
        "unit_conversions.json": [{"from_unit_id": 1, "to_unit_id": 2, "conversion_factor": 1000}],
        "product_barcodes.json": [{"product_id": 1, "barcode": "6901234567890"}],
        "nutritions.json": [{"ingredient_id": 99, "nutrients": {"energy": 100}, "is_verified": True}],
        "recipes/番茄炒蛋.json": {"id": 1, "name": "番茄炒蛋", "is_public": True, "ingredients": []},
        "user_places.json": [{"name": "家", "kind": "home"}],
        "price_records.json": [{"product_id": 1, "price": 9.9, "product_name": "x"}],
        "user_ingredient_blacklist.json": [{"ingredient_id": 99, "ingredient_name": "鸡蛋"}],
        "blacklist_group_subscriptions.json": [{"blacklist_group_id": 1}],
    }, scope="full")
    result = ExportImporter(db_session, user_id=2, is_admin=False).import_all(coll)

    # admin-only 数据未建 + 计入 skipped
    from app.models.blacklist_group import BlacklistGroup
    from app.models.product_barcode import ProductBarcode
    assert db_session.query(BlacklistGroup).count() == 0
    assert db_session.query(ProductBarcode).count() == 0
    assert result.skipped.get("blacklist_groups") == 1
    assert result.skipped.get("unit_conversions") == 1
    assert result.skipped.get("product_barcodes") == 1

    # 营养未自证（is_verified 强制 False）
    from app.models.nutrition_data import NutritionData
    nd = db_session.query(NutritionData).first()
    assert nd is not None and nd.is_verified is False

    # 菜谱私有（未绕过发布审核）
    from app.models.recipe import Recipe
    r = db_session.query(Recipe).first()
    assert r is not None and r.is_public is False and r.user_id == 2

    # 个人行为数据未克隆 + 计入 skipped
    from app.models.user_place import UserPlace
    from app.models.product import ProductRecord
    from app.models.user_ingredient_blacklist import UserIngredientBlacklist
    from app.models.blacklist_group_subscription import BlacklistGroupSubscription
    assert db_session.query(UserPlace).count() == 0
    assert db_session.query(ProductRecord).count() == 0
    assert db_session.query(UserIngredientBlacklist).count() == 0
    assert db_session.query(BlacklistGroupSubscription).count() == 0
    assert result.skipped.get("user_places") == 1


def test_e2e_normal_user_mine_roundtrip(db_session, make_collection):
    """端到端：普通用户 mine 包——菜谱恢复原 public、个人数据恢复。"""
    coll = make_collection({
        "recipes/我的菜.json": {"id": 1, "name": "我的菜", "is_public": True, "ingredients": []},
        "user_places.json": [{"name": "公司", "kind": "work"}],
    }, scope="mine")
    ExportImporter(db_session, user_id=2, is_admin=False).import_all(coll)
    from app.models.recipe import Recipe
    from app.models.user_place import UserPlace
    r = db_session.query(Recipe).first()
    assert r is not None and r.is_public is True and r.user_id == 2
    assert db_session.query(UserPlace).filter(UserPlace.user_id == 2).count() == 1


# ---------- 价格记录：查重 + 非自己的不计支出 ----------

def test_price_record_non_own_purchase_downgraded(db_session, make_collection):
    """非自己的 purchase 导入后降为 price（不计支出），并改归属当前用户。"""
    _seed_ingredient(db_session, name="苹果")
    coll = make_collection({
        "ingredients.json": [{"id": 99, "name": "苹果"}],
        "units.json": [{"id": 1, "name": "克"}],
        "products.json": [{"id": 1, "name": "苹果A", "ingredient_id": 99}],
        "price_records.json": [{
            "user_id": 999,
            "product_id": 1, "price": 5.5, "product_name": "苹果A",
            "original_unit_id": 1, "standard_unit_id": 1, "record_type": "purchase",
        }],
    }, scope="full")
    ExportImporter(db_session, user_id=2, is_admin=False).import_all(coll)
    from app.models.product import ProductRecord
    rec = db_session.query(ProductRecord).first()
    assert rec is not None
    assert rec.user_id == 2
    assert rec.record_type == "price"


def test_price_record_own_purchase_kept(db_session, make_collection):
    """自己的 purchase 保留（计入支出）。"""
    _seed_ingredient(db_session, name="苹果")
    coll = make_collection({
        "ingredients.json": [{"id": 99, "name": "苹果"}],
        "units.json": [{"id": 1, "name": "克"}],
        "products.json": [{"id": 1, "name": "苹果B", "ingredient_id": 99}],
        "price_records.json": [{
            "user_id": 2,
            "product_id": 1, "price": 5.5, "product_name": "苹果B",
            "original_unit_id": 1, "standard_unit_id": 1, "record_type": "purchase",
        }],
    }, scope="mine")
    ExportImporter(db_session, user_id=2, is_admin=False).import_all(coll)
    from app.models.product import ProductRecord
    rec = db_session.query(ProductRecord).first()
    assert rec is not None
    assert rec.record_type == "purchase"


def test_price_record_dedup(db_session, make_collection):
    """查重：除 id/审计外业务字段全相同的记录不重复导入。"""
    _seed_ingredient(db_session, name="苹果")
    coll = make_collection({
        "ingredients.json": [{"id": 99, "name": "苹果"}],
        "units.json": [{"id": 1, "name": "克"}],
        "products.json": [{"id": 1, "name": "苹果C", "ingredient_id": 99}],
        "price_records.json": [
            {"user_id": 2, "product_id": 1, "price": 3.3, "product_name": "苹果C", "original_unit_id": 1, "standard_unit_id": 1, "record_type": "price"},
            {"user_id": 2, "product_id": 1, "price": 3.3, "product_name": "苹果C", "original_unit_id": 1, "standard_unit_id": 1, "record_type": "price"},
        ],
    }, scope="mine")
    result = ExportImporter(db_session, user_id=2, is_admin=False).import_all(coll)
    from app.models.product import ProductRecord
    assert db_session.query(ProductRecord).count() == 1
    assert result.stats.get("price_records") == 1
    assert result.skipped.get("price_records_duplicate") == 1
