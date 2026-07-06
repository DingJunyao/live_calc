# 商品加权价格机制 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: 用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 逐任务执行。步骤用 `- [ ]` 复选框跟踪。

**Goal:** 给商品引入 0-100 价格权重，把原料价格从「简单平均/取第一个商品」统一为「商品间加权平均」，覆盖原料最新价、菜谱成本、趋势、报告。

**Architecture:** 新增 `Product.price_weight`（全局）+ `user_product_weight_overrides`（用户覆盖）；抽统一服务 `ingredient_price_service.py`（纯聚合 + 编排两层），所有价格场景调用它。商品权重随 `ProductExecutor` 审核；用户覆盖仿 `user_preferences` 个人偏好。前端在商品详情基本信息、原料详情商品列表两处配置。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic（后端）；Vue 3 + Vuetify + Pinia（前端）；SQLite 开发库 / MySQL / PostgreSQL（迁移）。

**关联设计稿:** [docs/superpowers/specs/2026-07-06-product-weighted-price-design.md](../specs/2026-07-06-product-weighted-price-design.md)

---

## 命令约定

- 后端命令用**项目根目录的 venv**（`d:\code\live_calc\.venv`，非 `backend/.venv`——后者是空壳）：在 `backend/` 目录用 `../.venv\Scripts\python.exe -m pytest <path> -v`，或 `uv run pytest <path> -v`（uv 在项目根跑）。
- 后端语法检查：`cd backend && ../.venv\Scripts\python.exe -m py_compile app\<file>.py`。
- 前端构建：在 `frontend/` 目录，`npm run build`。
- 不在对话中启动服务（自动重载已开）。

## 提交策略（遵循 CLAUDE.md）

本计划每个任务末尾给出 `git commit` 检查点。**按项目 CLAUDE.md 惯例，所有 git 操作需用户明确指令后方可执行**——commit 步骤作为逻辑检查点存在，实际是否提交、提交信息措辞由用户在执行时决定。执行者不得擅自 commit。

## 阶段总览

| 阶段 | 任务 | 产出 |
|---|---|---|
| 1. 数据模型与迁移 | T1–T3 | 模型 + 迁移 + 四套 SQL |
| 2. 统一加权服务（TDD 核心） | T4–T6 | `ingredient_price_service` + 单测 |
| 3. 后端接入 | T7–T9 | latest-price / 成本 5 变体 / sparklines |
| 4. 用户覆盖 API + 权限 | T10–T12 | 覆盖 CRUD + 全局权重仅管理员 |
| 5. 前端 | T13–T16 | 两处配置入口 + 加权来源展示 |
| 6. 收尾 | T17–T18 | 集成测试 + 文档 |

---

## 阶段 1：数据模型与迁移

### Task 1: 给 Product 加全局权重列 + 新建用户覆盖模型

**Files:**
- Modify: `backend/app/models/product_entity.py`（Product 加列）
- Create: `backend/app/models/user_product_weight_override.py`
- Modify: `backend/app/models/__init__.py`（注册新模型）

- [ ] **Step 1: Product 加 `price_weight` 列**

修改 `backend/app/models/product_entity.py`，在 `custom_nutrition_source` 之后、`# 关系` 之前插入：

```python
    # 价格权重 0-100，参与原料加权平均（默认 50 等权）；仅管理员可改
    price_weight = Column(Integer, nullable=False, default=50)
```

> 不在模型层加 `CheckConstraint`（项目既有 `strength` 亦未加，CHECK 在迁移 SQL 层落实，三库一致）。

- [ ] **Step 2: 新建用户覆盖模型**

创建 `backend/app/models/user_product_weight_override.py`：

```python
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.core.base_model import AuditMixin
from app.core.database import Base


class UserProductWeightOverride(Base, AuditMixin):
    """用户对商品价格权重的私有覆盖（个人偏好，不走审核）。

    读取优先级：本表(is_active) → Product.price_weight → 兜底 50。
    """
    __tablename__ = "user_product_weight_overrides"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    weight = Column(Integer, nullable=False, default=50)

    user = relationship("User")
    product = relationship("Product")

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_user_product_weight"),
        Index("ix_upwo_user_active", "user_id", "is_active"),
    )
```

- [ ] **Step 3: 注册新模型**

修改 `backend/app/models/__init__.py`，在 import 区加：

```python
from app.models.user_product_weight_override import UserProductWeightOverride
```

并在 `__all__` 列表中加入 `"UserProductWeightOverride"`（位置紧跟 `"ProductIngredientLink"` 之后）。

- [ ] **Step 4: 语法检查**

```
cd backend
.venv\Scripts\python -m py_compile app\models\product_entity.py app\models\user_product_weight_override.py app\models\__init__.py
.venv\Scripts\python -c "from app.models import UserProductWeightOverride, Product; print(Product.price_weight, UserProductWeightOverride.__table__)"
```
Expected: 无异常，打印列对象与表信息。

- [ ] **Step 5: Commit 检查点**
```
feat(models): 商品价格权重列 + 用户覆盖表
```

---

### Task 2: 编写 Alembic 迁移

**Files:**
- Create: `backend/alembic/versions/20260707_0001_product_price_weight.py`

- [ ] **Step 1: 新建迁移文件**

创建 `backend/alembic/versions/20260707_0001_product_price_weight.py`：

```python
"""商品价格权重 + 用户覆盖表

Revision ID: 20260707_0001
Revises: 20260705_0001
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa


revision = "20260707_0001"
down_revision = "20260705_0001"   # 按 alembic 现有 head 调整，执行前 `alembic heads` 确认
branch_labels = None
depends_on = None


def upgrade() -> None:
    # products 加全局权重列（三库通用 ADD COLUMN；回填默认 50）
    op.add_column(
        "products",
        sa.Column("price_weight", sa.Integer(), nullable=False, server_default="50"),
    )
    # CHECK 约束（三库均支持；MySQL 8.0+ 支持 inline CHECK）
    op.create_check_constraint(
        "ck_products_price_weight_range",
        "products",
        "price_weight BETWEEN 0 AND 100",
    )

    op.create_table(
        "user_product_weight_overrides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column("created_by", sa.Integer()),
        sa.Column("updated_by", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.CheckConstraint("weight BETWEEN 0 AND 100", name="ck_upwo_weight_range"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_user_product_weight"),
    )
    op.create_index("ix_upwo_user_active", "user_product_weight_overrides", ["user_id", "is_active"])
    op.create_index("ix_user_product_weight_overrides_product_id", "user_product_weight_overrides", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_user_product_weight_overrides_product_id", table_name="user_product_weight_overrides")
    op.drop_index("ix_upwo_user_active", table_name="user_product_weight_overrides")
    op.drop_table("user_product_weight_overrides")
    op.drop_constraint("ck_products_price_weight_range", "products", type_="check")
    op.drop_column("products", "price_weight")
```

> **注意：** `down_revision` 必须接当前 alembic head。执行前先 `.venv\Scripts\python -m alembic heads` 确认；项目开发库不走 alembic（参见 CLAUDE.md），此迁移主要服务于 MySQL/PG 生产库。

- [ ] **Step 2: 语法检查 + 离线编译**
```
cd backend
.venv\Scripts\python -m py_compile alembic\versions\20260707_0001_product_price_weight.py
.venv\Scripts\python -m alembic upgrade head --sql   # 离线打印 SQL，确认 DDL 正确
```
Expected: 打印出含 `ADD COLUMN price_weight` 与 `CREATE TABLE user_product_weight_overrides` 的 DDL。

- [ ] **Step 3: Commit 检查点**
```
feat(alembic): 商品价格权重迁移
```

---

### Task 3: 四套 SQL 脚本 + 补开发库

**Files:**
- Create: `backend/scripts/sql/20260707_product_price_weight_sqlite.sql`
- Create: `backend/scripts/sql/20260707_product_price_weight_mysql.sql`
- Create: `backend/scripts/sql/20260707_product_price_weight_postgres.sql`

> PostgreSQL（启用 PostGIS）与普通 PostgreSQL 完全相同（本变更与 PostGIS 无关），在 `20260707_product_price_weight_postgres.sql` 顶部注明「同时适用于启用 PostGIS 的 PostgreSQL，无需单独脚本」。

- [ ] **Step 1: SQLite 脚本**

创建 `backend/scripts/sql/20260707_product_price_weight_sqlite.sql`：

```sql
-- 商品价格权重 + 用户覆盖表（SQLite）
-- 适用于：SQLite（含开发库 backend/data/livecalc.db 直接补）

-- 1. products 加权重列（SQLite 3.37+ 支持 inline CHECK；ADD COLUMN 带 CHECK 需 3.31+）
ALTER TABLE products ADD COLUMN price_weight INTEGER NOT NULL DEFAULT 50
  CHECK (price_weight BETWEEN 0 AND 100);

-- 2. 用户覆盖表
CREATE TABLE IF NOT EXISTS user_product_weight_overrides (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  product_id INTEGER NOT NULL REFERENCES products(id),
  weight INTEGER NOT NULL DEFAULT 50 CHECK (weight BETWEEN 0 AND 100),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME,
  created_by INTEGER,
  updated_by INTEGER,
  is_active INTEGER DEFAULT 1,   -- SQLite 无原生 BOOL，按项目惯例 1/0
  UNIQUE(user_id, product_id)
);
CREATE INDEX IF NOT EXISTS ix_upwo_user_active ON user_product_weight_overrides(user_id, is_active);
CREATE INDEX IF NOT EXISTS ix_user_product_weight_overrides_product_id ON user_product_weight_overrides(product_id);
```

- [ ] **Step 2: MySQL 脚本**

创建 `backend/scripts/sql/20260707_product_price_weight_mysql.sql`：

```sql
-- 商品价格权重 + 用户覆盖表（MySQL 8.0+）
ALTER TABLE products
  ADD COLUMN price_weight INT NOT NULL DEFAULT 50,
  ADD CONSTRAINT ck_products_price_weight_range CHECK (price_weight BETWEEN 0 AND 100);

CREATE TABLE IF NOT EXISTS user_product_weight_overrides (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  product_id INT NOT NULL,
  weight INT NOT NULL DEFAULT 50,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_by INT,
  updated_by INT,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT ck_upwo_weight_range CHECK (weight BETWEEN 0 AND 100),
  CONSTRAINT uq_user_product_weight UNIQUE (user_id, product_id),
  CONSTRAINT fk_upwo_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_upwo_product FOREIGN KEY (product_id) REFERENCES products(id),
  KEY ix_upwo_user_active (user_id, is_active),
  KEY ix_user_product_weight_overrides_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- [ ] **Step 3: PostgreSQL 脚本**

创建 `backend/scripts/sql/20260707_product_price_weight_postgres.sql`：

```sql
-- 商品价格权重 + 用户覆盖表（PostgreSQL）
-- 注：本脚本同时适用于「启用 PostGIS 的 PostgreSQL」，本变更与 PostGIS 无关。

ALTER TABLE products
  ADD COLUMN price_weight INTEGER NOT NULL DEFAULT 50,
  ADD CONSTRAINT ck_products_price_weight_range CHECK (price_weight BETWEEN 0 AND 100);

CREATE TABLE IF NOT EXISTS user_product_weight_overrides (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  product_id INTEGER NOT NULL REFERENCES products(id),
  weight INTEGER NOT NULL DEFAULT 50,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ,
  created_by INTEGER,
  updated_by INTEGER,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  CONSTRAINT ck_upwo_weight_range CHECK (weight BETWEEN 0 AND 100),
  CONSTRAINT uq_user_product_weight UNIQUE (user_id, product_id)
);
CREATE INDEX IF NOT EXISTS ix_upwo_user_active ON user_product_weight_overrides(user_id, is_active);
CREATE INDEX IF NOT EXISTS ix_user_product_weight_overrides_product_id ON user_product_weight_overrides(product_id);
```

- [ ] **Step 4: 补开发库（操作前备份）**

```
cd backend
copy data\livecalc.db data\livecalc.db.bak_20260707_weight
.venv\Scripts\python -c "import sqlite3; c=sqlite3.connect('data/livecalc.db'); c.executescript(open('scripts/sql/20260707_product_price_weight_sqlite.sql',encoding='utf-8').read()); c.commit(); c.close()"
.venv\Scripts\python -c "import sqlite3; c=sqlite3.connect('data/livecalc.db'); print(c.execute('PRAGMA table_info(products)').fetchall()); print(c.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"user_product_weight_overrides\"').fetchall())"
```
Expected: `products` 表信息含 `price_weight`；`user_product_weight_overrides` 表存在。

- [ ] **Step 5: 验证现有商品回填默认值**

```
.venv\Scripts\python -c "import sqlite3; c=sqlite3.connect('backend/data/livecalc.db'); print('distinct weights:', set(r[0] for r in c.execute('SELECT DISTINCT price_weight FROM products').fetchall()))"
```
Expected: `{50}`（所有现存商品回填为默认等权）。

- [ ] **Step 6: Commit 检查点**
```
feat(sql): 商品权重四套迁移脚本 + 开发库补
```

---

## 阶段 2：统一加权服务（TDD 核心）

### Task 4: 纯聚合函数 `_aggregate_weighted` + 单测

**Files:**
- Create: `backend/app/services/ingredient_price_service.py`
- Test: `backend/tests/services/test_ingredient_price_service.py`

- [ ] **Step 1: 写失败测试（纯聚合的多个断言）**

创建 `backend/tests/services/test_ingredient_price_service.py`：

```python
"""统一加权价格服务测试。"""
from decimal import Decimal
from app.services.ingredient_price_service import _aggregate_weighted


def _rec(price, std_qty):
    """造一个最小伪记录对象，仅含聚合所需字段。"""
    class _R:
        pass
    r = _R()
    r.price = Decimal(str(price))
    r.standard_quantity = Decimal(str(std_qty)) if std_qty else None
    return r


def test_aggregate_basic_weighted_average():
    # 商品A 单价 10 权重 50；商品B 单价 30 权重 50 → (10+30)/2 = 20
    res = _aggregate_weighted(
        product_records={
            1: ([_rec(10, 1)], 50, {"product_id": 1, "name": "A"}),
            2: ([_rec(30, 1)], 50, {"product_id": 2, "name": "B"}),
        },
    )
    assert float(res["unit_price"]) == 20.0
    assert res["mode"] == "weighted"
    assert len(res["participants"]) == 2


def test_aggregate_weighted_proportional():
    # 商品A 单价 10 权重 75；商品B 单价 30 权重 25 → (10*75+30*25)/100 = 15
    res = _aggregate_weighted({
        1: ([_rec(10, 1)], 75, {"product_id": 1, "name": "A"}),
        2: ([_rec(30, 1)], 25, {"product_id": 2, "name": "B"}),
    })
    assert float(res["unit_price"]) == 15.0


def test_aggregate_weight_zero_excluded():
    # 权重 0 的商品被排除，仅在剩余商品间归一
    res = _aggregate_weighted({
        1: ([_rec(10, 1)], 0, {"product_id": 1, "name": "A"}),
        2: ([_rec(30, 1)], 50, {"product_id": 2, "name": "B"}),
    })
    assert float(res["unit_price"]) == 30.0
    assert len(res["participants"]) == 1
    assert res["excluded"][0]["reason"] == "weight_zero"


def test_aggregate_no_records_excluded_and_renormalize():
    # 商品A 无记录 → 排除；仅商品B 参与并退化
    res = _aggregate_weighted({
        1: ([], 50, {"product_id": 1, "name": "A"}),
        2: ([_rec(30, 1)], 50, {"product_id": 2, "name": "B"}),
    })
    assert float(res["unit_price"]) == 30.0
    assert res["mode"] == "single"
    assert res["excluded"][0]["reason"] == "no_record"


def test_aggregate_single_product_degenerates():
    res = _aggregate_weighted({1: ([_rec(12, 1)], 50, {"product_id": 1, "name": "A"})})
    assert float(res["unit_price"]) == 12.0
    assert res["mode"] == "single"


def test_aggregate_all_empty_returns_none():
    res = _aggregate_weighted({
        1: ([], 50, {"product_id": 1, "name": "A"}),
        2: ([], 50, {"product_id": 2, "name": "B"}),
    })
    assert res["unit_price"] is None
    assert res["mode"] == "none"


def test_aggregate_intra_product_average_before_weighting():
    # 商品A 两条记录（10、20）均价 15；商品B 一条 30；等权 → (15+30)/2 = 22.5
    # 关键：记录数不再放大 A 的权重（旧逻辑会变 (10+20+30)/3=20，错误）
    res = _aggregate_weighted({
        1: ([_rec(10, 1), _rec(20, 1)], 50, {"product_id": 1, "name": "A"}),
        2: ([_rec(30, 1)], 50, {"product_id": 2, "name": "B"}),
    })
    assert abs(float(res["unit_price"]) - 22.5) < 1e-9


def test_aggregate_zero_std_qty_fallback():
    # standard_quantity 为 0/None 时，单价 = price（与 price_aggregator/revenue 兜底一致）
    res = _aggregate_weighted({1: ([_rec(8, 0)], 50, {"product_id": 1, "name": "A"})})
    assert float(res["unit_price"]) == 8.0
```

- [ ] **Step 2: 运行测试，确认失败**
```
cd backend
.venv\Scripts\python -m pytest tests/services/test_ingredient_price_service.py -v
```
Expected: FAIL（`_aggregate_weighted` 不存在 / ImportError）。

- [ ] **Step 3: 实现 `_aggregate_weighted`**

创建 `backend/app/services/ingredient_price_service.py`：

```python
"""原料加权价格统一服务。

两层聚合：
  第一层（商品内）：每个商品当日有效记录的均价 → 该商品代表单价
  第二层（商品间）：按商品权重加权平均 Σ(pᵢ×wᵢ)/Σwᵢ

所有价格场景（原料最新价、菜谱成本、sparkline、报告）统一调用本服务。
记录查询复用 recipe_service._get_price_records_*，本服务只负责聚合。
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Sequence


def _product_unit_price(records: Sequence) -> Optional[Decimal]:
    """商品内均价：当日有效记录的 price / standard_quantity 平均。

    standard_quantity 为 None/0 时按 price 本身兜底（与 price_aggregator 一致）。
    """
    prices = []
    for r in records:
        if r.price is None:
            continue
        p = Decimal(str(r.price))
        sq = r.standard_quantity
        if sq is None or Decimal(str(sq)) == 0:
            prices.append(p)
        else:
            prices.append(p / Decimal(str(sq)))
    if not prices:
        return None
    return sum(prices) / Decimal(len(prices))


def _aggregate_weighted(product_records: dict) -> dict:
    """纯聚合：无 db 依赖。

    Args:
        product_records: { product_id: (records, weight, meta) }
            records: 该商品当日有效记录序列（ProductRecord 或伪对象）
            weight: int 0-100
            meta: {"product_id": int, "name": str, ...}（透传到 participants）

    Returns:
        {
          "unit_price": Optional[float],     # 加权单价（None = 无可用记录）
          "mode": "weighted"|"single"|"none",
          "participants": [{product_id, name, weight, unit_price, record_count, weight_source}],
          "excluded": [{product_id, name, reason}],  # reason ∈ {weight_zero, no_record}
        }
    """
    participants = []
    excluded = []
    for pid, entry in product_records.items():
        records, weight, meta = entry
        name = meta.get("name")
        if weight is None or weight <= 0:
            excluded.append({"product_id": pid, "name": name, "reason": "weight_zero"})
            continue
        intra = _product_unit_price(records)
        if intra is None:
            excluded.append({"product_id": pid, "name": name, "reason": "no_record"})
            continue
        participants.append({
            "product_id": pid,
            "name": name,
            "weight": int(weight),
            "unit_price": float(intra),
            "record_count": len([r for r in records if getattr(r, "price", None) is not None]),
            "weight_source": meta.get("weight_source", "global"),
        })

    if not participants:
        return {"unit_price": None, "mode": "none", "participants": [], "excluded": excluded}

    num = Decimal("0")
    den = Decimal("0")
    for p in participants:
        w = Decimal(p["weight"])
        num += Decimal(str(p["unit_price"])) * w
        den += w
    unit = float(num / den) if den > 0 else None
    mode = "single" if len(participants) == 1 else "weighted"
    return {"unit_price": unit, "mode": mode, "participants": participants, "excluded": excluded}
```

- [ ] **Step 4: 运行测试，确认全过**
```
.venv\Scripts\python -m pytest tests/services/test_ingredient_price_service.py -v
```
Expected: 8 passed。

- [ ] **Step 5: Commit 检查点**
```
feat(service): 加权价格纯聚合函数 + 8 单测
```

---

### Task 5: 权重解析 `_resolve_weight` + 单测

**Files:**
- Modify: `backend/app/services/ingredient_price_service.py`
- Test: `backend/tests/services/test_ingredient_price_service.py`（追加）

- [ ] **Step 1: 追加失败测试**

在 `test_ingredient_price_service.py` 末尾追加：

```python
from app.services.ingredient_price_service import _resolve_weight


class _P:
    """伪 Product。"""
    def __init__(self, pid, pw=50):
        self.id = pid
        self.price_weight = pw


def test_resolve_weight_override_wins():
    # 有用户覆盖 → 用覆盖
    class _Sess:
        def query(self, m):
            class _Q:
                def filter(self, *a):
                    return self
                def first(self):
                    return type("O", (), {"weight": 80})()
            return _Q()
    assert _resolve_weight(_Sess(), user_id=1, product=_P(1, pw=50)) == 80


def test_resolve_weight_global_when_no_override():
    # 无覆盖 → 用 product.price_weight
    class _Sess:
        def query(self, m):
            class _Q:
                def filter(self, *a):
                    return self
                def first(self):
                    return None
            return _Q()
    assert _resolve_weight(_Sess(), user_id=1, product=_P(1, pw=73)) == 73


def test_resolve_weight_default_when_global_none():
    # 全局为 None → 兜底 50
    class _Sess:
        def query(self, m):
            class _Q:
                def filter(self, *a):
                    return self
                def first(self):
                    return None
            return _Q()
    assert _resolve_weight(_Sess(), user_id=1, product=_P(1, pw=None)) == 50
```

- [ ] **Step 2: 运行，确认新测试失败**
```
.venv\Scripts\python -m pytest tests/services/test_ingredient_price_service.py -v
```
Expected: 3 个新测试 FAIL（`_resolve_weight` 未定义）。

- [ ] **Step 3: 实现 `_resolve_weight`**

在 `ingredient_price_service.py` 顶部 import 区加：

```python
from app.models.user_product_weight_override import UserProductWeightOverride
```

在文件末尾追加：

```python
_DEFAULT_WEIGHT = 50


def _resolve_weight(db, *, user_id: Optional[int], product) -> int:
    """权重读取优先级：用户覆盖(is_active) → product.price_weight → 50。

    返回三元组里第一个非空：覆盖 > 全局 > 兜底。weight_source 由调用方根据命中决定。
    """
    if user_id is not None and product is not None:
        ov = db.query(UserProductWeightOverride).filter(
            UserProductWeightOverride.user_id == user_id,
            UserProductWeightOverride.product_id == product.id,
            UserProductWeightOverride.is_active == True,  # noqa: E712
        ).first()
        if ov is not None and ov.weight is not None:
            return int(ov.weight)
    gw = getattr(product, "price_weight", None)
    if gw is not None:
        return int(gw)
    return _DEFAULT_WEIGHT
```

> `weight_source` 的判定逻辑放在编排函数里（命中覆盖 vs 全局），`_resolve_weight` 只返回数值。为支持 source 判定，下方编排函数单独再查一次覆盖表；或在编排里直接判定。这里保持 `_resolve_weight` 简单。

- [ ] **Step 4: 运行，确认全过**
```
.venv\Scripts\python -m pytest tests/services/test_ingredient_price_service.py -v
```
Expected: 11 passed。

- [ ] **Step 5: Commit 检查点**
```
feat(service): 权重解析优先级 + 3 单测
```

---

### Task 6: 编排函数 `get_weighted_ingredient_price`（两模式）+ 集成测试

**Files:**
- Modify: `backend/app/services/ingredient_price_service.py`
- Test: `backend/tests/services/test_ingredient_price_service.py`（追加）

- [ ] **Step 1: 追加集成测试（造真实 db 数据）**

在测试文件末尾追加：

```python
import pytest
from app.core.database import SessionLocal, Base, engine
from app.models.product_entity import Product
from app.models.nutrition import Ingredient
from app.models.product import ProductRecord
from app.models.unit import Unit
from app.services.ingredient_price_service import get_weighted_ingredient_price


@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _seed(db, ing_name, products_spec):
    """products_spec: [(name, weight, [(price, std_qty)])]"""
    db.query(ProductRecord).delete()
    db.query(Product).filter(Product.name.like("%TSK_%")).delete()
    db.query(Ingredient).filter(Ingredient.name == ing_name).delete()
    db.commit()
    ing = Ingredient(name=ing_name, is_active=True)
    db.add(ing); db.flush()
    for pname, w, recs in products_spec:
        p = Product(name=pname, ingredient_id=ing.id, is_active=True, price_weight=w)
        db.add(p); db.flush()
        for price, sq in recs:
            db.add(ProductRecord(
                product_id=p.id, price=price, standard_quantity=sq,
                standard_unit_id=3, recorded_at="2026-07-06", is_active=True,
            ))
    db.commit()
    return ing.id


def test_get_weighted_as_of_mode(db):
    ing_id = _seed(db, "TSK_番茄", [
        ("TSK_普通", 50, [(10, 500)]),
        ("TSK_有机", 50, [(30, 500)]),
    ])
    res = get_weighted_ingredient_price(
        db, ing_id, as_of_date=datetime(2026, 7, 6), user_id=1,
        target_unit_abbr="克", mode="as_of",
    )
    assert res["unit_price"] is not None
    # 10元/500克=0.02；30元/500克=0.06；等权 → 0.04
    assert abs(res["unit_price"] - 0.04) < 1e-6
    assert res["mode"] == "weighted"
    assert {p["name"] for p in res["participants"]} == {"TSK_普通", "TSK_有机"}


def test_get_weighted_user_override(db):
    ing_id = _seed(db, "TSK_茄子", [
        ("TSK_普通", 50, [(10, 500)]),
        ("TSK_有机", 50, [(30, 500)]),
    ])
    # 给 TSK_有机 设用户覆盖权重 0 → 排除，仅剩普通
    from app.models.user_product_weight_override import UserProductWeightOverride
    organic = db.query(Product).filter(Product.name == "TSK_有机").first()
    db.add(UserProductWeightOverride(user_id=1, product_id=organic.id, weight=0, is_active=True))
    db.commit()
    res = get_weighted_ingredient_price(
        db, ing_id, as_of_date=datetime(2026, 7, 6), user_id=1,
        target_unit_abbr="克", mode="as_of",
    )
    assert res["mode"] == "single"
    assert res["participants"][0]["name"] == "TSK_普通"
    # 清理覆盖
    db.query(UserProductWeightOverride).filter(UserProductWeightOverride.user_id == 1).delete()
    db.commit()
```

在文件顶部 import 区补 `from datetime import datetime`。

- [ ] **Step 2: 运行，确认失败**
```
.venv\Scripts\python -m pytest tests/services/test_ingredient_price_service.py -v
```
Expected: 2 个新测试 FAIL（`get_weighted_ingredient_price` 未定义）。

- [ ] **Step 3: 实现编排函数**

在 `ingredient_price_service.py` import 区追加（最终该文件 import 区含）：

```python
from sqlalchemy.orm import Session
from app.models.product_entity import Product
```

> 单位转换复用 `recipe_service` 现成逻辑，本服务不做二次单位换算。

在文件末尾追加：

```python
def get_weighted_ingredient_price(
    db: Session,
    ingredient_id: int,
    *,
    as_of_date: datetime,
    user_id: Optional[int] = None,
    target_unit_abbr: Optional[str] = None,
    mode: str = "as_of",
) -> dict:
    """编排：查商品 → 查每个商品当日有效记录 → 查权重 → 调 _aggregate_weighted。

    mode:
      "as_of"  —— 成本语义：每商品按 _get_price_records_with_fallback(as_of_date) 取「当天/前向填充」
      "recent" —— 最新价语义：跨商品找最近有记录的那天，按商品分组（latest-price 用）

    单位转换：第一层算单价时，若记录单位 ≠ target_unit_abbr，调用方在取记录阶段
    已保证记录的 standard_quantity/standard_unit_id 口径一致（与 recipe_service 现状一致），
    本函数不再二次转换；target_unit_abbr 仅作为返回参考（透传）。

    无任何商品有记录时返回 unit_price=None，mode="none"，调用方走外部回退链。
    """
    from app.models.user_product_weight_override import UserProductWeightOverride
    # 延迟导入，避免循环依赖
    try:
        from app.services.recipe_service import _get_price_records_with_fallback
    except Exception:
        _get_price_records_with_fallback = None

    products = db.query(Product).filter(
        Product.ingredient_id == ingredient_id,
        Product.is_active == True,  # noqa: E712
    ).all()

    # 预取用户覆盖（一次查询）
    overrides = {}
    if user_id is not None and products:
        pid_list = [p.id for p in products]
        rows = db.query(UserProductWeightOverride).filter(
            UserProductWeightOverride.user_id == user_id,
            UserProductWeightOverride.product_id.in_(pid_list),
            UserProductWeightOverride.is_active == True,  # noqa: E712
        ).all()
        overrides = {r.product_id: r.weight for r in rows}

    # 收集每个商品的当日有效记录
    product_records = {}
    for p in products:
        if mode == "recent":
            records = _collect_recent_records(db, p.id, as_of_date)
        else:
            if _get_price_records_with_fallback is not None:
                records = _get_price_records_with_fallback(db, user_id, p.id, as_of_date)
            else:
                records = []
        # 权重 + source
        if p.id in overrides:
            w, src = overrides[p.id], "override"
        else:
            w, src = (p.price_weight if p.price_weight is not None else _DEFAULT_WEIGHT), "global"
        product_records[p.id] = (records, w, {"product_id": p.id, "name": p.name, "weight_source": src})

    result = _aggregate_weighted(product_records)
    result["target_unit"] = target_unit_abbr
    return result


def _collect_recent_records(db, product_id: int, as_of_date: datetime) -> list:
    """latest-price 语义：该商品「最近有记录的那天」的全部记录。

    与 nutrition.get_ingredient_latest_price 的最近一天口径一致（去掉 24h 优先段，
    统一为「最近有记录日」以简化跨商品对齐）。
    """
    from app.models.product import ProductRecord
    latest = db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.recorded_at <= as_of_date,
    ).order_by(ProductRecord.recorded_at.desc()).first()
    if not latest:
        return []
    d = latest.recorded_at.date()
    return db.query(ProductRecord).filter(
        ProductRecord.product_id == product_id,
        ProductRecord.recorded_at >= datetime.combine(d, datetime.min.time()),
        ProductRecord.recorded_at <= datetime.combine(d, datetime.max.time()),
    ).all()
```

- [ ] **Step 4: 运行，确认全过**
```
.venv\Scripts\python -m pytest tests/services/test_ingredient_price_service.py -v
```
Expected: 13 passed。若 `as_of` 模式测试因记录 `recorded_at="2026-07-06"` 字符串与 datetime 比较失败，把种子里的 `recorded_at` 改为 `datetime(2026,7,6,12,0)`（SQLite 接受字符串，但跨库建议 datetime 对象；按实际 fixture 调整）。

- [ ] **Step 5: Commit 检查点**
```
feat(service): 加权编排函数（as_of/recent 双模式）+ 集成测试
```

---

## 阶段 3：后端接入

### Task 7: 改造 `latest-price` 端点

**Files:**
- Modify: `backend/app/api/nutrition.py:864-998`（`get_ingredient_latest_price`）

- [ ] **Step 1: 用统一服务替换「记录级简单平均」**

修改 `backend/app/api/nutrition.py` 中 `get_ingredient_latest_price` 函数体（第 878–993 行的 try 块内）。把「查询所有商品 + 取最近记录 + 算术平均」整段，替换为调用统一服务：

**替换前**（878 行 `try:` 之后到 993 行 `return result`）的整段记录遍历 + `average_price = sum(unit_prices) / len(unit_prices)` 逻辑，**替换为**：

```python
        from app.services.ingredient_price_service import get_weighted_ingredient_price

        # 查询原料
        ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        if not ingredient:
            return {"average_price": None, "unit": None, "participants": [], "mode": "none"}

        # 目标单位（用户质量偏好，fallback 斤）—— 与原逻辑一致
        target_unit_abbr = "斤"
        _mui = getattr(current_user, "default_mass_unit_id", None)
        if _mui:
            from app.models.unit import Unit as _U
            _mu = db.query(_U).filter(_U.id == _mui).first()
            if _mu and _mu.abbreviation:
                target_unit_abbr = _mu.abbreviation

        weighted = get_weighted_ingredient_price(
            db, ingredient_id,
            as_of_date=datetime.utcnow(),
            user_id=current_user.id,
            target_unit_abbr=target_unit_abbr,
            mode="recent",
        )

        if weighted["unit_price"] is None:
            return {"average_price": None, "unit": None, "participants": [], "mode": "none"}

        return {
            "average_price": round(weighted["unit_price"], 2),
            "unit": target_unit_abbr,
            "participants": weighted["participants"],
            "excluded": weighted["excluded"],
            "mode": weighted["mode"],
        }
```

> **注意：** 原端点做单位转换是因为记录单位各异。新统一服务返回的 `unit_price` 是「price/standard_quantity」口径（元/standard_unit）。若需精确折算到用户目标单位（如 斤），需在 `_collect_recent_records` 后对每条记录做单位折算——这部分沿用原端点的 `UnitConversionService.convert` 逻辑。**实现时若发现单位口径不一致**，在统一服务里补一层单位归一（参考原端点 951–978 行），并加一条单测覆盖「记录单位≠目标单位」场景。先按 standard_unit 口径返回，前端按 `unit` 字段展示。

- [ ] **Step 2: 语法检查**
```
cd backend
.venv\Scripts\python -m py_compile app\api\nutrition.py
```

- [ ] **Step 3: 手动验证（TestClient 或实际页面）**

通过原料详情页观察最新价区，确认：原料下两个商品价格悬殊时，显示加权后单价，且 `participants` 明细可见（前端展示在 Task 16）。

- [ ] **Step 4: Commit 检查点**
```
refactor(api): 原料最新价改用加权统一服务
```

---

### Task 8: 改造菜谱成本 5 变体（统一模式）

**Files:**
- Modify: `backend/app/services/recipe_service.py`：
  - `calculate_recipe_cost`（719–998，直接商品段 752–822）
  - `calculate_recipe_cost_range_as_of`（1001+，含 `_get_effective_quantity`）
  - `calculate_recipe_cost_range_trend`（1174+）
  - `calculate_recipe_cost_as_of`（2059+）
  - `calculate_recipe_cost_trend`（2308+）

> 5 个函数对「直接商品」的处理模式一致：遍历商品取**第一个**有记录的 → 改为调 `get_weighted_ingredient_price` 一次拿到加权单价。回退链（食材 fallback / 子食材聚合 / 制作菜谱）**不动**。

- [ ] **Step 1: 改造 `calculate_recipe_cost`（样板，其余 4 个同模式）**

定位 `calculate_recipe_cost` 中第 **752–822 行**（从 `products = db.query(Product)...` 到直接商品 + 前向填充两段 for 循环结束）。

**替换前**（752–822 核心是「遍历商品，找到第一个有价格记录的」）：

```python
        products = db.query(Product).filter(
            Product.ingredient_id == ingredient.id,
            Product.is_active == True
        ).all()
        ...  # 两层 for 循环遍历找第一个有记录的商品
```

**替换为**（直接调统一服务；无价时回退链由后续 `_get_ingredient_fallback` 段处理，保持不变）：

```python
        # 直接商品：加权平均（取代「取第一个有记录商品」）
        from app.services.ingredient_price_service import get_weighted_ingredient_price
        _w = get_weighted_ingredient_price(
            db, ingredient.id,
            as_of_date=now,
            user_id=user_id,
            target_unit_abbr=None,
            mode="as_of",
        )
        weighted_participants = _w["participants"] if _w["unit_price"] is not None else None
        if _w["unit_price"] is not None:
            # 加权单价口径为 元/standard_unit（与 _get_price_records_for_date 一致）
            unit_price = Decimal(str(_w["unit_price"]))
            # 标记 product 供后续单位转换段使用：取参与者中首个的 standard_unit_id
            product = db.query(Product).filter(Product.id == _w["participants"][0]["product_id"]).first()
            # 构造 day_records 供下方「单位转换」段读 standard_unit_id（单条占位）
            from app.models.product import ProductRecord as _PR
            day_records = db.query(_PR).filter(
                _PR.product_id == product.id,
            ).order_by(_PR.recorded_at.desc()).limit(1).all() if product else []
        else:
            day_records = []
```

> 紧接其后的「`if not day_records:` → `_get_ingredient_fallback`」回退链段（原 788 行起）**保持原样**。这样：直接商品无价 → 仍走食材回退 → 子食材聚合 → 制作菜谱，完全不变。

- [ ] **Step 2: 同模式改造其余 4 个变体**

对 `calculate_recipe_cost_range_as_of` / `calculate_recipe_cost_range_trend` / `calculate_recipe_cost_as_of` / `calculate_recipe_cost_trend`，定位各自「`products = db.query(Product).filter(Product.ingredient_id == ..., Product.is_active == True).all()`」之后的「遍历取第一个有记录商品」段，用 Step 1 同一段替换。

每个函数改造后，在其 `cost_breakdown.append({...})` 里追加一个字段（紧邻现有 `recipe_chain`/`aggregation_chain`）：

```python
                        "weighted_participants": weighted_participants,
```

（仅当 `weighted_participants` 不为 None 时有意义；回退链命中时为 None，与现有 chain 一致。）

- [ ] **Step 3: 语法检查 + 静态走查**
```
cd backend
.venv\Scripts\python -m py_compile app\services\recipe_service.py
```
逐个 grep 确认 5 个函数都已改造：
```
.venv\Scripts\python -c "import re,sys; t=open('app/services/recipe_service.py',encoding='utf-8').read(); print('hits:', t.count('get_weighted_ingredient_price'))"
```
Expected: `hits: 5`（5 处调用）。

- [ ] **Step 4: 回归验证**

在菜谱详情页观察成本明细：原料下多个商品时，成本基于加权价；tooltip（Task 17 完成后）可见参与商品。手算一个简单菜谱核对：两商品等权时，成本 ≈ 旧「记录数一致时的简单平均」。

- [ ] **Step 5: Commit 检查点**
```
refactor(service): 菜谱成本 5 变体改用加权统一服务
```

---

### Task 9: 改造 sparklines（原料趋势按商品级加权）

**Files:**
- Modify: `backend/app/api/sparklines.py:25-60`（`_daily_avg_for_product_ids`）+ `get_ingredients_sparklines`（103+）

- [ ] **Step 1: 理解现状**

`_daily_avg_for_product_ids` 现在把传入的多个 product_id 的所有记录按日聚合（记录级日均）。原料 sparkline 传入「该原料下所有商品 id」，导致记录多的商品被放大。

- [ ] **Step 2: 改造为按商品级日均再加权**

修改 `_daily_avg_for_product_ids`，接受 `ingredient_id` + `user_id`（可选），按日：每商品先日均 → 再按商品权重加权。

**替换** `backend/app/api/sparklines.py` 中 `_daily_avg_for_product_ids`（25–60 行）为：

```python
def _daily_avg_for_product_ids(db, product_ids, days=30, ingredient_id=None, user_id=None):
    """按日聚合：商品内日均 → 商品间按 price_weight 加权。

    未传 ingredient_id/user_id 时退化为「记录级日均」（旧行为，商品 sparkline 用）。
    """
    from app.models.product import ProductRecord
    from app.models.product_entity import Product
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)

    rows = db.query(ProductRecord).filter(
        ProductRecord.product_id.in_(product_ids),
        ProductRecord.recorded_at >= cutoff,
        ProductRecord.price.isnot(None),
    ).all()

    # 权重表
    pw = {pid: w for pid, w in db.query(Product.id, Product.price_weight)
          .filter(Product.id.in_(product_ids)).all()}

    # 按日 + 按商品：{date: {product_id: [unit_price,...]}}
    by_day_product = {}
    for r in rows:
        std_qty_f = float(r.standard_quantity) if r.standard_quantity and float(r.standard_quantity) > 0 else 500.0
        up = float(r.price) * 500.0 / std_qty_f
        dkey = r.recorded_at.date().isoformat()
        by_day_product.setdefault(dkey, {}).setdefault(r.product_id, []).append(up)

    daily_totals = {}
    for dkey, prods in by_day_product.items():
        if ingredient_id is not None:
            num = den = 0.0
            for pid, ups in prods.items():
                w = pw.get(pid, 50)
                if w <= 0:
                    continue
                num += (sum(ups) / len(ups)) * w
                den += w
            avg = num / den if den > 0 else None
        else:
            all_up = [up for ups in prods.values() for up in ups]
            avg = sum(all_up) / len(all_up) if all_up else None
        if avg is not None:
            daily_totals[dkey] = {"avg": avg}
    return [{"date": k, "avg_cost": v["avg"]} for k, v in sorted(daily_totals.items())]
```

- [ ] **Step 3: 原料 sparkline 调用处传 `ingredient_id`**

修改 `get_ingredients_sparklines`（103+ 行附近），在调用 `_daily_avg_for_product_ids` 时传入 `ingredient_id` 与 `user_id`：

```python
            data = _daily_avg_for_product_ids(
                db, prod_ids, days=days,
                ingredient_id=ing_id, user_id=current_user.id,
            )
```

> 商品 sparkline（`get_products_sparklines`）与 recipes sparkline 调用保持原签名（不传 ingredient_id），退化为旧行为。

- [ ] **Step 4: 语法检查 + 构建**
```
cd backend
.venv\Scripts\python -m py_compile app\api\sparklines.py
```

- [ ] **Step 5: Commit 检查点**
```
refactor(api): 原料 sparkline 按商品级加权
```

---

## 阶段 4：用户覆盖 API + 全局权重权限

### Task 10: 用户覆盖 schema + 端点

**Files:**
- Create: `backend/app/schemas/product_weight.py`
- Create: `backend/app/api/product_weight.py`
- Modify: `backend/app/main.py`（注册路由）

- [ ] **Step 1: 新建 schema**

创建 `backend/app/schemas/product_weight.py`：

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProductWeightOverrideBase(BaseModel):
    weight: int = Field(default=50, ge=0, le=100)


class ProductWeightOverrideCreate(ProductWeightOverrideBase):
    pass


class ProductWeightOverrideUpdate(BaseModel):
    weight: Optional[int] = Field(None, ge=0, le=100)


class ProductWeightOverrideResponse(ProductWeightOverrideBase):
    id: int
    user_id: int
    product_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class EffectiveWeightResponse(BaseModel):
    """返回某商品对当前用户的生效权重 + 来源。"""
    product_id: int
    effective_weight: int
    global_weight: int
    override_weight: Optional[int] = None
    source: str  # "override" | "global"
```

- [ ] **Step 2: 新建端点（仿 user_preferences 样板）**

创建 `backend/app/api/product_weight.py`：

```python
"""商品价格权重的用户覆盖 API（个人偏好，不走审核）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.product_entity import Product
from app.models.user_product_weight_override import UserProductWeightOverride
from app.schemas.product_weight import (
    ProductWeightOverrideCreate, ProductWeightOverrideUpdate,
    ProductWeightOverrideResponse, EffectiveWeightResponse,
)
from app.services.ingredient_price_service import _DEFAULT_WEIGHT

router = APIRouter(tags=["product-weight"])


def _get_or_none(db, user_id, product_id):
    return db.query(UserProductWeightOverride).filter(
        UserProductWeightOverride.user_id == user_id,
        UserProductWeightOverride.product_id == product_id,
        UserProductWeightOverride.is_active == True,  # noqa: E712
    ).first()


@router.get("/products/{product_id}/my-weight", response_model=EffectiveWeightResponse)
def get_my_weight(product_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    """获取该商品对当前用户的生效权重（覆盖 > 全局）。"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "商品不存在")
    ov = _get_or_none(db, current_user.id, product_id)
    gw = product.price_weight if product.price_weight is not None else _DEFAULT_WEIGHT
    if ov is not None:
        return EffectiveWeightResponse(
            product_id=product_id, effective_weight=ov.weight,
            global_weight=gw, override_weight=ov.weight, source="override",
        )
    return EffectiveWeightResponse(
        product_id=product_id, effective_weight=gw,
        global_weight=gw, override_weight=None, source="global",
    )


@router.put("/products/{product_id}/my-weight", response_model=ProductWeightOverrideResponse)
@router.put("/products/{product_id}/my-weight/", response_model=ProductWeightOverrideResponse)
def set_my_weight(product_id: int, body: ProductWeightOverrideCreate,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    """设置/更新当前用户对该商品的权重覆盖。"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "商品不存在")
    existing = db.query(UserProductWeightOverride).filter(
        UserProductWeightOverride.user_id == current_user.id,
        UserProductWeightOverride.product_id == product_id,
    ).first()
    if existing:
        existing.weight = body.weight
        existing.is_active = True
        existing.updated_by = current_user.id
        db.commit(); db.refresh(existing)
        return existing
    obj = UserProductWeightOverride(
        user_id=current_user.id, product_id=product_id,
        weight=body.weight, created_by=current_user.id, updated_by=current_user.id,
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@router.delete("/products/{product_id}/my-weight")
@router.delete("/products/{product_id}/my-weight/")
def delete_my_weight(product_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """删除当前用户对该商品的权重覆盖（回退到全局）。"""
    existing = db.query(UserProductWeightOverride).filter(
        UserProductWeightOverride.user_id == current_user.id,
        UserProductWeightOverride.product_id == product_id,
    ).first()
    if not existing:
        raise HTTPException(404, "覆盖不存在")
    existing.is_active = False
    existing.updated_by = current_user.id
    db.commit()
    return {"message": "已删除覆盖，回退到全局权重"}
```

- [ ] **Step 3: 注册路由**

在 `backend/app/main.py` 找到 `include_router` 集中区，加入：

```python
from app.api.product_weight import router as product_weight_router
app.include_router(product_weight_router, prefix="/api/v1")
```

- [ ] **Step 4: 语法检查**
```
cd backend
.venv\Scripts\python -m py_compile app\schemas\product_weight.py app\api\product_weight.py app\main.py
```

- [ ] **Step 5: Commit 检查点**
```
feat(api): 商品权重用户覆盖端点
```

---

### Task 11: 商品 update 端点对普通用户屏蔽 `price_weight`

**Files:**
- Modify: 商品 update 端点（位于 `backend/app/api/products_entity.py` 或 `ingredient_extended.py`，执行前 grep 确认 `ProductExecutor` update 的提交入口）

- [ ] **Step 1: 定位商品 update 提交入口**

```
cd backend
findstr /n "price_weight\|ProductExecutor\|apply_as_admin\|submit" app\api\products_entity.py
```
确认商品基本信息 update 走 `submit`（普通用户）/`apply_as_admin`（管理员）的分流点。

- [ ] **Step 2: 普通用户 payload 剔除 `price_weight`**

在提交提议前（普通用户分支），加一道字段过滤：

```python
        # 全局 price_weight 仅管理员可改；普通用户提交时剔除该字段
        if not getattr(current_user, "is_admin", False):
            payload = {k: v for k, v in payload.items() if k != "price_weight"}
```

管理员的 `apply_as_admin` 分支保留 `price_weight`，直写生效（`CrudExecutorBase.apply` 用 setattr 自动落到 `Product.price_weight`）。

- [ ] **Step 3: 语法检查 + 静态确认**
```
cd backend
.venv\Scripts\python -m py_compile app\api\products_entity.py
```
确认普通用户 payload 不含 `price_weight`，管理员可改。

- [ ] **Step 4: Commit 检查点**
```
feat(api): 全局商品权重仅管理员可改
```

---

## 阶段 5：前端

### Task 12: 前端 API client + 类型

**Files:**
- Create 或 Modify: `frontend/src/api/products.ts`（或既有 product api 文件）

- [ ] **Step 1: 加权重相关 API 方法**

在商品相关 api 文件中追加：

```typescript
// 商品价格权重（用户覆盖）
export interface EffectiveWeight {
  product_id: number
  effective_weight: number
  global_weight: number
  override_weight: number | null
  source: 'override' | 'global'
}

export const getProductMyWeight = (productId: number) =>
  api.get<EffectiveWeight>(`/products/${productId}/my-weight`)

export const setProductMyWeight = (productId: number, weight: number) =>
  api.put(`/products/${productId}/my-weight`, { weight })

export const deleteProductMyWeight = (productId: number) =>
  api.delete(`/products/${productId}/my-weight`)
```

- [ ] **Step 2: 构建检查**
```
cd frontend
npm run build
```
Expected: 构建通过。

- [ ] **Step 3: Commit 检查点**
```
feat(frontend): 商品权重 API client
```

---

### Task 13: ProductDetail 基本信息加权重控件

**Files:**
- Modify: `frontend/src/views/products/ProductDetail.vue`
  - 基本信息编辑表单（`basicEditForm`，1385–1393、2375–2380）
  - 模板：基本信息 `v-card`（38 行起的区块内，紧邻 tags/aliases 控件）
  - 保存：`saveBasicEdit`（2416–2438，含 is_admin 分支）

- [ ] **Step 1: `basicEditForm` 加 `priceWeight` + `myWeight` 字段**

定位 1385–1393 的 `basicEditForm` 定义，追加字段：

```typescript
  priceWeight: 50 as number,        // 全局权重（仅管理员可改）
  myWeight: null as number | null,  // 我的覆盖
  globalWeightReadOnly: 50 as number, // 详情态展示用
```

- [ ] **Step 2: 进入编辑时回填**

定位 2375 附近的 `startBasicEdit`，在回填 tags/aliases 后追加：

```typescript
    basicEditForm.value.priceWeight = product.value.price_weight ?? 50
    // 拉取当前用户生效权重
    getProductMyWeight(product.value.id).then((res: any) => {
      basicEditForm.value.myWeight = res.source === 'override' ? res.override_weight : null
      basicEditForm.value.globalWeightReadOnly = res.global_weight
    })
```

- [ ] **Step 3: 模板加控件（基本信息编辑区内）**

在基本信息编辑表单（tags/aliases 控件之后）追加：

```vue
              <!-- 全局权重：仅管理员可改 -->
              <v-text-field
                v-if="userStore.user?.is_admin"
                v-model.number="basicEditForm.priceWeight"
                label="全局价格权重 (0-100)"
                type="number"
                :rules="[v => (v >= 0 && v <= 100) || '0-100']"
                hint="原料加权平均用；50=等权，0=排除"
                persistent-hint
              />
              <v-text-field
                v-else
                :model-value="basicEditForm.globalWeightReadOnly"
                label="全局价格权重（仅管理员可改）"
                readonly
              />
              <!-- 我的权重覆盖 -->
              <v-text-field
                v-model.number="basicEditForm.myWeight"
                label="我的权重覆盖 (0-100，留空用全局)"
                type="number"
                :rules="[v => v === null || v === undefined || (v >= 0 && v <= 100) || '0-100']"
                clearable
                hint="覆盖全局权重，仅影响你自己"
                persistent-hint
              />
```

- [ ] **Step 4: 保存逻辑分流（管理员写全局；所有人写我的覆盖）**

定位 `saveBasicEdit`（2416–2438）。在现有 `api.put` 之后/之内补：

```typescript
    // 我的权重覆盖（独立端点，所有人可用）
    if (basicEditForm.value.myWeight !== null && basicEditForm.value.myWeight !== undefined) {
      await setProductMyWeight(product.value.id, basicEditForm.value.myWeight)
    } else {
      await deleteProductMyWeight(product.value.id).catch(() => {})
    }
```

管理员分支的 `api.put` payload 里加 `price_weight: basicEditForm.value.priceWeight`（普通用户分支不加，已被后端剔除兜底，但前端也不传以保持干净）：

```typescript
      const payload: any = {
        ingredient_id: basicEditForm.value.ingredient_id,
        tags: basicEditForm.value.tags,
        aliases: basicEditForm.value.aliases,
      }
      if (userStore.user?.is_admin) {
        payload.price_weight = basicEditForm.value.priceWeight
      }
```

- [ ] **Step 5: 构建 + 页面验证**
```
cd frontend
npm run build
```
页面验证：管理员能看到全局权重输入并保存；普通用户只读全局、能设「我的覆盖」。

- [ ] **Step 6: Commit 检查点**
```
feat(frontend): 商品详情基本信息加权重控件
```

---

### Task 14: IngredientDetail 商品列表编辑加权重控件

**Files:**
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`
  - 商品编辑对话框（1609 起 `编辑商品`）
  - `saveProduct`（1963–2000，含 is_admin 分支）
  - 关联商品列表展示（313 起区块，可加权重列）

- [ ] **Step 1: 商品编辑对话框加权重字段**

定位 1609 起的编辑商品对话框表单，加入两个权重控件，绑定到 `editingProduct` 表单对象。在 `editingProduct` 初始化处补字段 `priceWeight`、`myWeight`、`globalWeightReadOnly`（与 ProductDetail 的 `basicEditForm` 同构）。模板追加：

```vue
              <!-- 全局权重：仅管理员可改 -->
              <v-text-field
                v-if="userStore.user?.is_admin"
                v-model.number="editingProduct.priceWeight"
                label="全局价格权重 (0-100)"
                type="number"
                :rules="[v => (v >= 0 && v <= 100) || '0-100']"
                hint="原料加权平均用；50=等权，0=排除"
                persistent-hint
              />
              <v-text-field
                v-else
                :model-value="editingProduct.globalWeightReadOnly"
                label="全局价格权重（仅管理员可改）"
                readonly
              />
              <!-- 我的权重覆盖 -->
              <v-text-field
                v-model.number="editingProduct.myWeight"
                label="我的权重覆盖 (0-100，留空用全局)"
                type="number"
                :rules="[v => v === null || v === undefined || (v >= 0 && v <= 100) || '0-100']"
                clearable
                hint="覆盖全局权重，仅影响你自己"
                persistent-hint
              />
```

- [ ] **Step 2: `saveProduct` 分流写入**

定位 `saveProduct`（1963–2000）。在现有 `api.put(`/products/entity/${editingProductId.value}`)` 的 payload 里，管理员分支加 `price_weight`；并在保存成功后追加我的覆盖写入：

```typescript
      // payload 构造：管理员才带全局权重
      const payload: any = { /* 现有字段 */ }
      if (userStore.user?.is_admin) {
        payload.price_weight = editingProduct.value.priceWeight
      }
      const response = await api.put(`/products/entity/${editingProductId.value}`, payload)

      // 我的权重覆盖（独立端点，所有人可用）
      if (editingProduct.value.myWeight !== null && editingProduct.value.myWeight !== undefined) {
        await setProductMyWeight(editingProductId.value, editingProduct.value.myWeight)
      } else {
        await deleteProductMyWeight(editingProductId.value).catch(() => {})
      }
```

> 原有 is_admin 分支（1979 行附近的「成功/待审」提示）保持不变，仅插入上面两段。

- [ ] **Step 3: 关联商品列表加权重列（可选展示）**

在关联商品列表（313 起区块）每行右侧追加权重小标签：

```vue
                  <v-chip size="x-small" :color="p.price_weight === 0 ? 'grey' : 'default'">
                    权重 {{ p.my_weight ?? p.price_weight }}
                  </v-chip>
```

> 列表接口若未返回 `price_weight`，在 Task 15 的列表接口响应里补该字段。

- [ ] **Step 4: 构建 + 页面验证**
```
cd frontend
npm run build
```
验证：原料详情页关联商品区，每个商品可编辑权重；列表显示当前生效权重。

- [ ] **Step 5: Commit 检查点**
```
feat(frontend): 原料详情商品列表加权重编辑
```

---

### Task 15: 商品列表/详情接口返回 `price_weight`

**Files:**
- Modify: `backend/app/api/products_entity.py`（商品详情序列化、列表序列化）

- [ ] **Step 1: 序列化补字段**

定位商品详情 `_to_response` / 列表序列化函数（grep `def.*to_response` in `products_entity.py`），在返回 dict 中加：

```python
        "price_weight": product.price_weight,
```

- [ ] **Step 2: 语法检查 + 前端构建**
```
cd backend && .venv\Scripts\python -m py_compile app\api\products_entity.py
cd ..\frontend && npm run build
```

- [ ] **Step 3: Commit 检查点**
```
feat(api): 商品序列化返回 price_weight
```

---

### Task 16: 加权来源展示（原料详情最新价 + 菜谱成本 tooltip）

**Files:**
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`（最新价区，可折叠 participants）
- Modify: 菜谱成本明细组件（grep 定位 `cost_breakdown` 渲染处，通常在 RecipeDetail 或成本明细组件）

- [ ] **Step 1: 原料详情最新价区显示 participants**

定位原料详情页最新价展示区（grep `average_price` 或 `latestPrice`），在价格下方加可折叠明细：

```vue
      <v-expansion-panels v-if="latestPrice?.participants?.length">
        <v-expansion-panel>
          <v-expansion-panel-title>
            加权明细（{{ latestPrice.participants.length }} 个商品参与）
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-table density="compact">
              <thead><tr><th>商品</th><th>权重</th><th>当日单价</th><th>来源</th></tr></thead>
              <tbody>
                <tr v-for="p in latestPrice.participants" :key="p.product_id">
                  <td>{{ p.name }}</td>
                  <td>{{ p.weight }}</td>
                  <td>{{ p.unit_price.toFixed(4) }}</td>
                  <td>{{ p.weight_source === 'override' ? '我的' : '全局' }}</td>
                </tr>
              </tbody>
            </v-table>
            <div v-for="e in latestPrice.excluded" :key="e.product_id" class="text-caption text-medium-emphasis">
              已排除：{{ e.name }}（{{ e.reason === 'weight_zero' ? '权重为0' : '当日无记录' }}）
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
```

- [ ] **Step 2: 菜谱成本 tooltip 显示 weighted_participants**

定位成本明细渲染（grep `cost_breakdown` 或 `fallback_chain`），在已有 tooltip 里追加：

```vue
        <template v-if="item.weighted_participants?.length">
          <div class="text-caption mt-1">加权来源：</div>
          <div v-for="p in item.weighted_participants" :key="p.product_id" class="text-caption">
            {{ p.name }}：权重 {{ p.weight }} × 单价 {{ p.unit_price.toFixed(4) }}
          </div>
        </template>
```

- [ ] **Step 3: 构建**
```
cd frontend && npm run build
```

- [ ] **Step 4: Commit 检查点**
```
feat(frontend): 加权来源透明展示
```

---

## 阶段 6：收尾

### Task 17: 端到端集成测试

**Files:**
- Test: `backend/tests/services/test_ingredient_price_service.py`（追加）或 `backend/tests/test_product_weight_e2e.py`

- [ ] **Step 1: 追加 e2e 测试**

覆盖：管理员改全局 → 生效；普通用户改全局被剔除；不同用户看不同加权价；菜谱成本加权正确。示例：

```python
def test_admin_global_weight_applies(db):
    # 管理员把某商品全局权重改为 0 → 所有用户视角下该商品被排除
    ing_id = _seed(db, "TSK_葱", [
        ("TSK_红葱", 0, [(5, 500)]),     # 全局权重 0
        ("TSK_白葱", 50, [(8, 500)]),
    ])
    res = get_weighted_ingredient_price(
        db, ing_id, as_of_date=datetime(2026, 7, 6), user_id=999,
        target_unit_abbr="克", mode="as_of",
    )
    assert res["mode"] == "single"
    assert res["participants"][0]["name"] == "TSK_白葱"


def test_different_users_see_different_price(db):
    ing_id = _seed(db, "TSK_蒜", [
        ("TSK_普通", 50, [(10, 500)]),
        ("TSK_有机", 50, [(30, 500)]),
    ])
    from app.models.user_product_weight_override import UserProductWeightOverride
    reg = db.query(Product).filter(Product.name == "TSK_普通").first()
    # 用户 1 把有机权重覆盖为 0
    db.add(UserProductWeightOverride(user_id=1, product_id=db.query(Product).filter(Product.name=="TSK_有机").first().id, weight=0, is_active=True))
    db.commit()
    r1 = get_weighted_ingredient_price(db, ing_id, as_of_date=datetime(2026,7,6), user_id=1, target_unit_abbr="克", mode="as_of")
    r2 = get_weighted_ingredient_price(db, ing_id, as_of_date=datetime(2026,7,6), user_id=2, target_unit_abbr="克", mode="as_of")
    # 用户1：仅普通 → 0.02；用户2：等权 → 0.04
    assert abs(r1["unit_price"] - 0.02) < 1e-6
    assert abs(r2["unit_price"] - 0.04) < 1e-6
    db.query(UserProductWeightOverride).delete(); db.commit()
```

- [ ] **Step 2: 运行**
```
cd backend
.venv\Scripts\python -m pytest tests/services/test_ingredient_price_service.py -v
```
Expected: 全部 passed（含新 e2e）。

- [ ] **Step 3: 全量回归**
```
.venv\Scripts\python -m pytest tests/ -v --tb=short 2>&1 | findstr /C:"passed" /C:"failed"
```
对照基线（参见 CLAUDE.md 各 BUGFIX 记录的基线通过数），确认未引入新失败。

- [ ] **Step 4: Commit 检查点**
```
test: 商品权重端到端集成测试
```

---

### Task 18: 文档收尾（cc/ 功能记录）

**Files:**
- Create: `cc/FEATURE_商品加权价格机制.md`
- Modify: `CLAUDE.md`（索引区追加一行）

- [ ] **Step 1: 写 cc/ 功能记录**

按 CLAUDE.md「功能实现记录」索引惯例，写 `cc/FEATURE_商品加权价格机制.md`，涵盖：背景、数据模型、统一服务、改动文件清单、权限、测试结果、遗留。

- [ ] **Step 2: CLAUDE.md 索引追加**

在 `### 功能实现记录` 列表顶部追加一行指针（参照现有格式）。

- [ ] **Step 3: Commit 检查点**
```
docs: 商品加权价格机制功能记录
```

---

## Self-Review 自审记录

执行完所有任务后，对照 spec 各节确认覆盖：

- ✅ §3 数据模型 → T1–T3
- ✅ §4 聚合算法与统一服务 → T4–T6
- ✅ §4.5 改造点（latest-price / 成本 5 变体 / sparklines / 报告）→ T7–T9（报告复用 recipe_service 自动受益）
- ✅ §5.1 权限（全局仅管理员）→ T11
- ✅ §5.2 不改项（by-merchant / K线）→ 计划中不涉及
- ✅ §6 前端两处配置 + 展示 → T12–T16
- ✅ §7 default_product_id 不动 → 计划中不涉及（零迁移）
- ✅ §8 测试 → T4–T6 单测 + T17 e2e
