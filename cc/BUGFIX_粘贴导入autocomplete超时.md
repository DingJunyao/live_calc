# 粘贴导入 autocomplete 并发风暴超时修复

## 现象

个人中心 / 快速填写「粘贴导入」粘贴一两百行价格点「解析并匹配」，前半部分商品能匹配上，**后半部分大量商品匹配不上**（状态停在 unmatched，需手动处理）。浏览器 DevTools 可见 `/api/v1/products/autocomplete?q=xxx&limit=20` 后面的请求超时。

## 根因（双层瓶颈）

### 主因：前端解析阶段零并发限制

[PasteImportDialog.vue:256](../frontend/src/components/prices/PasteImportDialog.vue#L256) `doParse`：

```js
const okRows = rows.value.filter(r => r.ok)
await Promise.all(okRows.map(r => tryAutoMatch(r)))
```

`Promise.all(okRows.map(...))` 对每行**同时**发起 autocomplete 请求，零并发限制。200 行 → 瞬间 200 个 `GET /products/autocomplete` 齐发。每个 `tryAutoMatch` 内部一次请求（[:266](../frontend/src/components/prices/PasteImportDialog.vue#L266)）。

讽刺的是同文件 [doImport:450](../frontend/src/components/prices/PasteImportDialog.vue#L450) 导入阶段有 `CONCURRENCY = 5` 分批，解析阶段却裸奔——典型的「一处限流、一处漏」。

### 放大器：后端 autocomplete 全表扫描 + Python 内存遍历

[products_entity.py:815-826](../backend/app/api/products_entity.py#L815) `product_autocomplete`：

```python
products = db.query(Product).options(joinedload(Product.ingredient))\
    .filter(Product.is_active == True).all()   # 全表扫描所有活跃商品
...
for product in products:                        # Python 逐行子串匹配
    if search_lower in product.name.lower(): ...
    elif product.aliases: for alias in ...      # 遍历商品别名
    if not match_type and product.ingredient:
        if search_lower in product.ingredient.name.lower(): ...
        elif product.ingredient.aliases: for alias in ...  # 遍历原料别名
```

- **全表扫描**：拉所有活跃商品（实测 **851 个**）+ joinedload 关联原料（745 个）
- **不走索引**：匹配在 Python 层用 `in` 子串比对完成，O(N×M)（N=商品数、M=平均别名数）
- **库是 SQLite**（`backend/.env` 确认 `DATABASE_URL=sqlite:///./data/livecalc.db`），并发读能力弱

单次粗估 50-150ms（ORM hydrate 851 行 + Python 遍历）。200 并发 → 后端 SQLite 连接池打满 + 200 次全表扫排队。

### 传输层 + 超时

- vite dev proxy 走 HTTP/1.1，浏览器对同域并发连接约 6 个，200 请求大量排队
- 前端 axios `timeout = 10000`（[client.ts:5](../frontend/src/api/client.ts#L5)，`VITE_REQUEST_TIMEOUT` 默认 10s）
- 排队超 10s 的请求 `ECONNABORTED` → [tryAutoMatch catch:310](../frontend/src/components/prices/PasteImportDialog.vue#L310) `/* 保持 unmatched */` 静默吞掉 → 用户看到「后面没匹配到」

## 修复

对齐 `doImport` 的分批范式，把 `doParse` 的齐发 `Promise.all` 改为限流分批：

```js
const okRows = rows.value.filter(r => r.ok)
const MATCH_CONCURRENCY = 5
for (let i = 0; i < okRows.length; i += MATCH_CONCURRENCY) {
  await Promise.all(okRows.slice(i, i + MATCH_CONCURRENCY).map(r => tryAutoMatch(r)))
}
```

### 安全性

- `tryAutoMatch` 内部整体被 `try { ... } catch { /* 保持 unmatched */ }` 包住（[:265-313](../frontend/src/components/prices/PasteImportDialog.vue#L265)），无 rethrow，**必 resolve**
- 故 `Promise.all` 不会因某行失败 reject 带崩整批，单行失败仅该行保持 unmatched（语义不变）

### 性能

200 行 / 5 并发 × ~100ms ≈ 4s（远低于 10s 超时）。后端同时只承受 5 个全表扫，SQLite 不再被打爆。

## 边界 / 未动

- **后端 autocomplete 未动**：端点被 4 处共用（[QuickFillView:515](../frontend/src/views/prices/QuickFillView.vue#L515)、[PricesView:654](../frontend/src/views/prices/PricesView.vue#L654)、PasteImportDialog ×2），改语义/查询影响面大，YAGNI——前端限流已根治主因。
- **后端潜伏放大器仍在**：全表扫 + Python 遍历在数据量小时无感，商品继续增长后单次 autocomplete 会变慢。后续可选优化：SQL 层 `LIKE` 预过滤减少 Python 遍历行数 / 进程内 LRU 缓存全表结果（新增商品时失效）/ 新增 `POST /products/batch-match` 批量端点（200 次 HTTP 缩 1 次、1 次全表扫服务 200 名）。本次均不做。
- **doImport 的 CONCURRENCY 未统一**：两处各局部 `5`，语义都是「打后端的并发数」，未抽顶层常量（doImport 带进度/业务逻辑，强抽别扭，YAGNI）。

## 验证

- 前端 build 通过（26.03s，precache 131 entries，无新警告）
- 代码审查：分批逻辑正确、tryAutoMatch 必 resolve 保证 Promise.all 安全
- **手动验证待做**：粘贴 200 行，DevTools Network 看 autocomplete 每批 5 个并发（不再 200 齐发）、后半部分不再超时 unmatched

## 教训

- `Promise.all(items.map(asyncFn))` 是并发风暴经典坑——凡是「对一组数据逐个发请求」都要限流，且要覆盖**所有**批量调用点（导入限了、解析漏了就是本次 bug）
- 后端「全表扫 + Python 遍历」是潜伏放大器：数据量小时无感，量大或并发一上来就崩。autocomplete 这类高频只读端点尤其要注意
- 同文件已有正确范式（doImport CONCURRENCY=5）却在新逻辑（doParse）里漏抄——review 时「同类操作限流是否一致」该作为检查项

## 改动文件

- [frontend/src/components/prices/PasteImportDialog.vue](../frontend/src/components/prices/PasteImportDialog.vue)（doParse 单处，+6 行）

无表结构变更，无后端改动，无新依赖。未 commit。
