# 原料/商品 改删 + 层级提示 接入提议-审核框架 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 放开原料/商品的 update+delete 给普通用户走提议-审核框架（全 manual + 管理员直写即时生效 + delete 完整反级联），并修复食材层级关系前端提示（按角色区分）。

**Architecture:** 新建 ProductExecutor（delete 覆写级联 ProductRecord）；IngredientExecutor 覆写 delete 加级联（Product + Hierarchy）；4 个端点去 created_by 限制改分流；前端 6 处提示按角色。

**Tech Stack:** FastAPI + SQLAlchemy；Vue 3 + Vuetify。

**项目约束（务必遵守）：**
- **不主动 `git commit` / 开分支**（项目 CLAUDE.md）。每任务以测试通过 + `py_compile` / `npm run build` 为准。
- 不启动服务、不改数据库（本计划无表结构变更——Product/Ingredient/ProductRecord/IngredientHierarchy 都已有 is_active）。
- 后端用 `.venv`（uv 管理），命令用 Bash 工具（`cd /d/code/live_calc/backend && ...`）。
- 设计依据：[../specs/2026-06-30-ingredient-product-proposals-design.md](../specs/2026-06-30-ingredient-product-proposals-design.md)

---

## File Structure

### 后端新增
- `backend/app/services/proposals/executors/product.py` — `ProductExecutor`（继承 CrudExecutorBase，delete 覆写级联 ProductRecord）
- `backend/tests/test_product_ingredient_proposals.py` — 端点分流 + 执行器级联集成测试

### 后端修改
- `backend/app/services/proposals/executors/ingredient.py` — delete 覆写加级联（Product + Hierarchy + 菜谱检查）
- `backend/app/services/proposals/bootstrap.py` — 注册 ProductExecutor（全 manual）
- `backend/app/api/ingredient_extended.py` — 原料 update 分流（L527）
- `backend/app/api/nutrition.py` — 原料 delete 分流（L531，前端实际调用）
- `backend/app/api/products_entity.py` — 商品 update/delete 分流（L358/L410）

### 前端修改
- `frontend/src/views/ingredients/IngredientDetail.vue` — 基本信息/删除/层级提示按角色
- `frontend/src/views/products/ProductDetail.vue` — 基本信息/删除提示按角色

---

## Task 1: ProductExecutor 新建 + 单测

**Files:**
- Create: `backend/app/services/proposals/executors/product.py`
- Test: `backend/tests/test_product_ingredient_proposals.py`（本 task 先建文件加 ProductExecutor 单测）

- [ ] **Step 1: 写 ProductExecutor**

先读 `backend/app/services/proposals/executors/_crud_base.py`（理解 CrudExecutorBase + `_json_safe`）和 `backend/app/models/product_entity.py` / `backend/app/models/product.py`（Product + ProductRecord 模型，均有 is_active）。

Create `backend/app/services/proposals/executors/product.py`：
```python
"""商品执行器：CRUD + 软删（delete 级联 ProductRecord，revert 反级联复活）。

继承 CrudExecutorBase：update 吃基类 setattr；delete 覆写——
唯一商品检查（原料的唯一活跃商品拒删）+ 软删 Product + 级联软删其 ProductRecord +
snapshot；revert 按 snapshot 反级联复活 Product + ProductRecord。

payload 期望（update）：商品基本信息字段（name/brand/barcode/ingredient_id/tags/aliases/updated_by）。
entity_id：Product.id。
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.proposals.base import ApplyResult
from app.services.proposals.executors._crud_base import CrudExecutorBase, _json_safe
from app.models.product_entity import Product
from app.models.product import ProductRecord


class ProductExecutor(CrudExecutorBase):
    entity_type = "product"
    model_class = Product

    def validate(self, db: Session, proposal) -> None:
        action = proposal.action
        if action == "create":
            return  # 商品 create 不在本次范围
        eid = proposal.entity_id
        if eid is None:
            raise HTTPException(status_code=400, detail="update/delete 需 entity_id")
        obj = (
            db.query(Product)
            .filter(Product.id == eid, Product.is_active.is_(True))
            .first()
        )
        if obj is None:
            raise HTTPException(status_code=404, detail=f"商品 {eid} 不存在或已删除")

    def apply(self, db: Session, proposal) -> ApplyResult:
        if proposal.action == "delete":
            return self._apply_delete(db, proposal)
        return super().apply(db, proposal)

    def _apply_delete(self, db: Session, proposal) -> ApplyResult:
        eid = proposal.entity_id
        obj = (
            db.query(Product)
            .filter(Product.id == eid, Product.is_active.is_(True))
            .first()
        )
        if obj is None:
            raise HTTPException(status_code=404, detail=f"商品 {eid} 不存在或已删除")

        # 唯一商品检查：原料的唯一活跃商品不能删（双层检查之执行器侧）
        sibling_count = (
            db.query(Product)
            .filter(
                Product.ingredient_id == obj.ingredient_id,
                Product.is_active.is_(True),
                Product.id != eid,
            )
            .count()
        )
        if sibling_count == 0:
            raise HTTPException(
                status_code=400,
                detail=f"「{obj.name}」是其所属原料的唯一商品，无法删除。请先为该原料添加其他商品后再删除。",
            )

        # snapshot 级联 ProductRecord id（供 revert 复活）
        record_ids = [
            r.id
            for r in db.query(ProductRecord)
            .filter(ProductRecord.product_id == eid)
            .all()
        ]

        # 软删 Product + 级联软删 ProductRecord
        obj.is_active = False
        if record_ids:
            db.query(ProductRecord).filter(
                ProductRecord.product_id == eid
            ).update({"is_active": False}, synchronize_session=False)

        # 主记录全列快照（_json_safe 防 Decimal/date 入 JSON 列）+ 级联记录 id
        snapshot = {c.name: _json_safe(getattr(obj, c.name)) for c in obj.__table__.columns}
        snapshot["_cascade_record_ids"] = record_ids

        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"restore_active": True, "cascade_record_ids": record_ids},
            summary=f"已软删商品 {eid}（级联 {len(record_ids)} 条价格记录）",
        )

    def revert(self, db: Session, proposal) -> None:
        if proposal.action != "delete":
            return super().revert(db, proposal)
        rp = proposal.revert_payload or {}
        eid = proposal.entity_id
        obj = db.query(Product).get(eid) if eid else None
        if obj is not None:
            obj.is_active = True
        # 反级联：复活 ProductRecord
        cascade_ids = rp.get("cascade_record_ids") or []
        if cascade_ids:
            db.query(ProductRecord).filter(
                ProductRecord.id.in_(cascade_ids)
            ).update({"is_active": True}, synchronize_session=False)
```

- [ ] **Step 2: py_compile**

Run: `cd /d/code/live_calc/backend && python -m py_compile app/services/proposals/executors/product.py`
Expected: 无输出。

- [ ] **Step 3: 写 ProductExecutor 单测**

Create `backend/tests/test_product_ingredient_proposals.py`：
```python
"""商品/原料执行器级联 + 端点分流集成测试。"""
import pytest
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.main import app
from app.services.proposals.bootstrap import register_all

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup():
    register_all()
    previous = dict(app.dependency_overrides)
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def _proposal(action, payload, entity_id=None):
    return SimpleNamespace(
        action=action, payload=payload, entity_id=entity_id,
        snapshot=None, revert_payload=None, proposer_id=1,
    )


def _make_product(db_session, ingredient_id, name="测试商品", active=True, with_records=0):
    """建一个商品（+可选价格记录），返回 product。"""
    from app.models.product_entity import Product
    from app.models.product import ProductRecord
    from app.models.unit import Unit
    # 确保有一个质量单位（ProductRecord 需 original_unit_id/standard_unit_id）
    unit = db_session.query(Unit).filter(Unit.abbreviation == "g").first()
    if unit is None:
        unit = Unit(name="克", abbreviation="g", unit_type="mass", unit_system="metric")
        db_session.add(unit)
        db_session.commit()
        db_session.refresh(unit)
    from app.models.user import User
    user = db_session.query(User).first()
    uid = user.id if user else 1
    p = Product(name=name, ingredient_id=ingredient_id, is_active=active, created_by=uid)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    for _ in range(with_records):
        db_session.add(ProductRecord(
            user_id=uid, product_id=p.id, product_name=name, price=10,
            original_quantity=1, original_unit_id=unit.id,
            standard_quantity=1, standard_unit_id=unit.id, is_active=True,
        ))
    db_session.commit()
    return p


def test_product_delete_cascade_then_revert(db_session):
    """商品 delete 软删 + 级联软删 ProductRecord；revert 反级联复活。"""
    from app.services.proposals.executors.product import ProductExecutor
    from app.models.product_entity import Product
    from app.models.product import ProductRecord
    # 建原料 + 2 个商品（避免唯一商品检查）+ 商品 A 有 2 条价格记录
    ing_id = _make_ingredient(db_session)
    _make_product(db_session, ing_id, name="商品B")  # 兄弟，避免唯一
    p = _make_product(db_session, ing_id, name="商品A", with_records=2)
    record_ids = [r.id for r in db_session.query(ProductRecord).filter(ProductRecord.product_id == p.id).all()]

    ex = ProductExecutor()
    result = ex.apply(db_session, _proposal("delete", {}, entity_id=p.id))
    db_session.commit()
    db_session.refresh(p)
    assert p.is_active in (False, 0)
    assert all(
        r.is_active in (False, 0)
        for r in db_session.query(ProductRecord).filter(ProductRecord.id.in_(record_ids)).all()
    )
    # revert 反级联
    pr = _proposal("delete", {}, entity_id=p.id)
    pr.revert_payload = result.revert_payload
    pr.snapshot = result.snapshot
    ex.revert(db_session, pr)
    db_session.commit()
    db_session.refresh(p)
    assert p.is_active in (True, 1)
    assert all(
        r.is_active in (True, 1)
        for r in db_session.query(ProductRecord).filter(ProductRecord.id.in_(record_ids)).all()
    )


def _make_ingredient(db_session, name="测试原料_cascade"):
    from app.models.nutrition import Ingredient
    ing = Ingredient(name=name, is_active=True)
    db_session.add(ing)
    db_session.commit()
    db_session.refresh(ing)
    return ing.id


def test_product_delete_only_product_rejected(db_session):
    """唯一商品删除被拒（执行器 apply 时检查）。"""
    from app.services.proposals.executors.product import ProductExecutor
    ing_id = _make_ingredient(db_session)
    p = _make_product(db_session, ing_id, name="唯一商品")  # 无兄弟
    ex = ProductExecutor()
    with pytest.raises(Exception):
        ex.apply(db_session, _proposal("delete", {}, entity_id=p.id))
```

- [ ] **Step 4: 运行测试**

Run: `cd /d/code/live_calc/backend && python -m pytest tests/test_product_ingredient_proposals.py -v`
Expected: 2 passed（cascade revert + only-product rejected）。

> 若 ProductRecord 必填字段或 Unit/User fixture 不匹配，读模型调整 `_make_product` 辅助函数。`db_session` 是共享内存库，用独立 name/id 避免污染。

---

## Task 2: IngredientExecutor delete 覆写加级联 + 单测

**Files:**
- Modify: `backend/app/services/proposals/executors/ingredient.py`
- Test: `backend/tests/test_product_ingredient_proposals.py`（追加）

- [ ] **Step 1: 覆写 ingredient.py 的 apply/revert 加 delete 级联**

读 `backend/app/services/proposals/executors/ingredient.py` 现状（apply: merge 特判 + super；revert: merge 特判 + super）。

(1) 在 `apply` 方法的 `if proposal.action == "merge"` 之后、`return super().apply(...)` 之前，加 delete 特判：
```python
    def apply(self, db, proposal) -> ApplyResult:
        if proposal.action == "merge":
            return self._apply_merge(db, proposal)
        if proposal.action == "delete":
            return self._apply_delete(db, proposal)
        return super().apply(db, proposal)
```

(2) 在 `revert` 方法的 merge 特判之后、`super().revert` 之前，加 delete 特判：
```python
    def revert(self, db, proposal) -> None:
        if proposal.action == "merge":
            self._revert_merge(db, proposal)
            return
        if proposal.action == "delete":
            self._revert_delete(db, proposal)
            return
        super().revert(db, proposal)
```

(3) 在 `_revert_merge` 方法**之前**（或 `_apply_merge` 之后），新增两个方法：
```python
    def _apply_delete(self, db, proposal) -> ApplyResult:
        from app.models.recipe import RecipeIngredient
        from app.models.product_entity import Product
        from app.models.ingredient_hierarchy import IngredientHierarchy
        from app.services.proposals.executors._crud_base import _json_safe

        eid = proposal.entity_id
        ing = (
            db.query(Ingredient)
            .filter(Ingredient.id == eid, Ingredient.is_active.is_(True))
            .first()
        )
        if ing is None:
            raise HTTPException(status_code=404, detail=f"食材 {eid} 不存在或已删除")

        # 菜谱引用检查（双层检查之执行器侧）
        recipe_count = (
            db.query(RecipeIngredient)
            .filter(RecipeIngredient.ingredient_id == eid)
            .count()
        )
        if recipe_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"该食材已被 {recipe_count} 个菜谱引用，无法删除。请先移除菜谱中的该食材。",
            )

        # snapshot 级联：活跃商品 id + 相关层级关系 id
        product_ids = [
            p.id for p in db.query(Product).filter(
                Product.ingredient_id == eid, Product.is_active.is_(True)
            ).all()
        ]
        hierarchy_ids = [
            h.id for h in db.query(IngredientHierarchy).filter(
                or_(IngredientHierarchy.parent_id == eid,
                    IngredientHierarchy.child_id == eid)
            ).all()
        ]

        # 级联软删商品
        if product_ids:
            db.query(Product).filter(Product.id.in_(product_ids)).update(
                {"is_active": False}, synchronize_session=False)
        # 级联软删层级关系（parent / child 两向）
        db.query(IngredientHierarchy).filter(
            IngredientHierarchy.parent_id == eid
        ).update({"is_active": False}, synchronize_session=False)
        db.query(IngredientHierarchy).filter(
            IngredientHierarchy.child_id == eid
        ).update({"is_active": False}, synchronize_session=False)

        # 软删食材
        ing.is_active = False

        snapshot = {c.name: _json_safe(getattr(ing, c.name)) for c in ing.__table__.columns}
        snapshot["_cascade_product_ids"] = product_ids
        snapshot["_cascade_hierarchy_ids"] = hierarchy_ids

        return ApplyResult(
            snapshot=snapshot,
            revert_payload={"restore_active": True,
                            "cascade_product_ids": product_ids,
                            "cascade_hierarchy_ids": hierarchy_ids},
            summary=f"已软删食材 {eid}（级联 {len(product_ids)} 商品 / {len(hierarchy_ids)} 层级）",
        )

    def _revert_delete(self, db, proposal) -> None:
        from app.models.product_entity import Product
        from app.models.ingredient_hierarchy import IngredientHierarchy

        rp = proposal.revert_payload or {}
        eid = proposal.entity_id
        ing = db.query(Ingredient).get(eid) if eid else None
        if ing is not None:
            ing.is_active = True
        # 反级联：复活商品
        product_ids = rp.get("cascade_product_ids") or []
        if product_ids:
            db.query(Product).filter(Product.id.in_(product_ids)).update(
                {"is_active": True}, synchronize_session=False)
        # 反级联：复活层级关系
        hierarchy_ids = rp.get("cascade_hierarchy_ids") or []
        if hierarchy_ids:
            db.query(IngredientHierarchy).filter(
                IngredientHierarchy.id.in_(hierarchy_ids)
            ).update({"is_active": True}, synchronize_session=False)
```

> `or_` 已在文件顶部 import（`from sqlalchemy import and_, or_`，见现状 L13）。`_json_safe` 在 `_apply_delete` 内 import（避免顶部循环）。

- [ ] **Step 2: py_compile**

Run: `cd /d/code/live_calc/backend && python -m py_compile app/services/proposals/executors/ingredient.py`
Expected: 无输出。

- [ ] **Step 3: 追加 IngredientExecutor delete 级联单测**

追加到 `backend/tests/test_product_ingredient_proposals.py`：
```python
def test_ingredient_delete_cascade_then_revert(db_session):
    """原料 delete 级联软删商品+层级；revert 反级联复活。"""
    from app.services.proposals.executors.ingredient import IngredientExecutor
    from app.models.nutrition import Ingredient
    from app.models.product_entity import Product
    from app.models.ingredient_hierarchy import IngredientHierarchy

    ing_id = _make_ingredient(db_session, name="级联原料_x")
    child_ing_id = _make_ingredient(db_session, name="子原料_x")
    p = _make_product(db_session, ing_id, name="级联商品_x")
    h = IngredientHierarchy(parent_id=ing_id, child_id=child_ing_id, is_active=True)
    db_session.add(h)
    db_session.commit()
    db_session.refresh(h)

    ex = IngredientExecutor()
    result = ex.apply(db_session, _proposal("delete", {}, entity_id=ing_id))
    db_session.commit()
    db_session.refresh(p)
    db_session.refresh(h)
    ing = db_session.query(Ingredient).get(ing_id)
    assert ing.is_active in (False, 0)
    assert p.is_active in (False, 0)
    assert h.is_active in (False, 0)

    pr = _proposal("delete", {}, entity_id=ing_id)
    pr.revert_payload = result.revert_payload
    pr.snapshot = result.snapshot
    ex.revert(db_session, pr)
    db_session.commit()
    db_session.refresh(p)
    db_session.refresh(h)
    ing = db_session.query(Ingredient).get(ing_id)
    assert ing.is_active in (True, 1)
    assert p.is_active in (True, 1)
    assert h.is_active in (True, 1)


def test_ingredient_delete_with_recipe_rejected(db_session):
    """有菜谱引用的原料删除被拒（执行器 apply 时检查）。"""
    from app.services.proposals.executors.ingredient import IngredientExecutor
    from app.models.nutrition import Ingredient
    from app.models.recipe import RecipeIngredient
    ing_id = _make_ingredient(db_session, name="被引原料_x")
    # 建一条菜谱引用（recipe_id 用任意值，仅造引用计数）
    db_session.add(RecipeIngredient(recipe_id=999999, ingredient_id=ing_id,
                                    quantity=1, unit_id=1))
    db_session.commit()
    ex = IngredientExecutor()
    with pytest.raises(Exception):
        ex.apply(db_session, _proposal("delete", {}, entity_id=ing_id))
```

> 若 RecipeIngredient 必填字段不同（quantity/unit_id），读 `backend/app/models/recipe.py` 调整。IngredientHierarchy 必填字段读 `backend/app/models/ingredient_hierarchy.py`。

- [ ] **Step 4: 运行测试**

Run: `cd /d/code/live_calc/backend && python -m pytest tests/test_product_ingredient_proposals.py -v`
Expected: 4 passed（2 Product + 2 Ingredient）。

---

## Task 3: bootstrap 注册 ProductExecutor

**Files:**
- Modify: `backend/app/services/proposals/bootstrap.py`
- Test: `backend/tests/test_product_ingredient_proposals.py`（追加注册验证）

- [ ] **Step 1: 注册 ProductExecutor**

在 [bootstrap.py](../../../backend/app/services/proposals/bootstrap.py) 顶部 import 区加：
```python
from app.services.proposals.executors.product import ProductExecutor
```

在 `register_all` 内、`# 加载持久化策略覆盖默认` 注释**之前**加：
```python
    # 商品实体：全 manual（update/delete 均需审核）
    ExecutorRegistry.register(ProductExecutor(), default_policy="manual", default_risk="mid")
```

- [ ] **Step 2: py_compile + 追加注册验证测试**

Run: `cd /d/code/live_calc/backend && python -m py_compile app/services/proposals/bootstrap.py`

追加到 `backend/tests/test_product_ingredient_proposals.py`：
```python
def test_product_executor_registered_manual(db_session):
    from app.services.proposals.registry import ExecutorRegistry
    assert ExecutorRegistry.get("product") is not None
    assert ExecutorRegistry.policy_for("product", "update") == "manual"
    assert ExecutorRegistry.policy_for("product", "delete") == "manual"
```

- [ ] **Step 3: 运行测试**

Run: `cd /d/code/live_calc/backend && python -m pytest tests/test_product_ingredient_proposals.py::test_product_executor_registered_manual -v`
Expected: passed。

---

## Task 4: 4 端点分流 + 集成测试

**Files:**
- Modify: `backend/app/api/ingredient_extended.py`（原料 update L527）
- Modify: `backend/app/api/nutrition.py`（原料 delete L531）
- Modify: `backend/app/api/products_entity.py`（商品 update L358 / delete L410）
- Test: `backend/tests/test_product_ingredient_proposals.py`（追加端点分流测试）

- [ ] **Step 1: 商品 update_product 分流（最简单，先做）**

读 [products_entity.py:358](../../../backend/app/api/products_entity.py#L358) `update_product`。去掉 created_by 检查 + 403（L371-372），改分流。保留 barcode 唯一检查（L376-383）和 tags 序列化（L385-387）在端点提交时做，payload 带 updated_by：

替换 `update_product` 函数体（从 `db_product = ...` 到 `return db_product`）：
```python
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")

    update_data = product_update.model_dump(exclude_unset=True)

    # 检查条码唯一性（端点提交时）
    if 'barcode' in update_data and update_data['barcode']:
        existing = db.query(Product).filter(
            Product.barcode == update_data['barcode'],
            Product.id != product_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Barcode already exists")

    # 序列化 tags
    if 'tags' in update_data:
        update_data['tags'] = serialize_tags(update_data['tags'])

    update_data["updated_by"] = current_user.id

    # 分流：管理员直写 / 普通用户提议（全 manual）
    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="product", entity_id=product_id,
            action="update", payload=update_data, admin=current_user,
        )
    else:
        proposal_service.submit(
            db, entity_type="product", entity_id=product_id,
            action="update", payload=update_data, proposer=current_user,
        )
    db.commit()
    db.refresh(db_product)

    # 反序列化 tags 用于响应
    if db_product.tags:
        db_product.tags = deserialize_tags(db_product.tags)
    else:
        db_product.tags = []
    db_product.ingredient_name = db_product.ingredient.name if db_product.ingredient else None
    return db_product
```

确认 `proposal_service` 已 import（文件顶部应有 `from app.services.proposals import service as proposal_service`；若无则加，参照 units.py）。

- [ ] **Step 2: 商品 delete_product 分流**

读 [products_entity.py:410](../../../backend/app/api/products_entity.py#L410) `delete_product`。去掉 created_by 检查（L423-424）。唯一商品检查保留在端点（L426-436，提交时）+ 执行器 apply（Task 1 已加）。分流：

替换 `delete_product` 函数体：
```python
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 唯一商品检查（端点提交时；执行器 apply 时再查一次防审核期间变化）
    sibling_count = db.query(Product).filter(
        Product.ingredient_id == db_product.ingredient_id,
        Product.is_active == True,
        Product.id != product_id
    ).count()
    if sibling_count == 0:
        raise HTTPException(
            status_code=400,
            detail=f"「{db_product.name}」是其所属原料的唯一商品，无法删除。请先为该原料添加其他商品后再删除。"
        )

    # 分流：管理员直写（级联软删在执行器）/ 普通用户提议待审
    if current_user.is_admin:
        proposal_service.apply_as_admin(
            db, entity_type="product", entity_id=product_id,
            action="delete", payload={}, admin=current_user,
        )
        db.commit()
        return {"message": "商品已删除（管理员直写，级联软删价格记录）"}

    p = proposal_service.submit(
        db, entity_type="product", entity_id=product_id,
        action="delete", payload={}, proposer=current_user,
    )
    db.commit()
    return {"message": f"删除提议已提交（proposal_id={p.id}, status={p.status}）"}
```

- [ ] **Step 3: 原料 update_ingredient 分流（ingredient_extended）**

读 [ingredient_extended.py:527](../../../backend/app/api/ingredient_extended.py#L527) `update_ingredient`。改造要点：
- **去掉** created_by 检查（L550-551）和 is_imported 检查（L554-555）
- 基本信息字段（L557-586 的直接 setattr）改成构造 payload + 走提议
- **nutrition 处理逻辑（L590+）保留不动**（前端不传 nutrition，实际不触发）
- name 唯一检查保留在构造 payload 时

替换 L549（权限检查）到 L588（db.commit）之间的基本信息处理段为：
```python
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
```

> 保留其后的 nutrition 处理（`if nutrition:` 段）和 return 不动。确认 `proposal_service` 已 import（参照 units.py；若无则顶部加 `from app.services.proposals import service as proposal_service`）。
> 注意：update_ingredient 现状用 `Body(...)` 逐个参数（非 Pydantic model），payload 手动构造（无 Decimal 序列化问题，density 是 float）。

- [ ] **Step 4: 原料 delete 分流（nutrition.py L531）**

读 [nutrition.py:531](../../../backend/app/api/nutrition.py#L531) `soft_delete_ingredient`。去掉 created_by 检查。菜谱引用检查保留（提交时）+ 执行器 apply 时再查。分流：

替换 `soft_delete_ingredient` 函数体（保留 try/except 结构）：
```python
    try:
        from app.models.recipe import RecipeIngredient
        from app.services.proposals import service as proposal_service

        ingredient = db.query(Ingredient).filter(
            Ingredient.id == ingredient_id, Ingredient.is_active == True
        ).first()
        if not ingredient:
            raise HTTPException(status_code=404, detail="原料不存在")

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
```

> 去掉原级联软删商品/层级的代码（L982-994）——这些由执行器 apply 做了。去掉 created_by 检查（L979-980 等价位置）。

- [ ] **Step 5: py_compile 全部端点文件**

Run: `cd /d/code/live_calc/backend && python -m py_compile app/api/ingredient_extended.py app/api/nutrition.py app/api/products_entity.py`
Expected: 无输出。

- [ ] **Step 6: 追加端点分流集成测试**

追加到 `backend/tests/test_product_ingredient_proposals.py`：
```python
def test_admin_update_product_applied(db_session, as_admin):
    """管理员改商品即时生效。"""
    ing_id = _make_ingredient(db_session, name="upd_ing")
    p = _make_product(db_session, ing_id, name="旧名")
    resp = client.put(f"/api/v1/products/entity/{p.id}", json={"name": "新名"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "新名"


def test_non_admin_update_product_pending(db_session, as_non_admin):
    """普通用户改商品走 manual 待审（值未变）。"""
    ing_id = _make_ingredient(db_session, name="upd_ing2")
    p = _make_product(db_session, ing_id, name="旧名2")
    resp = client.put(f"/api/v1/products/entity/{p.id}", json={"name": "新名2"})
    assert resp.status_code == 200
    from app.models.product_entity import Product
    refreshed = db_session.query(Product).get(p.id)
    db_session.refresh(refreshed)
    assert refreshed.name == "旧名2"  # 待审未生效


def test_non_admin_delete_product_pending(db_session, as_non_admin):
    """普通用户删商品走 manual 待审（不立即删）。"""
    ing_id = _make_ingredient(db_session, name="del_ing")
    p = _make_product(db_session, ing_id, name="待删")
    _make_product(db_session, ing_id, name="兄弟")  # 避免唯一商品
    resp = client.delete(f"/api/v1/products/entity/{p.id}")
    assert resp.status_code == 200
    assert "已提交" in resp.json()["message"]
    from app.models.product_entity import Product
    refreshed = db_session.query(Product).get(p.id)
    db_session.refresh(refreshed)
    assert refreshed.is_active in (True, 1)  # 待审未删


def test_non_admin_update_ingredient_pending(db_session, as_non_admin):
    """普通用户改原料基本信息走 manual 待审。"""
    ing_id = _make_ingredient(db_session, name="原料_待改")
    resp = client.put(f"/api/v1/ingredients/{ing_id}", json={"aliases": ["新别名"]})
    assert resp.status_code == 200
    from app.models.nutrition import Ingredient
    refreshed = db_session.query(Ingredient).get(ing_id)
    db_session.refresh(refreshed)
    assert refreshed.aliases != ["新别名"] or refreshed.aliases is None  # 待审未生效


def test_non_admin_delete_ingredient_pending(db_session, as_non_admin):
    """普通用户删原料走 manual 待审。"""
    ing_id = _make_ingredient(db_session, name="原料_待删")
    resp = client.delete(f"/api/v1/nutrition/ingredients/{ing_id}")
    assert resp.status_code == 200
    assert "已提交" in resp.json()["message"]
    from app.models.nutrition import Ingredient
    refreshed = db_session.query(Ingredient).get(ing_id)
    db_session.refresh(refreshed)
    assert refreshed.is_active in (True, 1)  # 待审未删
```

> URL 前缀 `/api/v1`（确认 main.py 挂载）。原料 delete 用 `/api/v1/nutrition/ingredients/{id}`（前端实际路径）。

- [ ] **Step 7: 运行端点分流测试**

Run: `cd /d/code/live_calc/backend && python -m pytest tests/test_product_ingredient_proposals.py -v`
Expected: 全部 passed（执行器 4 + 注册 1 + 端点 5 = 10）。

---

## Task 5: 前端提示按角色 + build

**Files:**
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`（saveBasicInfo L3549 / deleteIngredient L3893 / 层级 add L3210 / edit L3244 / delete L3272）
- Modify: `frontend/src/views/products/ProductDetail.vue`（saveBasicInfo L2309 / deleteProduct L2596）

- [ ] **Step 1: IngredientDetail 5 处按角色提示**

确认 `userStore` 已引入（L1697-1700 已有 `useUserStore`）。参考 entity_unit_override 模式（`if (userStore.user?.is_admin)`）。

**(1) saveBasicInfo**（[L3579](../../../frontend/src/views/ingredients/IngredientDetail.vue#L3579)）成功分支改为：
```javascript
    if (userStore.user?.is_admin) {
      editingBasicInfo.value = false
      showMessage('基本信息已保存', 'success')
    } else {
      editingBasicInfo.value = false
      showMessage('已提交，待管理员审核', 'info')
    }
```
（保留其前的 `await api.put` + 制作菜谱关系处理 + `ingredient.value = fresh` 等；管理员才重新拉取详情，普通用户不拉取待审数据。具体：把 L3573-3579 的 `ingredient.value = fresh` + `editingBasicInfo.value = false` + `showMessage` 包进 if/else——管理员路径保留 `fresh` 拉取，普通用户跳过 `fresh` 拉取只关对话框提示待审。）

**(2) deleteIngredient**（[L3893](../../../frontend/src/views/ingredients/IngredientDetail.vue#L3893)）成功分支改为：
```javascript
    await api.delete(`/nutrition/ingredients/${ingredientId.value}`)
    if (userStore.user?.is_admin) {
      showMessage('删除成功', 'success')
      router.push('/data/ingredients')
    } else {
      showMessage('删除提议已提交，待管理员审核', 'info')
    }
```

**(3) addRelation**（[L3216-3218](../../../frontend/src/views/ingredients/IngredientDetail.vue#L3216)）成功分支改为：
```javascript
    if (userStore.user?.is_admin) {
      showMessage('关系添加成功', 'success')
      showAddRelationDialog.value = false
      await loadHierarchy()
    } else {
      showMessage('已提交，待管理员审核', 'info')
      showAddRelationDialog.value = false
    }
```

**(4) saveEditRelation**（[L3248-3250](../../../frontend/src/views/ingredients/IngredientDetail.vue#L3248)）成功分支改为：
```javascript
    if (userStore.user?.is_admin) {
      showMessage('关系更新成功', 'success')
      showEditRelationDialog.value = false
      await loadHierarchy()
    } else {
      showMessage('已提交，待管理员审核', 'info')
      showEditRelationDialog.value = false
    }
```

**(5) deleteRelation**（[L3273-3275](../../../frontend/src/views/ingredients/IngredientDetail.vue#L3273)）成功分支改为：
```javascript
    if (userStore.user?.is_admin) {
      showMessage('关系删除成功', 'success')
      showDeleteRelationDialog.value = false
      await loadHierarchy()
    } else {
      showMessage('删除提议已提交，待管理员审核', 'info')
      showDeleteRelationDialog.value = false
    }
```

> 三个函数均保留 try 块里的 api 调用与参数构造、catch 块、finally 块不变，只替换 `await api.xxx(...)` 之后到 catch 之前的成功分支。

- [ ] **Step 2: ProductDetail 2 处按角色提示**

**(1) saveBasicInfo**（[L2309](../../../frontend/src/views/products/ProductDetail.vue#L2309)）：成功分支按角色（管理员 `product.value = response` + 刷新 + 「基本信息已保存」；普通用户「已提交，待管理员审核」不刷新）。

**(2) deleteProduct**（[L2596](../../../frontend/src/views/products/ProductDetail.vue#L2596)）：成功分支按角色（管理员「删除成功」+ 跳转；普通用户「删除提议已提交，待管理员审核」）。

- [ ] **Step 3: npm run build**

Run: `cd /d/code/live_calc/frontend && npm run build`
Expected: 构建成功，无 error。

---

## 完成验证（全任务结束后）

- [ ] 后端：`cd /d/code/live_calc/backend && python -m pytest tests/test_product_ingredient_proposals.py tests/test_proposals_framework.py tests/test_shared_data.py tests/test_entity_executors.py tests/test_entity_unit_density_proposals.py -v`，全 passed（失败数不高于已知基线）。
- [ ] 前端 `npm run build` 通过。
- [ ] 手动验收（已运行的自动重载服务）：管理员改/删原料商品即时生效；普通用户改/删弹「待审核」、审核台能看到 `product`/`ingredient` 类型待审提议、批准后生效（delete 级联生效）；普通用户维护层级关系弹「待审核」。
