# 纯前端本地模式实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通过 `VITE_STORAGE_MODE=local` 环境变量，将现有全栈应用构建为纯前端版本，数据存浏览器 IndexedDB，后端业务逻辑移植为 TypeScript。

**Architecture:** `api/client.ts` 单点分发——云模式用 axios，本地模式用 `createLocalProxy()`。代理层按 URL 路由到 IndexedDB handler。后端算法（成本/营养/推荐等）移植为纯 TS 模块，无状态、可测试。

**Tech Stack:** Vue 3 + TypeScript + Vite + `idb` (IndexedDB) + existing Vuetify/Leaflet/ECharts

**Phases:**
1. **Phase 0** — 基础设施：`idb` 引入、database.ts、proxy.ts、build 开关
2. **Phase 1** — 核心 CRUD：units、products、product_records、ingredients、merchants handler
3. **Phase 2** — 菜谱 + 成本 + 营养：recipes CRUD、costCalculator、nutritionAggregator
4. **Phase 3** — 业务逻辑：mealRecommender、priceWeighted、hierarchyResolver、sparklines
5. **Phase 4** — 特色功能：USDA 搜索、blacklist、admin 配置
6. **Phase 5** — 浏览器 Agent：runner、tools、approval、templates
7. **Phase 6** — 页面适配：auth、router、userStore、隐藏功能、图片处理
8. **Phase 7** — 首次启动向导：LocalInitWizard.vue、seed.ts
9. **Phase 8** — 数据导入/导出 + 构建验证

---

## Phase 0：基础设施

目标是搭建本地模式的核心骨架——IndexedDB 数据库、路由代理、构建开关。

### Task 0.1: 安装 idb 并创建 database.ts

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/api/local/database.ts`

- [ ] **Step 1: 安装 idb**

```bash
cd frontend && npm install idb
```

- [ ] **Step 2: 创建 database.ts**

创建 IndexedDB 数据库定义，包含所有对象存储、索引、通用 CRUD 函数。

**File: `frontend/src/api/local/database.ts`**

```typescript
import { openDB, type IDBPDatabase, type DBSchema } from 'idb'

interface LiveCalcDB extends DBSchema {
  units: { key: number; value: any; indexes: { 'by_type': string } }
  unit_conversions: { key: number; value: any; indexes: { 'by_from_unit': number; 'by_to_unit': number } }
  ingredient_categories: { key: number; value: any }
  ingredients: { key: number; value: any; indexes: { 'by_name': string; 'by_category_id': number } }
  nutrition_data: { key: number; value: any; indexes: { 'by_ingredient_id': number } }
  products: { key: number; value: any; indexes: { 'by_name': string; 'by_ingredient_id': number } }
  product_records: { key: number; value: any; indexes: { 'by_product_id': number; 'by_merchant_id': number; 'by_recorded_at': string } }
  product_weight_overrides: { key: number; value: any; indexes: { 'by_product_id': number } }
  product_barcodes: { key: number; value: any; indexes: { 'by_product_id': number; 'by_code': string } }
  recipes: { key: number; value: any; indexes: { 'by_name': string } }
  recipe_ingredients: { key: number; value: any; indexes: { 'by_recipe_id': number; 'by_ingredient_id': number } }
  recipe_cost_history: { key: number; value: any; indexes: { 'by_recipe_id': number; 'by_recorded_at': string } }
  merchants: { key: number; value: any; indexes: { 'by_name': string } }
  merchant_favorites: { key: number; value: any; indexes: { 'by_merchant_id': number } }
  user_places: { key: number; value: any }
  ingredient_hierarchy: { key: number; value: any; indexes: { 'by_parent': number; 'by_child': number } }
  entity_unit_overrides: { key: number; value: any; indexes: { 'by_entity': [string, number] } }
  entity_densities: { key: number; value: any; indexes: { 'by_entity': [string, number] } }
  usda_foods: { key: number; value: any; indexes: { 'by_name': string } }
  usda_food_nutrients: { key: number; value: any; indexes: { 'by_fdc_id': number } }
  blacklist_groups: { key: number; value: any; indexes: { 'by_name': string } }
  blacklist_group_ingredients: { key: number; value: any; indexes: { 'by_group_id': number; 'by_ingredient_id': number } }
  blacklist_subscriptions: { key: number; value: any; indexes: { 'by_group_id': number } }
  meal_recommendations: { key: number; value: any; indexes: { 'by_date': string } }
  system_config: { key: string; value: { key: string; value: any } }
  images: { key: number; value: any; indexes: { 'by_entity': [string, number] } }
  import_tasks: { key: number; value: any }
  agent_sessions: { key: number; value: any }
}

const DB_NAME = 'livecalc_local'
const DB_VERSION = 1

let _db: IDBPDatabase<LiveCalcDB> | null = null

export async function getDb(): Promise<IDBPDatabase<LiveCalcDB>> {
  if (_db) return _db
  _db = await openDB<LiveCalcDB>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      const unitsStore = db.createObjectStore('units', { keyPath: 'id', autoIncrement: true })
      unitsStore.createIndex('by_type', 'unit_type')
      const ucStore = db.createObjectStore('unit_conversions', { keyPath: 'id', autoIncrement: true })
      ucStore.createIndex('by_from_unit', 'from_unit_id')
      ucStore.createIndex('by_to_unit', 'to_unit_id')
      db.createObjectStore('ingredient_categories', { keyPath: 'id', autoIncrement: true })
      const ingStore = db.createObjectStore('ingredients', { keyPath: 'id', autoIncrement: true })
      ingStore.createIndex('by_name', 'name')
      ingStore.createIndex('by_category_id', 'category_id')
      const ndStore = db.createObjectStore('nutrition_data', { keyPath: 'id', autoIncrement: true })
      ndStore.createIndex('by_ingredient_id', 'ingredient_id')
      const prodStore = db.createObjectStore('products', { keyPath: 'id', autoIncrement: true })
      prodStore.createIndex('by_name', 'name')
      prodStore.createIndex('by_ingredient_id', 'ingredient_id')
      const prStore = db.createObjectStore('product_records', { keyPath: 'id', autoIncrement: true })
      prStore.createIndex('by_product_id', 'product_id')
      prStore.createIndex('by_merchant_id', 'merchant_id')
      prStore.createIndex('by_recorded_at', 'recorded_at')
      const pwoStore = db.createObjectStore('product_weight_overrides', { keyPath: 'id', autoIncrement: true })
      pwoStore.createIndex('by_product_id', 'product_id')
      const pbStore = db.createObjectStore('product_barcodes', { keyPath: 'id', autoIncrement: true })
      pbStore.createIndex('by_product_id', 'product_id')
      pbStore.createIndex('by_code', 'code', { unique: true })
      const rStore = db.createObjectStore('recipes', { keyPath: 'id', autoIncrement: true })
      rStore.createIndex('by_name', 'name')
      const riStore = db.createObjectStore('recipe_ingredients', { keyPath: 'id', autoIncrement: true })
      riStore.createIndex('by_recipe_id', 'recipe_id')
      riStore.createIndex('by_ingredient_id', 'ingredient_id')
      const rchStore = db.createObjectStore('recipe_cost_history', { keyPath: 'id', autoIncrement: true })
      rchStore.createIndex('by_recipe_id', 'recipe_id')
      rchStore.createIndex('by_recorded_at', 'recorded_at')
      const mStore = db.createObjectStore('merchants', { keyPath: 'id', autoIncrement: true })
      mStore.createIndex('by_name', 'name')
      const mfStore = db.createObjectStore('merchant_favorites', { keyPath: 'id', autoIncrement: true })
      mfStore.createIndex('by_merchant_id', 'merchant_id')
      db.createObjectStore('user_places', { keyPath: 'id', autoIncrement: true })
      const ihStore = db.createObjectStore('ingredient_hierarchy', { keyPath: 'id', autoIncrement: true })
      ihStore.createIndex('by_parent', 'parent_id')
      ihStore.createIndex('by_child', 'child_id')
      const euoStore = db.createObjectStore('entity_unit_overrides', { keyPath: 'id', autoIncrement: true })
      euoStore.createIndex('by_entity', ['entity_type', 'entity_id'])
      const edStore = db.createObjectStore('entity_densities', { keyPath: 'id', autoIncrement: true })
      edStore.createIndex('by_entity', ['entity_type', 'entity_id'])
      const ufStore = db.createObjectStore('usda_foods', { keyPath: 'fdc_id' })
      ufStore.createIndex('by_name', 'description')
      const ufnStore = db.createObjectStore('usda_food_nutrients', { keyPath: 'id', autoIncrement: true })
      ufnStore.createIndex('by_fdc_id', 'fdc_id')
      const bgStore = db.createObjectStore('blacklist_groups', { keyPath: 'id', autoIncrement: true })
      bgStore.createIndex('by_name', 'name')
      const bgiStore = db.createObjectStore('blacklist_group_ingredients', { keyPath: 'id', autoIncrement: true })
      bgiStore.createIndex('by_group_id', 'group_id')
      bgiStore.createIndex('by_ingredient_id', 'ingredient_id')
      const bsStore = db.createObjectStore('blacklist_subscriptions', { keyPath: 'id', autoIncrement: true })
      bsStore.createIndex('by_group_id', 'group_id')
      const mlStore = db.createObjectStore('meal_recommendations', { keyPath: 'id', autoIncrement: true })
      mlStore.createIndex('by_date', 'date')
      db.createObjectStore('system_config', { keyPath: 'key' })
      const imgStore = db.createObjectStore('images', { keyPath: 'id', autoIncrement: true })
      imgStore.createIndex('by_entity', ['entity_type', 'entity_id'])
      db.createObjectStore('import_tasks', { keyPath: 'id', autoIncrement: true })
      db.createObjectStore('agent_sessions', { keyPath: 'id', autoIncrement: true })
    },
  })
  return _db
}

// 通用 CRUD 辅助函数
export async function getAll<T>(storeName: string): Promise<T[]> {
  const db = await getDb(); return (db as any).getAll(storeName)
}
export async function getById<T>(storeName: string, id: number | string): Promise<T | undefined> {
  const db = await getDb(); return (db as any).get(storeName, id)
}
export async function addOne<T>(storeName: string, value: T): Promise<number> {
  const db = await getDb(); return (db as any).add(storeName, value)
}
export async function putOne<T>(storeName: string, value: T): Promise<any> {
  const db = await getDb(); return (db as any).put(storeName, value)
}
export async function deleteOne(storeName: string, id: number | string): Promise<void> {
  const db = await getDb(); return (db as any).delete(storeName, id)
}
export async function countAll(storeName: string): Promise<number> {
  const db = await getDb(); return (db as any).count(storeName)
}
export async function getByIndex<T>(storeName: string, indexName: string, value: any): Promise<T[]> {
  const db = await getDb(); return (db as any).getAllFromIndex(storeName, indexName, value)
}
export async function clearStore(storeName: string): Promise<void> {
  const db = await getDb(); return (db as any).clear(storeName)
}
export async function hasData(storeName: string): Promise<boolean> {
  const db = await getDb(); const c = await (db as any).count(storeName); return c > 0
}
export async function batchAdd<T>(storeName: string, items: T[]): Promise<number> {
  const db = await getDb(); const tx = (db as any).transaction(storeName, 'readwrite'); let cnt = 0
  for (const item of items) { await tx.store.add(item); cnt++ }
  await tx.done; return cnt
}

- [ ] **Step 3: 验证编译**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -30
```
Expected: no new type errors from `database.ts`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/local/database.ts frontend/package.json frontend/package-lock.json
git commit -m "feat(local): add idb dependency and database layer"
```

### Task 0.2: 创建本地模式路由代理

**Files:**
- Create: `frontend/src/api/proxy.ts` — `createLocalProxy()` 工厂
- Create: `frontend/src/api/local/proxy.ts` — URL 路由引擎

- [ ] **Step 1: 创建 `api/local/proxy.ts` 路由引擎**

```typescript
// frontend/src/api/local/proxy.ts
// 路由分发引擎：解析 URL -> 匹配路由表 -> 调用 handler
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE'
interface HandlerModule {
  get?: (params: Record<string, string>, query?: any) => Promise<any>
  post?: (params: Record<string, string>, data?: any) => Promise<any>
  put?: (params: Record<string, string>, data?: any) => Promise<any>
  delete?: (params: Record<string, string>) => Promise<any>
}

export function parseRoute(method: HttpMethod, url: string): { handler: HandlerModule; pathParams: Record<string, string> } {
  const path = url.replace(/^\/api\/v1/, '')
  for (const [m, pattern, handler] of ROUTES) {
    if (m !== method) continue
    const params = matchPath(pattern, path)
    if (params !== null) return { handler, pathParams: params }
  }
  throw { status: 404, userMessage: `route not found: ${method} ${url}` }
}

function matchPath(pattern: string, path: string): Record<string, string> | null {
  const regexStr = pattern.replace(/:(\w+)/g, '(?<$1>[^/]+)')
  const regex = new RegExp(`^${regexStr}$`)
  const m = path.match(regex)
  return m?.groups || null
}

export async function localGet(url: string, params?: any): Promise<any> {
  const { handler, pathParams } = parseRoute('GET', url)
  return handler.get!(pathParams, params)
}
export async function localPost(url: string, data?: any): Promise<any> {
  const { handler, pathParams } = parseRoute('POST', url)
  return handler.post!(pathParams, data)
}
export async function localPut(url: string, data?: any): Promise<any> {
  const { handler, pathParams } = parseRoute('PUT', url)
  return handler.put!(pathParams, data)
}
export async function localDelete(url: string): Promise<any> {
  const { handler, pathParams } = parseRoute('DELETE', url)
  return handler.delete!(pathParams)
}

// 路由表（逐步填充）
const ROUTES: [string, string, HandlerModule][] = []

- [ ] **Step 2: 创建 `api/proxy.ts` 工厂**

```typescript
// frontend/src/api/proxy.ts
import { localGet, localPost, localPut, localDelete } from './local/proxy'

export function createLocalProxy() {
  return {
    get: (url: string, config?: any) => localGet(url, config?.params),
    post: (url: string, data?: any, config?: any) => localPost(url, data),
    put: (url: string, data?: any, config?: any) => localPut(url, data),
    delete: (url: string, config?: any) => localDelete(url),
  }
}
```

- [ ] **Step 3: 验证编译**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -30
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/proxy.ts frontend/src/api/local/proxy.ts
git commit -m "feat(local): add local proxy router"
```

### Task 0.3: 构建开关 — 修改 api 入口

**Files:**
- Create: `frontend/src/api/index.ts`
- Modify: 各 `import api from '@/api/client'` -> `import { api } from '@/api'`

- [ ] **Step 1: 创建 `frontend/src/api/index.ts`**

```typescript
// frontend/src/api/index.ts
import { api as cloudApi, REQUEST_TIMEOUT, LONG_REQUEST_TIMEOUT } from './client'

type ApiFn = (url: string, data?: any, config?: any) => Promise<any>
interface ApiLike { get: ApiFn; post: ApiFn; put: ApiFn; delete: ApiFn }

const storageMode = import.meta.env.VITE_STORAGE_MODE || 'cloud'

function createLocalApi(): ApiLike {
  return {
    get: async (url, config) => { const m = await import('./local/proxy'); return m.localGet(url, config?.params) },
    post: async (url, data) => { const m = await import('./local/proxy'); return m.localPost(url, data) },
    put: async (url, data) => { const m = await import('./local/proxy'); return m.localPut(url, data) },
    delete: async (url) => { const m = await import('./local/proxy'); return m.localDelete(url) },
  }
}

export const api: ApiLike = storageMode === 'local' ? createLocalApi() : cloudApi
export { REQUEST_TIMEOUT, LONG_REQUEST_TIMEOUT }
```

- [ ] **Step 2: 更新所有 import 路径**

```bash
cd d:/code/live_calc/frontend/src
grep -rl "from '@/api/client'" --include="*.ts" --include="*.vue" . | while read f; do
  sed -i "s|from '@/api/client'|from '@/api'|g" "$f"
done
```

- [ ] **Step 3: 验证编译**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -60
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/index.ts
git commit -m "feat(local): add storage mode switch VITE_STORAGE_MODE"
```

---

## Phase 1：核心 CRUD Handlers

### Task 1.1: Auth Handler

**Create:** `frontend/src/api/local/handlers/auth.ts`

```typescript
import type { HandlerModule } from '../proxy'

const localUser = {
  id: 1, username: 'local', email: 'local@local.dev', phone: null,
  is_admin: true, is_active: true, email_verified: true,
  avatar: null, nickname: null, created_at: new Date().toISOString(),
  nutrition_goals: null, daily_budget: null,
  unit_preferences: null, region_id: null,
}

export const auth: HandlerModule = {
  get: async (params, query) => {
    if (params[0] === 'config') return { require_invite_code: false }
    if (params[0] === 'me') return { ...localUser }
    if (params[0] === 'personal-stats') return { total_records: 0, total_products: 0, total_recipes: 0 }
    return localUser
  },
  post: async (params, data) => {
    if (['login', 'register', 'refresh'].includes(params[0])) {
      return { access_token: 'local-mode', refresh_token: 'local-mode', token_type: 'bearer' }
    }
    return { ok: true }
  },
  put: async (params, data) => ({ ...localUser, ...data }),
  delete: async () => ({ ok: true }),
}
```

在 `proxy.ts` 注册：

```typescript
import { auth } from './handlers/auth'
// ROUTES.push(
['GET', '/auth/config', auth],
['GET', '/auth/me', auth],
['GET', '/auth/personal-stats', auth],
['POST', '/auth/login', auth],
['POST', '/auth/register', auth],
['POST', '/auth/refresh', auth],
['PUT', '/auth/me/account', auth],
['PATCH', '/auth/me', auth],
// )
```

### Task 1.2: Units Handler

**Create:** `frontend/src/api/local/handlers/units.ts`

### Task 1.3: Products Handler

**Create:** `frontend/src/api/local/handlers/products.ts`

支持商品/价格记录 CRUD、autocomplete、my-weight、barcode。

### Task 1.4: Ingredients Handler

**Create:** `frontend/src/api/local/handlers/ingredients.ts`

### Task 1.5: Merchants Handler

**Create:** `frontend/src/api/local/handlers/merchants.ts`

### Task 1.6: Nutrition Handler

**Create:** `frontend/src/api/local/handlers/nutrition.ts`

支持营养数据 CRUD、latest-price 计算（引用 business 模块）。

### Task 1.7: Hierarchy Handler

**Create:** `frontend/src/api/local/handlers/hierarchy.ts`

---

## Phase 2：菜谱 + 成本 + 营养

### Task 2.1: unitConverter.ts

**Create:** `frontend/src/api/local/business/unitConverter.ts`

纯函数式换算：同类型 si_factor 比例，跨类型密度桥接。

### Task 2.2: Recipes Handler

**Create:** `frontend/src/api/local/handlers/recipes.ts`

### Task 2.3: costCalculator.ts

**Create:** `frontend/src/api/local/business/costCalculator.ts`

移植后端 `recipe_service.py` + `ingredient_price_service.py` 成本计算逻辑。

### Task 2.4: nutritionAggregator.ts

**Create:** `frontend/src/api/local/business/nutritionAggregator.ts`

---

## Phase 3：推荐 + 加权 + 层级

### Task 3.1: mealRecommender.ts

**Create:** `frontend/src/api/local/business/mealRecommender.ts`

### Task 3.2: priceWeighted.ts

**Create:** `frontend/src/api/local/business/priceWeighted.ts`

### Task 3.3: hierarchyResolver.ts

**Create:** `frontend/src/api/local/business/hierarchyResolver.ts`

### Task 3.4: Meals + Sparklines Handler

**Create:** `frontend/src/api/local/handlers/meals.ts`, `sparklines.ts`

---

## Phase 4：特殊功能

### Task 4.1: USDA Handler

**Create:** `frontend/src/api/local/handlers/usda.ts`

### Task 4.2: Blacklist Handler

**Create:** `frontend/src/api/local/handlers/blacklist.ts`

### Task 4.3: Admin Config Handler

**Create:** `frontend/src/api/local/handlers/admin.ts`

---

## Phase 5：浏览器 Agent

### Task 5.1: Agent Tools

**Create:** `frontend/src/api/local/agent/tools.ts`

定义 7 个预设工具：read_products, read_ingredients, read_recipes, read_nutrition, update_nutrition, batch_update, read_statistics。

### Task 5.2: Agent Runner

**Create:** `frontend/src/api/local/agent/runner.ts`

支持 Anthropic API 和 OpenAI API，用户配置 API Key。

### Task 5.3: Agent Approval

**Create:** `frontend/src/api/local/agent/approval.ts`

>50 条批量操作弹确认框。

### Task 5.4: Agent Task Templates

**Create:** `frontend/src/api/local/agent/taskTemplates.ts`

---

## Phase 6：页面适配

### Task 6.1: userStore

**Modify:** `frontend/src/stores/user.ts` — 本地模式返回固定管理员用户。

### Task 6.2: Router

**Modify:** `frontend/src/router/index.ts` — 本地模式跳过守卫。

### Task 6.3: mealsStore

**Modify:** `frontend/src/stores/meals.ts` — 本地模式不走轮询。

### Task 6.4: 隐藏管理功能

**Modify:** `frontend/src/components/layout/AppLayout.vue` — 隐藏图片存储等菜单。

### Task 6.5: 图片处理

**Modify:** `frontend/src/utils/image.ts` — 本地模式读 IndexedDB Blob。

---

## Phase 7：首次启动向导

### Task 7.1: 种子数据 seed.ts

**Create:** `frontend/src/api/local/seed.ts`

硬编码基础单位（kg/g/斤/L/mL/个等）和 13 个原料分类。

### Task 7.2: 向导页面

**Create:** `frontend/src/views/setup/LocalInitWizard.vue`
**Create:** `frontend/src/views/setup/SetupImportRepo.vue`
**Create:** `frontend/src/views/setup/SetupImportZip.vue`
**Create:** `frontend/src/views/setup/SetupSkip.vue`

### Task 7.3: 向导路由

**Modify:** `frontend/src/router/index.ts`
New: `/setup` 路由。

### Task 7.4: 启动检测

**Modify:** `frontend/src/App.vue` — 本地模式检测 units 表空则跳转 /setup。

---

## Phase 8：导入/导出 + 构建验证

### Task 8.1: 导入 Handler

**Create:** `frontend/src/api/local/handlers/exportImport.ts`

ZIP 导入/远程仓库导入/HowToCook 导入。

### Task 8.2: 导出 Handler

IndexedDB 数据打包为 ZIP 下载。

### Task 8.3: 完整构建验证

```bash
# 云模式构建（不受影响）
cd frontend && VITE_STORAGE_MODE=cloud npm run build
# 本地模式构建
cd frontend && VITE_STORAGE_MODE=local npm run build
# TS 类型检查
cd frontend && npx vue-tsc --noEmit
```

