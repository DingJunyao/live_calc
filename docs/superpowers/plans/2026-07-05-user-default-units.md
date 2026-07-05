# 用户级默认单位配置 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在用户层面实现自定义默认单位（能量/质量/容积/价格记录四类偏好），替换前后端所有写死的「斤」/「kcal」默认值，并彻底删除 `Ingredient.default_unit_id` 字段。

**Architecture:** `User` 表加 4 列单位偏好，`/auth/me` 返回 `unit_preferences`（后端解析单位名）；前端抽 `useUserUnits` composable 集中读取，各组件替换写死常量；`NUTRIENT_DEFINITIONS` 两份重复合并为公共模块；菜谱原料点击转换复用现成 `POST /units/convert`。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic（后端）；Vue 3 + TypeScript + Vuetify + Pinia（前端）；SQLite（开发库）/ MySQL / PostgreSQL（生产）。

**Spec:** [docs/superpowers/specs/2026-07-05-user-default-units-design.md](../specs/2026-07-05-user-default-units-design.md)

---

## 文件结构

### 后端新建/修改

| 文件 | 责任 | 操作 |
|---|---|---|
| `backend/app/models/user.py` | User 模型 | 修改：+4 列 |
| `backend/app/models/nutrition.py` | Ingredient 模型 | 修改：删 `default_unit_id` 列 + `default_unit` 关系 |
| `backend/alembic/versions/<new>_user_units_ingredient_default_unit.py` | 迁移 | 新建 |
| `backend/scripts/sql/<new>_user_units_sqlite.sql` 等 4 份 | 三引擎 SQL | 新建 |
| `backend/app/schemas/auth.py` | auth schema | 修改：UserResponse + UserProfileUpdate |
| `backend/app/api/auth.py` | /auth/me | 修改：GET/PATCH |
| `backend/app/schemas/nutrition.py` | ingredient schema | 修改：删 2 字段 |
| `backend/app/api/ingredient_extended.py` | ingredient API | 修改：清理 10+ 处 joinedload + 返回体 |
| `backend/app/api/nutrition.py` | ingredient create/update | 修改：删默认单位逻辑 |
| `backend/app/services/enhanced_recipe_import_service.py` 等 4 个导入器 | 导入 | 修改：不写 `default_unit_id` |
| `backend/tests/test_user_unit_preferences.py` | 测试 | 新建 |

### 前端新建/修改

| 文件 | 责任 | 操作 |
|---|---|---|
| `frontend/src/composables/useUserUnits.ts` | 单位偏好读取 + calorie 转换 | 新建 |
| `frontend/src/composables/nutrientDefinitions.ts` | NUTRIENT_DEFINITIONS 公共模块 | 新建 |
| `frontend/src/views/profile/ProfileView.vue` | 设置 UI + calorie 转换 | 修改 |
| `frontend/src/views/products/ProductDetail.vue` | 记价默认/图表/能量/营养 | 修改 |
| `frontend/src/views/ingredients/IngredientDetail.vue` | 记价默认/图表/能量/营养/删 default_unit 编辑 | 修改 |
| `frontend/src/views/prices/PricesView.vue` | 记价默认 | 修改 |
| `frontend/src/views/prices/QuickFillView.vue` | 记价默认 | 修改 |
| `frontend/src/components/prices/QuickPriceRecordDialog.vue` | 记价默认 | 修改 |
| `frontend/src/components/prices/PasteImportDialog.vue` | 解析无单位兜底 | 修改 |
| `frontend/src/views/recipes/RecipeDetail.vue` | 能量单位 | 修改 |
| `frontend/src/components/recipes/RecipeIngredientCard.vue` | 点击转换 | 修改 |

---

## Phase A · 后端数据层

### Task 1: User 模型加 4 列 + Ingredient 删字段

**Files:**
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/models/nutrition.py`

- [ ] **Step 1: User 模型加 4 列**

`backend/app/models/user.py` 在 `daily_budget` 行之后插入 4 列：

```python
    daily_budget = Column(Float, nullable=True, default=None)
    # 用户默认单位偏好（NULL 时前端 fallback）
    default_energy_unit = Column(String(10), nullable=True)  # 'kcal' | 'kJ'
    default_mass_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    default_volume_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    default_price_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Ingredient 模型删 default_unit_id 列与关系**

`backend/app/models/nutrition.py`：

删除列定义（约 26 行）：
```python
# 删除这一行
    default_unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, index=True)
```

删除关系（约 61 行）：
```python
# 删除这一行
    default_unit = relationship("Unit", lazy="select", foreign_keys=[default_unit_id])
```

- [ ] **Step 3: 验证模型可导入**

Run: `cd backend && .venv\Scripts\python.exe -c "from app.models.user import User; from app.models.nutrition import Ingredient; print('OK')"`
Expected: `OK`（无 ImportError）

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/user.py backend/app/models/nutrition.py
git commit -m "feat(models): add User unit preferences + drop Ingredient.default_unit_id"
```

---

### Task 2: alembic 迁移

**Files:**
- Create: `backend/alembic/versions/20260705_user_units_and_drop_ingredient_default_unit.py`

- [ ] **Step 1: 新建迁移文件**

```python
"""add user unit preferences and drop ingredient default_unit_id

Revision ID: 20260705_user_units
Revises: <当前 head>
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # User 加 4 列
    op.add_column('users', sa.Column('default_energy_unit', sa.String(10), nullable=True))
    op.add_column('users', sa.Column('default_mass_unit_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('default_volume_unit_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('default_price_unit_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_default_mass_unit', 'users', 'units',
                          ['default_mass_unit_id'], ['id'])
    op.create_foreign_key('fk_users_default_volume_unit', 'users', 'units',
                          ['default_volume_unit_id'], ['id'])
    op.create_foreign_key('fk_users_default_price_unit', 'users', 'units',
                          ['default_price_unit_id'], ['id'])

    # Ingredient 删 default_unit_id（SQLite 需表重建，batch_alter 安全跨引擎）
    with op.batch_alter_table('ingredients') as batch_op:
        batch_op.drop_column('default_unit_id')


def downgrade() -> None:
    with op.batch_alter_table('ingredients') as batch_op:
        batch_op.add_column(sa.Column('default_unit_id', sa.Integer(),
                                      sa.ForeignKey('units.id'), nullable=True))
    op.drop_constraint('fk_users_default_price_unit', 'users', type_='foreignkey')
    op.drop_constraint('fk_users_default_volume_unit', 'users', type_='foreignkey')
    op.drop_constraint('fk_users_default_mass_unit', 'users', type_='foreignkey')
    op.drop_column('users', 'default_price_unit_id')
    op.drop_column('users', 'default_volume_unit_id')
    op.drop_column('users', 'default_mass_unit_id')
    op.drop_column('users', 'default_energy_unit')
```

⚠️ 先用 `alembic heads` 查当前 head revision id，替换 `<当前 head>` 与 `Revises:`。

- [ ] **Step 2: 验证迁移可被 alembic 识别**

Run: `cd backend && .venv\Scripts\python.exe -m alembic heads`
Expected: 列出新 head（无报错）

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/20260705_user_units_and_drop_ingredient_default_unit.py
git commit -m "feat(alembic): migration for user units + drop ingredient default_unit_id"
```

---

### Task 3: 三引擎 SQL 脚本

**Files:**
- Create: `backend/scripts/sql/20260705_user_units_sqlite.sql`
- Create: `backend/scripts/sql/20260705_user_units_mysql.sql`
- Create: `backend/scripts/sql/20260705_user_units_postgres.sql`
- Create: `backend/scripts/sql/20260705_user_units_postgres_postgis.sql`

- [ ] **Step 1: SQLite 脚本**（batch_alter 等价；SQLite 删 FK 列需表重建，这里给出 add column + 重建 ingredients 表的完整流程）

写入 `backend/scripts/sql/20260705_user_units_sqlite.sql`：

```sql
-- 用户单位偏好（4 列）
ALTER TABLE users ADD COLUMN default_energy_unit VARCHAR(10);
ALTER TABLE users ADD COLUMN default_mass_unit_id INTEGER REFERENCES units(id);
ALTER TABLE users ADD COLUMN default_volume_unit_id INTEGER REFERENCES units(id);
ALTER TABLE users ADD COLUMN default_price_unit_id INTEGER REFERENCES units(id);

-- ingredients 删 default_unit_id：SQLite 需表重建
BEGIN TRANSACTION;
CREATE TABLE ingredients_new (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(200) NOT NULL,
  category_id INTEGER REFERENCES ingredient_categories(id),
  density NUMERIC(10, 6),
  aliases JSON,
  nutrition_id INTEGER REFERENCES nutrition_data(id),
  piece_weight NUMERIC(10, 3),
  piece_weight_unit_id INTEGER REFERENCES units(id),
  serving_weight NUMERIC(10, 3),
  serving_weight_unit_id INTEGER REFERENCES units(id),
  ai_inferred BOOLEAN NOT NULL DEFAULT 0,
  is_imported BOOLEAN NOT NULL DEFAULT 0,
  is_merged BOOLEAN NOT NULL DEFAULT 0,
  merged_into_id INTEGER REFERENCES ingredients(id),
  created_at DATETIME,
  updated_at DATETIME,
  created_by INTEGER,
  updated_by INTEGER,
  is_active BOOLEAN NOT NULL DEFAULT 1
);
-- 复制数据（不含 default_unit_id；列顺序按建表顺序对齐，先 SELECT 确认源列）
INSERT INTO ingredients_new (id, name, category_id, density, aliases, nutrition_id,
  piece_weight, piece_weight_unit_id, serving_weight, serving_weight_unit_id,
  ai_inferred, is_imported, is_merged, merged_into_id,
  created_at, updated_at, created_by, updated_by, is_active)
SELECT id, name, category_id, density, aliases, nutrition_id,
  piece_weight, piece_weight_unit_id, serving_weight, serving_weight_unit_id,
  ai_inferred, is_imported, is_merged, merged_into_id,
  created_at, updated_at, created_by, updated_by, is_active
FROM ingredients;
DROP TABLE ingredients;
ALTER TABLE ingredients_new RENAME TO ingredients;
-- 重建既有索引（按需补充，可用 .schema ingredients 原样恢复）
CREATE INDEX ix_ingredients_name ON ingredients (name);
CREATE INDEX ix_ingredients_is_active ON ingredients (is_active);
COMMIT;
```

⚠️ 执行前先用 `.schema ingredients` 核对源表列与索引，按实际补全 `CREATE INDEX`。

- [ ] **Step 2: MySQL 脚本**

写入 `backend/scripts/sql/20260705_user_units_mysql.sql`：

```sql
ALTER TABLE users
  ADD COLUMN default_energy_unit VARCHAR(10) NULL,
  ADD COLUMN default_mass_unit_id INT NULL,
  ADD COLUMN default_volume_unit_id INT NULL,
  ADD COLUMN default_price_unit_id INT NULL,
  ADD CONSTRAINT fk_users_default_mass_unit   FOREIGN KEY (default_mass_unit_id)   REFERENCES units(id),
  ADD CONSTRAINT fk_users_default_volume_unit FOREIGN KEY (default_volume_unit_id) REFERENCES units(id),
  ADD CONSTRAINT fk_users_default_price_unit  FOREIGN KEY (default_price_unit_id)  REFERENCES units(id);

ALTER TABLE ingredients DROP COLUMN default_unit_id;
```

- [ ] **Step 3: PostgreSQL 脚本（PostGIS 未启用与启用通用，本变更与 PostGIS 无关）**

写入 `backend/scripts/sql/20260705_user_units_postgres.sql` 与 `20260705_user_units_postgres_postgis.sql`（内容相同）：

```sql
ALTER TABLE users
  ADD COLUMN default_energy_unit VARCHAR(10),
  ADD COLUMN default_mass_unit_id INTEGER REFERENCES units(id),
  ADD COLUMN default_volume_unit_id INTEGER REFERENCES units(id),
  ADD COLUMN default_price_unit_id INTEGER REFERENCES units(id);

ALTER TABLE ingredients DROP COLUMN default_unit_id;
```

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/sql/20260705_user_units_*.sql
git commit -m "feat(sql): user units + drop ingredient default_unit_id for sqlite/mysql/pg"
```

---

### Task 4: 开发库直接补（开发库不走 alembic）

⚠️ 本项目开发库由 `create_all()` 建表，不走 alembic（参见 [BUGFIX_共享转型表结构漂移](../../../cc/BUGFIX_共享转型表结构漂移.md)）。

- [ ] **Step 1: 备份开发库**

Run:
```bash
cd backend/data
copy livecalc.db "livecalc.db.bak_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%"
```
（PowerShell 下用 `Copy-Item livecalc.db livecalc.db.bak_<timestamp>`）

- [ ] **Step 2: 用 SQLite MCP 或 sqlite3 执行 Task 3 的 SQLite 脚本**

通过项目配置的 SQLite MCP 执行 `20260705_user_units_sqlite.sql` 全文；或：
```bash
cd backend && .venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('data/livecalc.db'); c.executescript(open('scripts/sql/20260705_user_units_sqlite.sql').read()); c.commit(); print('done')"
```

- [ ] **Step 3: 验证 schema 生效**

Run:
```bash
cd backend && .venv\Scripts\python.exe -c "
import sqlite3
c = sqlite3.connect('data/livecalc.db')
print('users cols:', [r[1] for r in c.execute('PRAGMA table_info(users)')])
print('ingredients cols:', [r[1] for r in c.execute('PRAGMA table_info(ingredients)')])
"
```
Expected: `users cols` 含 4 个新列；`ingredients cols` 不含 `default_unit_id`。

- [ ] **Step 4: ORM 层验证**

Run:
```bash
cd backend && .venv\Scripts\python.exe -c "
from app.core.database import SessionLocal
from app.models.user import User
from app.models.nutrition import Ingredient
db = SessionLocal()
u = db.query(User).first()
print('user default_energy_unit attr:', u.default_energy_unit)
i = db.query(Ingredient).first()
print('ingredient has default_unit_id attr:', hasattr(i, 'default_unit_id'))
db.close()
"
```
Expected: `user default_energy_unit attr: None`；`ingredient has default_unit_id attr: False`。

---

## Phase B · 后端 API：用户单位偏好

### Task 5: auth schema 扩展

**Files:**
- Modify: `backend/app/schemas/auth.py`

- [ ] **Step 1: UserResponse 增 unit_preferences 字段**

`backend/app/schemas/auth.py` 的 `UserResponse`：

```python
class UnitPreference(BaseModel):
    id: int
    name: str
    abbreviation: str


class UnitPreferences(BaseModel):
    energy_unit: Optional[str] = None
    mass_unit: Optional[UnitPreference] = None
    volume_unit: Optional[UnitPreference] = None
    price_unit: Optional[UnitPreference] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone: Optional[str]
    is_admin: bool
    is_active: bool = True
    email_verified: bool
    created_at: Optional[str] = None
    nutrition_goals: Optional[dict] = None
    daily_budget: Optional[float] = None
    unit_preferences: Optional[UnitPreferences] = None

    class Config:
        from_attributes = True
```

- [ ] **Step 2: UserProfileUpdate 加 4 字段**

```python
class UserProfileUpdate(BaseModel):
    """用户自行更新个人设置（营养目标、预算、单位偏好）。"""
    daily_calorie_target: Optional[float] = None
    daily_protein_target: Optional[float] = None
    daily_carb_target: Optional[float] = None
    daily_fat_target: Optional[float] = None
    daily_budget: Optional[float] = None
    default_energy_unit: Optional[str] = None
    default_mass_unit_id: Optional[int] = None
    default_volume_unit_id: Optional[int] = None
    default_price_unit_id: Optional[int] = None
```

- [ ] **Step 3: py_compile**

Run: `cd backend && .venv\Scripts\python.exe -m py_compile app/schemas/auth.py`
Expected: 无输出（成功）

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/auth.py
git commit -m "feat(schema): add unit_preferences to UserResponse/UserProfileUpdate"
```

---

### Task 6: /auth/me GET/PATCH 单位偏好

**Files:**
- Modify: `backend/app/api/auth.py`

- [ ] **Step 1: 加单位偏好构造辅助函数**

在 `backend/app/api/auth.py` 顶部 import 区加：

```python
from app.schemas.auth import (
    # ... 现有 ...
    UnitPreference, UnitPreferences,
)
from app.models.unit import Unit
```

在 `_get_bool_config` 之后加辅助函数：

```python
def _build_unit_preferences(user: User, db: Session) -> UnitPreferences:
    """从 User 的 4 个单位字段构造 unit_preferences，解析单位名。"""
    def _pref(uid):
        if uid is None:
            return None
        u = db.query(Unit).filter(Unit.id == uid).first()
        if not u:
            return None
        return UnitPreference(id=u.id, name=u.name, abbreviation=u.abbreviation)

    return UnitPreferences(
        energy_unit=user.default_energy_unit,
        mass_unit=_pref(user.default_mass_unit_id),
        volume_unit=_pref(user.default_volume_unit_id),
        price_unit=_pref(user.default_price_unit_id),
    )
```

- [ ] **Step 2: GET /me 返回 unit_preferences**

修改 `get_me`（约 239 行），在 `daily_budget=...` 后加一行 `unit_preferences=_build_unit_preferences(current_user, db)`。给函数签名加 `db: Session = Depends(get_db)`：

```python
@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户信息（含营养目标、预算、单位偏好）。"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        created_at=serialize_datetime(current_user.created_at) if current_user.created_at else None,
        nutrition_goals={
            "daily_calorie_target": current_user.daily_calorie_target,
            "daily_protein_target": current_user.daily_protein_target,
            "daily_carb_target": current_user.daily_carb_target,
            "daily_fat_target": current_user.daily_fat_target,
        },
        daily_budget=current_user.daily_budget,
        unit_preferences=_build_unit_preferences(current_user, db),
    )
```

- [ ] **Step 3: PATCH /me 接收 4 字段 + 类型校验**

修改 `patch_me`（约 263 行），在写入循环后、`db.commit()` 前插入校验：

```python
@router.patch("/me", response_model=UserResponse)
async def patch_me(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户更新自己的营养目标、预算、单位偏好设置。"""
    update_data = profile_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有需要更新的字段")

    # 单位偏好校验
    if "default_energy_unit" in update_data:
        val = update_data["default_energy_unit"]
        if val is not None and val not in ("kcal", "kJ"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="default_energy_unit 必须是 kcal 或 kJ")

    _UNIT_TYPE_EXPECT = {
        "default_mass_unit_id": "mass",
        "default_volume_unit_id": "volume",
        "default_price_unit_id": None,  # 允许 mass/volume/count
    }
    _PRICE_ALLOWED = {"mass", "volume", "count"}
    for field, expected_type in _UNIT_TYPE_EXPECT.items():
        if field in update_data and update_data[field] is not None:
            uid = update_data[field]
            u = db.query(Unit).filter(Unit.id == uid).first()
            if not u:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"{field}={uid} 不存在")
            if expected_type is None:
                if u.unit_type not in _PRICE_ALLOWED:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail=f"价格记录单位必须是 mass/volume/count，得到 {u.unit_type}")
            elif u.unit_type != expected_type:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"{field} 必须是 {expected_type} 类型单位，得到 {u.unit_type}")

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
        email_verified=current_user.email_verified,
        created_at=serialize_datetime(current_user.created_at) if current_user.created_at else None,
        nutrition_goals={
            "daily_calorie_target": current_user.daily_calorie_target,
            "daily_protein_target": current_user.daily_protein_target,
            "daily_carb_target": current_user.daily_carb_target,
            "daily_fat_target": current_user.daily_fat_target,
        },
        daily_budget=current_user.daily_budget,
        unit_preferences=_build_unit_preferences(current_user, db),
    )
```

- [ ] **Step 4: py_compile**

Run: `cd backend && .venv\Scripts\python.exe -m py_compile app/api/auth.py`
Expected: 无输出

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/auth.py
git commit -m "feat(auth): /me returns unit_preferences + PATCH with type validation"
```

---

### Task 7: 后端测试 — /auth/me 单位偏好

**Files:**
- Create: `backend/tests/test_user_unit_preferences.py`

- [ ] **Step 1: 写测试（TDD）**

```python
"""用户单位偏好 /auth/me 测试。"""
from tests.conftest import client, register_and_login  # 按现有 conftest 调整


def test_get_me_returns_unit_preferences_null_when_unset():
    token = register_and_login()
    resp = client.get("/api/v1/auth/me",
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    up = resp.json()["unit_preferences"]
    assert up["energy_unit"] is None
    assert up["mass_unit"] is None
    assert up["volume_unit"] is None
    assert up["price_unit"] is None


def test_patch_me_sets_unit_preferences():
    token = register_and_login()
    # 先取一个 mass 单位 id 与一个 volume 单位 id
    units = client.get("/api/v1/units/").json()
    items = units if isinstance(units, list) else units["items"]
    mass_id = next(u["id"] for u in items if u["unit_type"] == "mass")
    volume_id = next(u["id"] for u in items if u["unit_type"] == "volume")
    count_id = next(u["id"] for u in items if u["unit_type"] == "count")

    resp = client.patch("/api/v1/auth/me",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"default_energy_unit": "kJ",
                              "default_mass_unit_id": mass_id,
                              "default_volume_unit_id": volume_id,
                              "default_price_unit_id": count_id})
    assert resp.status_code == 200
    up = resp.json()["unit_preferences"]
    assert up["energy_unit"] == "kJ"
    assert up["mass_unit"]["id"] == mass_id
    assert up["volume_unit"]["id"] == volume_id
    assert up["price_unit"]["id"] == count_id


def test_patch_me_rejects_wrong_unit_type():
    token = register_and_login()
    units = client.get("/api/v1/units/").json()
    items = units if isinstance(units, list) else units["items"]
    volume_id = next(u["id"] for u in items if u["unit_type"] == "volume")
    # 把 volume 单位塞给 mass 字段应 400
    resp = client.patch("/api/v1/auth/me",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"default_mass_unit_id": volume_id})
    assert resp.status_code == 400


def test_patch_me_rejects_invalid_energy_unit():
    token = register_and_login()
    resp = client.patch("/api/v1/auth/me",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"default_energy_unit": "calorie"})
    assert resp.status_code == 400


def test_patch_me_clears_preference_with_null():
    token = register_and_login()
    units = client.get("/api/v1/units/").json()
    items = units if isinstance(units, list) else units["items"]
    mass_id = next(u["id"] for u in items if u["unit_type"] == "mass")
    # 先设
    client.patch("/api/v1/auth/me",
                 headers={"Authorization": f"Bearer {token}"},
                 json={"default_mass_unit_id": mass_id})
    # 再清
    resp = client.patch("/api/v1/auth/me",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"default_mass_unit_id": None})
    assert resp.status_code == 200
    assert resp.json()["unit_preferences"]["mass_unit"] is None
```

⚠️ 按现有 `backend/tests/conftest.py` 调整 `register_and_login` 的实际签名。

- [ ] **Step 2: 跑测试，预期失败（GET 已实现，但验证全绿）**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/test_user_unit_preferences.py -v`
Expected: 5 passed（GET/PATCH 已在 Task 6 实现；若失败则回到 Task 6 修）

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_user_unit_preferences.py
git commit -m "test(auth): user unit preferences GET/PATCH incl. type validation"
```

---

## Phase C · 后端清理 Ingredient.default_unit_id

### Task 8: schemas/nutrition.py 删字段

**Files:**
- Modify: `backend/app/schemas/nutrition.py:13-14`

- [ ] **Step 1: 删除两行**

定位（约 13-14 行）：
```python
    default_unit_id: Optional[int] = None
    default_unit_name: Optional[str] = None
```
整行删除。

- [ ] **Step 2: grep 确认 schema 内无残留**

Run: `cd backend && findstr /N "default_unit" app\schemas\nutrition.py`
Expected: 无匹配。

- [ ] **Step 3: py_compile + Commit**

```bash
cd backend && .venv\Scripts\python.exe -m py_compile app/schemas/nutrition.py
git add backend/app/schemas/nutrition.py
git commit -m "refactor(schema): drop default_unit_id/default_unit_name from ingredient schema"
```

---

### Task 9: ingredient_extended.py 清理（10+ 处）

**Files:**
- Modify: `backend/app/api/ingredient_extended.py`

该文件以下行处均需清理（删 `joinedload(Ingredient.default_unit)` 行 + 返回字典中的 `"default_unit": ...` 键）：

| 行 | 内容 | 处理 |
|---|---|---|
| 185-190 | autocomplete joinedload + `default_unit` 变量 | 删 joinedload 行、删变量声明 |
| 198 | `"default_unit": default_unit,` | 删 |
| 219 | 详情 joinedload | 删 joinedload 行 |
| 247 | children joinedload | 删 |
| 254 | children `"default_unit"` | 删 |
| 265 | 详情 `"default_unit"` | 删 |
| 318-329 | resolve hierarchy joinedload + `"default_unit"` | 删 joinedload、删键 |
| 346-362 | alternatives joinedload + `"default_unit"` | 删 joinedload、删键 |
| 369-404 | `_get_default_mass_unit_id` + create_ingredient 默认斤逻辑 | **删整个函数 + 删 `default_unit` 参数 + 删 unit_id 解析分支 + `Ingredient(...)` 不传 `default_unit_id`** |
| 411 | `default_unit_id=unit_id,` | 删 |
| 504-516 | create 返回体 joinedload + `"default_unit"` | 删 joinedload、删键 |
| 534-569 | update_ingredient `default_unit`/`default_unit_id` 参数 + payload 分支 | 删参数、删分支 |
| 685-699 | update 返回体 joinedload + `default_unit_id`/`default_unit_name` | 删 joinedload、删键 |
| 797, 852 | list joinedload | 删 |
| 891, 916, 936 | list/detail 返回 `"default_unit"` | 删键 |

- [ ] **Step 1: 删 `_get_default_mass_unit_id` 函数（约 369-376 行）**

定位：
```python
def _get_default_mass_unit_id(db: Session) -> Optional[int]:
    """获取默认质量单位（斤）的 ID"""
    jin_unit = db.query(Unit).filter(Unit.abbreviation == "斤").first()
    if jin_unit:
        ...
```
整段函数删除。

- [ ] **Step 2: create_ingredient 删 default_unit 参数与默认斤逻辑**

函数签名（约 382-385 行）删 `default_unit: Optional[str] = Body(None),`。

函数体（约 396-411）：
```python
        # 删除整个 unit_id 解析块：
        #   unit_id = None
        #   if default_unit: ...
        #   else: unit_id = _get_default_mass_unit_id(db)
        # 并把 Ingredient(...) 里的 default_unit_id=unit_id, 这一行删除
        new_ingredient = Ingredient(
            name=name,
            category_id=category_id,
            aliases=aliases or [],
            density=density,
            created_by=current_user.id
        )
```

- [ ] **Step 3: update_ingredient 删 default_unit 相关参数与 payload 分支**

函数签名（约 534-535）删 `default_unit` 与 `default_unit_id` 两个参数。

函数体（约 563-569）删除：
```python
        if default_unit_id is not None:
            payload["default_unit_id"] = default_unit_id if default_unit_id > 0 else None
        elif default_unit is not None:
            from app.services.unit_matcher import UnitMatcher
            matcher = UnitMatcher(db)
            unit_obj = matcher.match_or_create_unit(default_unit)
            payload["default_unit_id"] = unit_obj.id if unit_obj else None
```

- [ ] **Step 4: 批量删所有 `joinedload(Ingredient.default_unit)` 行**

共约 8 处（行 186, 219, 247, 319, 347, 506, 687, 797, 852, 916）。逐一删除整行 `joinedload(Ingredient.default_unit),`。注意保留同处其它 `joinedload`（如 `category_obj`、`serving_weight_unit`）。

- [ ] **Step 5: 批量删返回字典中的 `"default_unit"` / `"default_unit_id"` / `"default_unit_name"` 键**

共约 9 处（行 190 声明的 `default_unit =` 变量、198、254、265、329、362、516、698-699、891、936）。逐一删除。

- [ ] **Step 6: 删除文件顶部不再使用的 import（若 Unit 仅用于已删函数）**

grep 确认 `Unit` 是否还被该文件其它地方用：
Run: `cd backend && findstr /N "Unit" app\api\ingredient_extended.py`
若仅剩 import 行无使用，删除 import。

- [ ] **Step 7: py_compile**

Run: `cd backend && .venv\Scripts\python.exe -m py_compile app/api/ingredient_extended.py`
Expected: 无输出

- [ ] **Step 8: grep 确认文件内无残留 default_unit**

Run: `cd backend && findstr /N "default_unit" app\api\ingredient_extended.py`
Expected: 无匹配。

- [ ] **Step 9: Commit**

```bash
git add backend/app/api/ingredient_extended.py
git commit -m "refactor(api): purge Ingredient.default_unit from ingredient_extended"
```

---

### Task 10: nutrition.py 清理 create/update ingredient

**Files:**
- Modify: `backend/app/api/nutrition.py`

需清理位置（来自 grep）：

| 行 | 内容 | 处理 |
|---|---|---|
| 263-265, 382-384 | select/load 列含 `Ingredient.default_unit_id` | 删该列引用 |
| 394-399 | `get_ingredient` 计算 `default_unit_name` | 删整段 |
| 412-413 | `get_ingredient` 返回 `default_unit_id`/`default_unit_name` | 删两键 |
| 434-483 | `create_ingredient`：签名 `default_unit_id` 参数 + 默认斤逻辑 + 返回 | 删参数、删默认斤块、删返回键 |
| 494-533 | `update_ingredient`：签名 + 赋值 + 返回 | 删参数、删赋值行、删返回键 |

- [ ] **Step 1: create_ingredient 删 default_unit_id 参数与默认斤逻辑**

签名（约 436 行）删 `default_unit_id: int = Body(None),`。

函数体（约 450-461）改为：
```python
        new_ingredient = Ingredient(
            name=name,
            aliases=aliases_list,
            created_by=current_user.id,
            updated_by=current_user.id
        )
```
（删除 `unit_id = default_unit_id; if unit_id is None: ...` 整块，删除 `default_unit_id=unit_id,` 行）

返回体（约 469-482）删除 `default_unit_name` 计算块与 `"default_unit_id"` / `"default_unit_name"` 两键。

- [ ] **Step 2: update_ingredient 删 default_unit_id**

签名（约 496）删 `default_unit_id: Optional[int] = Body(None),`。

函数体（约 519-520）删除：
```python
        if default_unit_id is not None:
            ingredient.default_unit_id = default_unit_id
```
返回体（约 531）删 `"default_unit_id": ingredient.default_unit_id,`。

- [ ] **Step 3: get_ingredient 删 default_unit_name**

约 394-399 删除：
```python
        default_unit_name = None
        if ingredient.default_unit_id:
            unit = db.query(Unit).filter(Unit.id == ingredient.default_unit_id).first()
            if unit:
                default_unit_name = unit.name
```
返回体（约 412-413）删 `default_unit_id` / `default_unit_name` 两键。

select 列引用（约 263-265, 382-384）删 `Ingredient.default_unit_id,` 行。

- [ ] **Step 4: py_compile + grep 确认**

Run: `cd backend && .venv\Scripts\python.exe -m py_compile app/api/nutrition.py && findstr /N "default_unit" app\api\nutrition.py`
Expected: 无输出 + 无匹配。

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/nutrition.py
git commit -m "refactor(api): purge Ingredient.default_unit from nutrition create/update/get"
```

---

### Task 11: 导入服务清理 default_unit_id

**Files:**
- Modify: `backend/app/services/enhanced_recipe_import_service.py`
- Modify: `backend/app/services/json_recipe_import_service.py`
- Modify: `backend/app/services/recipe_import_service.py`
- Modify: `backend/app/services/importer/importers/howtocook.py`

- [ ] **Step 1: 定位所有写入点**

Run: `cd backend && findstr /N "default_unit_id\|_get_default_mass_unit_id\|default_unit" app\services\enhanced_recipe_import_service.py app\services\json_recipe_import_service.py app\services\recipe_import_service.py app\services\importer\importers\howtocook.py`

- [ ] **Step 2: 逐文件删除 default_unit_id 赋值**

每个文件中，凡是 `Ingredient(...)` 构造或 `ingredient.default_unit_id = ...` 赋值或 `default_unit_id=...` 关键字参数，整行/整键删除。

典型模式（enhanced/json/howtocook）：
```python
# 删除这种行：
ingredient = Ingredient(name=..., default_unit_id=<jin_id>, ...)
# 改为：
ingredient = Ingredient(name=..., ...)
```

若文件内有本地 `_get_default_mass_unit_id` 辅助函数，整函数删除。

- [ ] **Step 3: py_compile 全部 + grep 确认**

Run:
```bash
cd backend
.venv\Scripts\python.exe -m py_compile app/services/enhanced_recipe_import_service.py app/services/json_recipe_import_service.py app/services/recipe_import_service.py app/services/importer/importers/howtocook.py
findstr /N "default_unit" app\services\enhanced_recipe_import_service.py app\services\json_recipe_import_service.py app\services\recipe_import_service.py app\services\importer\importers\howtocook.py
```
Expected: 无输出 + 无匹配。

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/enhanced_recipe_import_service.py backend/app/services/json_recipe_import_service.py backend/app/services/recipe_import_service.py backend/app/services/importer/importers/howtocook.py
git commit -m "refactor(import): stop writing Ingredient.default_unit_id"
```

---

### Task 12: 后端整体校验 + executor 适配确认

- [ ] **Step 1: 全后端 grep 确认无 default_unit_id 写/读残留**

Run: `cd backend && findstr /S /N "default_unit" app\*.py`
Expected: 仅可能剩 `entity_unit_overrides` 等无关项；不应有 `Ingredient.default_unit` 或 `default_unit_id`（ingredient 语义）。

- [ ] **Step 2: 验证 IngredientExecutor 动态反射不受影响**

executor 的 snapshot（[ingredient.py:244](../../../backend/app/services/proposals/executors/ingredient.py#L244)）用 `{c.name: ... for c in ing.__table__.columns}` 动态反射列——删字段后自动不含 `default_unit_id`，无需改。

Run（跑现有 executor 相关测试）:
```bash
cd backend && .venv\Scripts\python.exe -m pytest tests/test_proposals_framework.py tests/test_shared_data.py -v
```
Expected: 通过数不低于基线（允许既有无关失败）。

- [ ] **Step 3: 启动后端确认无报错（手动，开发者已有自动重载服务）**

观察后端日志，确认无 `AttributeError: default_unit` 或 `no such column: default_unit_id`。

- [ ] **Step 4: 全量回归测试**

Run: `cd backend && .venv\Scripts\python.exe -m pytest tests/ -v --tb=short`
Expected: 失败数不高于基线（既有 auth/import/locations 等无关失败可接受），不应新增因 default_unit 引起的失败。

- [ ] **Step 5: Commit（如有零散修复）**

```bash
git add -A
git commit -m "fix(backend): cleanup residual default_unit references"
```

---

## Phase D · 前端基础

### Task 13: useUserUnits composable

**Files:**
- Create: `frontend/src/composables/useUserUnits.ts`

- [ ] **Step 1: 写 composable**

```typescript
// composables/useUserUnits.ts
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

export interface UnitPref {
  id: number
  name: string
  abbreviation: string
}

const FALLBACK_MASS_NAME = '斤'
const FALLBACK_VOLUME_NAME = 'mL'
const FALLBACK_PRICE_NAME = '斤'

export function useUserUnits() {
  const userStore = useUserStore()
  const up = computed(() => (userStore.user as any)?.unit_preferences ?? null)

  const energyUnit = computed<'kcal' | 'kJ'>(() => up.value?.energy_unit ?? 'kcal')
  const massUnit = computed<UnitPref | null>(() => up.value?.mass_unit ?? null)
  const volumeUnit = computed<UnitPref | null>(() => up.value?.volume_unit ?? null)
  const priceUnit = computed<UnitPref | null>(() => up.value?.price_unit ?? null)

  const massUnitName = computed(() => massUnit.value?.name ?? FALLBACK_MASS_NAME)
  const volumeUnitName = computed(() => volumeUnit.value?.name ?? FALLBACK_VOLUME_NAME)
  const priceUnitName = computed(() => priceUnit.value?.name ?? FALLBACK_PRICE_NAME)

  // calorie 转换：库存 kcal，前端按 energyUnit 显示/输入
  const toDisplayCalorie = (kcal: number | null | undefined): number | null => {
    if (kcal === null || kcal === undefined) return null
    return energyUnit.value === 'kJ' ? +(kcal * 4.184).toFixed(0) : kcal
  }
  const fromDisplayCalorie = (v: number | null | undefined): number | null => {
    if (v === null || v === undefined) return null
    return energyUnit.value === 'kJ' ? +(v / 4.184).toFixed(0) : v
  }

  return {
    energyUnit, massUnit, volumeUnit, priceUnit,
    massUnitName, volumeUnitName, priceUnitName,
    toDisplayCalorie, fromDisplayCalorie,
  }
}
```

- [ ] **Step 2: build 验证**

Run: `cd frontend && npm run build`
Expected: 成功（composable 未被引用时不报错）。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/composables/useUserUnits.ts
git commit -m "feat(frontend): add useUserUnits composable"
```

---

### Task 14: nutrientDefinitions.ts 抽离（DRY）+ 三处接入

**Files:**
- Create: `frontend/src/composables/nutrientDefinitions.ts`
- Modify: `frontend/src/views/products/ProductDetail.vue`（约 1399-1470）
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`（约 2151-2220）
- Modify: `frontend/src/views/recipes/RecipeDetail.vue`（约 599）

- [ ] **Step 1: 抽离公共模块**

```typescript
// composables/nutrientDefinitions.ts
export interface NutrientDef {
  key: string
  label: string
  units: string[]
  defaultUnit: string
}

// 基础定义（能量 defaultUnit 由 buildNutrientDefinitions 参数化）
const BASE_DEFS: Omit<NutrientDef, 'defaultUnit'>[] = [
  { key: 'energy', label: '能量', units: ['kcal', 'kJ'] },
  { key: 'protein', label: '蛋白质', units: ['g', 'mg'] },
  { key: 'fat', label: '脂肪', units: ['g', 'mg'] },
  { key: 'carbohydrate', label: '碳水化合物', units: ['g', 'mg'] },
  { key: 'fiber', label: '膳食纤维', units: ['g'] },
  { key: 'calcium', label: '钙', units: ['mg', 'μg', 'g'] },
  { key: 'iron', label: '铁', units: ['mg', 'μg'] },
  { key: 'sodium', label: '钠', units: ['mg', 'g'] },
  { key: 'potassium', label: '钾', units: ['mg', 'g'] },
  { key: 'vitamin_a_rae', label: '维生素A', units: ['μg', 'IU', 'mg'] },
  { key: 'vitamin_c', label: '维生素C', units: ['mg', 'g'] },
  { key: 'vitamin_b1', label: '维生素B1', units: ['mg', 'μg'] },
  { key: 'vitamin_b2', label: '维生素B2', units: ['mg', 'μg'] },
  { key: 'vitamin_b12', label: '维生素B12', units: ['μg', 'mg'] },
  { key: 'vitamin_d', label: '维生素D', units: ['μg', 'IU'] },
  { key: 'vitamin_e', label: '维生素E', units: ['mg', 'IU'] },
  { key: 'vitamin_k', label: '维生素K', units: ['μg', 'mg'] },
  { key: 'magnesium', label: '镁', units: ['mg', 'g'] },
  { key: 'zinc', label: '锌', units: ['mg', 'μg'] },
  { key: 'selenium', label: '硒', units: ['μg', 'mg'] },
  { key: 'cholesterol', label: '胆固醇', units: ['mg', 'g'] },
  { key: 'saturated_fat', label: '饱和脂肪', units: ['g', 'mg'] },
  { key: 'folate', label: '叶酸', units: ['μg', 'mg'] },
  { key: 'phosphorus', label: '磷', units: ['mg', 'g'] },
  { key: 'copper', label: '铜', units: ['mg', 'μg'] },
  { key: 'manganese', label: '锰', units: ['mg', 'μg'] },
  { key: 'vitamin_b6', label: '维生素B6', units: ['mg', 'μg'] },
  { key: 'pantothenic_acid', label: '维生素B5', units: ['mg'] },
  { key: 'monounsaturated_fat', label: '单不饱和脂肪', units: ['g', 'mg'] },
  { key: 'polyunsaturated_fat', label: '多不饱和脂肪', units: ['g', 'mg'] },
]

const DEFAULT_UNIT_BY_KEY: Record<string, string> = {
  energy: 'kcal',  // 由 buildNutrientDefinitions 覆盖
  protein: 'g', fat: 'g', carbohydrate: 'g', fiber: 'g',
  calcium: 'mg', iron: 'mg', sodium: 'mg', potassium: 'mg',
  vitamin_a_rae: 'μg', vitamin_c: 'mg', vitamin_b1: 'mg', vitamin_b2: 'mg',
  vitamin_b12: 'μg', vitamin_d: 'μg', vitamin_e: 'mg', vitamin_k: 'μg',
  magnesium: 'mg', zinc: 'mg', selenium: 'μg', cholesterol: 'mg',
  saturated_fat: 'g', folate: 'μg', phosphorus: 'mg', copper: 'mg',
  manganese: 'mg', vitamin_b6: 'mg', pantothenic_acid: 'mg',
  monounsaturated_fat: 'g', polyunsaturated_fat: 'g',
}

export function buildNutrientDefinitions(energyUnit: 'kcal' | 'kJ' = 'kcal'): NutrientDef[] {
  return BASE_DEFS.map(d => ({
    ...d,
    defaultUnit: d.key === 'energy' ? energyUnit : DEFAULT_UNIT_BY_KEY[d.key],
  }))
}
```

- [ ] **Step 2: ProductDetail.vue 接入**

替换本地 `const NUTRIENT_DEFINITIONS = [...]`（约 1399-1430）为：

```typescript
import { buildNutrientDefinitions } from '@/composables/nutrientDefinitions'
import { useUserUnits } from '@/composables/useUserUnits'
const { energyUnit } = useUserUnits()
const NUTRIENT_DEFINITIONS = computed(() => buildNutrientDefinitions(energyUnit.value))
```

⚠️ NUTRIENT_DEFINITIONS 现在是 Ref，所有使用处加 `.value`（或用 `NUTRIENT_DEFINITIONS.value`）。`getDefaultNutrientDef`（约 1469）的能量分支 `defaultUnit = isEnergy ? 'kcal'` 改为 `isEnergy ? energyUnit.value`。

逐处用 grep 确认使用点：`cd frontend && grep -n "NUTRIENT_DEFINITIONS" src/views/products/ProductDetail.vue`，把所有引用改为 `.value`（在 setup 中自动解包的场景除外）。

- [ ] **Step 3: IngredientDetail.vue 接入**

同 Step 2，替换本地 `NUTRIENT_DEFINITIONS`（约 2151-2220）为 `computed(() => buildNutrientDefinitions(energyUnit.value))`，加 import，使用处加 `.value`。

- [ ] **Step 4: RecipeDetail.vue 能量单位**

[RecipeDetail.vue:599](../../../frontend/src/views/recipes/RecipeDetail.vue#L599) `coreNutritionItems`：

```typescript
import { useUserUnits } from '@/composables/useUserUnits'
const { energyUnit } = useUserUnits()
const coreNutritionItems = computed(() => [
  { key: '能量', label: '能量', unit: energyUnit.value },
  { key: '蛋白质', label: '蛋白质', unit: 'g' },
  { key: '脂肪', label: '脂肪', unit: 'g' },
  { key: '碳水化合物', label: '碳水化合物', unit: 'g' },
  { key: '钠', label: '钠', unit: 'mg' }
])
```
使用处加 `.value`。

- [ ] **Step 5: build**

Run: `cd frontend && npm run build`
Expected: 成功。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/composables/nutrientDefinitions.ts frontend/src/views/products/ProductDetail.vue frontend/src/views/ingredients/IngredientDetail.vue frontend/src/views/recipes/RecipeDetail.vue
git commit -m "refactor(frontend): extract NUTRIENT_DEFINITIONS DRY + energy unit per user pref"
```

---

## Phase E · 前端个人中心

### Task 15: ProfileView 单位偏好设置 UI

**Files:**
- Modify: `frontend/src/views/profile/ProfileView.vue`

- [ ] **Step 1: 设置列表新增「单位偏好」入口**

在「饮食偏好」`v-list-item`（约 94-103 行）之后插入：

```html
        <v-list-item @click="openUnitPrefsDialog">
          <template #prepend>
            <v-icon>mdi-ruler</v-icon>
          </template>
          <v-list-item-title>单位偏好</v-list-item-title>
          <v-list-item-subtitle>能量 / 质量 / 容积 / 记价默认单位</v-list-item-subtitle>
          <template #append>
            <v-icon>mdi-chevron-right</v-icon>
          </template>
        </v-list-item>
```

- [ ] **Step 2: 加对话框 + 状态 + 加载/保存逻辑**

在 `<script setup>` 加：

```typescript
import { useUserUnits } from '@/composables/useUserUnits'
const { energyUnit } = useUserUnits()

const unitPrefsDialog = ref(false)
const savingUnitPrefs = ref(false)
const unitOptionsAll = ref<any[]>([])
const unitPrefsForm = ref({
  default_energy_unit: 'kcal' as 'kcal' | 'kJ',
  default_mass_unit_id: null as number | null,
  default_volume_unit_id: null as number | null,
  default_price_unit_id: null as number | null,
})

const massUnitOptions = computed(() => unitOptionsAll.value.filter(u => u.unit_type === 'mass'))
const volumeUnitOptions = computed(() => unitOptionsAll.value.filter(u => u.unit_type === 'volume'))
const priceUnitOptions = computed(() => unitOptionsAll.value.filter(u => ['mass', 'volume', 'count'].includes(u.unit_type)))

async function openUnitPrefsDialog() {
  const u = userStore.user as any
  unitPrefsForm.value = {
    default_energy_unit: u?.unit_preferences?.energy_unit ?? 'kcal',
    default_mass_unit_id: u?.unit_preferences?.mass_unit?.id ?? null,
    default_volume_unit_id: u?.unit_preferences?.volume_unit?.id ?? null,
    default_price_unit_id: u?.unit_preferences?.price_unit?.id ?? null,
  }
  if (!unitOptionsAll.value.length) {
    try {
      const res = await api.get('/units/', { params: { limit: 200 } })
      unitOptionsAll.value = (res.items || res || []) as any[]
    } catch (e) { /* ignore */ }
  }
  unitPrefsDialog.value = true
}

async function saveUnitPrefs() {
  savingUnitPrefs.value = true
  try {
    await api.patch('/auth/me', {
      default_energy_unit: unitPrefsForm.value.default_energy_unit || null,
      default_mass_unit_id: unitPrefsForm.value.default_mass_unit_id || null,
      default_volume_unit_id: unitPrefsForm.value.default_volume_unit_id || null,
      default_price_unit_id: unitPrefsForm.value.default_price_unit_id || null,
    })
    await userStore.fetchUser()
    unitPrefsDialog.value = false
  } catch (e: any) {
    notify('保存失败：' + (e?.userMessage || e?.message || '未知错误'), 'error')
  } finally {
    savingUnitPrefs.value = false
  }
}
```

`computed` 已在文件顶部 import；如未 import 则补 `import { ref, computed, onMounted, watch } from 'vue'`。

- [ ] **Step 3: 加对话框模板**

在「饮食偏好」对话框之后插入：

```html
    <!-- 单位偏好对话框 -->
    <v-dialog v-model="unitPrefsDialog" max-width="480">
      <v-card>
        <v-card-title class="d-flex align-center">
          单位偏好
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="unitPrefsDialog = false" />
        </v-card-title>
        <v-card-text>
          <p class="text-caption text-medium-emphasis mb-4">
            设置你的默认单位，所有页面将按此显示与填写。
          </p>
          <v-select
            v-model="unitPrefsForm.default_energy_unit"
            :items="[{ title: '千卡 (kcal)', value: 'kcal' }, { title: '千焦 (kJ)', value: 'kJ' }]"
            item-title="title"
            item-value="value"
            label="能量单位"
            variant="outlined"
            density="compact"
            class="mb-3"
          />
          <v-autocomplete
            v-model="unitPrefsForm.default_mass_unit_id"
            :items="massUnitOptions"
            item-title="name"
            item-value="id"
            label="默认质量单位"
            variant="outlined"
            density="compact"
            class="mb-3"
            clearable
          />
          <v-autocomplete
            v-model="unitPrefsForm.default_volume_unit_id"
            :items="volumeUnitOptions"
            item-title="name"
            item-value="id"
            label="默认容积单位"
            variant="outlined"
            density="compact"
            class="mb-3"
            clearable
          />
          <v-autocomplete
            v-model="unitPrefsForm.default_price_unit_id"
            :items="priceUnitOptions"
            item-title="name"
            item-value="id"
            label="默认记价单位（含个/包/瓶）"
            variant="outlined"
            density="compact"
            clearable
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="unitPrefsDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="savingUnitPrefs" @click="saveUnitPrefs">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
```

- [ ] **Step 4: build**

Run: `cd frontend && npm run build`
Expected: 成功。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/profile/ProfileView.vue
git commit -m "feat(profile): unit preferences settings dialog"
```

---

### Task 16: daily_calorie_target 跟随能量单位转换

**Files:**
- Modify: `frontend/src/views/profile/ProfileView.vue`

- [ ] **Step 1: 输入框标签按能量单位 + 数值转换**

「每日热量」`v-text-field`（约 178-188 行）改为：

```html
              <v-text-field
                v-model.number="nutritionForm.daily_calorie_target"
                :label="`每日热量 (${energyUnit})`"
                type="number"
                variant="outlined"
                density="compact"
                hide-details="auto"
                :min="energyUnit === 'kJ' ? 2000 : 500"
                :max="energyUnit === 'kJ' ? 21000 : 5000"
                step="50"
              />
```

- [ ] **Step 2: openNutritionDialog 打开时按能量单位换算显示**

Task 15 已 `import { useUserUnits }` 并 `const { energyUnit } = useUserUnits()`——本 Step **扩展该解构**（不重复 import），把那行改为：

```typescript
const { energyUnit, toDisplayCalorie, fromDisplayCalorie } = useUserUnits()
```

然后修改 `openNutritionDialog`（约 388 行），用 `toDisplayCalorie`：

```typescript

function openNutritionDialog() {
  const u = userStore.user as any
  const storedKcal = u?.nutrition_goals?.daily_calorie_target ?? 2000
  nutritionForm.value = {
    daily_calorie_target: toDisplayCalorie(storedKcal) as number,
    daily_protein_target: u?.nutrition_goals?.daily_protein_target ?? 60,
    daily_carb_target: u?.nutrition_goals?.daily_carb_target ?? 300,
    daily_fat_target: u?.nutrition_goals?.daily_fat_target ?? 65,
    daily_budget: u?.daily_budget ?? null,
  }
  nutritionDialog.value = true
}
```

- [ ] **Step 3: saveNutrition 保存时换算回 kcal**

修改 `saveNutrition`（约 401 行）：

```typescript
async function saveNutrition() {
  savingNutrition.value = true
  try {
    await api.patch('/auth/me', {
      daily_calorie_target: fromDisplayCalorie(nutritionForm.value.daily_calorie_target),
      daily_protein_target: nutritionForm.value.daily_protein_target || null,
      daily_carb_target: nutritionForm.value.daily_carb_target || null,
      daily_fat_target: nutritionForm.value.daily_fat_target || null,
      daily_budget: nutritionForm.value.daily_budget || null,
    })
    await userStore.fetchUser()
    nutritionDialog.value = false
  } catch (e: any) {
    notify('保存失败：' + (e?.userMessage || e?.message || '未知错误'), 'error')
  } finally {
    savingNutrition.value = false
  }
}
```

- [ ] **Step 4: build**

Run: `cd frontend && npm run build`
Expected: 成功。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/profile/ProfileView.vue
git commit -m "feat(profile): daily_calorie_target follows user energy unit"
```

---

## Phase F · 前端接入点替换

### Task 17: 记价默认单位接入（6 文件）

每个文件：import `useUserUnits`，把硬编码 `'斤'`（记价场景）替换为 `priceUnitName.value`。

**Files:**
- Modify: `frontend/src/views/products/ProductDetail.vue`
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`
- Modify: `frontend/src/views/prices/PricesView.vue`
- Modify: `frontend/src/views/prices/QuickFillView.vue`
- Modify: `frontend/src/components/prices/QuickPriceRecordDialog.vue`
- Modify: `frontend/src/components/prices/PasteImportDialog.vue`

- [ ] **Step 1: ProductDetail.vue**

import（顶部 script）：`import { useUserUnits } from '@/composables/useUserUnits'` + `const { priceUnitName } = useUserUnits()`。

替换（注意仅记价场景，图表单位在 Task 18）：
- 行 1557: `unit: '斤',` → `unit: priceUnitName.value,`
- 行 1571: `unit: currentIngredientDefaultUnit.value || '斤',` → `unit: priceUnitName.value,`（currentIngredientDefaultUnit 整体弃用——原料默认单位已删，改用用户偏好；该 computed（2099-2105）可一并删除）
- 行 1583: `unit: record.original_unit || '斤',` → `unit: record.original_unit || priceUnitName.value,`
- 行 2686: `priceForm.value = { price: 0, quantity: 1, unit: '斤', merchant_id: null }` → `unit: priceUnitName.value,`

删除 `currentIngredientDefaultUnit` computed（约 2099-2105）及其使用。

- [ ] **Step 2: IngredientDetail.vue**

import + `const { priceUnitName } = useUserUnits()`。

- 行 2099: `unit: '斤',` → `unit: priceUnitName.value,`

- [ ] **Step 3: PricesView.vue**

import + `const { priceUnitName } = useUserUnits()`。

- 行 706: `original_unit: '斤',` → `original_unit: priceUnitName.value,`

- [ ] **Step 4: QuickFillView.vue**

import + `const { priceUnitName } = useUserUnits()`。

- 行 436: `unit: '斤',` → `unit: priceUnitName.value,`
- 行 457: `unit: '斤',` → `unit: priceUnitName.value,`
- 行 391-394 fallback：`{ title: '斤 (斤)', value: '斤' },` → `{ title: \`${priceUnitName.value} (${priceUnitName.value})\`, value: priceUnitName.value },`；`{ title: '个 (个)', value: '个' },` 保留（计数兜底）。

- [ ] **Step 5: QuickPriceRecordDialog.vue**

import + `const { priceUnitName } = useUserUnits()`。

- 行 155: `original_unit: '斤',` → `original_unit: priceUnitName.value,`
- 行 250: `original_unit: props.defaultUnit || '斤',` → `original_unit: props.defaultUnit || priceUnitName.value,`
- 行 169: FALLBACK_UNITS 中 `{ title: '斤', value: '斤' }` 保持（API 加载失败兜底，不动）。

- [ ] **Step 6: PasteImportDialog.vue — 解析无单位时兜底**

import + `const { priceUnitName } = useUserUnits()`。

定位解析函数（解析每行 `名称 价格[/数量单位]`）。在解析出 `row.unit` 后，若为空则填 `priceUnitName.value`：

```typescript
// 解析后：
if (!row.unit) {
  row.unit = priceUnitName.value
}
```

具体位置：定位 `rawText` 解析成 rows 的函数，在 `row.unit` 赋值处加兜底。

- [ ] **Step 7: build**

Run: `cd frontend && npm run build`
Expected: 成功。

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/products/ProductDetail.vue frontend/src/views/ingredients/IngredientDetail.vue frontend/src/views/prices/PricesView.vue frontend/src/views/prices/QuickFillView.vue frontend/src/components/prices/QuickPriceRecordDialog.vue frontend/src/components/prices/PasteImportDialog.vue
git commit -m "feat(frontend): default price-record unit reads user preference"
```

---

### Task 18: 价格趋势图表单位接入

**Files:**
- Modify: `frontend/src/views/products/ProductDetail.vue:2096`
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`（价格趋势 unit 传参）

- [ ] **Step 1: ProductDetail.vue chartUnit**

import 补 `massUnitName`（与 Task 17 同一 useUserUnits 调用）：`const { priceUnitName, massUnitName } = useUserUnits()`。

- 行 2096: `const chartUnit = computed(() => '斤')` → `const chartUnit = computed(() => massUnitName.value)`

- [ ] **Step 2: 后端聚合 standard_unit 折算目标对齐**

⚠️ 关键：图表把所有记录折算到 chartUnit 显示。改 chartUnit 为用户质量单位后，后端聚合（`/products/{id}/price-trend` 等端点）若硬编码折算到「斤/克」，标签与数值会不一致。

定位后端折算点：
Run: `cd backend && findstr /S /N "standard_unit\|price_per\|斤" app\api\products.py app\api\products_entity.py`

若后端按固定单位折算，且前端要按用户单位显示，两种修法（择一，按实际代码定）：
- (a) 后端聚合端点接收 `target_unit` 查询参数，按用户单位折算返回（推荐，前端传 `massUnitName`）。
- (b) 前端拿到后端「按克」聚合的数据后，本地用 si_factor 转到用户单位（仅同类质量转换，可行）。

实现时按实际后端结构选；若后端已按「克」返回且前端原本转「斤」，改为转 `massUnitName` 即可（方案 b，最小改动）。

- [ ] **Step 3: IngredientDetail.vue 价格趋势单位**

定位其价格趋势 `<PriceTrendChart :unit="...">`，把硬编码「斤」改为 `massUnitName.value`。同样按 Step 2 处理后端折算对齐。

Run: `cd frontend && grep -n "PriceTrendChart\|chartUnit\|'斤'" src/views/ingredients/IngredientDetail.vue`

- [ ] **Step 4: build**

Run: `cd frontend && npm run build`
Expected: 成功。

- [ ] **Step 5: 手动验证（开发者已有自动重载服务）**

打开商品/原料详情，价格趋势图 Y 轴标签应显示用户质量单位（如「kg」），数据点数值应与标签匹配。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/products/ProductDetail.vue frontend/src/views/ingredients/IngredientDetail.vue
git commit -m "feat(frontend): price trend chart uses user mass unit"
```

---

### Task 19: 菜谱原料点击转换

**Files:**
- Modify: `frontend/src/components/recipes/RecipeIngredientCard.vue`

- [ ] **Step 1: import useUserUnits + 状态**

`<script setup>` 顶部加：

```typescript
import { useUserUnits } from '@/composables/useUserUnits'
import { api } from '@/api/client'

const { massUnit, volumeUnit, massUnitName, volumeUnitName } = useUserUnits()

// 每行转换状态：key=ingredient.id，value='original' | 'converted'
const convertState = ref<Record<number, 'original' | 'converted'>>({})
// 转换结果缓存：key=`${ingId}:${from}:${to}`，value=转换后数值
const convertCache = ref<Record<string, number>>({})
const converting = ref<Record<number, boolean>>({})
```

- [ ] **Step 2: 转换函数**

```typescript
// 判断原料单位类型（按 abbreviation/name 粗判；后端 units 表有 unit_type 但原料行只有 unit 字符串）
async function ensureConverted(ingredient: RecipeIngredient): Promise<{ value: string; unit: string } | null> {
  const fromUnit = ingredient.unit
  if (!fromUnit || !ingredient.quantity) return null
  // 目标单位：先尝试质量，再体积（按单位名匹配由后端 /units/convert 判定类型）
  const targets = [massUnit.value, volumeUnit.value]
  for (const target of targets) {
    if (!target) continue
    const cacheKey = `${ingredient.id}:${fromUnit}:${target.abbreviation}`
    if (cacheKey in convertCache.value) {
      return { value: formatQty(convertCache.value[cacheKey] * servingsRatio(ingredient)), unit: target.name }
    }
    try {
      const res = await api.post('/units/convert', {
        value: Number(ingredient.quantity), from_unit: fromUnit, to_unit: target.abbreviation,
      })
      if (res?.value !== undefined && res.value !== null) {
        convertCache.value[cacheKey] = res.value
        return { value: formatQty(res.value * servingsRatio(ingredient)), unit: target.name }
      }
    } catch { /* 该方向不可转，试下一个 target */ }
  }
  return null  // 无法转换
}

function servingsRatio(ingredient: RecipeIngredient): number {
  return displayServings.value / originalServings.value
}

function formatQty(n: number): string {
  if (Number.isInteger(n)) return n.toString()
  return n.toFixed(2).replace(/\.?0+$/, '')
}

async function toggleConvert(ingredient: RecipeIngredient) {
  const cur = convertState.value[ingredient.id]
  if (cur === 'converted') {
    convertState.value[ingredient.id] = 'original'
    return
  }
  // 适量/少许/无单位 → 提示
  if (!ingredient.unit || ['适量', '少许'].includes(String(ingredient.original_quantity))) return
  converting.value[ingredient.id] = true
  try {
    const got = await ensureConverted(ingredient)
    if (got) convertState.value[ingredient.id] = 'converted'
    // 转换失败：不切（保持原始）
  } finally {
    converting.value[ingredient.id] = false
  }
}
```

⚠️ `/units/convert` 请求体字段名按后端 [UnitConvertRequest](../../../backend/app/api/units.py#L347) 实际定义调整（`from_unit` / `to_unit` 可能是 id 或字符串；若是 id，需先把 ingredient.unit 字符串解析成 id——可前端先 `GET /units/` 缓存 name→id 映射）。

- [ ] **Step 3: 模板加切换交互**

把行 100-113 的数量 `<div>` 改为可点击 + 双态显示：

```html
            <div
              class="ingredient-quantity text-body-2 text-right mr-4 cursor-pointer"
              style="min-width: 80px"
              @click="toggleConvert(ingredient)"
              :title="convertState[ingredient.id] === 'converted' ? '点击切回原始' : '点击转换为我偏好的单位'"
            >
              <template v-if="convertState[ingredient.id] === 'converted'">
                <v-icon v-if="converting[ingredient.id]" size="small" class="mr-1">mdi-loading</v-icon>
                <ConvertedQuantity :ingredient="ingredient" />
              </template>
              <template v-else-if="ingredient.quantity && ingredient.quantity_range">
                {{ ingredient.quantity_range.min }}~{{ ingredient.quantity_range.max }} {{ ingredient.unit }}
                <span class="text-medium-emphasis">（推荐 {{ ingredient.quantity }} {{ ingredient.unit }}）</span>
              </template>
              <span v-else-if="scaleQuantity(ingredient.quantity, originalServings)">
                {{ scaleQuantity(ingredient.quantity, originalServings) }} {{ ingredient.unit }}
              </span>
              <span v-else-if="ingredient.quantity_range">
                {{ ingredient.quantity_range.min }}~{{ ingredient.quantity_range.max }} {{ ingredient.unit }}
              </span>
              <span v-else-if="ingredient.original_quantity">{{ ingredient.original_quantity }}</span>
              <span v-else>-</span>
              <v-chip
                v-if="convertState[ingredient.id]"
                size="x-small"
                variant="tonal"
                color="primary"
                class="ml-1"
              >{{ convertState[ingredient.id] === 'converted' ? (massUnitName + '/' + volumeUnitName) : '' }}</v-chip>
            </div>
```

`ConvertedQuantity` 是个轻量子组件（或用内联 async component）。简化方案：直接用 `ensureConverted` 同步读缓存渲染——点击前先 await，渲染时读 `convertCache` + 目标单位。为避免子组件复杂度，推荐用「点击即 await 转换 → 转换结果存入 reactive `convertedDisplay[ingId] = {value, unit}`，模板直接渲染」：

替换上方 `<ConvertedQuantity>` 为：
```html
<span>{{ convertedDisplay[ingredient.id]?.value }} {{ convertedDisplay[ingredient.id]?.unit }}</span>
```
并在 `ensureConverted` 成功后 `convertedDisplay.value[ingredient.id] = got`。

加 `const convertedDisplay = ref<Record<number, { value: string; unit: string }>>({})`。

- [ ] **Step 4: build**

Run: `cd frontend && npm run build`
Expected: 成功。

- [ ] **Step 5: 手动验证**

打开菜谱详情，点原料数量 → 切换为用户单位；再点 → 切回。「适量」行点击无反应（不切）。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/recipes/RecipeIngredientCard.vue
git commit -m "feat(recipe): click-to-convert ingredient quantity to user unit"
```

---

### Task 20: serving_weight 等产出量显示接入

**Files:**
- Modify: 各显示 `serving_weight` 的页面（grep 定位）

- [ ] **Step 1: 定位全部显示点**

Run: `cd frontend && grep -rn "serving_weight" src/`

预期涉及：`IngredientDetail.vue`（半成品产出量显示）、`RecipeDetail.vue`（成品产出）、相关成本明细 tooltip。

- [ ] **Step 2: 按「质量→massUnitName / 体积→volumeUnitName」替换显示**

每处显示 `serving_weight` + 单位的地方：
- 若显示单位是质量类（g/kg/斤）→ 标签/数值用 `massUnitName`（数值需 si_factor 转换；若后端已按某基准返回，前端转）。
- 若体积类 → `volumeUnitName`。

最小实现：显示标签从硬编码单位改为用户偏好单位名；数值若需跨单位换算则用前端 si_factor 或调 `/units/convert`。

- [ ] **Step 3: build + 手动验证**

Run: `cd frontend && npm run build`
Expected: 成功。

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(frontend): serving_weight display uses user unit"
```

---

## Phase G · 收尾

### Task 21: 全量 grep 扫尾 + build + 静态校验

- [ ] **Step 1: 前端 grep 确认无遗漏的硬编码「斤」/kcal**

Run:
```bash
cd frontend && grep -rn "'斤'\|\"斤\"\|: '斤'\|unit: 'kcal'\|defaultUnit: 'kcal'" src/
```
逐项核查：应仅剩 FALLBACK 兜底常量（如 QuickPriceRecordDialog `FALLBACK_UNITS`）与 import.meta 元数据；记价/图表/能量场景不应再有。

- [ ] **Step 2: 后端 grep 确认无 default_unit 残留（ingredient 语义）**

Run: `cd backend && findstr /S /N "Ingredient.default_unit\|default_unit_id" app\*.py`
Expected: 无 ingredient 语义的 default_unit_id（允许 entity_unit_overrides 等无关项）。

- [ ] **Step 3: 前端 build**

Run: `cd frontend && npm run build`
Expected: 成功，无类型错误。

- [ ] **Step 4: 后端 py_compile 全量 + 回归**

Run:
```bash
cd backend
.venv\Scripts\python.exe -m compileall app\ -q
.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```
Expected: compileall 无错；pytest 失败数不高于基线。

- [ ] **Step 5: 手动端到端冒烟（开发者已有自动重载服务）**

- 个人中心 → 单位偏好：设能量 kJ、质量 kg、容积 mL、记价 个 → 保存 → 刷新仍生效。
- 饮食偏好：「每日热量」标签变 (kJ)，数值 = 原 kcal × 4.184；保存后库仍 kcal。
- 商品详情：添加价格记录默认单位 = 个；价格趋势图轴 = kg。
- 菜谱详情：点原料数量 → 切到 kg/mL；再点切回；适量行不切。
- 原料详情：基本信息编辑不再有「默认单位」字段（字段已删）。

- [ ] **Step 6: 最终 commit（如有扫尾修复）**

```bash
git add -A
git commit -m "chore: sweep residual hardcoded units after user-default-units migration"
```

---

## 记录要点

实现完成后，按 [CLAUDE.md](../../../CLAUDE.md) 索引在「功能实现记录」补一条，要点：
- User 加 4 列单位偏好 + Ingredient 删 default_unit_id（含 ingredient_extended 10+ 处清理、nutrition/导入服务/审核 schema 联动）
- /auth/me 返回 unit_preferences（后端解析单位名）
- 前端 useUserUnits composable + nutrientDefinitions DRY 抽离
- 菜谱原料点击转换（复用 POST /units/convert）
- daily_calorie_target 跟随能量单位转换
- 含 alembic + 三引擎 SQL + 开发库直接补（不走 alembic 的项目惯例）
