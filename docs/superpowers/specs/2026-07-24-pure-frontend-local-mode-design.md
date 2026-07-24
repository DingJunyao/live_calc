# 纯前端本地模式设计文档

> 通过环境变量开关，将现有全栈应用构建为纯前端版本——数据存储在浏览器 IndexedDB 中，所有后端业务逻辑移植为 TypeScript。

---

## 一、动机与目标

现有项目是 FastAPI + Vue 3 全栈应用。本设计旨在**不加第二套代码库**的前提下，通过构建参数输出一个纯前端版本，让用户完全在浏览器内使用所有核心功能，无需任何后端服务。

### 范围

- **保留**：商品/价格/菜谱/原料/商家 CRUD、成本计算、营养分析、今日推荐、单位换算、商品加权、USDA 匹配、黑名单、地图（SDK 本就前端跑）、数据导入/导出、浏览器 Agent
- **去掉**：用户管理、邀请码、提议审核流程、SMTP/邮件、Agent 后台进程（改为浏览器原生 Agent）
- **用户**：单用户自动管理员

### 非目标

- 不修改现有云模式的任何代码路径
- 不重构视图层代码
- 不支持多用户

---

## 二、构建策略

### 环境变量开关

```
# .env.local
VITE_STORAGE_MODE=local    # 默认 'cloud'
```

`vite.config.ts` 无需额外配置——环境变量在运行时由前端代码读取。

### 核心切入：api/client.ts 替换

唯一改动点是 `api/client.ts`。原先的：

```typescript
export const api = createAxiosInstance()
```

变为：

```typescript
const mode = import.meta.env.VITE_STORAGE_MODE || 'cloud'
export const api = mode === 'local'
  ? createLocalProxy()
  : createAxiosInstance()
```

`createLocalProxy()` 返回的对象具有相同签名 `{ get, post, put, delete }`，但内部路由到 IndexedDB 操作而非 HTTP 请求。

**上层代码零改动**——所有视图、store、composable 仍写 `api.get('/products')`，本地模式下透明切换到 IndexedDB。

---

## 三、目录结构

所有本地模式代码集中在 `frontend/src/api/local/`：

```
frontend/src/api/
├── client.ts          ← 环境变量分发（唯一被改的现有文件）
├── proxy.ts           ← createLocalProxy() 实现
├── local/
│   ├── database.ts    ← IndexedDB 定义、初始化、迁移、事务封装
│   ├── seed.ts        ← 种子数据导入（单位/分类/USDA等）
│   ├── proxy.ts       ← URL 路由分发引擎
│   ├── handlers/      ← 每个域名一组 CRUD 操作
│   │   ├── auth.ts
│   │   ├── products.ts
│   │   ├── ingredients.ts
│   │   ├── recipes.ts
│   │   ├── nutrition.ts
│   │   ├── merchants.ts
│   │   ├── units.ts
│   │   ├── meals.ts
│   │   ├── usda.ts
│   │   ├── agents.ts
│   │   ├── hierarchy.ts
│   │   ├── sparklines.ts
│   │   ├── blacklist.ts
│   │   ├── exportImport.ts
│   │   └── admin.ts
│   ├── business/      ← 后端算法 TypeScript 移植
│   │   ├── costCalculator.ts
│   │   ├── nutritionAggregator.ts
│   │   ├── mealRecommender.ts
│   │   ├── unitConverter.ts
│   │   ├── priceWeighted.ts
│   │   └── hierarchyResolver.ts
│   └── agent/         ← 浏览器原生 Agent 实现
│       ├── runner.ts          ← Agent 执行引擎
│       ├── tools.ts           ← IndexedDB 工具集定义
│       ├── approval.ts        ← 简化审批逻辑
│       └── taskTemplates.ts   ← 任务提示词模板
```

---

## 四、IndexedDB 数据层

### 数据库

- `idb` 库（~1.5KB，Promise 封装，零依赖）
- 数据库名：`livecalc_local`
- 版本管理：`idb` 的 `upgrade` 回调处理 schema 变更

### 对象存储设计

| Store | Key | 索引 | 说明 |
|-------|-----|------|------|
| `units` | id (autoIncrement) | by_type | 基础单位 + 自定义单位 |
| `unit_conversions` | id | by_from_unit, by_to_unit | 单位换算关系 |
| `ingredient_categories` | id | - | 13 个预设分类 |
| `ingredients` | id | by_name, by_category_id | 原料 |
| `nutrition_data` | id | by_ingredient_id | 营养数据 |
| `products` | id | by_name, by_ingredient_id | 商品实体 |
| `product_records` | id | by_product_id, by_merchant_id, by_recorded_at | 价格记录 |
| `product_weight_overrides` | id | by_product_id | 用户级权重覆盖 |
| `product_barcodes` | id | by_product_id | 商品条码 |
| `recipes` | id | by_name | 菜谱 |
| `recipe_ingredients` | id | by_recipe_id, by_ingredient_id | 菜谱原料关联 |
| `recipe_cost_history` | id | by_recipe_id, by_recorded_at | 成本历史 |
| `merchants` | id | by_name | 商家 |
| `merchant_favorites` | id | by_merchant_id | 收藏商家 |
| `user_places` | id | - | 常用地点 |
| `ingredient_hierarchy` | id | by_parent, by_child | 原料层级关系 |
| `entity_unit_overrides` | id | by_entity (复合) | 实体单位覆盖 |
| `entity_densities` | id | by_entity (复合) | 实体密度 |
| `usda_foods` | fdc_id | by_name | USDA 食品库 |
| `usda_food_nutrients` | id | by_fdc_id | USDA 营养素 |
| `blacklist_groups` | id | by_name | 黑名单分组 |
| `blacklist_group_ingredients` | id | by_group_id | 分组原料映射 |
| `blacklist_subscriptions` | id | by_group_id | 分组订阅 |
| `meal_recommendations` | id | by_date | 推荐缓存 |
| `system_config` | key (string) | - | KV 配置（地图/AI/存储等） |
| `images` | id | by_entity (复合) | 图片 Blob 存储 |
| `import_tasks` | id | - | 导入任务记录 |
| `agent_sessions` | id | - | Agent 会话记录 |

### 事务策略

- **读操作**：单 store 或 `readonly` 多 store 事务
- **写操作**：`readwrite` 事务，小批量（100 条）写避免卡 UI
- **跨 store 操作**（如成本计算需读 7 个 store）：统一 `readonly` 事务，数据在内存中组合

---

## 五、业务逻辑移植

### 5.1 单位换算（`unitConverter.ts`）

移植自 `backend/app/services/unit_conversion_service.py`（~300 行 Python → ~200 行 TS）

- 同类型：`si_factor` 比例换算
- 跨类型（体积↔质量）：查 `entity_unit_overrides` + `entity_densities`，密度桥接
- 递归 5 层上限
- 输入：`convert(value, fromUnitId, toUnitId, entityType?, entityId?)`

### 5.2 成本计算（`costCalculator.ts`）

移植自 `recipe_service.py` + `ingredient_price_service.py`（~600 行 Python → ~400 行 TS）

- 遍历每个原料 → 查对应商品 → 加权最新价
- 单位归一化：用量单位 × 商品单价单位
- `quantity_range` 取平均
- 半成品菜谱递归（`result_ingredient_id`）
- `ingredient_hierarchy` 回退链
- `as_of` 时间点 + 趋势（`range_trend`）

### 5.3 营养聚合（`nutritionAggregator.ts`）

移植自 `backend/app/api/nutrition.py`（~400 行 → ~300 行 TS）

- 按 `NutritionData` 计算每 100g 实际用量
- kcal↔kJ 按用户偏好转换
- NRV% 按中国 GB 标准
- USDA 数据合并

### 5.4 今日推荐（`mealRecommender.ts`）

移植自 `backend/app/services/meal_recommender.py`（~500 行 → ~350 行 TS）

- 候选菜谱池 → 过滤黑名单
- 评分：分数加权随机（`score + 0.05`，`random.choices`）
- 排除当日已选
- 缓存到 IndexedDB `meal_recommendations`

### 5.5 USDA 搜索（`handlers/usda.ts`）

- 空格分词 AND 匹配（内存搜索）
- 支持中英文
- 从 IndexedDB `usda_foods` / `usda_food_nutrients` 读取
- 首次搜索可触发 USDA 数据下载（fetch raw JSON）

### 5.6 商品加权价格（`priceWeighted.ts`）

- 多商品按权重加权平均
- `resolve_weight` 逻辑（全局/用户覆盖）

---

## 六、浏览器 Agent

### 核心差异

| 项目 | 后端 Agent | 浏览器 Agent |
|------|-----------|-------------|
| 执行环境 | Python subprocess | 浏览器 JS |
| 模型 | Claude Code CLI / LangChain | Anthropic / OpenAI API |
| 数据访问 | 自由 SQL | 预设 IndexedDB 工具 |
| 需配置 | 无 | 用户提供 API Key |
| 审批 | SQL 守卫（行数检测） | 操作类型 + 影响范围检查 |

### 架构

```
用户输入指令 → runner.ts 构造 API 请求
  → Anthropic/OpenAI API（带工具定义）
  → AI 选择工具 + 参数
  → tools.ts 执行 IndexedDB 操作
  → 结果返回 AI，继续直到完成
```

### 预设工具集

- `read_products` / `read_product` —— 查询商品
- `read_recipes` / `read_recipe` —— 查询菜谱
- `read_ingredients` / `read_ingredient` —— 查询原料
- `read_nutrition` —— 查询营养数据
- `update_nutrition` —— 更新营养素（批量 USDA 匹配）
- `batch_update` —— 批量修改（受审批控制）
- `read_statistics` —— 数据统计

### 审批

大数据修改操作（>50 条）弹对话框审批，小修改自动执行。审批 UI 复用现有 `AgentApprovalCard`。

### 页面状态

Agent 任务台页面保留，但：
- 运行时不再有 SSE 流（改为 Promise 链 + 逐步渲染）
- 任务类型限于 IndexedDB 工具能完成的操作
- 用户需在 AI 配置页设置 API Key

---

## 七、页面与路由适配

### 需要修改的文件（极少）

| 文件 | 改动 |
|------|------|
| `api/client.ts` | 环境变量分发（单行改动 + import） |
| `stores/user.ts` | 本地模式返回固定管理员用户 |
| `stores/meals.ts` | 本地模式不走轮询，直接计算结果 |
| `router/index.ts` | 本地模式守卫跳过认证检查 |
| `utils/image.ts` | 本地模式从 IndexedDB Blob 生成 URL |
| `utils/errorHandler.ts` | 本地模式错误信息简化 |

### 需要隐藏/提示的功能

| 页面/功能 | 处理 |
|----------|------|
| Agent 任务台 | 保留，提示需配 API Key |
| 图片存储配置 | 隐藏（固定 IndexedDB Blob） |
| SMTP/邮件配置 | 隐藏 |
| 用户管理 | 隐藏 |
| 邀请码 | 隐藏 |

### 认证简化

本地模式：
- `userStore` 直接造一个 `{ id: 1, username: 'local', is_admin: true }` 用户
- `login()` / `register()` / `logout()` 为空操作
- `token` 设固定值 `'local-mode'`
- 路由守卫 `requiresAuth` / `adminOnly` 直接放行
- `/login` 和 `/register` 重定向到 `/`

### 地图

地图 SDK 全部在浏览器端运行。本地模式下地图不受影响：
- 高德/百度/腾讯/天地图/OSM SDK 加载照常
- API Key 在 `system_config` 里配置
- `MapPicker` / `MerchantMapView` 零改动

---

## 八、首次启动向导

### 触发条件

```typescript
const unitCount = await db.count('units')
if (unitCount === 0) {
  // 首次启动 → 跳转 /setup
}
```

### 新增路由

```typescript
{
  path: '/setup',
  name: 'local-setup',
  component: () => import('@/views/setup/LocalInitWizard.vue'),
  meta: { requiresAuth: false, title: '初始化' },
}
```

全屏布局，无侧边栏/顶栏。

### 三种初始化方式

**① 从 HowToCook 仓库导入**
- 浏览器 fetch GitHub raw JSON
- 解析 → 写入 IndexedDB
- 顺序：单位 → 分类 → 原料 → 商品 → 菜谱 → 营养
- 进度条展示

**② 上传 ZIP 数据包**
- 复用数据导入的 ZIP 解析逻辑
- 逐条写 IndexedDB
- 进度条展示

**③ 空白起步**
- 只导入硬编码的基础单位 + 13 个原料分类
- 跳转到首页，用户自行在数据维护中心导入

### USDA 数据

- 首次 USDA 搜索时触发下载（fetch JSON）
- 有网络即时下载，离线降级提示

---

## 九、图片处理

- 图片以 Blob 形式存 IndexedDB `images` store
- `getImageUrl()` → 本地模式从 DB 读出 Blob → `URL.createObjectURL(blob)`
- 组件卸载时 `URL.revokeObjectURL()` 清理
- 导入 ZIP 时图片解包写入
- 数据导出时 Blob 重新打包 ZIP

---

## 十、数据导入/导出

**导入**（保留现有功能）：
- 从 ZIP → IndexedDB
- 从远程仓库 → IndexedDB

**导出**（保留现有功能）：
- 从 IndexedDB → 打包为 ZIP 下载
- 兼容云版导出格式，两者互导

---

## 十一、工作量估算

| 部分 | 文件数 | 行数 | 难度 |
|------|--------|------|------|
| IndexedDB 数据层 | 1 | ~300 | 中 |
| 路由代理 | 2 | ~250 | 中 |
| Handler（15 个） | 15 | ~3000 | 中 |
| 业务逻辑移植（6 个） | 6 | ~1500 | 中 |
| 浏览器 Agent | 4 | ~1000 | 高 |
| 页面适配 | 5-8 处 | ~200 | 低 |
| 首次启动向导 | 3-4 | ~500 | 中 |
| 种子数据脚本 | 1 | ~100 | 低 |
| **总计** | **~35 文件** | **~7000 行** | **中-高** |

---

## 十二、验收标准

1. `VITE_STORAGE_MODE=local` 构建的纯前端版本可离线运行
2. 商品/价格/菜谱/原料/商家 CRUD 正常
3. 成本计算、营养分析结果与云版一致
4. 今日推荐可生成
5. 单位换算正确
6. 地图功能正常
7. 图片上传/展示正常
8. 数据导入/导出工作
9. 首次启动向导三选项均可完成初始化
10. Agent 页面可用（含 API Key 配置 → 执行 IndexedDB 操作）
11. `VITE_STORAGE_MODE=cloud` 构建的云版完全不受影响
