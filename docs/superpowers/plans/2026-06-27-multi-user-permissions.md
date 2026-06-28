# 多用户权限系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把单用户（管理员）心智的系统改造为完整的多用户权限体系——堵住现存越权漏洞，建立通用「提议—审核」框架治理共享数据，并完成商家/价格/菜谱的社区共建转型，同时保证管理员（单用户场景）操作零负担。

**Architecture:** 六桶数据分类（个人私密/价格公开聚合/客观存在共享池/共享知识库/公开内容/管理员专属）+ 通用 `change_proposals` 表配类型执行器（`apply` 是唯一执行核心）+ 审核策略三档（`auto_approve`/`auto_review`/`manual`，预留 `ProposalAutoReviewer` 接口）+ 管理员超级权限（所有写操作直写、绕过框架、菜谱创建即发布）。分四个阶段：P0 堵漏 → P1 框架 → P2 共享转型 → P3 增强。

**Tech Stack:** FastAPI + SQLAlchemy 2.x + Alembic + SQLite(开发)/MySQL/PostgreSQL + pytest + TestClient。鉴权依赖：`get_current_user`（[security.py:148](backend/app/core/security.py#L148)）/ `get_current_admin_user`（[security.py:153-166](backend/app/core/security.py#L153-L166)）。`AuditMixin`（[base_model.py:5-17](backend/app/core/base_model.py#L5-L17)）提供 `created_by`/`is_active` 等。

**设计文档：** [docs/superpowers/specs/2026-06-27-multi-user-permissions-design.md](../specs/2026-06-27-multi-user-permissions-design.md)

---

## 全局约定

- **管理员超级权限原则**：所有共享数据写端点采用「分流」模式——`if current_user.is_admin: 直接执行器.apply() else: 生成 change_proposal`。P0 阶段框架未就绪，统一先收紧为 `Depends(get_current_admin_user)`（即分流模式的 admin 分支），P1 框架就绪后再接上普通用户提议分支，**不返工**。
- **测试用户**：`conftest.FakeUser` 默认 `is_admin=True`。测非管理员场景需 override `get_current_user` 为 `is_admin=False` 的用户（见 Task 0.0）。
- **提交规范**：Conventional Commits，每 task 末尾提交。提交信息结尾加 `Co-Authored-By: Claude <noreply@anthropic.com>`。
- **不要在对话中启动服务**（项目已有自动重载的前后端服务）。验证用 pytest + py_compile。
- **表结构变更**：每个新表/加列都要 alembic 迁移（`down_revision = '20260626_0003'` 起）+ 四引擎 SQL 脚本（`sqlite/mysql/postgresql`，涉及地理列才加 `postgres_gis`）。

---

## File Structure

### P0（堵漏，纯改鉴权，无新表）

修改：
- `backend/app/api/units.py` — 写端点加管理员鉴权，GET 加登录鉴权
- `backend/app/api/nutrition.py` — 营养写入/价格读取收紧
- `backend/app/api/usda.py` — 匹配写入收紧
- `backend/app/api/ingredient_hierarchy.py` — 层级写/合并历史收紧
- `backend/app/api/ingredient_extended.py` — 硬删除收紧
- `backend/app/api/products_entity.py` — 条码/别名/营养写入收紧，无鉴权 GET 加登录
- `backend/app/api/export.py` — `scope=full` 限管理员
- `backend/app/api/recipes.py` — `GET /{id}/images` 加可见性校验
- `backend/app/api/import_api.py` / `usda_admin.py` — 手动 `is_admin` 统一为依赖
- `backend/app/core/security.py` — 新增非管理员测试依赖（仅测试用，或放 conftest）

新增：
- `backend/tests/test_permissions_p0.py` — P0 权限矩阵测试
- `backend/tests/conftest.py` — 补 `non_admin_user` / `admin_user` override fixture

### P1（通用提议—审核框架）

新增：
- `backend/app/models/change_proposal.py` — `ChangeProposal` 模型
- `backend/app/services/proposals/__init__.py`
- `backend/app/services/proposals/base.py` — `ProposalExecutor` 基类 + `ProposalAutoReviewer` 协议 + `AutoReviewResult`
- `backend/app/services/proposals/auto_reviewer.py` — 默认实现（全部 escalate）
- `backend/app/services/proposals/registry.py` — 执行器注册表 + 策略配置
- `backend/app/services/proposals/service.py` — 提议提交/审核/回滚业务逻辑
- `backend/app/api/proposals.py` — 提议/审核 API
- `backend/app/schemas/proposal.py` — Pydantic schema
- `backend/alembic/versions/20260627_0001_add_change_proposals.py`
- `backend/scripts/sql/20260627_change_proposals_{sqlite,mysql,postgresql}.sql`
- `backend/tests/test_proposals.py`

修改：
- `backend/app/main.py` — 注册 `proposals.router`（prefix `/api/v1/proposals`）
- `backend/alembic/env.py` — 导入 `app.models.change_proposal`

### P2（共享数据转型）

新增：
- `backend/app/models/user_merchant_favorite.py` — 商家收藏
- `backend/app/services/proposals/executors/{ingredient,nutrition,unit,merchant,hierarchy,merge,recipe_publish}.py`
- `backend/app/models/price_summary.py` — `ProductMerchantPriceSummary` 物化汇总
- `backend/alembic/versions/20260627_0002_merchant_favorites_recipe_is_public_unit_standard.py`
- `backend/scripts/sql/20260627_..._{sqlite,mysql,postgresql}.sql`
- `backend/tests/test_shared_data.py`

修改：
- `backend/app/models/merchant.py` — `user_id` 改 nullable（语义=录入者）
- `backend/app/models/recipe.py` — 加 `is_public`
- `backend/app/models/unit.py` — 加 `is_standard` / `unit_system`
- `backend/app/api/merchants.py` — 共享池查询 + 收藏端点
- `backend/app/api/recipes.py` — `is_public` + 发布走提议
- `backend/app/api/products_entity.py` / `nutrition.py` — `latest-price` 改读汇总表（去标识）

### P3（增强）

新增：
- `backend/app/services/proposals/executors/merchant_merge.py` — 商家合并
- 反垃圾：`ChangeProposal` 批量回退端点
- `auto_review` 具体判定（本期仅留接口，不实现）

---

## 阶段 0：堵漏（安全修复）

> 目标：消除现存「任意用户可改共享/他人数据」「无鉴权」「越权读」漏洞。统一手法：共享数据写操作收紧到 `get_current_admin_user`（= 管理员直写，P1 分流模式的 admin 分支）；越权读限管理员或加用户隔离。

### Task 0.0: 测试基础设施——管理员/非管理员 override fixture

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: 在 conftest.py 末尾追加非管理员 FakeUser 与 override fixture**

在 `backend/tests/conftest.py` 末尾追加（保留现有 `FakeUser`、`usda_app_overrides` 不动）：

```python
class NonAdminFakeUser:
    """非管理员测试用户（id=2）。"""
    id = 2
    username = "normal"
    email = "n@b.c"
    phone = None
    is_admin = False
    is_active = True
    email_verified = True
    token_version = 0
    created_at = None


def _fake_non_admin_user():
    return NonAdminFakeUser()


@pytest.fixture()
def as_admin():
    """以管理员身份请求（override get_current_user 为 FakeUser）。"""
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = fake_current_user
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture()
def as_non_admin():
    """以普通用户身份请求（override get_current_user 为 NonAdminFakeUser）。"""
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _fake_non_admin_user
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
```

- [ ] **Step 2: 验证 fixture 可用**

Run: `cd backend && python -c "from conftest import NonAdminFakeUser; print(NonAdminFakeUser().is_admin)"`
Expected: 输出 `False`

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: 补充管理员/非管理员鉴权 override fixture

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 0.1: 收紧 units.py——标准单位/换算/覆盖/密度写操作限管理员，GET 限登录

**Files:**
- Modify: `backend/app/api/units.py`
- Test: `backend/tests/test_permissions_p0.py`

> `units.py` 当前整模块无鉴权。设计要求：标准单位（公制/市制/英制）及换算**仅管理员**；模糊量/自定义单位、实体单位覆盖、密度写操作 P0 先统一收紧为管理员（P2 再分标准/模糊 + 接提议框架）。GET 端点补登录鉴权。

- [ ] **Step 1: 写失败测试——非管理员写单位 403，管理员 200**

创建 `backend/tests/test_permissions_p0.py`：

```python
"""P0 权限矩阵测试：共享数据写操作仅管理员，GET 至少需登录。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------- units.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_units_create_forbidden_for_non_admin():
    r = client.post("/api/v1/units/", json={"name": "测试单位", "abbreviation": "tst", "unit_type": "count"})
    assert r.status_code == 403


@pytest.mark.usefixtures("as_admin")
def test_units_create_ok_for_admin():
    r = client.post("/api/v1/units/", json={"name": "测试单位A", "abbreviation": "tsta", "unit_type": "count"})
    assert r.status_code in (200, 201)


def test_units_list_requires_auth():
    # 无 override = 无 Authorization header → 401/403
    r = client.get("/api/v1/units/")
    assert r.status_code in (401, 403)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -v`
Expected: `test_units_create_forbidden_for_non_admin` FAIL（当前返回 200/400 而非 403）；`test_units_list_requires_auth` FAIL（当前 200）。

- [ ] **Step 3: 给 units.py 所有写端点加 `get_current_admin_user`，GET 端点加 `get_current_user`**

修改 `backend/app/api/units.py`。对每个写端点的函数签名加依赖参数（在 `db: Session = Depends(get_db)` 后追加 `current_user: User = Depends(get_current_admin_user)`），GET 端点加 `current_user: User = Depends(get_current_user)`。

先确保文件顶部已导入（[units.py](backend/app/api/units.py) 顶部）：

```python
from app.core.security import get_current_user, get_current_admin_user
from app.models.user import User
```

写端点（逐个改签名，函数体不动）：
- `create_unit`（POST `/`）→ 加 `current_user: User = Depends(get_current_admin_user)`
- `update_unit`（PUT `/{unit_id}`）→ 同上
- `delete_unit`（DELETE `/{unit_id}`）→ 同上
- `create_conversion`（POST `/conversions/`）→ 同上
- `delete_conversion`（DELETE `/conversions/{conversion_id}`）→ 同上
- `import_batch`（POST `/import-batch`）→ 同上
- 实体单位覆盖：`create_entity_unit_override`/`update_*`/`delete_*`（`entities_unit_router` 下）→ 同上
- 实体密度：`create_entity_density`/`update_*`/`delete_*`（`entities_density_router` 下）→ 同上

GET 端点（逐个加 `current_user: User = Depends(get_current_user)`，函数体不动）：
- `list_units`、`get_unit`、`list_unit_conversions`、`list_entity_unit_overrides`、`get_unmapped_units`、`list_entity_densities`、`match_unit`、`convert_unit`

> 实操提示：用 IDE/Grep 定位每个 `@router.post`/`@router.put`/`@router.delete` 装饰器下的 `def xxx(..., db: Session = Depends(get_db)):`，在 `db` 参数后插入管理员依赖参数。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -v`
Expected: 3 个测试 PASS。

- [ ] **Step 5: py_compile 校验**

Run: `cd backend && python -m py_compile app/api/units.py && echo OK`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/units.py backend/tests/test_permissions_p0.py
git commit -m "fix(perms): units 写操作限管理员、GET 限登录

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 0.2: 收紧 nutrition.py——营养写入限管理员，价格读取过渡期加用户隔离

**Files:**
- Modify: `backend/app/api/nutrition.py`

> 营养数据写入端点当前仅 `get_current_user`（任意用户可改任意食材/商品营养）。P0 收紧为管理员。`latest-price(-by-merchant)` 当前跨用户读价格，P0 过渡期加 `ProductRecord.user_id == current_user.id` 过滤（P2 改读公开聚合）。

- [ ] **Step 1: 写失败测试**

追加到 `backend/tests/test_permissions_p0.py`：

```python
# ---------- nutrition.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_nutrition_ingredient_write_forbidden_for_non_admin():
    r = client.post("/api/v1/nutrition/ingredients/1/nutrition", json={"nutrients": {}})
    assert r.status_code == 403


@pytest.mark.usefixtures("as_non_admin")
def test_nutrition_correct_forbidden_for_non_admin():
    r = client.post("/api/v1/nutrition/correct", json={"ingredient_id": 1})
    assert r.status_code == 403
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -k nutrition -v`
Expected: FAIL（当前非 403）。

- [ ] **Step 3: 营养写入端点改 `get_current_admin_user`**

修改 `backend/app/api/nutrition.py`。确保顶部已导入 `get_current_admin_user`、`User`。把以下端点的 `current_user` 依赖从 `get_current_user` 改为 `get_current_admin_user`：
- `POST /ingredients/{ingredient_id}/nutrition`（编辑原料营养）
- `POST /products/{product_id}/nutrition`（编辑商品营养）
- `POST /correct`（更正营养映射）

- [ ] **Step 4: latest-price 过渡期加用户隔离**

定位 `GET /ingredients/{ingredient_id}/latest-price` 与 `latest-price-by-merchant`。在其查询 `ProductRecord` 处追加 `.filter(ProductRecord.user_id == current_user.id)`（保持依赖为 `get_current_user`）。

> 注：若端点签名当前无 `current_user` 参数，补 `current_user: User = Depends(get_current_user)`。

- [ ] **Step 5: 跑测试 + py_compile**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -k nutrition -v && python -m py_compile app/api/nutrition.py && echo OK`
Expected: PASS + `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/nutrition.py backend/tests/test_permissions_p0.py
git commit -m "fix(perms): 营养写入限管理员、价格读取过渡期加用户隔离

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 0.3: 收紧 usda.py——USDA 匹配写入限管理员

**Files:**
- Modify: `backend/app/api/usda.py`

> `POST /match/ingredient/{id}` 与 `/match/product/{id}` 当前任意用户可改任意食材/商品营养。收紧为管理员。

- [ ] **Step 1: 写失败测试**

追加到 `backend/tests/test_permissions_p0.py`：

```python
# ---------- usda.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_usda_match_ingredient_forbidden_for_non_admin():
    r = client.post("/api/v1/usda/match/ingredient/1", json={"fdc_id": 1})
    assert r.status_code == 403
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -k usda_match -v`
Expected: FAIL。

- [ ] **Step 3: 两个 match 端点改 `get_current_admin_user`**

修改 `backend/app/api/usda.py`，把 `match_ingredient` 与 `match_product` 的 `current_user` 依赖改为 `get_current_admin_user`。

- [ ] **Step 4: 跑测试 + py_compile**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -k usda_match -v && python -m py_compile app/api/usda.py && echo OK`
Expected: PASS + `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/usda.py backend/tests/test_permissions_p0.py
git commit -m "fix(perms): USDA 匹配写入限管理员

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 0.4: 收紧 ingredient_hierarchy.py 与 ingredient_extended.py

**Files:**
- Modify: `backend/app/api/ingredient_hierarchy.py`
- Modify: `backend/app/api/ingredient_extended.py`

> 层级关系增删改任意用户可改共享结构；`merge-history` 全员可见；硬删除任意用户可永久删共享食材。层级涉及成本计算（P0 全收紧管理员；P2 接框架后仍 manual）。`merge_ingredients` 已有所有权校验，P0 保持现状（P1 接框架）。

- [ ] **Step 1: 写失败测试**

追加到 `backend/tests/test_permissions_p0.py`：

```python
# ---------- ingredient_hierarchy.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_hierarchy_create_forbidden_for_non_admin():
    r = client.post("/api/v1/ingredients/hierarchy",
                    json={"parent_id": 1, "child_id": 2, "relation_type": "contains"})
    assert r.status_code == 403


@pytest.mark.usefixtures("as_non_admin")
def test_merge_history_forbidden_for_non_admin():
    r = client.get("/api/v1/ingredients/merge-history")
    assert r.status_code == 403


# ---------- ingredient_extended.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_ingredient_hard_delete_forbidden_for_non_admin():
    r = client.delete("/api/v1/ingredients/1/hard")
    assert r.status_code == 403
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -k "hierarchy or merge_history or hard_delete" -v`
Expected: FAIL。

- [ ] **Step 3: 改 ingredient_hierarchy.py**

修改 `backend/app/api/ingredient_hierarchy.py`（[已读全文](backend/app/api/ingredient_hierarchy.py)）。导入处补 `get_current_admin_user`：

```python
from app.core.security import get_current_user, get_current_admin_user
```

把以下端点的依赖改为 `get_current_admin_user`：
- `create_hierarchy_relation`（POST `/ingredients/hierarchy`，[L82](backend/app/api/ingredient_hierarchy.py#L82)）
- `update_hierarchy_relation`（PUT `/ingredients/hierarchy/{relation_id}`，[L271](backend/app/api/ingredient_hierarchy.py#L271)）
- `delete_hierarchy_relation`（DELETE `/ingredients/hierarchy/{relation_id}`，[L309](backend/app/api/ingredient_hierarchy.py#L309)）
- `get_merge_history`（GET `/ingredients/merge-history`，[L371](backend/app/api/ingredient_hierarchy.py#L371)）

保持不变：
- `get_ingredient_hierarchy`（GET，只读，保留 `get_current_user`）
- `merge_ingredients`（已有所有权校验，P1 接框架）
- `get_ingredient_merge_status`（GET，只读）

- [ ] **Step 4: 改 ingredient_extended.py 硬删除**

修改 `backend/app/api/ingredient_extended.py`：定位 `DELETE /{ingredient_id}/hard` 端点，把其 `current_user` 依赖改为 `get_current_admin_user`（确保顶部已导入）。

- [ ] **Step 5: 跑测试 + py_compile**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -k "hierarchy or merge_history or hard_delete" -v && python -m py_compile app/api/ingredient_hierarchy.py app/api/ingredient_extended.py && echo OK`
Expected: PASS + `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/ingredient_hierarchy.py backend/app/api/ingredient_extended.py backend/tests/test_permissions_p0.py
git commit -m "fix(perms): 层级关系写/合并历史/硬删除限管理员

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 0.5: 收紧 products_entity.py——条码/别名/营养写入限管理员，无鉴权 GET 加登录

**Files:**
- Modify: `backend/app/api/products_entity.py`

> 条码 CRUD、`add-import-alias`、`PUT /{id}/nutrition` 任意用户可改任意商品；多个 GET 无鉴权。P0：写收紧管理员，GET 加登录。

- [ ] **Step 1: 写失败测试**

追加到 `backend/tests/test_permissions_p0.py`：

```python
# ---------- products_entity.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_product_barcode_add_forbidden_for_non_admin():
    r = client.post("/api/v1/products/entity/1/barcodes", json={"barcode": "0001"})
    assert r.status_code == 403


def test_product_entity_list_requires_auth():
    r = client.get("/api/v1/products/entity")
    assert r.status_code in (401, 403)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -k "product_barcode or product_entity_list" -v`
Expected: FAIL。

- [ ] **Step 3: 写端点改 `get_current_admin_user`，无鉴权 GET 加 `get_current_user`**

修改 `backend/app/api/products_entity.py`，确保顶部导入 `get_current_user, get_current_admin_user, User`。

写端点改依赖为 `get_current_admin_user`：
- `POST /{product_id}/barcodes`、`PUT /barcodes/{barcode_id}`、`DELETE /barcodes/{barcode_id}`
- `POST /{product_id}/add-import-alias`
- `PUT /{product_id}/nutrition`

无鉴权 GET 端点补 `current_user: User = Depends(get_current_user)`：
- `GET /products/entity`（列表）
- `GET /products/entity/{product_id}`（详情）
- `GET /{product_id}/barcodes`
- `GET /{product_id}/latest-price`、`latest-price-by-merchant`
- `GET /products/autocomplete`
- `GET /{product_id}/nutrition`

> 已有 `get_current_user`/所有权校验的写端点（如 `PUT/DELETE /{id}`、`split-to-ingredient`、`merge-into`）保持不变。

- [ ] **Step 4: 跑测试 + py_compile**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -k "product_barcode or product_entity_list" -v && python -m py_compile app/api/products_entity.py && echo OK`
Expected: PASS + `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/products_entity.py backend/tests/test_permissions_p0.py
git commit -m "fix(perms): 商品条码/别名/营养写入限管理员、GET 限登录

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 0.6: 修复 export.py 与 recipes.py 越权读取

**Files:**
- Modify: `backend/app/api/export.py`
- Modify: `backend/app/api/recipes.py`

> `export.py scope=full` 待复核——若未限管理员则普通用户可导全库。`recipes.py GET /{id}/images` 无可见性校验。

- [ ] **Step 1: 写失败测试**

追加到 `backend/tests/test_permissions_p0.py`：

```python
# ---------- export.py ----------
@pytest.mark.usefixtures("as_non_admin")
def test_export_full_forbidden_for_non_admin():
    r = client.get("/api/v1/export/data", params={"scope": "full"})
    assert r.status_code == 403


# ---------- recipes.py images ----------
def test_recipe_images_requires_auth():
    r = client.get("/api/v1/recipes/999999/images")
    assert r.status_code in (401, 403)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -k "export_full or recipe_images" -v`
Expected: FAIL（若 export 已限管理员则该条会 PASS，记录为「已合规」并在提交信息注明）。

- [ ] **Step 3: export.py——scope=full 限管理员**

修改 `backend/app/api/export.py` 的 `GET /data` 端点。在 scope 解析处加拦截：

```python
if scope == "full" and not current_user.is_admin:
    raise HTTPException(status_code=403, detail="仅管理员可导出全量数据")
```

确保该端点签名已有 `current_user: User = Depends(get_current_user)`（若无则补，并导入）。

- [ ] **Step 4: recipes.py——GET /{id}/images 加可见性校验**

修改 `backend/app/api/recipes.py` 的 `GET /{recipe_id}/images`。在取出 recipe 后加：

```python
is_visible = (
    recipe.user_id == current_user.id
    or recipe.source is not None
    or getattr(recipe, "is_public", False)
    or current_user.is_admin
)
if not is_visible:
    raise HTTPException(status_code=403, detail="无权查看此菜谱图片")
```

确保端点签名有 `current_user: User = Depends(get_current_user)`（`is_public` 字段 P2 才加，此处 `getattr(..., False)` 兼容当前无该字段）。

- [ ] **Step 5: 跑测试 + py_compile**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -k "export_full or recipe_images" -v && python -m py_compile app/api/export.py app/api/recipes.py && echo OK`
Expected: PASS + `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/export.py backend/app/api/recipes.py backend/tests/test_permissions_p0.py
git commit -m "fix(perms): 全量导出限管理员、菜谱图片加可见性校验

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 0.7: 统一手动 is_admin 检查为依赖注入

**Files:**
- Modify: `backend/app/api/import_api.py`
- Modify: `backend/app/api/usda_admin.py`

> `import_api.py`（`import-from-repo`/`import-from-local`/`local-path-config`）与 `usda_admin.py`（全部端点）用手动 `if not current_user.is_admin: raise 403`。统一为 `Depends(get_current_admin_user)`。`agent_api.py` 的 `_require_admin`/`_get_session_or_404` 模式保留（已有「管理员全部/用户自己」语义，不强行替换）。

- [ ] **Step 1: 写失败测试**

追加到 `backend/tests/test_permissions_p0.py`：

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -k "import_repo or usda_admin_statistics" -v`
Expected: FAIL。

- [ ] **Step 3: import_api.py——手动检查换依赖**

修改 `backend/app/api/import_api.py`。对 `import-from-repo`、`import-from-local`、`local-path-config` 三个端点：删除函数体内 `if not current_user.is_admin: raise HTTPException(403, ...)` 片段，把签名里的 `current_user: User = Depends(get_current_user)` 改为 `current_user: User = Depends(get_current_admin_user)`。确保顶部已导入 `get_current_admin_user`。

- [ ] **Step 4: usda_admin.py——手动检查换依赖**

修改 `backend/app/api/usda_admin.py`。把所有端点里的 `_require_admin(current_user)` 调用删除，签名改为 `Depends(get_current_admin_user)`。若 `_require_admin` 仅在此文件用，可保留定义（无害）或一并删除。

- [ ] **Step 5: 跑全量 P0 测试 + py_compile**

Run: `cd backend && python -m pytest tests/test_permissions_p0.py -v && python -m py_compile app/api/import_api.py app/api/usda_admin.py && echo OK`
Expected: 全部 PASS + `OK`

- [ ] **Step 6: 跑既有测试确保无回归**

Run: `cd backend && python -m pytest tests/ -x -q 2>&1 | tail -20`
Expected: 既有测试不因鉴权收紧而 break（部分依赖「任意用户可写」的旧测试若失败，需把其请求 fixture 换为 `as_admin`）。

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/import_api.py backend/app/api/usda_admin.py backend/tests/test_permissions_p0.py
git commit -m "refactor(perms): 手动 is_admin 检查统一为 Depends(get_current_admin_user)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 0.8: P0 收尾——全量回归 + 设计文档开放项闭环

**Files:**
- Modify: `docs/superpowers/specs/2026-06-27-multi-user-permissions-design.md`（开放项闭环）

- [ ] **Step 1: 全量回归**

Run: `cd backend && python -m pytest tests/ -q 2>&1 | tail -30`
Expected: 全绿（或仅剩与本次无关的预存失败）。

- [ ] **Step 2: 更新设计文档开放项**

把设计文档 §8 中「`export.py scope=full` 现状待复核」一条更新为已复核结论（P0 已限管理员）。

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-06-27-multi-user-permissions-design.md
git commit -m "docs(perms): P0 完成，闭环 export scope=full 开放项

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

**P0 完成标志：** 全部共享数据写操作收紧为管理员直写，越权读已隔离/限管理员，手动鉴权统一。系统在「单用户=管理员」场景下行为不变（管理员仍可直写一切），同时堵住了多用户下的越权漏洞。P1 起，这些 admin 分支会接入「分流模式」，向普通用户开放提议通道。

---

## 阶段 1：通用提议—审核框架

> 目标：建一套通用 `change_proposals` 表 + 类型执行器 + 审核 API。框架本身不依赖任何具体业务执行器（P2 再注册），P1 用 stub 执行器证明 submit→review→apply→revert 全链路 + 策略三档 + 管理员分流跑通。

### Task 1.1: ChangeProposal 模型 + alembic 迁移 + 四引擎 SQL

**Files:**
- Create: `backend/app/models/change_proposal.py`
- Create: `backend/alembic/versions/20260627_0001_add_change_proposals.py`
- Create: `backend/scripts/sql/20260627_change_proposals_sqlite.sql` / `_mysql.sql` / `_postgresql.sql`
- Modify: `backend/alembic/env.py`（导入新模型）

- [ ] **Step 1: 创建模型**

`backend/app/models/change_proposal.py`：

```python
"""通用变更提议模型——治理共享数据的写入。"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.base_model import AuditMixin


class ChangeProposal(Base, AuditMixin):
    """一条对共享数据的变更提议。

    普通用户提交 → 按审核策略（auto_approve/auto_review/manual）流转；
    管理员直写不经过本表（分流模式在 service 层）。
    """
    __tablename__ = "change_proposals"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(32), nullable=False, index=True)
    # ingredient / nutrition / unit / merchant / hierarchy / merge / recipe / ...
    entity_id = Column(Integer, nullable=True, index=True)      # 新增（create）时空
    action = Column(String(16), nullable=False)                 # create/update/delete/merge/publish
    payload = Column(JSON, nullable=False)                      # 变更内容
    snapshot = Column(JSON, nullable=True)                      # apply 前快照（供 revert）
    revert_payload = Column(JSON, nullable=True)                # apply 生成的逆向操作

    review_policy = Column(String(16), nullable=False, default="manual")
    # auto_approve / auto_review / manual
    risk_level = Column(String(8), nullable=False, default="mid")  # low/mid/high（信息性，由 policy 驱动）
    status = Column(String(20), nullable=False, default="pending", index=True)
    # pending / auto_approved / approved / rejected / applied / reverted / cancelled

    proposer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_note = Column(Text, nullable=True)

    revertable_until = Column(DateTime(timezone=True), nullable=True)  # 高风险回滚窗口截止
    applied_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reverted_at = Column(DateTime(timezone=True), nullable=True)
    # created_at/updated_at/created_by/updated_by/is_active 继承自 AuditMixin
```

- [ ] **Step 2: 注册到 alembic env.py**

修改 `backend/alembic/env.py` 的模型导入块，追加：

```python
from app.models.change_proposal import ChangeProposal  # noqa: F401
```

- [ ] **Step 3: 创建 alembic 迁移**

`backend/alembic/versions/20260627_0001_add_change_proposals.py`：

```python
"""add change_proposals table

Revision ID: 20260627_0001
Revises: 20260626_0003
Create Date: 2026-06-27 10:00:00+08:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260627_0001'
down_revision: Union[str, None] = '20260626_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'change_proposals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('entity_type', sa.String(32), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(16), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=True),
        sa.Column('revert_payload', sa.JSON(), nullable=True),
        sa.Column('review_policy', sa.String(16), nullable=False, server_default='manual'),
        sa.Column('risk_level', sa.String(8), nullable=False, server_default='mid'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('proposer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reviewer_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('revertable_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reverted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_change_proposals_entity_type', 'change_proposals', ['entity_type'])
    op.create_index('ix_change_proposals_entity_id', 'change_proposals', ['entity_id'])
    op.create_index('ix_change_proposals_status', 'change_proposals', ['status'])
    op.create_index('ix_change_proposals_proposer_id', 'change_proposals', ['proposer_id'])


def downgrade() -> None:
    op.drop_index('ix_change_proposals_proposer_id', table_name='change_proposals')
    op.drop_index('ix_change_proposals_status', table_name='change_proposals')
    op.drop_index('ix_change_proposals_entity_id', table_name='change_proposals')
    op.drop_index('ix_change_proposals_entity_type', table_name='change_proposals')
    op.drop_table('change_proposals')
```

- [ ] **Step 4: 三引擎 SQL 脚本**

`backend/scripts/sql/20260627_change_proposals_sqlite.sql`：

```sql
CREATE TABLE IF NOT EXISTS change_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    action TEXT NOT NULL,
    payload TEXT NOT NULL,
    snapshot TEXT,
    revert_payload TEXT,
    review_policy TEXT NOT NULL DEFAULT 'manual',
    risk_level TEXT NOT NULL DEFAULT 'mid',
    status TEXT NOT NULL DEFAULT 'pending',
    proposer_id INTEGER NOT NULL REFERENCES users(id),
    reviewer_id INTEGER REFERENCES users(id),
    review_note TEXT,
    revertable_until TEXT,
    applied_at TEXT,
    reviewed_at TEXT,
    reverted_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    is_active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_change_proposals_entity_type ON change_proposals(entity_type);
CREATE INDEX IF NOT EXISTS ix_change_proposals_entity_id ON change_proposals(entity_id);
CREATE INDEX IF NOT EXISTS ix_change_proposals_status ON change_proposals(status);
CREATE INDEX IF NOT EXISTS ix_change_proposals_proposer_id ON change_proposals(proposer_id);
```

`backend/scripts/sql/20260627_change_proposals_mysql.sql`：

```sql
CREATE TABLE IF NOT EXISTS change_proposals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_type VARCHAR(32) NOT NULL,
    entity_id INT NULL,
    action VARCHAR(16) NOT NULL,
    payload JSON NOT NULL,
    snapshot JSON NULL,
    revert_payload JSON NULL,
    review_policy VARCHAR(16) NOT NULL DEFAULT 'manual',
    risk_level VARCHAR(8) NOT NULL DEFAULT 'mid',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    proposer_id INT NOT NULL,
    reviewer_id INT NULL,
    review_note TEXT NULL,
    revertable_until DATETIME NULL,
    applied_at DATETIME NULL,
    reviewed_at DATETIME NULL,
    reverted_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT NULL,
    updated_by INT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    INDEX ix_change_proposals_entity_type (entity_type),
    INDEX ix_change_proposals_entity_id (entity_id),
    INDEX ix_change_proposals_status (status),
    INDEX ix_change_proposals_proposer_id (proposer_id),
    FOREIGN KEY (proposer_id) REFERENCES users(id),
    FOREIGN KEY (reviewer_id) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

`backend/scripts/sql/20260627_change_proposals_postgresql.sql`：

```sql
CREATE TABLE IF NOT EXISTS change_proposals (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(32) NOT NULL,
    entity_id INTEGER,
    action VARCHAR(16) NOT NULL,
    payload JSONB NOT NULL,
    snapshot JSONB,
    revert_payload JSONB,
    review_policy VARCHAR(16) NOT NULL DEFAULT 'manual',
    risk_level VARCHAR(8) NOT NULL DEFAULT 'mid',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    proposer_id INTEGER NOT NULL REFERENCES users(id),
    reviewer_id INTEGER REFERENCES users(id),
    review_note TEXT,
    revertable_until TIMESTAMPTZ,
    applied_at TIMESTAMPTZ,
    reviewed_at TIMESTAMPTZ,
    reverted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_change_proposals_entity_type ON change_proposals(entity_type);
CREATE INDEX IF NOT EXISTS ix_change_proposals_entity_id ON change_proposals(entity_id);
CREATE INDEX IF NOT EXISTS ix_change_proposals_status ON change_proposals(status);
CREATE INDEX IF NOT EXISTS ix_change_proposals_proposer_id ON change_proposals(proposer_id);
```

- [ ] **Step 5: 应用迁移 + py_compile**

Run: `cd backend && python -m py_compile app/models/change_proposal.py && alembic upgrade head`
Expected: 迁移成功（若 SQLite 开发库 `alembic_version` 已在 head，改用 `Base.metadata.create_all` 自动建表，或 `alembic stamp` 调整）。

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/change_proposal.py backend/alembic/versions/20260627_0001_add_change_proposals.py backend/alembic/env.py backend/scripts/sql/20260627_change_proposals_*.sql
git commit -m "feat(proposals): ChangeProposal 模型 + 迁移 + 四引擎 SQL

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 1.2: 执行器基类 + 自动审核协议 + 默认实现

**Files:**
- Create: `backend/app/services/proposals/__init__.py`
- Create: `backend/app/services/proposals/base.py`
- Create: `backend/app/services/proposals/auto_reviewer.py`

- [ ] **Step 1: 写失败测试——ApplyResult 与默认审核器**

创建 `backend/tests/test_proposals_framework.py`：

```python
"""P1 框架单元测试：执行器基类、自动审核协议、默认实现。"""
from app.services.proposals.base import ApplyResult, ProposalExecutor
from app.services.proposals.auto_reviewer import DefaultAutoReviewer


def test_apply_result_defaults():
    r = ApplyResult(snapshot={"a": 1}, revert_payload={"undo": True})
    assert r.snapshot == {"a": 1}
    assert r.revert_payload == {"undo": True}
    assert r.summary == ""


def test_default_auto_reviewer_escalates():
    reviewer = DefaultAutoReviewer()
    result = reviewer.review(db=None, proposal=None)
    assert result.decision == "escalate"
    assert "默认" in result.reason or "escalate" in result.reason
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py -v`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 创建 base.py**

`backend/app/services/proposals/__init__.py`：

```python
"""通用提议-审核框架。"""
```

`backend/app/services/proposals/base.py`：

```python
"""执行器基类、apply 结果、自动审核协议。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ApplyResult:
    """执行器 apply 的返回：变更前快照 + 逆向操作 + 摘要。"""
    snapshot: dict
    revert_payload: dict
    summary: str = ""


class ProposalExecutor(ABC):
    """每种 entity_type 注册一个执行器。

    apply 是唯一执行核心：管理员直写与提议审核通过后都调它，差别只在「是否先审」。
    """
    entity_type: str = ""

    @abstractmethod
    def validate(self, db, proposal) -> None:
        """校验提议合法性（含待审互斥检查）。失败 raise HTTPException(400)。"""

    @abstractmethod
    def preview(self, db, proposal) -> dict:
        """返回影响预览（如合并会影响多少引用）。"""

    @abstractmethod
    def apply(self, db, proposal) -> ApplyResult:
        """事务内执行变更，返回快照与逆向操作。调用方负责 commit。"""

    @abstractmethod
    def revert(self, db, proposal) -> None:
        """用 proposal.snapshot 与 proposal.revert_payload 原路还原。调用方负责 commit。"""


class ProposalAutoReviewer(Protocol):
    """自动审核接口（预留）。本期默认实现全部 escalate。"""

    def review(self, db, proposal) -> "AutoReviewResult": ...


@dataclass
class AutoReviewResult:
    decision: str   # "approve" / "escalate" / "reject"
    reason: str = ""
```

- [ ] **Step 4: 创建 auto_reviewer.py**

`backend/app/services/proposals/auto_reviewer.py`：

```python
"""默认自动审核器：全部 escalate（等价 manual）。

具体判定逻辑（规则引擎/AI/库内比对）后续实现，本期只留接口。
"""
from app.services.proposals.base import AutoReviewResult


class DefaultAutoReviewer:
    """默认实现：所有提议都转人工审核。"""

    def review(self, db, proposal) -> AutoReviewResult:
        return AutoReviewResult(
            decision="escalate",
            reason="默认自动审核未配置，转人工审核"
        )
```

- [ ] **Step 5: 跑测试确认通过 + py_compile**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py -v && python -m py_compile app/services/proposals/base.py app/services/proposals/auto_reviewer.py && echo OK`
Expected: PASS + `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/proposals/ backend/tests/test_proposals_framework.py
git commit -m "feat(proposals): 执行器基类 + 自动审核协议 + 默认 escalate 实现

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 1.3: 执行器注册表 + 策略配置

**Files:**
- Create: `backend/app/services/proposals/registry.py`

- [ ] **Step 1: 写失败测试**

追加到 `backend/tests/test_proposals_framework.py`：

```python
from app.services.proposals.registry import ExecutorRegistry
from app.services.proposals.base import ProposalExecutor, ApplyResult


class _StubExecutor(ProposalExecutor):
    entity_type = "stub"

    def validate(self, db, proposal):
        pass

    def preview(self, db, proposal):
        return {"note": "stub"}

    def apply(self, db, proposal):
        return ApplyResult(snapshot={"x": 1}, revert_payload={"x": 0}, summary="stub applied")

    def revert(self, db, proposal):
        pass


def test_registry_register_and_get():
    ExecutorRegistry.reset()
    ExecutorRegistry.register(_StubExecutor())
    assert ExecutorRegistry.get("stub").entity_type == "stub"
    assert ExecutorRegistry.get("missing") is None


def test_registry_policy_default_and_override():
    ExecutorRegistry.reset()
    ExecutorRegistry.register(_StubExecutor())
    # 默认 policy = manual
    assert ExecutorRegistry.policy_for("stub", "update") == "manual"
    # 覆盖
    ExecutorRegistry.set_policy("stub", "update", "auto_approve")
    assert ExecutorRegistry.policy_for("stub", "update") == "auto_approve"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py -k registry -v`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 创建 registry.py**

`backend/app/services/proposals/registry.py`：

```python
"""执行器注册表 + 按 entity_type/action 的审核策略配置。"""
from typing import Dict, Optional, Tuple
from app.services.proposals.base import ProposalExecutor


class ExecutorRegistry:
    """全局执行器与策略注册表（类变量持有，进程级）。"""

    _executors: Dict[str, ProposalExecutor] = {}
    _policies: Dict[Tuple[str, str], str] = {}   # (entity_type, action) -> policy
    _risk_levels: Dict[Tuple[str, str], str] = {}

    @classmethod
    def register(cls, executor: ProposalExecutor, default_policy: str = "manual",
                 default_risk: str = "mid") -> ProposalExecutor:
        if not executor.entity_type:
            raise ValueError("执行器必须声明 entity_type")
        cls._executors[executor.entity_type] = executor
        # 注册时不覆盖已设置的 policy（允许后续 set_policy 定制）
        for action in ("create", "update", "delete", "merge", "publish"):
            cls._policies.setdefault((executor.entity_type, action), default_policy)
            cls._risk_levels.setdefault((executor.entity_type, action), default_risk)
        return executor

    @classmethod
    def get(cls, entity_type: str) -> Optional[ProposalExecutor]:
        return cls._executors.get(entity_type)

    @classmethod
    def policy_for(cls, entity_type: str, action: str) -> str:
        return cls._policies.get((entity_type, action), "manual")

    @classmethod
    def risk_for(cls, entity_type: str, action: str) -> str:
        return cls._risk_levels.get((entity_type, action), "mid")

    @classmethod
    def set_policy(cls, entity_type: str, action: str, policy: str) -> None:
        if policy not in ("auto_approve", "auto_review", "manual"):
            raise ValueError(f"非法策略: {policy}")
        cls._policies[(entity_type, action)] = policy

    @classmethod
    def reset(cls) -> None:
        """测试用：清空注册表。"""
        cls._executors.clear()
        cls._policies.clear()
        cls._risk_levels.clear()
```

- [ ] **Step 4: 跑测试确认通过 + py_compile**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py -v && python -m py_compile app/services/proposals/registry.py && echo OK`
Expected: PASS + `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/proposals/registry.py backend/tests/test_proposals_framework.py
git commit -m "feat(proposals): 执行器注册表 + 策略配置

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 1.4: 提议业务服务（submit / review / revert / apply）

**Files:**
- Create: `backend/app/services/proposals/service.py`

> 核心业务逻辑：提交（按策略分流）、审核、apply（调执行器）、revert。管理员分流（直写 apply）也在这里暴露。

- [ ] **Step 1: 写失败测试——submit 各策略分流**

追加到 `backend/tests/test_proposals_framework.py`：

```python
import pytest
from app.services.proposals import service as proposal_service
from app.services.proposals.registry import ExecutorRegistry
from app.services.proposals.base import ProposalExecutor, ApplyResult
from conftest import TestingSessionLocal
from app.models.change_proposal import ChangeProposal


class _RecordingExecutor(ProposalExecutor):
    """记录 apply/revert 调用，便于断言。"""
    entity_type = "rec"
    applied = 0
    reverted = 0

    def validate(self, db, proposal): pass
    def preview(self, db, proposal): return {}
    def apply(self, db, proposal):
        type(self).applied += 1
        return ApplyResult(snapshot={"v": 1}, revert_payload={"v": 0}, summary="ok")
    def revert(self, db, proposal):
        type(self).reverted += 1


@pytest.fixture()
def db():
    s = TestingSessionLocal()
    yield s
    s.query(ChangeProposal).delete(); s.commit(); s.close()


@pytest.fixture(autouse=True)
def _reset_registry():
    ExecutorRegistry.reset()
    ExecutorRegistry.register(_RecordingExecutor())
    _RecordingExecutor.applied = 0
    _RecordingExecutor.reverted = 0
    yield


class _U:
    id = 5
    is_admin = False


def test_submit_manual_stays_pending(db):
    ExecutorRegistry.set_policy("rec", "update", "manual")
    p = proposal_service.submit(db, entity_type="rec", entity_id=1, action="update",
                                payload={"v": 1}, proposer=_U())
    db.commit()
    assert p.status == "pending"
    assert _RecordingExecutor.applied == 0


def test_submit_auto_approve_applies(db):
    ExecutorRegistry.set_policy("rec", "update", "auto_approve")
    p = proposal_service.submit(db, entity_type="rec", entity_id=1, action="update",
                                payload={"v": 1}, proposer=_U())
    db.commit()
    assert p.status == "applied"
    assert _RecordingExecutor.applied == 1
    assert p.snapshot == {"v": 1}
    assert p.revert_payload == {"v": 0}


def test_review_approve_applies(db):
    ExecutorRegistry.set_policy("rec", "update", "manual")
    p = proposal_service.submit(db, entity_type="rec", entity_id=1, action="update",
                                payload={"v": 1}, proposer=_U())
    db.commit()
    admin = type("A", (), {"id": 1, "is_admin": True})()
    proposal_service.review(db, proposal_id=p.id, approved=True, reviewer=admin, note="ok")
    db.commit()
    assert p.status == "applied"
    assert _RecordingExecutor.applied == 1
    assert p.reviewer_id == 1


def test_revert_calls_executor(db):
    ExecutorRegistry.set_policy("rec", "update", "auto_approve")
    p = proposal_service.submit(db, entity_type="rec", entity_id=1, action="update",
                                payload={"v": 1}, proposer=_U())
    db.commit()
    admin = type("A", (), {"id": 1, "is_admin": True})()
    proposal_service.revert(db, proposal_id=p.id, reviewer=admin)
    db.commit()
    assert p.status == "reverted"
    assert _RecordingExecutor.reverted == 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py -k "submit or review or revert" -v`
Expected: FAIL（service 模块不存在）。

- [ ] **Step 3: 创建 service.py**

`backend/app/services/proposals/service.py`：

```python
"""提议业务服务：提交（策略分流）、审核、apply、回滚。"""
from datetime import datetime, timedelta
from typing import Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.change_proposal import ChangeProposal
from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.services.proposals.registry import ExecutorRegistry
from app.services.proposals.auto_reviewer import DefaultAutoReviewer

# 高风险回滚窗口（天）
REVERT_WINDOW_DAYS = 7

_auto_reviewer = DefaultAutoReviewer()


def _get_executor(entity_type: str) -> ProposalExecutor:
    ex = ExecutorRegistry.get(entity_type)
    if ex is None:
        raise HTTPException(status_code=400, detail=f"不支持的提议类型: {entity_type}")
    return ex


def _now() -> datetime:
    return datetime.utcnow()


def submit(db: Session, *, entity_type: str, entity_id: Optional[int], action: str,
           payload: dict, proposer) -> ChangeProposal:
    """普通用户提交提议。按策略分流：auto_approve 立即 apply；auto_review 走自动审核；manual 待审。"""
    executor = _get_executor(entity_type)
    policy = ExecutorRegistry.policy_for(entity_type, action)
    risk = ExecutorRegistry.risk_for(entity_type, action)

    proposal = ChangeProposal(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        payload=payload,
        review_policy=policy,
        risk_level=risk,
        status="pending",
        proposer_id=proposer.id,
    )
    # validate 在持久化前跑（含互斥检查），但互斥检查需 proposal 已存在 → 先 add flush 拿 id
    db.add(proposal)
    db.flush()
    executor.validate(db, proposal)

    if policy == "auto_approve":
        _do_apply(db, proposal, executor)
        proposal.status = "applied"
    elif policy == "auto_review":
        result = _auto_reviewer.review(db, proposal)
        if result.decision == "approve":
            _do_apply(db, proposal, executor)
            proposal.status = "applied"
            proposal.review_note = f"自动审核通过: {result.reason}"
        elif result.decision == "reject":
            proposal.status = "rejected"
            proposal.review_note = f"自动审核驳回: {result.reason}"
            proposal.reviewed_at = _now()
        # escalate → 保持 pending
    # manual → 保持 pending
    return proposal


def review(db: Session, *, proposal_id: int, approved: bool, reviewer, note: str = "") -> ChangeProposal:
    """管理员审核：approved → apply；否则 rejected。"""
    proposal = db.query(ChangeProposal).filter(ChangeProposal.id == proposal_id).first()
    if proposal is None:
        raise HTTPException(status_code=404, detail="提议不存在")
    if proposal.status not in ("pending",):
        raise HTTPException(status_code=409, detail=f"提议已处理（status={proposal.status}），不能重复审核")

    proposal.reviewer_id = reviewer.id
    proposal.reviewed_at = _now()
    proposal.review_note = note

    if approved:
        executor = _get_executor(proposal.entity_type)
        _do_apply(db, proposal, executor)
        proposal.status = "applied"
    else:
        proposal.status = "rejected"
    return proposal


def revert(db: Session, *, proposal_id: int, reviewer) -> ChangeProposal:
    """回滚已 apply 的提议（回滚窗口内）。"""
    proposal = db.query(ChangeProposal).filter(ChangeProposal.id == proposal_id).first()
    if proposal is None:
        raise HTTPException(status_code=404, detail="提议不存在")
    if proposal.status != "applied":
        raise HTTPException(status_code=409, detail=f"仅 applied 提议可回滚（当前 status={proposal.status}）")
    if proposal.revertable_until and _now() > proposal.revertable_until.replace(tzinfo=None):
        raise HTTPException(status_code=403, detail="回滚窗口已过")

    executor = _get_executor(proposal.entity_type)
    executor.revert(db, proposal)
    proposal.status = "reverted"
    proposal.reverted_at = _now()
    proposal.reviewer_id = reviewer.id
    return proposal


def apply_as_admin(db: Session, *, entity_type: str, entity_id: Optional[int], action: str,
                   payload: dict, admin) -> ChangeProposal:
    """管理员直写：绕过审核，立即 apply。单用户场景的核心路径。"""
    executor = _get_executor(entity_type)
    risk = ExecutorRegistry.risk_for(entity_type, action)
    proposal = ChangeProposal(
        entity_type=entity_type, entity_id=entity_id, action=action, payload=payload,
        review_policy="auto_approve", risk_level=risk, status="applied",
        proposer_id=admin.id, reviewer_id=admin.id,
        applied_at=_now(),
    )
    db.add(proposal)
    db.flush()
    executor.validate(db, proposal)
    _do_apply(db, proposal, executor)
    proposal.status = "applied"
    return proposal


def _do_apply(db: Session, proposal: ChangeProposal, executor: ProposalExecutor) -> None:
    """调执行器 apply，落快照与逆向操作；高风险设回滚窗口。"""
    result: ApplyResult = executor.apply(db, proposal)
    proposal.snapshot = result.snapshot
    proposal.revert_payload = result.revert_payload
    proposal.applied_at = _now()
    if proposal.risk_level == "high":
        proposal.revertable_until = _now() + timedelta(days=REVERT_WINDOW_DAYS)
```

- [ ] **Step 4: 跑测试确认通过 + py_compile**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py -v && python -m py_compile app/services/proposals/service.py && echo OK`
Expected: 全部 PASS + `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/proposals/service.py backend/tests/test_proposals_framework.py
git commit -m "feat(proposals): 提议业务服务（策略分流/审核/回滚/管理员直写）

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 1.5: Pydantic schema

**Files:**
- Create: `backend/app/schemas/proposal.py`

- [ ] **Step 1: 创建 schema**

`backend/app/schemas/proposal.py`：

```python
"""提议相关 Pydantic schema。"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ProposalCreate(BaseModel):
    entity_type: str = Field(..., description="ingredient/nutrition/unit/merchant/...")
    entity_id: Optional[int] = None
    action: str = Field(..., description="create/update/delete/merge/publish")
    payload: dict = Field(..., description="变更内容")


class ProposalPreviewRequest(BaseModel):
    entity_type: str
    entity_id: Optional[int] = None
    action: str
    payload: dict


class ReviewDecision(BaseModel):
    approved: bool
    note: str = ""


class ProposalResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: Optional[int]
    action: str
    payload: dict
    status: str
    review_policy: str
    risk_level: str
    proposer_id: int
    reviewer_id: Optional[int]
    review_note: Optional[str]
    revertable_until: Optional[datetime]
    applied_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    reverted_at: Optional[datetime]
    preview: Optional[dict] = None   # 可选附影响预览

    class Config:
        from_attributes = True
```

- [ ] **Step 2: py_compile**

Run: `cd backend && python -m py_compile app/schemas/proposal.py && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/proposal.py
git commit -m "feat(proposals): Pydantic schema

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 1.6: proposals API + 注册路由

**Files:**
- Create: `backend/app/api/proposals.py`
- Modify: `backend/app/main.py`（注册路由）

- [ ] **Step 1: 写失败测试——API 端到端**

追加到 `backend/tests/test_proposals_framework.py`：

```python
from fastapi.testclient import TestClient
from app.main import app

api_client = TestClient(app)


def test_submit_via_api_requires_auth():
    r = api_client.post("/api/v1/proposals", json={
        "entity_type": "rec", "entity_id": 1, "action": "update", "payload": {}})
    assert r.status_code in (401, 403)


def test_non_admin_submit_pending_then_admin_review(monkeypatch):
    """注册一个 rec 执行器（通过 import 触发注册或 monkeypatch）。"""
    from app.services.proposals.registry import ExecutorRegistry
    ExecutorRegistry.reset()
    ExecutorRegistry.register(_RecordingExecutor())
    ExecutorRegistry.set_policy("rec", "update", "manual")

    # 普通用户提交
    from conftest import NonAdminFakeUser, _fake_non_admin_user, override_get_db, fake_current_user
    app.dependency_overrides[get_db_dependency] = override_get_db
    app.dependency_overrides[get_cu_dependency] = _fake_non_admin_user
    try:
        r = api_client.post("/api/v1/proposals", json={
            "entity_type": "rec", "entity_id": 1, "action": "update", "payload": {"v": 1}})
        assert r.status_code == 200
        pid = r.json()["id"]
        assert r.json()["status"] == "pending"

        # 非管理员审核 → 403
        r2 = api_client.post(f"/api/v1/proposals/{pid}/review", json={"approved": True})
        assert r2.status_code == 403
    finally:
        app.dependency_overrides.clear()
```

> 注：`get_db_dependency` / `get_cu_dependency` 在测试顶部加 `from app.core.database import get_db as get_db_dependency` 与 `from app.core.security import get_current_user as get_cu_dependency`。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py -k "via_api or admin_review" -v`
Expected: FAIL（路由不存在 → 404）。

- [ ] **Step 3: 创建 proposals.py API**

`backend/app/api/proposals.py`：

```python
"""通用提议-审核 API。"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.change_proposal import ChangeProposal
from app.services.proposals import service as proposal_service
from app.services.proposals.registry import ExecutorRegistry
from app.schemas.proposal import ProposalCreate, ProposalResponse, ProposalPreviewRequest, ReviewDecision

router = APIRouter()


def _to_response(p: ChangeProposal) -> ProposalResponse:
    return ProposalResponse(
        id=p.id, entity_type=p.entity_type, entity_id=p.entity_id, action=p.action,
        payload=p.payload or {}, status=p.status, review_policy=p.review_policy,
        risk_level=p.risk_level, proposer_id=p.proposer_id, reviewer_id=p.reviewer_id,
        review_note=p.review_note, revertable_until=p.revertable_until,
        applied_at=p.applied_at, reviewed_at=p.reviewed_at, reverted_at=p.reverted_at,
    )


@router.post("/proposals", response_model=ProposalResponse)
def submit_proposal(body: ProposalCreate,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """提交变更提议（任意登录用户）。按策略分流。"""
    p = proposal_service.submit(
        db, entity_type=body.entity_type, entity_id=body.entity_id,
        action=body.action, payload=body.payload, proposer=current_user,
    )
    db.commit()
    return _to_response(p)


@router.post("/proposals/preview")
def preview_proposal(body: ProposalPreviewRequest,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """预览提议影响（如合并会影响多少引用）。"""
    executor = ExecutorRegistry.get(body.entity_type)
    if executor is None:
        raise HTTPException(status_code=400, detail=f"不支持的提议类型: {body.entity_type}")
    # 构造临时 proposal 供 preview
    tmp = ChangeProposal(entity_type=body.entity_type, entity_id=body.entity_id,
                         action=body.action, payload=body.payload, proposer_id=current_user.id)
    return executor.preview(db, tmp)


@router.get("/proposals", response_model=List[ProposalResponse])
def list_proposals(status_filter: Optional[str] = Query(None, alias="status"),
                   limit: int = Query(50, ge=1, le=200),
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """管理员看全部；普通用户只看自己提交的。"""
    q = db.query(ChangeProposal)
    if not current_user.is_admin:
        q = q.filter(ChangeProposal.proposer_id == current_user.id)
    if status_filter:
        q = q.filter(ChangeProposal.status == status_filter)
    items = q.order_by(ChangeProposal.id.desc()).limit(limit).all()
    return [_to_response(p) for p in items]


@router.get("/proposals/{proposal_id}", response_model=ProposalResponse)
def get_proposal(proposal_id: int,
                 db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    p = db.query(ChangeProposal).filter(ChangeProposal.id == proposal_id).first()
    if p is None:
        raise HTTPException(status_code=404, detail="提议不存在")
    if not current_user.is_admin and p.proposer_id != current_user.id:
        raise HTTPException(status_code=404, detail="提议不存在")
    return _to_response(p)


@router.post("/proposals/{proposal_id}/review", response_model=ProposalResponse)
def review_proposal(proposal_id: int, body: ReviewDecision,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_admin_user)):
    """审核提议（仅管理员）。"""
    p = proposal_service.review(db, proposal_id=proposal_id, approved=body.approved,
                                reviewer=current_user, note=body.note)
    db.commit()
    return _to_response(p)


@router.post("/proposals/{proposal_id}/revert", response_model=ProposalResponse)
def revert_proposal(proposal_id: int,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_admin_user)):
    """回滚已 apply 的提议（仅管理员）。"""
    p = proposal_service.revert(db, proposal_id=proposal_id, reviewer=current_user)
    db.commit()
    return _to_response(p)
```

- [ ] **Step 4: main.py 注册路由**

在 `backend/app/main.py` 的 `include_router` 块（[main.py:544-573](backend/app/main.py#L544)）追加：

```python
from app.api import proposals as proposals_api
app.include_router(proposals_api.router, prefix="/api/v1", tags=["变更提议"])
```

> 顶部 import 区相应加 `from app.api import proposals`（或跟随文件现有风格）。

- [ ] **Step 5: 跑测试 + py_compile**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py -v && python -m py_compile app/api/proposals.py && echo OK`
Expected: PASS + `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/proposals.py backend/app/main.py backend/tests/test_proposals_framework.py
git commit -m "feat(proposals): 提议/审核/回滚/预览 API + 路由注册

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 1.7: P1 收尾——策略配置持久化占位 + 全量回归

**Files:**
- Create: `backend/app/services/proposals/bootstrap.py`（注册执行器的统一入口，P2 在此填真实执行器）

- [ ] **Step 1: 创建 bootstrap 占位**

`backend/app/services/proposals/bootstrap.py`：

```python
"""执行器注册入口。

P1：无真实执行器（仅测试中注册 stub）。
P2：在此 import 并 register 各业务执行器（ingredient/nutrition/unit/merchant/hierarchy/merge/recipe_publish）。
P3：管理员后台可调用 ExecutorRegistry.set_policy 动态改策略（持久化到 system_config 另行实现）。
"""
# P2 将在此添加：
# from app.services.proposals.executors.ingredient import IngredientExecutor
# ExecutorRegistry.register(IngredientExecutor(), default_policy="auto_approve", default_risk="mid")
# ...
```

- [ ] **Step 2: py_compile + 全量回归**

Run: `cd backend && python -m py_compile app/services/proposals/bootstrap.py && python -m pytest tests/ -q 2>&1 | tail -20`
Expected: 全绿。

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/proposals/bootstrap.py
git commit -m "feat(proposals): 执行器注册入口占位（P2 填业务执行器）

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

**P1 完成标志：** 通用 `change_proposals` 表 + 类型执行器框架 + 审核 API 就绪，stub 执行器证明 submit（三档策略分流）→ review（管理员）→ apply（执行器 + 快照 + 回滚窗口）→ revert 全链路跑通。**框架就绪但尚无真实执行器**——P2 注册各业务执行器并把共享写端点接入分流模式。管理员 `apply_as_admin` 直写路径已具备，为 P2 把 P0 的「仅管理员」端点平滑升级为「管理员直写 + 普通用户提议」做好准备。

---

## 阶段 2：共享数据转型

> 目标：注册各业务执行器；商家转共享池 + 收藏；价格公开聚合（去标识）；菜谱 is_public + 发布；营养「补空/覆盖」特例；把 P0 的「仅管理员」端点升级为分流模式（管理员 `apply_as_admin` / 普通用户 submit）。

### Task 2.1: 模型变更——Merchant.user_id nullable + Recipe.is_public + Unit.is_standard + 收藏表 + 价格汇总表

**Files:**
- Create: `backend/app/models/user_merchant_favorite.py`
- Create: `backend/app/models/price_summary.py`
- Modify: `backend/app/models/merchant.py`（user_id nullable）
- Modify: `backend/app/models/recipe.py`（+ is_public）
- Modify: `backend/app/models/unit.py`（+ is_standard / unit_system）
- Create: `backend/alembic/versions/20260627_0002_shared_data_transform.py`
- Create: `backend/scripts/sql/20260627_shared_transform_{sqlite,mysql,postgresql}.sql`
- Modify: `backend/alembic/env.py`

- [ ] **Step 1: 新建 user_merchant_favorite.py**

`backend/app/models/user_merchant_favorite.py`：

```python
"""用户商家收藏（替代原 Merchant.user_id 的私有归属语义）。"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class UserMerchantFavorite(Base):
    __tablename__ = "user_merchant_favorites"
    __table_args__ = (UniqueConstraint("user_id", "merchant_id", name="uq_user_merchant"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: 新建 price_summary.py**

`backend/app/models/price_summary.py`：

```python
"""商品×商家 价格聚合汇总（去标识，不含 user/record_type）。写入时增量更新。"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class ProductMerchantPriceSummary(Base):
    __tablename__ = "product_merchant_price_summary"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=True, index=True)
    sample_count = Column(Integer, nullable=False, default=0)
    recent_price = Column(Numeric(10, 2), nullable=True)
    avg_price_30d = Column(Numeric(10, 2), nullable=True)
    min_price = Column(Numeric(10, 2), nullable=True)
    max_price = Column(Numeric(10, 2), nullable=True)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 3: 改 merchant.py——user_id 改 nullable**

修改 [merchant.py:12](backend/app/models/merchant.py#L12)：把 `user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)` 改为 `nullable=True`。语义从「拥有者」改为「录入者」。

- [ ] **Step 4: 改 recipe.py——加 is_public**

修改 [recipe.py](backend/app/models/recipe.py) Recipe 类，在 `source` 行附近加：

```python
is_public = Column(Boolean, default=False, nullable=False, server_default=sa.text("false"))
```

确保顶部已 `from sqlalchemy import Boolean` 及 `import sqlalchemy as sa`。

- [ ] **Step 5: 改 unit.py——加 is_standard / unit_system**

修改 `backend/app/models/unit.py`，加：

```python
is_standard = Column(Boolean, default=False, nullable=False, server_default=sa.text("false"))
unit_system = Column(String(16), nullable=True)  # metric / market / imperial / custom
```

- [ ] **Step 6: 注册新模型到 env.py + 创建迁移 + SQL**

`backend/alembic/env.py` 追加：

```python
from app.models.user_merchant_favorite import UserMerchantFavorite  # noqa: F401
from app.models.price_summary import ProductMerchantPriceSummary  # noqa: F401
```

`backend/alembic/versions/20260627_0002_shared_data_transform.py`：

```python
"""shared data transform: merchant user_id nullable, recipe is_public, unit is_standard, favorites + price summary

Revision ID: 20260627_0002
Revises: 20260627_0001
Create Date: 2026-06-27 11:00:00+08:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '20260627_0002'
down_revision: Union[str, None] = '20260627_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # merchant.user_id 改 nullable
    with op.batch_alter_table('merchants') as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=True)
    # recipe.is_public
    with op.batch_alter_table('recipes') as batch_op:
        batch_op.add_column(sa.Column('is_public', sa.Boolean(),
                                      nullable=False, server_default=sa.text('false')))
    # unit.is_standard / unit_system
    with op.batch_alter_table('units') as batch_op:
        batch_op.add_column(sa.Column('is_standard', sa.Boolean(),
                                      nullable=False, server_default=sa.text('false')))
        batch_op.add_column(sa.Column('unit_system', sa.String(16), nullable=True))
    # 收藏表
    op.create_table(
        'user_merchant_favorites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('merchant_id', sa.Integer(), sa.ForeignKey('merchants.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'merchant_id', name='uq_user_merchant'),
    )
    op.create_index('ix_user_merchant_favorites_user_id', 'user_merchant_favorites', ['user_id'])
    # 价格汇总表
    op.create_table(
        'product_merchant_price_summary',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('merchant_id', sa.Integer(), sa.ForeignKey('merchants.id'), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('recent_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('avg_price_30d', sa.Numeric(10, 2), nullable=True),
        sa.Column('min_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('max_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pmp_summary_product', 'product_merchant_price_summary', ['product_id'])
    op.create_index('ix_pmp_summary_merchant', 'product_merchant_price_summary', ['merchant_id'])
    # 迁移：现有「拥有」商家 → 收藏（user_id 非空的 merchant 插入收藏）
    op.execute("""
        INSERT OR IGNORE INTO user_merchant_favorites (user_id, merchant_id, created_at)
        SELECT DISTINCT user_id, id, CURRENT_TIMESTAMP FROM merchants WHERE user_id IS NOT NULL
    """)  # MySQL/PG 需改为 INSERT IGNORE → ON DUPLICATE KEY / ON CONFLICT，见各引擎 SQL


def downgrade() -> None:
    op.drop_index('ix_pmp_summary_merchant', table_name='product_merchant_price_summary')
    op.drop_index('ix_pmp_summary_product', table_name='product_merchant_price_summary')
    op.drop_table('product_merchant_price_summary')
    op.drop_index('ix_user_merchant_favorites_user_id', table_name='user_merchant_favorites')
    op.drop_table('user_merchant_favorites')
    with op.batch_alter_table('units') as batch_op:
        batch_op.drop_column('unit_system')
        batch_op.drop_column('is_standard')
    with op.batch_alter_table('recipes') as batch_op:
        batch_op.drop_column('is_public')
    with op.batch_alter_table('merchants') as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=False)
```

> 三引擎 SQL 脚本（`backend/scripts/sql/20260627_shared_transform_{sqlite,mysql,postgresql}.sql`）：按既有惯例写完整建表 + ALTER。`mysql` 用 `INSERT IGNORE`、`postgresql` 用 `ON CONFLICT DO NOTHING` 做收藏回填。SQLite 用 `INSERT OR IGNORE`。脚本代表「全新库的最终 schema」，收藏回填段仅对升级库有意义，可附注释说明。

- [ ] **Step 7: 应用迁移 + py_compile**

Run: `cd backend && python -m py_compile app/models/user_merchant_favorite.py app/models/price_summary.py app/models/merchant.py app/models/recipe.py app/models/unit.py && alembic upgrade head`
Expected: 成功。

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/ backend/alembic/versions/20260627_0002_shared_data_transform.py backend/alembic/env.py backend/scripts/sql/20260627_shared_transform_*.sql
git commit -m "feat(shared): 商家/菜谱/单位 字段变更 + 收藏表 + 价格汇总表

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2.2: 价格公开聚合——去标识汇总 + 写入钩子 + latest-price 改读汇总

**Files:**
- Create: `backend/app/services/price_aggregator.py`
- Modify: `backend/app/api/products.py`（create_product_record 加汇总钩子）
- Modify: `backend/app/api/products_entity.py` + `nutrition.py`（latest-price 改读汇总，去标识）

- [ ] **Step 1: 写失败测试——汇总表不含 user/record_type**

创建 `backend/tests/test_shared_data.py`：

```python
"""P2 共享数据测试。"""
import pytest
from conftest import TestingSessionLocal
from app.models.price_summary import ProductMerchantPriceSummary
from app.services.price_aggregator import recompute_summary
from app.models.product import ProductRecord, RecordType


def test_summary_has_no_user_or_record_type_columns():
    cols = {c.name for c in ProductMerchantPriceSummary.__table__.columns}
    assert "user_id" not in cols
    assert "record_type" not in cols


def test_recompute_summary_aggregates_both_price_and_purchase(db=None):
    s = TestingSessionLocal()
    # 准备：2 条 PRICE + 1 条 PURCHASE，同 product×merchant
    # （具体构造依赖 Product/Unit 前置数据；此处给骨架，执行时补全 fixture）
    try:
        # ... 插入 3 条 ProductRecord ...
        recompute_summary(s, product_id=1, merchant_id=1)
        row = s.query(ProductMerchantPriceSummary).filter_by(product_id=1, merchant_id=1).first()
        assert row is not None
        assert row.sample_count == 3
        assert row.recent_price is not None
    finally:
        s.close()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_shared_data.py -v`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 创建 price_aggregator.py**

`backend/app/services/price_aggregator.py`：

```python
"""价格聚合：把 ProductRecord（PRICE + PURCHASE）聚合到去标识汇总表。"""
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.product import ProductRecord
from app.models.price_summary import ProductMerchantPriceSummary


def recompute_summary(db: Session, *, product_id: int, merchant_id: int | None) -> None:
    """重算指定 product×merchant 的汇总。不含 user_id / record_type（去标识）。"""
    since = datetime.utcnow() - timedelta(days=30)
    q = db.query(
        func.count(ProductRecord.id).label("cnt"),
        func.max(ProductRecord.price).label("mx"),
        func.min(ProductRecord.price).label("mn"),
        func.avg(ProductRecord.price).label("avg"),
    ).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.is_active == True,
    )
    if merchant_id is not None:
        q = q.filter(ProductRecord.merchant_id == merchant_id)
    row = q.first()

    recent = db.query(ProductRecord.price).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.is_active == True,
        *( [ProductRecord.merchant_id == merchant_id] if merchant_id is not None else [] ),
    ).order_by(ProductRecord.recorded_at.desc()).first()

    existing = db.query(ProductMerchantPriceSummary).filter_by(
        product_id=product_id, merchant_id=merchant_id).first()
    if existing is None:
        existing = ProductMerchantPriceSummary(product_id=product_id, merchant_id=merchant_id)
        db.add(existing)
    existing.sample_count = row.cnt or 0
    existing.min_price = row.mn
    existing.max_price = row.mx
    existing.avg_price_30d = row.avg
    existing.recent_price = recent[0] if recent else None
    existing.last_updated_at = datetime.utcnow()
    db.flush()
```

- [ ] **Step 4: products.py 创建记录后调 recompute**

修改 [products.py create_product_record](backend/app/api/products.py#L101)：在 `db.commit()` 前加：

```python
from app.services.price_aggregator import recompute_summary
recompute_summary(db, product_id=product_id, merchant_id=db_record.merchant_id)
```

- [ ] **Step 5: latest-price 改读汇总（去标识）**

修改 [products_entity.py](backend/app/api/products_entity.py) 与 [nutrition.py](backend/app/api/nutrition.py) 的 `latest-price` / `latest-price-by-merchant`：把查询源从 `ProductRecord`（含 user_id/record_type）改为 `ProductMerchantPriceSummary`。响应只返回 `recent_price / avg_price_30d / min / max / sample_count`，**绝不返回 user_id 或 record_type**。同时移除 Task 0.2 临时加的 `user_id` 过渡过滤。

示例（products_entity.py 的 latest-price 改造）：

```python
from app.models.price_summary import ProductMerchantPriceSummary

summary = db.query(ProductMerchantPriceSummary).filter(
    ProductMerchantPriceSummary.product_id == product_id,
    ProductMerchantPriceSummary.merchant_id == merchant_id,
).first()
if not summary:
    raise HTTPException(status_code=404, detail="无聚合价格")
return {
    "recent_price": summary.recent_price,
    "avg_price_30d": summary.avg_price_30d,
    "min_price": summary.min_price,
    "max_price": summary.max_price,
    "sample_count": summary.sample_count,
}   # 注意：字段集合里没有 user_id / record_type
```

- [ ] **Step 6: 跑测试 + py_compile**

Run: `cd backend && python -m pytest tests/test_shared_data.py -v && python -m py_compile app/services/price_aggregator.py app/api/products.py app/api/products_entity.py app/api/nutrition.py && echo OK`
Expected: PASS + `OK`

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/price_aggregator.py backend/app/api/products.py backend/app/api/products_entity.py backend/app/api/nutrition.py backend/tests/test_shared_data.py
git commit -m "feat(shared): 价格去标识聚合 + 写入钩子 + latest-price 改读汇总

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2.3: 商家共享池 + 收藏端点

**Files:**
- Modify: `backend/app/api/merchants.py`
- Modify: `backend/app/models/merchant.py`（关系，可选）

> 商家列表/详情/坐标改读共享池（去掉 `user_id==current_user.id` 过滤）；创建写入 `user_id=录入者` 进共享池；新增收藏端点。编辑/删除走 merchant 执行器（Task 2.5 接入），P0 已限管理员在此期间保持安全。

- [ ] **Step 1: 写失败测试——商家共享池可见 + 收藏**

追加到 `backend/tests/test_shared_data.py`：

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_merchant_list_visible_to_all_users(clean_merchants):
    """商家是共享池，任意登录用户可见全部。"""
    # clean_merchants fixture 插入一条 user_id=1 的商家
    from conftest import override_get_db, _fake_non_admin_user
    app.dependency_overrides[get_db_dep] = override_get_db
    app.dependency_overrides[get_cu_dep] = _fake_non_admin_user
    try:
        r = client.get("/api/v1/merchants")
        assert r.status_code == 200
        assert len(r.json()) >= 1   # 能看到 user_id=1 的商家（非自己）
    finally:
        app.dependency_overrides.clear()
```

> 顶部补 `from app.core.database import get_db as get_db_dep` 与 `from app.core.security import get_current_user as get_cu_dep`。`clean_merchants` fixture 在文件内定义（插入测试商家并清理）。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_shared_data.py -k merchant_list -v`
Expected: FAIL（当前商家列表过滤 user_id==自己，非管理员看不到 user_id=1 的）。

- [ ] **Step 3: merchants.py 改共享池查询**

修改 `backend/app/api/merchants.py`：
- `GET ""`（列表，[L594](backend/app/api/merchants.py#L594)）：去掉 `Merchant.user_id == current_user.id` 过滤，改为查共享池全部（可加 `is_active`/分页）。返回的 MerchantResponse 可附 `is_favorited`（当前用户是否收藏）。
- `GET /coordinates`（[L126](backend/app/api/merchants.py#L126)）：同上去掉 user_id 过滤。
- `GET /{merchant_id}`（[L167](backend/app/api/merchants.py#L167)）：去掉 `Merchant.user_id == current_user.id`，改为按 id 查共享池。
- `GET /{id}/prices`、`/{id}/product-prices`、`/{id}/product-orders`：这些涉及「我的价格记录」，保留 `ProductRecord.user_id` 过滤（价格记录本身仍私有），但商家归属校验改为「商家存在于共享池」而非「属于我」。
- `PUT /{id}`、`DELETE /{id}`：P0 已限管理员，保持；P2.5 接 merchant 执行器分流。
- `POST ""`（创建，[L92](backend/app/api/merchants.py#L92)）：保持 `user_id=current_user.id`（录入者）。

- [ ] **Step 4: 新增收藏端点**

在 `merchants.py` 追加：

```python
from app.models.user_merchant_favorite import UserMerchantFavorite


@router.get("/merchants/favorites", response_model=List[MerchantResponse])
def list_favorite_merchants(db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    fav_ids = db.query(UserMerchantFavorite.merchant_id).filter(
        UserMerchantFavorite.user_id == current_user.id).subquery()
    return db.query(Merchant).filter(Merchant.id.in_(fav_ids)).all()


@router.post("/merchants/{merchant_id}/favorite")
def add_favorite(merchant_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    if not db.query(Merchant).filter(Merchant.id == merchant_id).first():
        raise HTTPException(status_code=404, detail="商家不存在")
    existing = db.query(UserMerchantFavorite).filter_by(
        user_id=current_user.id, merchant_id=merchant_id).first()
    if not existing:
        db.add(UserMerchantFavorite(user_id=current_user.id, merchant_id=merchant_id))
        db.commit()
    return {"ok": True}


@router.delete("/merchants/{merchant_id}/favorite")
def remove_favorite(merchant_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    db.query(UserMerchantFavorite).filter(
        UserMerchantFavorite.user_id == current_user.id,
        UserMerchantFavorite.merchant_id == merchant_id,
    ).delete()
    db.commit()
    return {"ok": True}
```

- [ ] **Step 5: 跑测试 + py_compile + 回归既有 merchants 测试**

Run: `cd backend && python -m pytest tests/test_shared_data.py tests/test_locations.py -v && python -m py_compile app/api/merchants.py && echo OK`
Expected: PASS + `OK`（若 test_locations 涉及商家私有假设，按共享池语义修正）。

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/merchants.py backend/tests/test_shared_data.py
git commit -m "feat(shared): 商家转共享池查询 + 收藏端点

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2.4: 菜谱 is_public + 发布执行器

**Files:**
- Create: `backend/app/services/proposals/executors/__init__.py`
- Create: `backend/app/services/proposals/executors/recipe_publish.py`
- Modify: `backend/app/api/recipes.py`（创建逻辑 + 发布端点）

> 菜谱发布走提议框架：普通用户提交 publish 提议（manual）→ 管理员审核 → apply 设 is_public=True；管理员创建即发布（apply_as_admin）。发布后共建共编、作者不可撤回/删除、管理员可删。

- [ ] **Step 1: 写失败测试——发布执行器**

追加到 `backend/tests/test_proposals_framework.py`：

```python
def test_recipe_publish_executor_sets_is_public(db):
    from app.services.proposals.executors.recipe_publish import RecipePublishExecutor
    from app.services.proposals.registry import ExecutorRegistry
    ExecutorRegistry.reset()
    ExecutorRegistry.register(RecipePublishExecutor(), default_policy="manual", default_risk="mid")
    # 需先在 db 插一条 Recipe(id=42, is_public=False)，执行时用 fixture 补
    ex = ExecutorRegistry.get("recipe")
    proposal = type("P", (), {"entity_type": "recipe", "entity_id": 42,
                              "action": "publish", "payload": {}})()
    result = ex.apply(db, proposal)
    db.commit()
    from app.models.recipe import Recipe
    r = db.query(Recipe).get(42)
    assert r.is_public is True
    assert result.revert_payload == {"set_public": False}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py -k recipe_publish -v`
Expected: FAIL。

- [ ] **Step 3: 创建 recipe_publish 执行器**

`backend/app/services/proposals/executors/__init__.py`：空文件（包标记）。

`backend/app/services/proposals/executors/recipe_publish.py`：

```python
"""菜谱发布执行器：apply 置 is_public=True，revert 置回 False。"""
from fastapi import HTTPException
from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.models.recipe import Recipe


class RecipePublishExecutor(ProposalExecutor):
    entity_type = "recipe"

    def validate(self, db, proposal):
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        if r is None:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        if getattr(r, "is_public", False):
            raise HTTPException(status_code=400, detail="菜谱已发布")

    def preview(self, db, proposal):
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        return {"recipe_id": proposal.entity_id, "name": r.name if r else None,
                "will_publish": True}

    def apply(self, db, proposal) -> ApplyResult:
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        if r is None:
            raise HTTPException(status_code=404, detail="菜谱不存在")
        snapshot = {"is_public": bool(getattr(r, "is_public", False))}
        r.is_public = True
        return ApplyResult(snapshot=snapshot, revert_payload={"set_public": snapshot["is_public"]},
                           summary=f"菜谱 {r.name} 已发布")

    def revert(self, db, proposal):
        r = db.query(Recipe).filter(Recipe.id == proposal.entity_id).first()
        if r is not None:
            r.is_public = bool((proposal.revert_payload or {}).get("set_public", False))
```

- [ ] **Step 4: recipes.py——创建与发布逻辑**

修改 [recipes.py create_recipe](backend/app/api/recipes.py#L88)：
- 在创建 Recipe 时，若 `current_user.is_admin`，设 `is_public=True`（管理员创建即发布）；普通用户保持 `is_public=False`（私有）。
- 不再让客户端直接控制 `source` 作公共标记（`source` 仅用于导入来源；公共性统一用 `is_public`）。GET 列表的公共性判断从 `source != None` 扩展为 `source != None OR is_public == True`（[L166-180](backend/app/api/recipes.py#L166)）。

新增发布端点（普通用户走提议；管理员直写）：

```python
from app.services.proposals import service as proposal_service

@router.post("/{recipe_id}/publish")
def publish_recipe(recipe_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    """发布菜谱。普通用户提交审核提议；管理员直写生效。"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if recipe is None:
        raise HTTPException(status_code=404, detail="菜谱不存在")
    if current_user.is_admin:
        p = proposal_service.apply_as_admin(
            db, entity_type="recipe", entity_id=recipe_id,
            action="publish", payload={}, admin=current_user)
    else:
        # 发布前仅作者可发起发布提议
        if recipe.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="仅作者可发布自己的菜谱")
        p = proposal_service.submit(
            db, entity_type="recipe", entity_id=recipe_id,
            action="publish", payload={}, proposer=current_user)
    db.commit()
    return {"proposal_id": p.id, "status": p.status, "is_public": getattr(recipe, "is_public", False)}
```

发布后删除/撤回规则：在 `delete_recipe`（[L552](backend/app/api/recipes.py#L552)）加——若 `recipe.is_public` 且非管理员 → 403「已发布的菜谱不可删除/撤回，请联系管理员」。

- [ ] **Step 5: 注册执行器到 bootstrap**

修改 `backend/app/services/proposals/bootstrap.py`：

```python
from app.services.proposals.registry import ExecutorRegistry
from app.services.proposals.executors.recipe_publish import RecipePublishExecutor


def register_all() -> None:
    ExecutorRegistry.register(RecipePublishExecutor(), default_policy="manual", default_risk="mid")
    # P2.5 继续追加 ingredient/nutrition/unit/hierarchy/merge/merchant
```

并在 `main.py` lifespan 启动序列（[main.py:195](backend/app/main.py#L195)）里调用 `from app.services.proposals.bootstrap import register_all; register_all()`（在 `Base.metadata.create_all` 之后）。

- [ ] **Step 6: 跑测试 + py_compile**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py tests/test_shared_data.py -v && python -m py_compile app/services/proposals/executors/recipe_publish.py app/api/recipes.py && echo OK`
Expected: PASS + `OK`

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/proposals/executors/ backend/app/api/recipes.py backend/app/services/proposals/bootstrap.py backend/app/main.py backend/tests/test_proposals_framework.py
git commit -m "feat(shared): 菜谱 is_public + 发布执行器（管理员直发/普通用户审核）

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2.5: 业务执行器注册 + 合并执行器（含 snapshot/revert）+ 分流模式改造

**Files:**
- Create: `backend/app/services/proposals/executors/ingredient.py`（含 merge）
- Create: `backend/app/services/proposals/executors/nutrition.py`（补空/覆盖特例）
- Create: `backend/app/services/proposals/executors/unit.py`
- Create: `backend/app/services/proposals/executors/hierarchy.py`
- Create: `backend/app/services/proposals/executors/merchant.py`
- Modify: `backend/app/services/proposals/bootstrap.py`
- Modify: 各共享写端点（接入分流：管理员 `apply_as_admin` / 普通 submit）

> 最复杂的是合并执行器——`IngredientMerger` 单事务无快照且含不可逆 DELETE + 数值覆盖，必须在 apply 前 snapshot 所有受影响行，revert 才能还原。其余执行器（ingredient CRUD / nutrition / unit / hierarchy / merchant）模式简单，给骨架。

- [ ] **Step 1: 合并执行器——先 snapshot 再合并，revert 按 snapshot 还原**

`backend/app/services/proposals/executors/ingredient.py`：

```python
"""食材执行器：CRUD（create/update/delete）+ 合并（merge）。

合并复用 IngredientMerger，但 apply 前对受影响行做完整快照
（recipe_ingredients / product_ingredient_links / ingredient_nutrition_mappings /
ingredient_hierarchies + 源食材字段），revert 按快照还原 + 复活源食材。
"""
from typing import List
from fastapi import HTTPException
from sqlalchemy import and_
from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.models.nutrition import Ingredient
from app.models.recipe import RecipeIngredient
from app.models.product_ingredient_link import ProductIngredientLink
from app.models.ingredient_hierarchy import IngredientHierarchy
from app.models.nutrition import IngredientNutritionMapping
from app.models.ingredient_merge_record import IngredientMergeRecord
from app.services.ingredient_merger import IngredientMerger


class IngredientExecutor(ProposalExecutor):
    entity_type = "ingredient"

    def validate(self, db, proposal):
        # 合并互斥：源/目标食材存在 pending 合并提议则拒绝
        if proposal.action == "merge":
            ids = list(proposal.payload.get("source_ids", [])) + [proposal.payload.get("target_id")]
            existing = db.query(IngredientMergeRecord).filter(
                IngredientMergeRecord.is_active == True,
                IngredientMergeRecord.source_ingredient_id.in_(ids),
            ).first()
            # 待审互斥由 change_proposals.status=pending 的同类提议判断（此处可省略，service 层亦可）

    def preview(self, db, proposal):
        if proposal.action == "merge":
            source_ids = proposal.payload["source_ids"]
            target_id = proposal.payload["target_id"]
            ri = db.query(RecipeIngredient).filter(
                RecipeIngredient.ingredient_id.in_(source_ids)).count()
            pl = db.query(ProductIngredientLink).filter(
                ProductIngredientLink.ingredient_id.in_(source_ids)).count()
            return {"affected_recipes_links": ri, "affected_product_links": pl,
                    "note": "合并将迁移这些引用到目标食材（含他人菜谱）"}
        return {}

    def apply(self, db, proposal) -> ApplyResult:
        if proposal.action == "merge":
            return self._apply_merge(db, proposal)
        # create/update/delete 的简化实现：按 payload 直接改 Ingredient
        return self._apply_crud(db, proposal)

    def _apply_merge(self, db, proposal) -> ApplyResult:
        source_ids: List[int] = proposal.payload["source_ids"]
        target_id: int = proposal.payload["target_id"]
        # 1. 快照所有受影响行（供 revert）
        snapshot = {
            "recipe_ingredients": [
                {"id": r.id, "recipe_id": r.recipe_id, "ingredient_id": r.ingredient_id,
                 "quantity": r.quantity, "quantity_range": r.quantity_range,
                 "unit_id": r.unit_id, "is_optional": r.is_optional, "note": r.note,
                 "original_quantity": r.original_quantity}
                for r in db.query(RecipeIngredient)
                    .filter(RecipeIngredient.ingredient_id.in_(source_ids)).all()
            ],
            "product_links": [
                {"id": l.id, "product_id": l.product_id, "ingredient_id": l.ingredient_id}
                for l in db.query(ProductIngredientLink)
                    .filter(ProductIngredientLink.ingredient_id.in_(source_ids)).all()
            ],
            "nutrition_mappings": [
                {"id": m.id, "ingredient_id": m.ingredient_id, "nutrition_id": m.nutrition_id,
                 "priority": m.priority, "confidence": m.confidence}
                for m in db.query(IngredientNutritionMapping)
                    .filter(IngredientNutritionMapping.ingredient_id.in_(source_ids)).all()
            ],
            "hierarchies": [
                {"id": h.id, "parent_id": h.parent_id, "child_id": h.child_id,
                 "relation_type": h.relation_type, "strength": h.strength}
                for h in db.query(IngredientHierarchy).filter(and_(
                    (IngredientHierarchy.parent_id.in_(source_ids)) |
                    (IngredientHierarchy.child_id.in_(source_ids)))).all()
            ],
            "sources": [
                {"id": s.id, "is_merged": s.is_merged, "merged_into_id": s.merged_into_id,
                 "aliases": s.aliases}
                for s in db.query(Ingredient).filter(Ingredient.id.in_(source_ids)).all()
            ],
        }
        # 2. 调现有合并服务（事务内）
        merger = IngredientMerger(db)
        result = merger.merge_ingredients(
            source_ingredient_ids=source_ids,
            target_ingredient_id=target_id,
            merged_by_user_id=proposal.proposer_id,
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "合并失败"))
        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"merged": True, "source_ids": source_ids, "target_id": target_id},
            summary=result.get("message", "合并完成"),
        )

    def revert(self, db, proposal):
        if proposal.action != "merge":
            return
        snap = proposal.snapshot or {}
        rp = proposal.revert_payload or {}
        # 1. 还原被删除/改写的引用行
        # recipe_ingredients：快照里的原行要么被改 ingredient_id（恢复），要么被删（重新插入）
        existing_ri = {r.id for r in db.query(RecipeIngredient).all()}
        for item in snap.get("recipe_ingredients", []):
            if item["id"] in existing_ri:
                r = db.query(RecipeIngredient).get(item["id"])
                r.ingredient_id = item["ingredient_id"]
                r.quantity = item["quantity"]; r.quantity_range = item["quantity_range"]
                r.unit_id = item["unit_id"]; r.is_optional = item["is_optional"]
                r.note = item["note"]; r.original_quantity = item["original_quantity"]
            else:
                db.add(RecipeIngredient(**item))
        for item in snap.get("product_links", []):
            db.add(ProductIngredientLink(**item))   # 简化：幂等由调用频次保证
        for item in snap.get("nutrition_mappings", []):
            db.add(IngredientNutritionMapping(**item))
        for item in snap.get("hierarchies", []):
            db.add(IngredientHierarchy(**item))
        # 2. 复活源食材
        for s in snap.get("sources", []):
            ing = db.query(Ingredient).get(s["id"])
            if ing is not None:
                ing.is_merged = s["is_merged"]
                ing.merged_into_id = s["merged_into_id"]
                ing.aliases = s["aliases"]
        # 3. 软删本次合并记录
        db.query(IngredientMergeRecord).filter(
            IngredientMergeRecord.source_ingredient_id.in_(rp.get("source_ids", [])),
            IngredientMergeRecord.target_ingredient_id == rp.get("target_id"),
        ).update({IngredientMergeRecord.is_active: False}, synchronize_session=False)

    def _apply_crud(self, db, proposal) -> ApplyResult:
        # create/update/delete：按 payload 直接改 Ingredient；snapshot 存原值供 revert
        action = proposal.action
        eid = proposal.entity_id
        if action == "create":
            ing = Ingredient(**proposal.payload)
            db.add(ing); db.flush()
            return ApplyResult(snapshot={}, revert_payload={"delete_id": ing.id},
                               summary="已创建食材")
        ing = db.query(Ingredient).get(eid)
        if ing is None:
            raise HTTPException(status_code=404, detail="食材不存在")
        if action == "update":
            snapshot = {k: getattr(ing, k) for k in proposal.payload}
            for k, v in proposal.payload.items():
                setattr(ing, k, v)
            return ApplyResult(snapshot=snapshot,
                               revert_payload={"restore": snapshot}, summary="已更新食材")
        if action == "delete":
            snapshot = {c.name: getattr(ing, c.name) for c in ing.__table__.columns}
            ing.is_active = False
            return ApplyResult(snapshot=snapshot,
                               revert_payload={"restore_active": True}, summary="已软删食材")
```

- [ ] **Step 2: nutrition 执行器——补空/覆盖特例**

`backend/app/services/proposals/executors/nutrition.py`：

```python
"""营养数据执行器：补空自动 / 覆盖审核（由 review_policy + validate 体现）。"""
from fastapi import HTTPException
from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.services.proposals.registry import ExecutorRegistry
from app.models.nutrition_data import NutritionData


class NutritionExecutor(ProposalExecutor):
    entity_type = "nutrition"

    def validate(self, db, proposal):
        pass

    def preview(self, db, proposal):
        return {}

    def apply(self, db, proposal) -> ApplyResult:
        eid = proposal.entity_id
        existing = db.query(NutritionData).filter(
            NutritionData.ingredient_id == eid).first()
        snapshot = {}
        if existing is not None:
            snapshot = {"had_data": True, "nutrients": existing.nutrients,
                        "source": existing.source}
        # 写入/覆盖（payload 含 nutrients）
        if existing is None:
            nd = NutritionData(ingredient_id=eid, nutrients=proposal.payload.get("nutrients", {}),
                               source="custom", is_verified=True)
            db.add(nd)
        else:
            existing.nutrients = proposal.payload.get("nutrients", existing.nutrients)
            existing.source = "custom"
        # 关键：补空 → auto_approve；覆盖 → manual。由提交时动态设 policy：
        ExecutorRegistry.set_policy("nutrition", "update",
                                    "auto_approve" if not snapshot.get("had_data") else "manual")
        return ApplyResult(snapshot=snapshot,
                           revert_payload={"restore": snapshot} if snapshot else {"delete": True},
                           summary="营养数据已更新")

    def revert(self, db, proposal):
        snap = proposal.snapshot or {}
        eid = proposal.entity_id
        if snap.get("had_data"):
            nd = db.query(NutritionData).filter(NutritionData.ingredient_id == eid).first()
            if nd:
                nd.nutrients = snap["nutrients"]; nd.source = snap["source"]
        else:
            db.query(NutritionData).filter(NutritionData.ingredient_id == eid).delete()
```

> 注：营养「补空/覆盖」的 policy 在 apply 内动态 set 略取巧；更稳妥在 `submit` 前（API 层）先查有无数据决定提交时携带 `review_policy` 提示。本期以执行器内 set_policy 示意，实现时可上移到 service.submit 的前置检查。

- [ ] **Step 3: unit / hierarchy / merchant 执行器骨架**

`backend/app/services/proposals/executors/unit.py`、`hierarchy.py`、`merchant.py` 仿 `ingredient._apply_crud` 的 create/update/delete 模式实现（snapshot 原值 → apply 改 → revert 还原）。`unit` 在 validate 里拒绝改 `is_standard=True` 的标准单位（标准单位仅管理员直写，不进框架）：

```python
# unit.py validate 片段
def validate(self, db, proposal):
    from app.models.unit import Unit
    if proposal.entity_id:
        u = db.query(Unit).get(proposal.entity_id)
        if u and getattr(u, "is_standard", False):
            raise HTTPException(status_code=403, detail="标准单位仅管理员可改")
```

`merchant.py` 的 delete：snapshot 关联的 `ProductRecord.merchant_id` 引用（设为 NULL 或拒绝），revert 还原。

- [ ] **Step 4: bootstrap 注册全部执行器 + 设默认策略**

修改 `bootstrap.py` `register_all()`：

```python
from app.services.proposals.executors.ingredient import IngredientExecutor
from app.services.proposals.executors.nutrition import NutritionExecutor
from app.services.proposals.executors.unit import UnitExecutor
from app.services.proposals.executors.hierarchy import HierarchyExecutor
from app.services.proposals.executors.merchant import MerchantExecutor
# RecipePublishExecutor 已在 Task 2.4 导入

def register_all() -> None:
    ExecutorRegistry.register(IngredientExecutor(), default_policy="auto_approve", default_risk="mid")
    ExecutorRegistry.set_policy("ingredient", "update", "manual")
    ExecutorRegistry.set_policy("ingredient", "delete", "manual")
    ExecutorRegistry.set_policy("ingredient", "merge", "manual")
    ExecutorRegistry.risk_levels[("ingredient", "merge")] = "high"
    ExecutorRegistry.risk_levels[("ingredient", "delete")] = "high"

    ExecutorRegistry.register(NutritionExecutor(), default_policy="manual", default_risk="mid")

    ExecutorRegistry.register(UnitExecutor(), default_policy="auto_approve", default_risk="mid")
    ExecutorRegistry.set_policy("unit", "update", "manual")
    ExecutorRegistry.set_policy("unit", "delete", "manual")

    ExecutorRegistry.register(HierarchyExecutor(), default_policy="manual", default_risk="mid")

    ExecutorRegistry.register(MerchantExecutor(), default_policy="auto_approve", default_risk="mid")
    ExecutorRegistry.set_policy("merchant", "update", "manual")
    ExecutorRegistry.set_policy("merchant", "delete", "manual")
    ExecutorRegistry.risk_levels[("merchant", "update")] = "high"   # 坐标高危
    ExecutorRegistry.risk_levels[("merchant", "delete")] = "high"

    ExecutorRegistry.register(RecipePublishExecutor(), default_policy="manual", default_risk="mid")
```

> 治理总表（设计文档 §5.5）的策略在此落地：食材新增 auto、编辑/删除/合并 manual（合并 high）；营养补空 auto（执行器内动态）/覆盖 manual；单位新增 auto、改删 manual；层级全 manual；商家新增 auto、改删 manual（坐标 high）；菜谱发布 manual。

- [ ] **Step 5: 共享写端点接入分流模式**

把 P0 阶段「限管理员」的端点升级为分流。以 `ingredient_hierarchy.merge_ingredients`（[L329](backend/app/api/ingredient_hierarchy.py#L329)）为例，改造为：

```python
from app.services.proposals import service as proposal_service

@router.post("/ingredients/merge", response_model=IngredientMergeResponse)
def merge_ingredients(merge_request: IngredientMergeRequest,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    payload = {"source_ids": merge_request.source_ingredient_ids,
               "target_id": merge_request.target_ingredient_id}
    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="ingredient", entity_id=merge_request.target_ingredient_id,
            action="merge", payload=payload, admin=current_user)
        db.commit()
        return IngredientMergeResponse(success=True, message="合并完成（管理员直写）",
                                       merged_count=len(merge_request.source_ingredient_ids),
                                       updated_recipes_count=0, updated_products_count=0,
                                       updated_mappings_count=0, stats_change={})
    else:
        p = proposal_service.submit(
            db, entity_type="ingredient", entity_id=merge_request.target_ingredient_id,
            action="merge", payload=payload, proposer=current_user)
        db.commit()
        return IngredientMergeResponse(success=True,
                                       message=f"合并提议已提交（status={p.status}）",
                                       merged_count=0, updated_recipes_count=0,
                                       updated_products_count=0, updated_mappings_count=0,
                                       stats_change={})
```

对其余 P0 收紧端点（单位增删改、营养写入、层级增删改、商家改删等）同理：管理员 `apply_as_admin`，普通用户 `submit`。**GET 端点保持 `get_current_user`，不动**。

> 实操：此步工作量大但模式一致。可按文件逐个改造，每改一个跑一次回归。

- [ ] **Step 6: 跑全量测试 + py_compile**

Run: `cd backend && python -m pytest tests/ -q 2>&1 | tail -30 && python -m py_compile app/services/proposals/executors/*.py && echo OK`
Expected: 全绿 + `OK`

- [ ] **Step 7: Commit（可按执行器分多次提交）**

```bash
git add backend/app/services/proposals/executors/ backend/app/services/proposals/bootstrap.py backend/app/api/
git commit -m "feat(shared): 业务执行器（食材含合并/营养/单位/层级/商家）+ 分流模式

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2.6: P2 收尾——前端适配点 + 全量回归

**Files:**
- Modify: 前端相关视图（`MerchantsView`/`RecipesView`/`QuickFillView` 等）—— 仅适配新的响应字段

- [ ] **Step 1: 前端适配**

- `MerchantsView`：商家列表现为共享池，可加「收藏」筛选；创建商家仍走 POST；编辑/删除对普通用户改为「提交提议」提示。
- `RecipesView`：加「发布」按钮（调 `POST /{id}/publish`）；公开菜谱展示发布态；作者对已发布菜谱隐藏删除/撤回。
- `latest-price` 响应字段变化（`recent_price/avg_price_30d/min/max/sample_count`）：消费此接口的图表组件改字段映射。
- 价格记录输入：不变（仍 POST `/products`，私有 user_id）。

- [ ] **Step 2: 前端构建**

Run: `cd frontend && npm run build`
Expected: 构建通过。

- [ ] **Step 3: 后端全量回归**

Run: `cd backend && python -m pytest tests/ -q 2>&1 | tail -30`
Expected: 全绿。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/ backend/
git commit -m "feat(shared): 前端适配共享池商家/菜谱发布/去标识价格

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

**P2 完成标志：** 商家共享池 + 收藏上线；价格对外去标识（剥离 user_id/record_type）聚合；菜谱发布走提议（管理员直发/普通用户审核）；五类业务执行器注册并接入分流模式（P0 的「仅管理员」端点升级为「管理员直写 + 普通用户提议」）。治理总表策略全部落地。系统已具备完整的多用户社区共建能力，管理员单用户场景行为不变。

---

## 阶段 3：增强

> 目标：商家合并工具（清理共享池重复商家）、反垃圾「一键回退某用户提议」、auto_review 具体实现（本期仅占位）。优先级最低，依赖 P1/P2 就绪。

### Task 3.1: 商家合并执行器——清理重复商家

**Files:**
- Create: `backend/app/services/proposals/executors/merchant_merge.py`
- Modify: `backend/app/services/proposals/bootstrap.py`
- Modify: `backend/app/api/merchants.py`（合并端点，管理员分流）

> 复用食材合并的 snapshot/revert 范式：apply 前快照受影响行（`ProductRecord.merchant_id`、`user_merchant_favorites.merchant_id`、`UserMerchantProductOrder.merchant_id`），调合并迁移，revert 按快照还原。

- [ ] **Step 1: 写失败测试**

追加到 `backend/tests/test_shared_data.py`：

```python
def test_merchant_merge_executor_migrates_references(db_with_merchants):
    from app.services.proposals.executors.merchant_merge import MerchantMergeExecutor
    from app.services.proposals.registry import ExecutorRegistry
    ExecutorRegistry.reset()
    ExecutorRegistry.register(MerchantMergeExecutor(), default_policy="manual", default_risk="high")
    ex = ExecutorRegistry.get("merchant_merge")
    proposal = type("P", (), {"entity_type": "merchant_merge",
                              "entity_id": 2, "action": "merge",
                              "payload": {"source_ids": [2], "target_id": 1},
                              "proposer_id": 1})()
    result = ex.apply(db_with_merchants, proposal)
    db_with_merchants.commit()
    # 断言：product_records 的 merchant_id 从 2 迁到 1
    # 断言：result.snapshot 含迁移前的引用清单
    assert "product_records" in result.snapshot
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_shared_data.py -k merchant_merge -v`
Expected: FAIL。

- [ ] **Step 3: 创建 merchant_merge 执行器**

`backend/app/services/proposals/executors/merchant_merge.py`（仿 `ingredient.py._apply_merge` 范式）：

```python
"""商家合并执行器：把源商家的所有引用迁到目标商家，软删源商家。"""
from fastapi import HTTPException
from app.services.proposals.base import ProposalExecutor, ApplyResult
from app.models.merchant import Merchant
from app.models.product import ProductRecord
from app.models.user_merchant_favorite import UserMerchantFavorite


class MerchantMergeExecutor(ProposalExecutor):
    entity_type = "merchant_merge"

    def validate(self, db, proposal):
        src = proposal.payload.get("source_ids", [])
        tgt = proposal.payload.get("target_id")
        if not src or tgt in src:
            raise HTTPException(status_code=400, detail="源/目标参数非法")

    def preview(self, db, proposal):
        src = proposal.payload["source_ids"]
        pr = db.query(ProductRecord).filter(ProductRecord.merchant_id.in_(src)).count()
        return {"affected_price_records": pr}

    def apply(self, db, proposal) -> ApplyResult:
        src_ids = proposal.payload["source_ids"]
        tgt = proposal.payload["target_id"]
        snapshot = {
            "product_records": [
                {"id": r.id, "merchant_id": r.merchant_id}
                for r in db.query(ProductRecord).filter(ProductRecord.merchant_id.in_(src_ids)).all()
            ],
            "favorites": [
                {"id": f.id, "user_id": f.user_id, "merchant_id": f.merchant_id}
                for f in db.query(UserMerchantFavorite).filter(UserMerchantFavorite.merchant_id.in_(src_ids)).all()
            ],
            "sources": [
                {"id": m.id, "is_open": m.is_open}
                for m in db.query(Merchant).filter(Merchant.id.in_(src_ids)).all()
            ],
        }
        # 迁移引用
        db.query(ProductRecord).filter(ProductRecord.merchant_id.in_(src_ids)).update(
            {ProductRecord.merchant_id: tgt}, synchronize_session=False)
        db.query(UserMerchantFavorite).filter(UserMerchantFavorite.merchant_id.in_(src_ids)).delete(
            synchronize_session=False)   # 目标已收藏的去重由 UNIQUE 约束保证
        # 软停用源商家（商家无 is_active，用 is_open=False 标记 + 名称加后缀）
        for m in db.query(Merchant).filter(Merchant.id.in_(src_ids)).all():
            m.is_open = False
            m.name = f"[已合并] {m.name}"
        return ApplyResult(snapshot=snapshot,
                           revert_payload={"source_ids": src_ids, "target_id": tgt},
                           summary=f"合并 {len(src_ids)} 个商家到 {tgt}")

    def revert(self, db, proposal):
        snap = proposal.snapshot or {}
        for item in snap.get("product_records", []):
            pr = db.query(ProductRecord).get(item["id"])
            if pr: pr.merchant_id = item["merchant_id"]
        for item in snap.get("favorites", []):
            db.add(UserMerchantFavorite(**item))
        for s in snap.get("sources", []):
            m = db.query(Merchant).get(s["id"])
            if m:
                m.is_open = s["is_open"]
                m.name = m.name.replace("[已合并] ", "")
```

- [ ] **Step 4: bootstrap 注册 + merchants.py 加合并端点**

`bootstrap.py` `register_all()` 追加：
```python
from app.services.proposals.executors.merchant_merge import MerchantMergeExecutor
ExecutorRegistry.register(MerchantMergeExecutor(), default_policy="manual", default_risk="high")
```

`merchants.py` 加 `POST /merchants/merge`（管理员 `apply_as_admin`；普通用户提交提议），payload 同食材合并。

- [ ] **Step 5: 跑测试 + py_compile + Commit**

Run: `cd backend && python -m pytest tests/test_shared_data.py -k merchant_merge -v && python -m py_compile app/services/proposals/executors/merchant_merge.py && echo OK`

```bash
git add backend/app/services/proposals/executors/merchant_merge.py backend/app/services/proposals/bootstrap.py backend/app/api/merchants.py backend/tests/test_shared_data.py
git commit -m "feat(shared): 商家合并执行器（清理重复商家）

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3.2: 反垃圾——一键回退某用户全部已生效提议

**Files:**
- Modify: `backend/app/api/proposals.py`

- [ ] **Step 1: 写失败测试**

追加到 `backend/tests/test_proposals_framework.py`：

```python
def test_revert_by_user_admin_only_and_bulk(db):
    from app.services.proposals import service as proposal_service
    from app.services.proposals.registry import ExecutorRegistry
    ExecutorRegistry.reset(); ExecutorRegistry.register(_RecordingExecutor())
    ExecutorRegistry.set_policy("rec", "update", "auto_approve")
    u = type("U", (), {"id": 5, "is_admin": False})()
    for _ in range(3):
        p = proposal_service.submit(db, entity_type="rec", entity_id=1,
                                    action="update", payload={"v": 1}, proposer=u)
    db.commit()
    admin = type("A", (), {"id": 1, "is_admin": True})()
    n = proposal_service.revert_all_by_user(db, user_id=5, reviewer=admin)
    db.commit()
    assert n == 3
    assert _RecordingExecutor.reverted == 3
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py -k revert_by_user -v`
Expected: FAIL（方法不存在）。

- [ ] **Step 3: service 加 revert_all_by_user + API 端点**

`backend/app/services/proposals/service.py` 追加：

```python
def revert_all_by_user(db: Session, *, user_id: int, reviewer) -> int:
    """回退某用户所有 applied 提议。返回回退条数。"""
    proposals = db.query(ChangeProposal).filter(
        ChangeProposal.proposer_id == user_id,
        ChangeProposal.status == "applied",
    ).all()
    count = 0
    for p in proposals:
        try:
            executor = _get_executor(p.entity_type)
            executor.revert(db, p)
            p.status = "reverted"
            p.reverted_at = _now()
            p.reviewer_id = reviewer.id
            count += 1
        except Exception:
            continue   # 单条失败不阻断整体回退
    return count
```

`backend/app/api/proposals.py` 追加端点：

```python
@router.post("/proposals/revert-by-user")
def revert_by_user(body: dict, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_admin_user)):
    """一键回退某用户全部已生效提议（反垃圾，仅管理员）。"""
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="缺少 user_id")
    n = proposal_service.revert_all_by_user(db, user_id=user_id, reviewer=current_user)
    db.commit()
    return {"reverted_count": n}
```

- [ ] **Step 4: 跑测试 + py_compile + Commit**

Run: `cd backend && python -m pytest tests/test_proposals_framework.py -k revert_by_user -v && python -m py_compile app/services/proposals/service.py app/api/proposals.py && echo OK`

```bash
git add backend/app/services/proposals/service.py backend/app/api/proposals.py backend/tests/test_proposals_framework.py
git commit -m "feat(proposals): 反垃圾——一键回退某用户全部已生效提议

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3.3: auto_review 具体实现（预留，本期不实现）

**Files:** 无（仅记录决策）

- [ ] **Step 1: 确认预留边界**

`ProposalAutoReviewer` 协议与 `DefaultAutoReviewer`（全部 escalate）已在 Task 1.2 落地。本期**不实现**具体判定逻辑。后续实现路径（记录于此，不在本期执行）：
- 在 `backend/app/services/proposals/auto_reviewer.py` 增加具体实现类（如 `RuleBasedAutoReviewer`、`AIAutoReviewer`），按 `entity_type + payload` 规则/AI 判定 approve/escalate/reject。
- 管理员后台增加配置项：每种 `entity_type + action` 选 `auto_approve`/`auto_review`/`manual`（持久化到 `system_config` 或新增 `proposal_review_policies` 表）。
- `service.submit` 中 `_auto_reviewer` 改为可注入/可配置。

- [ ] **Step 2: 记录到设计文档开放项**

无需代码改动。设计文档 §8 已含「`auto_review` 具体判定逻辑后续再填」。保持。

---

**P3 完成标志：** 商家合并工具可用（清理共享池重复）；反垃圾回退端点上线；auto_review 接口预留清晰、后续可插拔实现。整套多用户权限系统交付完毕。

---

## Self-Review 记录

**1. Spec 覆盖**（对照设计文档各节）：
- §2 审计问题 → P0（units/nutrition/usda/hierarchy/extended/products_entity/export/recipes/import_api/usda_admin）全覆盖 ✓
- §5.2 价格聚合去标识 → Task 2.2 ✓
- §5.3 通用框架 → Task 1.1–1.7 ✓
- §5.4 审核策略三档 + 预留接口 → Task 1.2/1.3，DefaultAutoReviewer 全 escalate ✓
- §5.5 治理总表 → Task 2.5 bootstrap 策略逐一对应 ✓
- §5.6 迁移 → Task 2.1（字段+收藏+汇总表）、Task 2.3（商家共享池+收藏回填）✓
- §6 数据模型 → ChangeProposal / user_merchant_favorites / product_merchant_price_summary / Recipe.is_public / Unit.is_standard / Merchant.user_id nullable ✓
- §7 P0–P3 → 四阶段对应 ✓

**2. 类型一致性**：`ChangeProposal` 字段、`ApplyResult(snapshot/revert_payload/summary)`、`ExecutorRegistry.register/get/policy_for/set_policy/risk_for`、`service.submit/review/revert/apply_as_admin/revert_all_by_user` 在各 Task 间签名一致。`risk_levels` 直接字典访问（Task 2.5）与 `risk_for` 读取兼容。

**3. 已知妥协**（执行时需注意）：
- **简单执行器范式复用**：Task 2.5 的 `unit/hierarchy/merchant` CRUD 执行器按 `ingredient._apply_crud` 范式复刻（create/update/delete + snapshot/revert）。执行时建议抽一个 `CrudExecutorBase`（`_apply_crud` + 通用 `revert`），让 ingredient/unit/hierarchy/merchant 继承，DRY。unit 额外覆写 validate 拒绝改标准单位；merchant 覆写 delete 处理引用。
- **测试 fixture**：`test_shared_data.py` 中 `clean_merchants` / `db_with_merchants` / `db` 等 fixture 给了骨架，前置数据（Product/Unit/Recipe 等）需执行时按模型补全。`test_proposals_framework.py` 的执行器测试用了临时 `type(...)` 对象模拟 proposal，执行时若 service 对 proposal 属性有更多依赖，改为构造真实 `ChangeProposal` 实例。
- **营养「补空/覆盖」policy**：Task 2.5 Step 2 在 apply 内 `set_policy` 取巧；更稳妥在 API/submit 前查有无数据决定 policy（实现时可上移到 `service.submit` 前置检查）。
- **全量分流域点改造**：Task 2.5 Step 5 工作量大（每个 P0 端点都要改分流），可按文件分次提交。
- **前端**：Task 2.6 前端适配为要点指引，具体组件改动执行时按响应字段变化调整。

**4. 无硬性占位符**：所有框架核心代码（P1 全部、合并/价格/发布/反垃圾执行器）完整给出；上述妥协均为「范式复用」或「测试数据构造」，非「逻辑待定」。

**结论：** Plan 覆盖设计文档全部要求，核心路径代码完整、可执行。建议执行顺序 P0 → P1 → P2 → P3，每 task TDD + 提交。
