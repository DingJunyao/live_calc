# 单位管理重设计

## 概述

统一管理系统中的单位，支持公制/市制/英制/计数/模糊量五类单位，实现商品/原料级别的自定义单位覆盖和密度管理。

## 设计文档

详见 [2026-05-21-unit-management-design.md](../docs/plans/2026-05-21-unit-management-design.md)

## 核心改动

### 数据模型

- `units` 表新增 `unit_system`（度量体系）和 `default_estimate`（模糊量默认估算值）字段
- 新增 `entity_unit_overrides` 表：商品/原料级别的自定义包装单位
- 新增 `entity_densities` 表：商品/原料级别的密度数据（默认为水的密度 1000 kg/m³）

### 换算逻辑

- **si_factor 为唯一基准**：同类型单位换算公式 `value × from.si_factor / to.si_factor`
  - 标准：kg=1, m³=1, m=1
- **跨类型换算**：体积↔质量通过密度
- **覆盖优先级**：商品 > 原料 > 全局
- **全程使用 Decimal** 运算

### 后端文件

- `backend/app/models/unit.py` — Unit 模型新增字段
- `backend/app/models/entity_unit_override.py` — 实体单位覆盖模型
- `backend/app/models/entity_density.py` — 实体密度模型
- `backend/app/schemas/unit.py` — Pydantic schemas
- `backend/app/services/unit_conversion_service.py` — 重写的换算服务
- `backend/app/api/units.py` — 更新的 API 路由
- `backend/alembic/versions/20260521_1832_...` — 数据库迁移
- `backend/alembic/sql/unit_management.sql` — 多引擎 SQL

### 前端文件

- `frontend/src/types/index.ts` — 新增 EntityUnitOverride、EntityDensity 接口
- `frontend/src/views/admin/UnitsView.vue` — 完全重写的管理页面
- `frontend/src/components/prices/QuickPriceRecordDialog.vue` — API 加载单位
- `frontend/src/components/prices/PriceRecordForm.vue` — API 加载单位
- `frontend/src/views/prices/PricesView.vue` — API 加载单位
- `frontend/src/views/ingredients/IngredientDetail.vue` — 单位与密度管理
- `frontend/src/views/products/ProductDetail.vue` — 单位与密度管理

### API 端点

- `GET /api/v1/units/` — 支持 unit_system 过滤
- `POST /api/v1/units/convert` — 使用新 convert 方法
- `GET/POST/PUT/DELETE /api/v1/entities/{entity_type}/{entity_id}/units` — 实体单位覆盖 CRUD
- `GET/POST/DELETE /api/v1/entities/{entity_type}/{entity_id}/density` — 实体密度管理

### 已废弃

- `backend/app/utils/unit_converter.py` — 标记为 deprecated
- `backend/app/models/ingredient_density.py` — 标记为 deprecated
