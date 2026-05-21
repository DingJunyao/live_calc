# 单位管理重设计

## 概述

统一管理系统中所有单位，包含公制、市制、英制、计数和模糊量五类，支持全局单位维护和商品/原料级别的自定义单位覆盖。

## 决策记录

| 项 | 决定 |
|----|------|
| 整体方案 | 混合：全局管通用换算，商品/原料管专属换算 |
| 包装单位命名 | 带规格后缀：盒(12个)、盒(30个) |
| 模糊量词 | 特殊单位类型，给默认估算值，不参与精确换算 |
| 通用计数单位 | 只保留"个"，默认100g |
| 覆盖优先级 | 商品 > 原料 > 全局 |
| 多买优惠 | 记录实际交易，不建模价格阶梯 |
| 换算基准 | si_factor 为唯一基准，标准单位=1（kg/L/m） |
| 页面方案 | 重写 UnitsView.vue |

## 数据模型

### 1. units 表改动

新增字段 `unit_system`：

| 字段 | 类型 | 说明 |
|------|------|------|
| unit_system | String(20) | 度量体系：metric/market/imperial/count/vague |

**度量体系说明：**

| unit_system | 含义 | 示例 |
|-------------|------|------|
| metric | 公制 | g, kg, mg, L, ml, m, cm |
| market | 市制 | 斤, 两, 钱, 杯, 汤匙, 茶匙 |
| imperial | 英制 | lb, oz, cup, fl_oz, ft, in |
| count | 计数 | 个（仅此一个，默认=100g） |
| vague | 模糊量 | 适量, 少许, 一撮 |

**si_factor 基准：**

| unit_type | 标准单位 | si_factor |
|-----------|---------|-----------|
| mass | kg | 1 |
| volume | m³ | 1 |
| length | m | 1 |

示例：g=0.001, 斤=0.5, 两=0.05, lb=0.453592, L=0.001, ml=0.000001

**同类型换算公式：**
```
result = value × from_unit.si_factor / to_unit.si_factor
```

**移除/弃用：**
- `base_unit_id` — 被 si_factor 取代
- `unit_conversions` 表仅保留用于跨类型换算（体积↔质量，需密度）和非线性场景（温度）

### 2. 新增 entity_unit_overrides 表

商品/原料级别的自定义单位覆盖，复用一张表：

```sql
CREATE TABLE entity_unit_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type VARCHAR(20) NOT NULL,    -- 'ingredient' 或 'product'
    entity_id INTEGER NOT NULL,           -- 原料ID 或 商品ID
    unit_name VARCHAR(50) NOT NULL,       -- 如 "盒(12个)"、"根"
    base_unit_id INTEGER REFERENCES units(id),  -- 指向 "个"
    conversion_factor DECIMAL(15, 10),     -- 如 12（一盒12个）
    weight_per_unit DECIMAL(10, 3),        -- 如 55（一个55g）
    weight_unit_id INTEGER REFERENCES units(id), -- 指向 "g"
    is_default BOOLEAN DEFAULT FALSE,      -- 是否为该实体的默认计数单位
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id, unit_name)
);
```

**示例数据：**

| entity_type | entity_id | unit_name | base_unit_id | conversion_factor | weight_per_unit | weight_unit_id |
|-------------|-----------|-----------|-------------|-------------------|-----------------|---------------|
| ingredient | 鸡蛋 | 个 | 个(id) | 1 | 55 | g(id) |
| ingredient | 鸡蛋 | 盒(12个) | 个(id) | 12 | 660 | g(id) |
| product | 某品牌鸡蛋30枚 | 盒(30个) | 个(id) | 30 | 1650 | g(id) |
| ingredient | 火腿肠 | 根 | 个(id) | 1 | 60 | g(id) |

### 3. 模糊量单位

作为特殊单位存在 units 表中：

| name | abbreviation | unit_system | unit_type | default_estimate | si_factor |
|------|-------------|-------------|-----------|-----------------|-----------|
| 适量 | 适量 | vague | mass | 5g | NULL |
| 少许 | 少许 | vague | mass | 2g | NULL |
| 一撮 | 一撮 | vague | mass | 1g | NULL |

- si_factor 为 NULL，不参与精确换算
- default_estimate 字段存储默认估算值（需在 units 表新增）

## 单位解析优先级

```
商品级定义（最优先）
    ↓ 未找到时回退
原料级定义
    ↓ 未找到时回退
全局单位定义（兜底：个=100g）
```

**价格记录时的单位加载逻辑：**
1. 始终加载全局质量/体积单位（g, kg, 斤, 两, lb...）
2. 选中商品后，查询 entity_unit_overrides（先查 product 级，无则查 ingredient 级）
3. 将找到的自定义单位追加到列表

## 换算关系简化

### 同类型换算

- 唯一基准：`si_factor`，公式 `result = value × from.si_factor / to.si_factor`
- 全程使用 Python `Decimal` 运算，避免 float 精度损失
- 移除 `base_unit_id` 字段

### 跨类型换算

通过物理公式链式计算，`unit_conversions` 表仅记录非标准的跨类型映射：

```
长度 → 体积:  L × W × H（维度计算，公式驱动）
体积 → 质量:  volume × density（需要密度数据）
质量 → 体积:  mass / density（需要密度数据）
```

### 密度管理

密度数据同样遵循覆盖优先级：**商品 > 原料 > 默认值（水）**

扩展现有 `ingredient_densities` 表为 `entity_densities`，支持商品级别：

```sql
CREATE TABLE entity_densities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type VARCHAR(20) NOT NULL,    -- 'ingredient' 或 'product'
    entity_id INTEGER NOT NULL,
    density DECIMAL(10, 6) NOT NULL,     -- kg/m³（SI 基准）
    temperature DECIMAL(5, 2),           -- 参考温度（℃），可选
    condition VARCHAR(100),              -- 状态描述，如"常温""冷藏"
    source VARCHAR(200),                 -- 数据来源
    confidence DECIMAL(3, 2) DEFAULT 1.0, -- 置信度 0~1
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id, condition)
);
```

**常见密度参考值：**

| 物质 | 密度 (kg/m³) | 说明 |
|------|-------------|------|
| 水 | 1000 | 默认值 |
| 食用油 | 920 | 约 0.92 g/mL |
| 牛奶 | 1030 | 约 1.03 g/mL |
| 蜂蜜 | 1420 | 约 1.42 g/mL |
| 酱油 | 1150 | 约 1.15 g/mL |

**密度解析逻辑：**
1. 查询商品级密度 → 有则使用
2. 无则查询原料级密度 → 有则使用
3. 都无则使用默认值：1000 kg/m³（水）

### 移除
- `base_unit_id` 字段（被 si_factor 取代）
- `unit_conversions` 表中同类型的换算记录（被 si_factor 计算取代）
- 旧 `ingredient_densities` 表（被 `entity_densities` 取代）

### 保留
- `unit_conversions` 用于温度等非线性换算

## 后台管理页面 UI

### 页面布局

```
┌─────────────────────────────────────────┐
│  单位管理                    [+ 添加单位] │
├─────────────────────────────────────────┤
│  筛选: [单位体系 ▼]  [单位类型 ▼]  🔍搜索 │
├─────────────────────────────────────────┤
│                                         │
│  ▸ 公制 (8)     ← 可折叠分组            │
│    g    kg    mg    L    ml    m ...     │
│                                         │
│  ▸ 市制 (6)                             │
│    斤    两    钱    杯    汤匙  茶匙     │
│                                         │
│  ▸ 英制 (6)                             │
│    lb   oz   cup  fl_oz  ft   in        │
│                                         │
│  ▸ 计数 (1)                             │
│    个 (=100g)                            │
│                                         │
│  ▸ 模糊量 (3)                           │
│    适量 (~5g)  少许 (~2g)  一撮 (~1g)    │
│                                         │
├─────────────────────────────────────────┤
│  ┌─ 换算关系（点击单位时展开）──────────┐ │
│  │  kg = 1 (基准)                       │ │
│  │  g  = 0.001                          │ │
│  │  斤 = 0.5                            │ │
│  │  lb = 0.453592                       │ │
│  │  自动换算预览:                        │ │
│  │  1 kg = 1000 g = 2 斤 = 2.205 lb    │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 核心交互

**单位卡片/行：**
- 显示：名称、缩写、si_factor、是否常用
- 点击展开详情面板，显示换算预览（以基准单位为1，自动计算到同类型其他单位的换算）

**添加/编辑单位对话框：**
- 单位名称、缩写、复数形式
- 单位体系（metric/market/imperial/count/vague）
- 单位类型（mass/volume/length）
- si_factor（相对于 kg/L/m 的系数）
- 是否常用、显示顺序
- 对于 vague 类型：额外显示"默认估算值"字段（default_estimate）

**跨类型换算管理：**
- 在单位详情面板中，管理 volume↔mass 的换算关系
- 关联 ingredient_density 数据

## 实施范围

### 后端
1. units 表新增 `unit_system`、`default_estimate` 字段
2. 创建 `entity_unit_overrides` 表
3. 简化 `UnitConversionService`，以 si_factor 为主要换算方式
4. 新增 API 端点：
   - `GET /api/v1/units/` — 列表（支持按 unit_system 过滤）
   - `POST /api/v1/units/` — 创建
   - `PUT /api/v1/units/{id}` — 更新
   - `DELETE /api/v1/units/{id}` — 删除
   - `GET /api/v1/units/{id}/conversions` — 跨类型换算关系
   - `POST /api/v1/units/convert` — 换算（优先 si_factor）
   - `GET /api/v1/entities/{type}/{id}/units` — 获取实体的自定义单位
   - `POST /api/v1/entities/{type}/{id}/units` — 创建实体自定义单位
   - `PUT /api/v1/entities/{type}/{id}/units/{unit_id}` — 更新
   - `DELETE /api/v1/entities/{type}/{id}/units/{unit_id}` — 删除
5. 提供数据库迁移脚本（SQLite/MySQL/PostgreSQL）

### 前端
1. 重写 `UnitsView.vue` 管理页面
2. 修改价格记录组件（PriceRecordForm、QuickPriceRecordDialog）的单位选择逻辑
3. 原料/商品详情页增加自定义单位管理区域

### 不在本次范围
- 用户单位偏好设置页面
- 区域单位设置页面
- ingredient_density 管理界面
