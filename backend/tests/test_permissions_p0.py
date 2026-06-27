"""P0 权限矩阵测试：共享数据写操作仅管理员，GET 至少需登录。

Task 2.5b 后：部分写端点升级为分流模式（管理员 apply_as_admin 直写 /
普通用户 submit 提议）。分流端点要求 ExecutorRegistry 已注册业务执行器
（main.py lifespan 中 register_all；TestClient 不触发 lifespan，故此模块
通过 autouse fixture 显式注册）。
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.proposals.registry import ExecutorRegistry
from app.services.proposals.bootstrap import register_all

client = TestClient(app)


@pytest.fixture(autouse=True)
def _register_executors():
    """注册业务执行器（TestClient 不触发 main.py lifespan，故显式注册一次）。

    已注册的执行器重复 register 不会覆盖已设策略（registry.register 用 setdefault），
    故多次调用安全。
    """
    if not ExecutorRegistry.get("ingredient"):
        register_all()
    yield


# ---------- units.py ----------
# Task 2.5b: 单位 create 改为分流（管理员 apply_as_admin / 普通用户 submit）。
# 治理总表 unit.create 默认 auto_approve → 普通用户提交即生效（200，非 403）。
@pytest.mark.usefixtures("as_non_admin")
def test_units_create_dispatch_non_admin_submits():
    r = client.post("/api/v1/units/", json={"name": "测试单位", "abbreviation": "tst", "unit_type": "count"})
    # 普通用户走 submit（auto_approve → applied → 200）；unit 执行器不要求 Ingredient 存在
    assert r.status_code in (200, 201)


@pytest.mark.usefixtures("as_admin")
def test_units_create_ok_for_admin():
    r = client.post("/api/v1/units/", json={"name": "测试单位A", "abbreviation": "tsta", "unit_type": "count"})
    assert r.status_code in (200, 201)


def test_units_list_requires_auth():
    # 无 override = 无 Authorization header → 401/403
    r = client.get("/api/v1/units/")
    assert r.status_code in (401, 403)


# ---------- nutrition.py ----------
# Task 2.5b: 营养 ingredient 写入改为分流（补空 auto / 覆盖 manual）。
@pytest.mark.usefixtures("as_non_admin")
def test_nutrition_ingredient_write_dispatch_non_admin_submits():
    # ingredient_id=999 不存在的场景由执行器 validate 抛 404（校验发生在 submit 之前）
    r = client.post("/api/v1/nutrition/ingredients/999/nutrition",
                    json={"nutrients": [], "base_quantity": 100, "base_unit": "g", "source": "custom"})
    # 非管理员现在走 submit 路径：执行器 validate 发现食材不存在 → 404（而非旧的 403）
    assert r.status_code in (404, 200, 201)


@pytest.mark.usefixtures("as_non_admin")
def test_nutrition_correct_forbidden_for_non_admin():
    # correct 仍保留管理员直写（不进分流）
    r = client.post("/api/v1/nutrition/correct", json={"ingredient_id": 1})
    assert r.status_code == 403


# ---------- usda.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_usda_match_ingredient_forbidden_for_non_admin():
    r = client.post("/api/v1/usda/match/ingredient/1", json={"fdc_id": 1})
    assert r.status_code == 403


# ---------- ingredient_hierarchy.py ----------
# Task 2.5b: 层级 create/update/delete 改为分流。
# hierarchy 治理总表全 manual → 普通用户提交即待审（200），不再 403。
@pytest.mark.usefixtures("as_non_admin")
def test_hierarchy_create_dispatch_non_admin_submits():
    # parent_id/child_id=1/2 不存在 → 404 校验先跑（校验发生在 submit 之前）
    r = client.post("/api/v1/ingredients/hierarchy",
                    json={"parent_id": 1, "child_id": 2, "relation_type": "contains"})
    assert r.status_code in (404, 200, 201)


@pytest.mark.usefixtures("as_non_admin")
def test_merge_history_forbidden_for_non_admin():
    # GET 合并历史仍限管理员（不进分流）
    r = client.get("/api/v1/ingredients/merge-history")
    assert r.status_code == 403


@pytest.mark.usefixtures("as_non_admin")
def test_hierarchy_update_dispatch_non_admin_submits():
    r = client.put("/api/v1/ingredients/hierarchy/1", json={"strength": 50})
    # relation 不存在 → 404（校验发生在 submit 之前）；若存在则提交待审 200
    assert r.status_code in (404, 200)


@pytest.mark.usefixtures("as_non_admin")
def test_hierarchy_delete_dispatch_non_admin_submits():
    r = client.delete("/api/v1/ingredients/hierarchy/1")
    assert r.status_code in (404, 200)


# ---------- ingredient_extended.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_ingredient_hard_delete_forbidden_for_non_admin():
    r = client.delete("/api/v1/ingredients/1/hard")
    assert r.status_code == 403


# ---------- products_entity.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_product_barcode_add_forbidden_for_non_admin():
    r = client.post("/api/v1/products/entity/1/barcodes", json={"barcode": "0001"})
    assert r.status_code == 403


def test_product_entity_list_requires_auth():
    r = client.get("/api/v1/products/entity")
    assert r.status_code in (401, 403)


# ---------- export.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_export_full_forbidden_for_non_admin():
    r = client.get("/api/v1/export/data", params={"scope": "full"})
    assert r.status_code == 403


# ---------- recipes.py images ----------
def test_recipe_images_requires_auth():
    r = client.get("/api/v1/recipes/999999/images")
    assert r.status_code in (401, 403)


@pytest.mark.usefixtures("as_non_admin")
def test_recipe_images_forbidden_for_non_author_private():
    """登录用户看他人私有菜谱图 → 403（真正的登录用户间越权场景）。"""
    from conftest import TestingSessionLocal
    from app.models.recipe import Recipe
    db = TestingSessionLocal()
    try:
        recipe = Recipe(name="他人私有菜谱", user_id=999, source=None)
        db.add(recipe)
        db.commit()
        db.refresh(recipe)
        rid = recipe.id
    finally:
        db.close()
    r = client.get(f"/api/v1/recipes/{rid}/images")
    assert r.status_code == 403


# ---------- import_api.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_import_repo_forbidden_for_non_admin():
    r = client.post("/api/v1/import/data/import-from-repo", json={})
    assert r.status_code == 403


# ---------- usda_admin.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_usda_admin_statistics_forbidden_for_non_admin():
    r = client.get("/api/v1/admin/usda/statistics")
    assert r.status_code == 403
