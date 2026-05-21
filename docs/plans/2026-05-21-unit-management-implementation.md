# 单位管理重设计 - 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重写单位管理系统，统一公制/市制/英制/计数/模糊量五类单位的换算逻辑，支持商品/原料级别的自定义单位覆盖和密度管理。

**Architecture:** 以 `si_factor` 为唯一换算基准（kg/L/m=1），新增 `entity_unit_overrides` 和 `entity_densities` 两张表实现覆盖优先级链（商品>原料>全局），`unit_conversions` 表仅保留跨类型/非线性换算。全程使用 Decimal 运算。

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (后端)，Vue 3 + Vuetify (前端)

**设计文档:** `docs/plans/2026-05-21-unit-management-design.md`

---

## Task 1: 后端 — 数据库迁移

**Files:**
- Create: `backend/alembic/versions/YYYYMMDD_HHMM_add_unit_system_and_entity_tables.py`
- Modify: `backend/app/models/unit.py`
- Create: `backend/app/models/entity_unit_override.py`
- Create: `backend/app/models/entity_density.py`

### Step 1: 更新 Unit 模型

在 `backend/app/models/unit.py` 的 Unit 类中新增字段：

```python
# 在 is_common 字段之后添加
unit_system = Column(String(20), nullable=True)  # metric/market/imperial/count/vague
default_estimate = Column(Numeric(10, 3), nullable=True)  # 模糊量的默认估算值（kg为单位）
```

同时为 si_factor 字段添加注释说明基准单位：
- mass: kg=1
- volume: m³=1
- length: m=1

`base_unit_id` 字段暂时保留（兼容），但标记为 deprecated，不在新代码中使用。

### Step 2: 创建 EntityUnitOverride 模型

新建 `backend/app/models/entity_unit_override.py`：

```python
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class EntityUnitOverride(Base):
    __tablename__ = "entity_unit_overrides"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(20), nullable=False)  # 'ingredient' 或 'product'
    entity_id = Column(Integer, nullable=False)
    unit_name = Column(String(50), nullable=False)  # 如 "盒(12个)"、"根"
    base_unit_id = Column(Integer, ForeignKey("units.id"))  # 指向 "个"
    conversion_factor = Column(Numeric(15, 10))  # 如 12（一盒12个）
    weight_per_unit = Column(Numeric(10, 3))  # 如 55（一个55g）
    weight_unit_id = Column(Integer, ForeignKey("units.id"))  # 指向质量单位
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "unit_name", name="uq_entity_unit"),
    )

    base_unit = relationship("Unit", foreign_keys=[base_unit_id])
    weight_unit = relationship("Unit", foreign_keys=[weight_unit_id])
```

### Step 3: 创建 EntityDensity 模型

新建 `backend/app/models/entity_density.py`：

```python
from sqlalchemy import Column, Integer, String, Numeric, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class EntityDensity(Base):
    __tablename__ = "entity_densities"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(20), nullable=False)  # 'ingredient' 或 'product'
    entity_id = Column(Integer, nullable=False)
    density = Column(Numeric(10, 6), nullable=False)  # kg/m³（SI 基准）
    temperature = Column(Numeric(5, 2))  # 参考温度（℃）
    condition = Column(String(100))  # 状态描述
    source = Column(String(200))
    confidence = Column(Numeric(3, 2), default=1.0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "condition", name="uq_entity_density"),
    )
```

### Step 4: 注册模型

在模型 `__init__.py` 或 `backend/app/models/__init__.py` 中导入新模型确保 Alembic 能检测到。

### Step 5: 创建 Alembic 迁移

运行 `alembic revision --autogenerate -m "add_unit_system_and_entity_tables"` 生成迁移。

手动检查迁移脚本，确保包含：
- units 表新增 `unit_system`、`default_estimate` 列
- 创建 `entity_unit_overrides` 表
- 创建 `entity_densities` 表

### Step 6: 为现有单位数据设置 unit_system

在迁移脚本中添加数据迁移：

```python
# 设置现有单位的 unit_system
op.execute("UPDATE units SET unit_system = 'metric' WHERE abbreviation IN ('g', 'kg', 'mg', 'L', 'ml', 'm', 'cm', 'mm')")
op.execute("UPDATE units SET unit_system = 'market' WHERE abbreviation IN ('斤', '两', '钱', '杯', '汤匙', '茶匙')")
op.execute("UPDATE units SET unit_system = 'imperial' WHERE abbreviation IN ('lb', 'oz', 'cup', 'fl_oz', 'ft', 'in')")
op.execute("UPDATE units SET unit_system = 'count' WHERE unit_type = 'count'")
```

### Step 7: 提供多引擎 SQL 脚本

创建 `backend/alembic/sql/unit_management.sql`，包含 SQLite/MySQL/PostgreSQL 三种版本的 DDL。

### Step 8: 运行迁移验证

运行 `alembic upgrade head`，检查数据库表结构是否正确。

---

## Task 2: 后端 — Schemas

**Files:**
- Modify: `backend/app/api/units.py`（内联 schemas）
- Create: `backend/app/schemas/unit.py`

### Step 1: 创建 unit schemas 文件

新建 `backend/app/schemas/unit.py`，将 `backend/app/api/units.py` 中内联定义的 Pydantic 模型提取出来：

```python
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class UnitBase(BaseModel):
    name: str
    abbreviation: str
    plural_form: Optional[str] = None
    unit_type: str  # mass/volume/length/count/vague
    unit_system: Optional[str] = None  # metric/market/imperial/count/vague
    si_factor: Optional[Decimal] = None
    is_si_base: bool = False
    is_common: bool = False
    display_order: int = 0
    default_estimate: Optional[Decimal] = None


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    name: Optional[str] = None
    abbreviation: Optional[str] = None
    plural_form: Optional[str] = None
    unit_type: Optional[str] = None
    unit_system: Optional[str] = None
    si_factor: Optional[Decimal] = None
    is_si_base: Optional[bool] = None
    is_common: Optional[bool] = None
    display_order: Optional[int] = None
    default_estimate: Optional[Decimal] = None


class UnitResponse(UnitBase):
    id: int

    class Config:
        from_attributes = True


class EntityUnitOverrideBase(BaseModel):
    unit_name: str
    conversion_factor: Optional[Decimal] = None
    weight_per_unit: Optional[Decimal] = None
    weight_unit_id: Optional[int] = None
    is_default: bool = False


class EntityUnitOverrideCreate(EntityUnitOverrideBase):
    pass


class EntityUnitOverrideUpdate(BaseModel):
    unit_name: Optional[str] = None
    conversion_factor: Optional[Decimal] = None
    weight_per_unit: Optional[Decimal] = None
    weight_unit_id: Optional[int] = None
    is_default: Optional[bool] = None


class EntityUnitOverrideResponse(EntityUnitOverrideBase):
    id: int
    entity_type: str
    entity_id: int
    base_unit_id: Optional[int] = None

    class Config:
        from_attributes = True


class EntityDensityBase(BaseModel):
    density: Decimal  # kg/m³
    temperature: Optional[Decimal] = None
    condition: Optional[str] = None
    source: Optional[str] = None
    confidence: Decimal = Decimal("1.0")


class EntityDensityCreate(EntityDensityBase):
    pass


class EntityDensityUpdate(BaseModel):
    density: Optional[Decimal] = None
    temperature: Optional[Decimal] = None
    condition: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[Decimal] = None


class EntityDensityResponse(EntityDensityBase):
    id: int
    entity_type: str
    entity_id: int

    class Config:
        from_attributes = True


class UnitConvertRequest(BaseModel):
    value: Decimal
    from_unit: str  # abbreviation
    to_unit: str  # abbreviation
    entity_type: Optional[str] = None  # 'ingredient' 或 'product'
    entity_id: Optional[int] = None


class UnitConvertResponse(BaseModel):
    value: Decimal
    from_unit: str
    to_unit: str
    method: str  # 'si_factor' / 'entity_override' / 'density' / 'not_supported'
```

---

## Task 3: 后端 — 重写 UnitConversionService

**Files:**
- Rewrite: `backend/app/services/unit_conversion_service.py`

### Step 1: 重写换算服务

核心改动：
1. 全程使用 `Decimal` 运算
2. 同类型换算优先用 `si_factor`
3. 支持 entity override 查询
4. 支持密度查询（entity_densities 优先级链）

```python
from sqlalchemy.orm import Session
from sqlalchemy import and_
from decimal import Decimal
from typing import Optional, Tuple, Dict, List
from app.models.unit import Unit
from app.models.entity_unit_override import EntityUnitOverride
from app.models.entity_density import EntityDensity


class UnitConversionService:
    def __init__(self, db: Session):
        self.db = db

    def get_unit_by_abbr(self, abbreviation: str) -> Optional[Unit]:
        return self.db.query(Unit).filter(Unit.abbreviation == abbreviation).first()

    def convert_si(self, value: Decimal, from_unit: Unit, to_unit: Unit) -> Optional[Decimal]:
        """同类型换算：si_factor 基准"""
        if from_unit.unit_type != to_unit.unit_type:
            return None
        if not from_unit.si_factor or not to_unit.si_factor:
            return None
        result = value * from_unit.si_factor / to_unit.si_factor
        return result.quantize(Decimal("0.000001"))

    def get_density(self, entity_type: str, entity_id: int) -> Decimal:
        """获取密度（kg/m³），遵循优先级链：商品>原料>水(1000)"""
        # 1. 查商品/原料级
        density = self.db.query(EntityDensity).filter(
            and_(
                EntityDensity.entity_type == entity_type,
                EntityDensity.entity_id == entity_id,
            )
        ).first()
        if density:
            return density.density

        # 2. 如果是 product，回退查 ingredient（需要查询 product→ingredient 关系）
        if entity_type == "product":
            from app.models.product_entity import Product
            product = self.db.query(Product).filter(Product.id == entity_id).first()
            if product and product.ingredient_id:
                density = self.db.query(EntityDensity).filter(
                    and_(
                        EntityDensity.entity_type == "ingredient",
                        EntityDensity.entity_id == product.ingredient_id,
                    )
                ).first()
                if density:
                    return density.density

        # 3. 默认：水的密度
        return Decimal("1000")

    def convert_volume_to_mass(
        self, value: Decimal, from_unit: Unit, entity_type: str = None, entity_id: int = None
    ) -> Optional[Tuple[Decimal, Unit]]:
        """体积→质量（通过密度）"""
        if from_unit.unit_type != "volume":
            return None
        density = self.get_density(entity_type, entity_id)  # kg/m³
        # value(from_unit) → m³ → kg → g
        value_m3 = value * from_unit.si_factor  # 转为 m³
        value_kg = value_m3 * density  # m³ × kg/m³ = kg
        # 返回 kg 单位的结果
        kg_unit = self.db.query(Unit).filter(Unit.abbreviation == "kg").first()
        return value_kg, kg_unit

    def convert(
        self,
        value: Decimal,
        from_unit_abbr: str,
        to_unit_abbr: str,
        entity_type: str = None,
        entity_id: int = None,
    ) -> Optional[Tuple[Decimal, str]]:
        """
        统一换算入口。
        返回 (结果值, 换算方式)
        """
        from_unit = self.get_unit_by_abbr(from_unit_abbr)
        to_unit = self.get_unit_by_abbr(to_unit_abbr)
        if not from_unit or not to_unit:
            return None

        # 相同单位
        if from_unit.id == to_unit.id:
            return value, "same"

        # 1. 同类型：si_factor
        if from_unit.unit_type == to_unit.unit_type:
            result = self.convert_si(value, from_unit, to_unit)
            if result is not None:
                return result, "si_factor"

        # 2. 体积→质量（通过密度）
        if from_unit.unit_type == "volume" and to_unit.unit_type == "mass":
            result = self.convert_volume_to_mass(value, from_unit, entity_type, entity_id)
            if result:
                value_kg, kg_unit = result
                # kg → 目标单位
                final = self.convert_si(value_kg, kg_unit, to_unit)
                if final is not None:
                    return final, "density"

        # 3. 质量→体积（通过密度）
        if from_unit.unit_type == "mass" and to_unit.unit_type == "volume":
            density = self.get_density(entity_type, entity_id)
            value_kg = value * from_unit.si_factor  # → kg
            value_m3 = value_kg / density  # kg / (kg/m³) = m³
            result = value_m3 / to_unit.si_factor
            return result.quantize(Decimal("0.000001")), "density"

        return None

    def get_entity_units(self, entity_type: str, entity_id: int) -> List[Dict]:
        """获取实体的自定义单位列表（含回退逻辑）"""
        # 1. 查商品级
        if entity_type == "product":
            overrides = self.db.query(EntityUnitOverride).filter(
                and_(
                    EntityUnitOverride.entity_type == "product",
                    EntityUnitOverride.entity_id == entity_id,
                )
            ).all()
            if overrides:
                return overrides

            # 回退查原料级
            from app.models.product_entity import Product
            product = self.db.query(Product).filter(Product.id == entity_id).first()
            if product and product.ingredient_id:
                overrides = self.db.query(EntityUnitOverride).filter(
                    and_(
                        EntityUnitOverride.entity_type == "ingredient",
                        EntityUnitOverride.entity_id == product.ingredient_id,
                    )
                ).all()
                if overrides:
                    return overrides

        # 2. 查原料级
        return self.db.query(EntityUnitOverride).filter(
            and_(
                EntityUnitOverride.entity_type == entity_type,
                EntityUnitOverride.entity_id == entity_id,
            )
        ).all()

    def get_available_units(self, entity_type: str = None, entity_id: int = None) -> List[Unit]:
        """获取可用单位列表（全局 + 实体专属）"""
        # 全局单位（排除 vague 类型）
        global_units = (
            self.db.query(Unit)
            .filter(Unit.unit_system != "vague", Unit.is_active != False)
            .order_by(Unit.display_order)
            .all()
        )
        return global_units
```

### Step 2: 验证无语法错误

确保 import 正确，Decimal 使用无误。

---

## Task 4: 后端 — API 路由更新

**Files:**
- Modify: `backend/app/api/units.py`

### Step 1: 更新单位 CRUD 接口

在 `backend/app/api/units.py` 中：

1. 替换内联 schemas 为 `from app.schemas.unit import ...`
2. 更新 GET /units/ 支持按 `unit_system` 过滤
3. 更新 POST /units/convert 使用新的 `UnitConversionService.convert()` 方法
4. 添加 `unit_system` 和 `default_estimate` 字段到创建/更新接口

### Step 2: 添加实体单位覆盖 API

新增路由组：

```
GET    /api/v1/entities/{entity_type}/{entity_id}/units        — 获取实体自定义单位
POST   /api/v1/entities/{entity_type}/{entity_id}/units        — 创建
PUT    /api/v1/entities/{entity_type}/{entity_id}/units/{id}   — 更新
DELETE /api/v1/entities/{entity_type}/{entity_id}/units/{id}   — 删除
```

### Step 3: 添加实体密度 API

新增路由组：

```
GET    /api/v1/entities/{entity_type}/{entity_id}/density        — 获取密度
POST   /api/v1/entities/{entity_type}/{entity_id}/density        — 创建/更新
DELETE /api/v1/entities/{entity_type}/{entity_id}/density/{id}   — 删除
```

### Step 4: 在 main.py 注册路由（如需要）

检查路由是否已自动注册，否则手动添加。

---

## Task 5: 前端 — 更新 TypeScript 类型

**Files:**
- Modify: `frontend/src/types/index.ts`

### Step 1: 更新 Unit 接口

```typescript
export interface Unit {
  id: number
  name: string
  abbreviation: string
  plural_form: string | null
  unit_type: string
  unit_system: string | null  // metric/market/imperial/count/vague
  si_factor: number | null
  is_si_base: boolean
  is_common: boolean
  display_order: number
  default_estimate: number | null
}

export interface EntityUnitOverride {
  id: number
  entity_type: string
  entity_id: number
  unit_name: string
  base_unit_id: number | null
  conversion_factor: number | null
  weight_per_unit: number | null
  weight_unit_id: number | null
  is_default: boolean
}

export interface EntityDensity {
  id: number
  entity_type: string
  entity_id: number
  density: number  // kg/m³
  temperature: number | null
  condition: string | null
  source: string | null
  confidence: number
}
```

---

## Task 6: 前端 — 重写 UnitsView.vue

**Files:**
- Rewrite: `frontend/src/views/admin/UnitsView.vue`

### Step 1: 重写页面

按设计文档中的 UI 布局重写，核心功能：

1. **按 unit_system 分组展示**（可折叠）：公制/市制/英制/计数/模糊量
2. **筛选器**：单位体系 + 单位类型 + 搜索
3. **单位卡片/行**：显示名称、缩写、si_factor、是否常用
4. **点击展开换算预览**：`1 [单位] = [值] [基准单位]`，以及到同类型其他常用单位的换算
5. **添加/编辑对话框**：包含 unit_system、si_factor、default_estimate（vague 类型）等字段
6. **跨类型换算管理**：在详情面板中维护 volume↔mass 换算

### Step 2: 确保构建通过

运行 `npm run build`（在 frontend 目录）验证无编译错误。

---

## Task 7: 前端 — 更新价格记录组件

**Files:**
- Modify: `frontend/src/components/prices/QuickPriceRecordDialog.vue`
- Modify: `frontend/src/components/prices/PriceRecordForm.vue`
- Modify: `frontend/src/views/prices/PricesView.vue`

### Step 1: 替换硬编码单位列表

将三个文件中的硬编码单位列表替换为 API 加载：

```typescript
// 加载全局单位 + 实体自定义单位
const loadUnits = async () => {
  const [globalRes, entityRes] = await Promise.all([
    api.get('/units/', { params: { limit: 100 } }),
    productId.value
      ? api.get(`/entities/product/${productId.value}/units`)
      : Promise.resolve({ data: [] }),
  ])
  // 合并去重
  const globalUnits = (globalRes.items || globalRes || []).map(u => ({
    title: `${u.name} (${u.abbreviation})`,
    value: u.abbreviation,
  }))
  const entityUnits = (entityRes.data || []).map(eu => ({
    title: eu.unit_name,
    value: eu.unit_name,
  }))
  unitOptions.value = [...entityUnits, ...globalUnits]
}
```

### Step 2: 在商品选择后触发单位加载

当用户选择/输入商品后，调用 `loadUnits()` 更新单位列表。

---

## Task 8: 前端 — 原料/商品详情页增加单位管理

**Files:**
- Modify: `frontend/src/views/ingredients/IngredientDetail.vue`
- Modify: `frontend/src/views/products/ProductDetail.vue`

### Step 1: 在详情页添加"自定义单位"区域

在原料详情页和商品详情页中添加：
- 自定义单位列表（来自 `entity_unit_overrides`）
- 添加/编辑/删除自定义单位的对话框
- 密度管理区域（显示当前密度，支持编辑）

### Step 2: 确保构建通过

运行 `npm run build` 验证。

---

## Task 9: 清理旧代码

**Files:**
- Deprecate: `backend/app/utils/unit_converter.py`（标记为 deprecated，不删除）
- Deprecate: `backend/app/models/ingredient_density.py`（保留表但不再新增使用）

### Step 1: 标记旧代码为 deprecated

在 `unit_converter.py` 顶部添加注释说明此文件已废弃，新代码应使用 `UnitConversionService`。

### Step 2: 确保无引用断裂

搜索所有引用 `ingredient_density` 和 `unit_converter` 的地方，确保兼容性。

---

## 实施顺序

1. Task 1 (数据库迁移) — 基础设施
2. Task 2 (Schemas) — 数据契约
3. Task 3 (Service) — 核心逻辑
4. Task 4 (API) — 接口层
5. Task 5 (前端类型) — 前端基础
6. Task 6 (管理页面) — 管理界面
7. Task 7 (价格组件) — 核心功能集成
8. Task 8 (详情页) — 实体单位管理
9. Task 9 (清理) — 收尾
