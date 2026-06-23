# 快速填写自定义商品顺序 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在快速填写页面自动记录用户每次保存价格记录时的商品顺序，按最近三天加权排序，实现「当前用户 × 当前商家」维度的自定义商品顺序。

**Architecture:** 后端新增 `user_merchant_product_orders` 表记录每日排序，新增 `POST product-orders` 端点写入、修改 `GET product-prices` 端点附加 `custom_sort_score`；前端 QuickFillView 在 `saveAll` 末尾调用新端点记录顺序，排序逻辑改为加权分优先。粘贴导入按文本顺序收集 product_id 再调用同一端点。

**Tech Stack:** 后端 FastAPI + SQLAlchemy + Alembic，前端 Vue 3 + TypeScript + Axios

---

### 文件结构

| 文件 | 操作 | 职责 |
|---|---|---|
| `backend/app/models/user_merchant_product_order.py` | 新建 | `UserMerchantProductOrder` SQLAlchemy 模型 |
| `backend/app/models/__init__.py` | 修改 | 注册新模型 |
| `backend/app/api/merchants.py` | 修改 | 新增 `POST product-orders` + 修改 `GET product-prices` 附加排序分 |
| `backend/app/schemas/merchant.py` | 修改 | 新增 `ProductOrderCreate` 请求 schema |
| `backend/alembic/versions/20260623_0001_add_user_merchant_product_orders.py` | 新建 | 建表迁移 |
| `backend/scripts/sql/20260623_user_merchant_product_orders_sqlite.sql` | 新建 | SQLite 建表脚本 |
| `backend/scripts/sql/20260623_user_merchant_product_orders_mysql.sql` | 新建 | MySQL 建表脚本 |
| `backend/scripts/sql/20260623_user_merchant_product_orders_postgres.sql` | 新建 | PostgreSQL 建表脚本 |
| `backend/scripts/sql/20260623_user_merchant_product_orders_postgres_gis.sql` | 新建 | PostgreSQL (PostGIS) 建表脚本 |
| `backend/tests/models/test_user_merchant_product_order.py` | 新建 | 模型单元测试 + API 集成测试 |
| `frontend/src/views/prices/QuickFillView.vue` | 修改 | saveAll 记顺序 + 排序逻辑改加分优先 + limit 调整 |
| `frontend/src/components/prices/PasteImportDialog.vue` | 修改 | doImport 按文本顺序收集 product_id 并 emit |

---

### Task 1: 新增 UserMerchantProductOrder 模型

**Files:**
- Create: `backend/app/models/user_merchant_product_order.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 创建模型文件**

```python
# backend/app/models/user_merchant_product_order.py

import sqlalchemy as sa
from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class UserMerchantProductOrder(Base):
    """用户 × 商家 × 商品的每日排序记录。"""

    __tablename__ = "user_merchant_product_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    session_date = Column(Date, nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        sa.UniqueConstraint(
            "user_id", "merchant_id", "product_id", "session_date",
            name="uq_umpo_user_merchant_product_date",
        ),
        sa.Index("idx_umpo_lookup", "user_id", "merchant_id", "session_date"),
    )
```

- [ ] **Step 2: 在 `__init__.py` 注册模型**

在 `backend/app/models/__init__.py` 末尾追加：

```python
from app.models.user_merchant_product_order import UserMerchantProductOrder
__all__.append("UserMerchantProductOrder")
```

---

### Task 2: 新增 Pydantic Schema

**Files:**
- Modify: `backend/app/schemas/merchant.py`

- [ ] **Step 1: 追加请求 schema**

在 `MerchantCoordinateResponse` 定义之后追加：

```python
class ProductOrderCreate(BaseModel):
    """保存每日排序记录的请求体。"""
    product_ids: list[int] = Field(..., min_length=1, description="本次保存的商品 ID 列表（按页面显示顺序）")
    session_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="按用户时区的会话日期 YYYY-MM-DD")
```

注意列表类型用 `list[int]`（Pydantic v2），不要用 `List[int]`（Python 3.9+）。

---

### Task 3: 新增 POST product-orders 端点

**Files:**
- Modify: `backend/app/api/merchants.py`

- [ ] **Step 1: 导入新 schema 和模型**

在文件顶部添加：

```python
from app.schemas.merchant import ProductOrderCreate
from app.models.user_merchant_product_order import UserMerchantProductOrder
```

- [ ] **Step 2: 新增端点**

在 `get_merchant_product_prices` 定义之前或之后（同 router）追加：

```python
from datetime import date as date_type


@router.post("/{merchant_id}/product-orders")
async def save_product_orders(
    merchant_id: int,
    body: ProductOrderCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """保存本次快速填写的商品顺序。

    按 (user_id, merchant_id, product_id, session_date) upsert 每条记录。
    sort_order 取 product_ids 数组的索引（从 0 开始）。
    """
    try:
        # 校验商家存在且属于当前用户
        merchant = db.query(Merchant).filter(
            Merchant.id == merchant_id,
            Merchant.user_id == current_user.id,
        ).first()
        if not merchant:
            raise HTTPException(status_code=404, detail="商家不存在")

        # 解析日期
        try:
            sess_date = date_type.fromisoformat(body.session_date)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="session_date 格式无效，应为 YYYY-MM-DD")

        existing = {}
        existing_rows = db.query(UserMerchantProductOrder).filter(
            UserMerchantProductOrder.user_id == current_user.id,
            UserMerchantProductOrder.merchant_id == merchant_id,
            UserMerchantProductOrder.session_date == sess_date,
        ).all()
        for row in existing_rows:
            key = (current_user.id, merchant_id, row.product_id, sess_date)
            existing[key] = row

        for idx, pid in enumerate(body.product_ids):
            key = (current_user.id, merchant_id, pid, sess_date)
            if key in existing:
                existing[key].sort_order = idx
            else:
                record = UserMerchantProductOrder(
                    user_id=current_user.id,
                    merchant_id=merchant_id,
                    product_id=pid,
                    session_date=sess_date,
                    sort_order=idx,
                )
                db.add(record)

        db.commit()
        return {"message": f"已保存 {len(body.product_ids)} 条排序记录"}

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
```

---

### Task 4: 修改 GET product-prices 附加 custom_sort_score

**Files:**
- Modify: `backend/app/api/merchants.py`

- [ ] **Step 1: 调整 limit 参数上限**

将 `limit: int = Query(20, ge=1, le=100)` 改为 `le=500`（快速填写页需要最多 200 个）。

- [ ] **Step 2: 在 SQL 查询之后、分页之前添加排序分计算**

在 `total = db.execute(...)` 行之后、`unit_service = UnitConversionService(db)` 之前插入：

```python
        # 计算自定义排序分（最近 3 天加权）
        from datetime import timedelta, date as date_type
        custom_scores: dict[int, float] = {}
        score_records = db.query(UserMerchantProductOrder).filter(
            UserMerchantProductOrder.user_id == current_user.id,
            UserMerchantProductOrder.merchant_id == merchant_id,
            UserMerchantProductOrder.session_date >= date_type.today() - timedelta(days=2),
        ).all()

        if score_records:
            # 按 session_date 分组加权
            today = date_type.today()
            weights: dict[date_type, int] = {}
            for offset, w in [(0, 3), (1, 2), (2, 1)]:
                d = today - timedelta(days=offset)
                weights[d] = w

            product_weights: dict[int, float] = {}  # product_id -> 加权 sort_order 和
            product_counts: dict[int, float] = {}    # product_id -> 权重和

            for rec in score_records:
                w = weights.get(rec.session_date, 0)
                if w > 0:
                    pid = rec.product_id
                    product_weights[pid] = product_weights.get(pid, 0) + rec.sort_order * w
                    product_counts[pid] = product_counts.get(pid, 0) + w

            for pid in product_weights:
                custom_scores[pid] = product_weights[pid] / product_counts[pid]
```

- [ ] **Step 3: 在 items.append 中附加 `custom_sort_score`**

在 `items.append({...})` 字典中新增一行：

```python
            "custom_sort_score": custom_scores.get(r.product_id),
```

注意：`get()` 返回 `None`（Python 类型为 `Optional[float]`），JSON 序列化后为 `null`。前端据此区分有无分数的商品。

---

### Task 5: Alembic 迁移

**Files:**
- Create: `backend/alembic/versions/20260623_0001_add_user_merchant_product_orders.py`

- [ ] **Step 1: 生成迁移文件**

```python
"""add user_merchant_product_orders table

Revision ID: 20260623_0001
Revises: <当前最新 revision ID>
Create Date: 2026-06-23 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "20260623_0001"
down_revision: Union[str, None] = "<当前最新 revision ID>"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_merchant_product_orders",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("merchant_id", sa.Integer(), nullable=False, index=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"],),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"],),
        sa.UniqueConstraint(
            "user_id", "merchant_id", "product_id", "session_date",
            name="uq_umpo_user_merchant_product_date",
        ),
    )
    op.create_index(
        "idx_umpo_lookup",
        "user_merchant_product_orders",
        ["user_id", "merchant_id", "session_date"],
    )


def downgrade() -> None:
    op.drop_index("idx_umpo_lookup", table_name="user_merchant_product_orders")
    op.drop_table("user_merchant_product_orders")
```

- [ ] **Step 2: 确认当前最新 revision ID**

运行以下命令获取：

```bash
alembic current
```

或者查看 `backend/alembic/versions/` 下最新文件的 revision ID。

将 `<当前最新 revision ID>` 替换为实际值。

- [ ] **Step 3: 运行迁移测试**

```bash
alembic upgrade head
```

预期：无错误，`user_merchant_product_orders` 表已创建。

---

### Task 6: SQL 建表脚本

**Files:** Create 4 files in `backend/scripts/sql/`

- [ ] **Step 1: SQLite**

```sql
-- backend/scripts/sql/20260623_user_merchant_product_orders_sqlite.sql
-- 快速填写自定义商品顺序 - 用户 × 商家 × 商品每日排序记录

CREATE TABLE IF NOT EXISTS user_merchant_product_orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    merchant_id INTEGER NOT NULL REFERENCES merchants(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    session_date DATE NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  DATETIME DEFAULT (datetime('now')),
    UNIQUE(user_id, merchant_id, product_id, session_date)
);

CREATE INDEX IF NOT EXISTS idx_umpo_lookup
    ON user_merchant_product_orders(user_id, merchant_id, session_date);
```

- [ ] **Step 2: MySQL**

```sql
-- backend/scripts/sql/20260623_user_merchant_product_orders_mysql.sql

CREATE TABLE IF NOT EXISTS user_merchant_product_orders (
    id          INT PRIMARY KEY AUTO_INCREMENT,
    user_id     INT NOT NULL,
    merchant_id INT NOT NULL,
    product_id  INT NOT NULL,
    session_date DATE NOT NULL,
    sort_order  INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_umpo_user_merchant_product_date (user_id, merchant_id, product_id, session_date),
    INDEX idx_umpo_lookup (user_id, merchant_id, session_date),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (merchant_id) REFERENCES merchants(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- [ ] **Step 3: PostgreSQL（无 PostGIS）**

```sql
-- backend/scripts/sql/20260623_user_merchant_product_orders_postgres.sql

CREATE TABLE IF NOT EXISTS user_merchant_product_orders (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    merchant_id INTEGER NOT NULL REFERENCES merchants(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    session_date DATE NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, merchant_id, product_id, session_date)
);

CREATE INDEX IF NOT EXISTS idx_umpo_lookup
    ON user_merchant_product_orders(user_id, merchant_id, session_date);
```

- [ ] **Step 4: PostgreSQL（有 PostGIS）**

同上（与 PostGIS 无关，内容一致）。

---

### Task 7: 后端测试

**Files:**
- Create: `backend/tests/models/test_user_merchant_product_order.py`

- [ ] **Step 1: 创建测试文件**

```python
# backend/tests/models/test_user_merchant_product_order.py

"""UserMerchantProductOrder 模型 & API 集成测试。"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.core.security import get_current_user
from app.models.user import User
from app.models.merchant import Merchant
from app.models.product import Product

# 内存库 setup（与 tests/conftest.py 类似）
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class FakeUser:
    id = 1
    username = "testuser"
    email = "test@example.com"
    phone = None
    is_admin = False
    email_verified = True
    created_at = None


def fake_current_user():
    return FakeUser()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_override():
    """每个测试前后安装/卸载 override。"""
    prev = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = fake_current_user
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(prev)


@pytest.fixture()
def db():
    """提供会话并清理所有数据。"""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
    # 清理
    session = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture()
def test_data(db):
    """创建测试用用户、商家、商品。"""
    from app.models.user_merchant_product_order import UserMerchantProductOrder

    user = User(id=1, username="testuser", email="test@example.com",
                hashed_password="x", is_admin=False)
    merchant = Merchant(id=1, user_id=1, name="测试超市")
    product_a = Product(id=1, name="牛奶", user_id=1)
    product_b = Product(id=2, name="面包", user_id=1)
    product_c = Product(id=3, name="鸡蛋", user_id=1)

    db.add_all([user, merchant, product_a, product_b, product_c])
    db.commit()
    return {"merchant_id": 1, "product_ids": [1, 2, 3]}


def _create_price_record(db, uid, mid, pid, price=1.0):
    """辅助：创建一条产品价格记录。"""
    from app.models.product_record import ProductRecord
    from app.models.unit import Unit
    unit = db.query(Unit).filter(Unit.abbreviation == "斤").first()
    if not unit:
        unit = Unit(abbreviation="斤", name="斤", unit_type="mass")
        db.add(unit)
        db.commit()
        db.refresh(unit)
    rec = ProductRecord(
        user_id=uid, merchant_id=mid, product_id=pid,
        price=price, original_quantity=1, original_unit="斤",
        standard_quantity=500, standard_unit_id=unit.id,
        record_type="price",
    )
    db.add(rec)
    db.commit()


class TestSaveProductOrders:
    """测试 POST /api/v1/merchants/{id}/product-orders"""

    def test_save_orders_success(self, db, test_data):
        mid = test_data["merchant_id"]
        pids = test_data["product_ids"]

        resp = client.post(f"/api/v1/merchants/{mid}/product-orders", json={
            "product_ids": pids,
            "session_date": "2026-06-23",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "已保存" in data["message"]

        # 验证数据已写入
        from app.models.user_merchant_product_order import UserMerchantProductOrder
        session = TestingSessionLocal()
        try:
            records = session.query(UserMerchantProductOrder).filter(
                UserMerchantProductOrder.merchant_id == mid,
                UserMerchantProductOrder.session_date == date(2026, 6, 23),
            ).order_by(UserMerchantProductOrder.sort_order).all()
            assert len(records) == 3
            assert [r.product_id for r in records] == [1, 2, 3]
            assert [r.sort_order for r in records] == [0, 1, 2]
        finally:
            session.close()

    def test_save_orders_upsert(self, db, test_data):
        """同一天同商品再次保存应更新 sort_order。"""
        mid = test_data["merchant_id"]

        # 第一次保存
        client.post(f"/api/v1/merchants/{mid}/product-orders", json={
            "product_ids": [1, 2, 3],
            "session_date": "2026-06-23",
        })
        # 第二次保存相同商品但顺序不同
        client.post(f"/api/v1/merchants/{mid}/product-orders", json={
            "product_ids": [3, 2, 1],
            "session_date": "2026-06-23",
        })

        from app.models.user_merchant_product_order import UserMerchantProductOrder
        session = TestingSessionLocal()
        try:
            records = session.query(UserMerchantProductOrder).filter(
                UserMerchantProductOrder.merchant_id == mid,
                UserMerchantProductOrder.session_date == date(2026, 6, 23),
            ).order_by(UserMerchantProductOrder.sort_order).all()
            # 应仍是 3 条记录，但顺序变为 [3, 2, 1]
            assert len(records) == 3
            assert [(r.product_id, r.sort_order) for r in records] == [(3, 0), (2, 1), (1, 2)]
        finally:
            session.close()

    def test_save_orders_invalid_date(self, db, test_data):
        mid = test_data["merchant_id"]
        resp = client.post(f"/api/v1/merchants/{mid}/product-orders", json={
            "product_ids": [1, 2],
            "session_date": "2026/06/23",  # 格式错误
        })
        assert resp.status_code == 422  # Pydantic validation

    def test_save_orders_merchant_not_found(self, db, test_data):
        resp = client.post("/api/v1/merchants/999/product-orders", json={
            "product_ids": [1, 2],
            "session_date": "2026-06-23",
        })
        assert resp.status_code == 404


class TestCustomSortScore:
    """测试 GET product-prices 返回 custom_sort_score。"""

    def _create_price_record(self, db, uid, mid, pid, price=1.0):
        """辅助：创建一条价格记录。"""
        from app.models.product_record import ProductRecord
        from app.models.unit import Unit
        unit = db.query(Unit).filter(Unit.abbreviation == "斤").first()
        if not unit:
            unit = Unit(abbreviation="斤", name="斤", unit_type="mass")
            db.add(unit)
            db.commit()
            db.refresh(unit)
        rec = ProductRecord(
            user_id=uid, merchant_id=mid, product_id=pid,
            price=price, original_quantity=1, original_unit="斤",
            standard_quantity=500, standard_unit_id=unit.id,
            record_type="price",
        )
        db.add(rec)
        db.commit()

    def test_custom_sort_score_in_response(self, db, test_data):
        """验证设置了排序分的商品有 custom_sort_score 字段。"""
        from app.models.user_merchant_product_order import UserMerchantProductOrder
        mid = test_data["merchant_id"]
        pids = test_data["product_ids"]  # [1, 2, 3]

        # 先创建价格记录（product-prices 只返回有价格记录的商品）
        _create_price_record(db, 1, mid, 1)
        _create_price_record(db, 1, mid, 2)
        _create_price_record(db, 1, mid, 3)

        # 写入排序记录
        client.post(f"/api/v1/merchants/{mid}/product-orders", json={
            "product_ids": [2, 1, 3],
            "session_date": "2026-06-23",
        })

        resp = client.get(f"/api/v1/merchants/{mid}/product-prices?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        # 找到有 custom_sort_score 的商品
        items = data["items"]
        scored = [i for i in items if i["custom_sort_score"] is not None]
        unscored = [i for i in items if i["custom_sort_score"] is None]
        assert len(scored) == 3  # 三个商品都有排序记录
        # 按 custom_sort_score 排序：应该有 2(score≈0) → 1(score≈1) → 3(score≈2)
        scored_sorted = sorted(scored, key=lambda i: i["custom_sort_score"])
        assert [s["product_id"] for s in scored_sorted] == [2, 1, 3]

    def test_no_custom_score_by_default(self, db, test_data):
        """没有排序记录时 custom_sort_score 为 null。"""
        mid = test_data["merchant_id"]
        _create_price_record(db, 1, mid, 1)

        resp = client.get(f"/api/v1/merchants/{mid}/product-prices?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["custom_sort_score"] is None


class TestWeightedSorting:
    """测试加权排序算法。"""

    def test_three_day_weighted(self, db, test_data):
        """最近 3 天加权后，今天权重最大。"""
        from app.models.user_merchant_product_order import UserMerchantProductOrder
        mid = test_data["merchant_id"]

        # 创建价格记录
        for pid in [1, 2, 3]:
            _create_price_record(db, 1, mid, pid)

        today = date.today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)

        # 前天：牛奶(0) 面包(1)
        # 昨天：鸡蛋(0) 牛奶(1)
        # 今天：面包(0)
        orders_data = [
            (1, day_before, 0), (2, day_before, 1),
            (3, yesterday, 0), (1, yesterday, 1),
            (2, today, 0),
        ]
        for pid, sess_date, sort_order in orders_data:
            rec = UserMerchantProductOrder(
                user_id=1, merchant_id=mid, product_id=pid,
                session_date=sess_date, sort_order=sort_order,
            )
            db.add(rec)
        db.commit()

        resp = client.get(f"/api/v1/merchants/{mid}/product-prices?limit=10")
        assert resp.status_code == 200
        items = resp.json()["items"]
        scored = [(i["product_id"], i["custom_sort_score"]) for i in items if i["custom_sort_score"] is not None]

        # 验证计算
        # 牛奶: (0×1 + 1×2) / 3 = 0.67
        # 面包: (1×1 + 0×3) / 4 = 0.25
        # 鸡蛋: (0×2) / 2 = 0
        score_map = {pid: score for pid, score in scored}
        assert score_map[1] == pytest.approx(0.666, abs=0.01)
        assert score_map[2] == pytest.approx(0.25, abs=0.01)
        assert score_map[3] == pytest.approx(0, abs=0.01)

        # 排序：鸡蛋(0) → 面包(0.25) → 牛奶(0.67)
        scored_sorted = sorted(scored, key=lambda x: x[1])
        assert [p[0] for p in scored_sorted] == [3, 2, 1]
```

- [ ] **Step 2: 运行测试**

```bash
cd backend
pytest tests/models/test_user_merchant_product_order.py -v
```

预期：所有测试通过。

---

### Task 8: 前端 QuickFillView 修改

**Files:**
- Modify: `frontend/src/views/prices/QuickFillView.vue`

- [ ] **Step 1: saveAll 末尾追加 record order**

在 `saveAll()` 函数末尾、`showSnackbar` 之前，找到 `addHiddenItems` 调用之后的位置，插入：

```typescript
// 保存顺序记录（仅记录有 product_id 的历史商品）
if (savedProductIds.length > 0 && selectedMerchantId.value) {
  const sessionDate = new Date().toLocaleDateString('en-CA', {
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  })
  try {
    await api.post(`/merchants/${selectedMerchantId.value}/product-orders`, {
      product_ids: savedProductIds,
      session_date: sessionDate,
    })
  } catch (e: any) {
    console.warn('[quick-fill] 记录排序失败:', e?.response?.data || e?.message || e)
    // 不影响主流程，仅 fallback 日志
  }
}
```

注意：这是纯后台记录，失败也不应阻塞用户操作——用 `try/catch` 包裹。

- [ ] **Step 2: 修改排序逻辑**

找到 `onMerchantChange()` 中的排序代码（当前使用的 `zhCollator` 排序），替换为：

```typescript
items.sort((a: any, b: any) => {
  const aScore = a.custom_sort_score
  const bScore = b.custom_sort_score
  // 有分数的排前面，没分数的排后面
  if (aScore != null && bScore == null) return -1
  if (aScore == null && bScore != null) return 1
  if (aScore != null && bScore != null) return aScore - bScore
  // 都没分数 → 默认分类 > 拼音
  const catCmp = (a.category_sort_order ?? 999999) - (b.category_sort_order ?? 999999)
  if (catCmp !== 0) return catCmp
  return zhCollator.compare(String(a.product_name ?? ''), String(b.product_name ?? ''))
})
```

- [ ] **Step 3: 调整 limit**

找到 `onMerchantChange` 中调用 `product-prices` 的 API 调用，将 `limit` 从当前值改为 `200`（或接受一个参数 `limit=200`）。

- [ ] **Step 4: 修改 onPasteImported**

```typescript
async function onPasteImported(savedProductIds: number[]) {
  if (selectedMerchantId.value && savedProductIds.length > 0) {
    const sessionDate = new Date().toLocaleDateString('en-CA', {
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    })
    try {
      await api.post(`/merchants/${selectedMerchantId.value}/product-orders`, {
        product_ids: savedProductIds,
        session_date: sessionDate,
      })
    } catch (e: any) {
      console.warn('[quick-fill] 记录粘贴导入排序失败:', e?.response?.data || e?.message || e)
    }
  }
  await onMerchantChange(selectedMerchantId.value)
}
```

---

### Task 9: 前端 PasteImportDialog 修改

**Files:**
- Modify: `frontend/src/components/prices/PasteImportDialog.vue`

- [ ] **Step 1: 扩展 emits 声明**

找到 `defineEmits` 调用，增加 `imported` 事件携带 `productIds`：

```typescript
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'imported', productIds?: number[]): void
}>()
```

- [ ] **Step 2: 在 doImport 中收集 product_id**

在 `doImport()` 函数的 `const targets = importableRows.value` 之后、并发保存循环之前，加入：

```typescript
// 按 targets 顺序记录 product_id
const savedProductIds: (number | null)[] = new Array(targets.length).fill(null)
```

在并发保存循环中，`settled.forEach((s, j)` 回调内找到 success 分支，加入：

```typescript
if (s.status === 'fulfilled') {
  success++
  // 收集 product_id（按 targets 顺序，i+j = 绝对索引）
  const idx = i + j
  if (idx >= 0) {
    if (batch[j].row.mode === 'existing' && batch[j].row.productId) {
      savedProductIds[idx] = batch[j].row.productId
    } else if (batch[j].row.mode === 'new_attach') {
      const res = (s as PromiseFulfilledResult<any>).value
      if (res?.data?.product_id) {
        savedProductIds[idx] = res.data.product_id
      }
    }
  }
}
```

注意：`i` 是外层循环的起始偏移量，`j` 是内层 batch 中的偏移，`i+j` 就是该行在 `payloads`/`targets` 中的绝对索引。

- [ ] **Step 3: 修改 emit 调用**

在 `doImport()` 末尾，`if (failures.length === 0)` 之前，保存完成后 emit：

```typescript
const validIds = savedProductIds.filter((id): id is number => id != null)
emit('imported', validIds.length > 0 ? validIds : undefined)
```

- [ ] **Step 4: 更新父组件事件处理**

回到 QuickFillView.vue，更新 `onPasteImported` 函数签名：

```diff
- async function onPasteImported() {
+ async function onPasteImported(savedProductIds?: number[]) {
```

然后在函数体内处理 `savedProductIds`（已在 Task 8 Step 4 完成）。

---

### Task 10: 验证前端构建

- [ ] **Step 1: 运行 TypeScript 类型检查**

```bash
cd frontend
npx vue-tsc --noEmit
```

预期：无类型错误。

- [ ] **Step 2: 运行 Vite 构建**

```bash
npx vite build
```

预期：构建成功，无错误。

---

## 关键设计决策

### 时区处理
- `session_date` 由前端计算，使用 `Intl.DateTimeFormat().resolvedOptions().timeZone` 获取用户时区
- 后端信任前端传入的日期，不做时区转换
- `GET product-prices` 中的加权排序使用 `date.today()`（服务器时间），仅用于近 3 天筛选，不影响前端传入的 session_date

### 失败容忍
- 排序记录写入失败不影响主流程——`try/catch` 后仅 console.warn
- 前端排序使用 `custom_sort_score`，该字段为 `null` 时回退到默认排序

### 分页限制
- `GET product-prices` 上限从 100 改为 500（后端）
- 前端默认传 `limit=200`（足够覆盖大多数超市的商品数）
- 如果仍有超出的情况，前端在 onMounted 中分批拉取所有商品后排序（入选未做，YAGNI）

### 数据清理
- 仅保留最近 3 天的排序记录用于加权
- 旧记录不做自动删除（YAGNI，后续可按需加定时任务）
