# 快速填写自定义商品顺序

## 概述

当前快速填写页面的商品按「分类 sort_order → 拼音」排列。对于固定路线的超市，用户希望自定义顺序，系统通过「记录学习」自动记住用户每次保存时的商品顺序，并按最近三次加权排序。

## 需求要点

- 记录用户在某超市保存价格记录时的商品顺序
- 最近三天加权排序（今天×3、昨天×2、前天×1）
- 仅记录 `record_type=price` 的记录（不计入出项目）
- 按用户所在时区计算日期
- 填过的商品排前面，没填过的保持默认（分类→拼音）顺序
- 粘贴导入也纳入顺序学习——按粘贴文本的顺序记录
- 仅针对「当前用户 + 当前商家」生效

## 数据模型

### 新增表：`user_merchant_product_orders`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer PK | 主键 |
| `user_id` | Integer FK → users.id | 用户 |
| `merchant_id` | Integer FK → merchants.id | 商家 |
| `product_id` | Integer FK → products.id | 商品 |
| `session_date` | Date | 会话日期（按用户时区） |
| `sort_order` | Integer | 在该次会话中的位置（从 0 开始） |
| `created_at` | DateTime | 创建时间 |

**约束：** `UNIQUE(user_id, merchant_id, product_id, session_date)` — 同一天同商品只记一次
**索引：** `(user_id, merchant_id, session_date)` — 快速查询最近排序记录

## 排序算法

### 加权规则

| 天数 | 权重 |
|---|---|
| 今天 | ×3 |
| 昨天 | ×2 |
| 前天 | ×1 |

对每个商品计算加权平均 `sort_order`：

```
score = Σ(sort_order × weight) / Σ(weight)
```

### 分段排序

1. **第一段**：最近 3 天有出现过（有排序记录）的商品 → 按加权平均分升序
2. **第二段**：没出现过的商品 → 按当前默认规则（分类 sort_order → 拼音）

### 示例

| 商品 | 前天(×1) | 昨天(×2) | 今天(×3) | 加权平均 | 分段 |
|---|---|---|---|---|---|
| 牛奶 | 0 | 1 | — | (0×1 + 1×2)/3≈0.67 | 第一段 |
| 面包 | 1 | — | — | (1×1)/3≈0.33 | 第一段 |
| 鸡蛋 | — | 0 | — | (0×2)/3=0 | 第一段 |
| 黄油 | — | — | — | — | 第二段 |

最终顺序：**鸡蛋 → 面包 → 牛奶 → [分割] → 黄油（默认规则）**

## 后端变更

### 新增模型：`UserMerchantProductOrder`

文件：`backend/app/models/user_merchant_product_order.py`

SQLAlchemy 模型，对应上表结构。在 `app/models/__init__.py` 引入。

### 新增端点：`POST /api/v1/merchants/{merchant_id}/product-orders`

**请求体：**
```json
{
  "product_ids": [12, 35, 8, 21, 47],
  "session_date": "2026-06-23"
}
```

- `session_date` 由前端按用户时区传入：`new Date().toLocaleDateString('en-CA', { timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone })` → `"2026-06-23"`
- 后端逐条 upsert：同 `(user_id, merchant_id, product_id, session_date)` 已存在则更新 `sort_order`，不存在则插入
- `sort_order` 取 `product_ids` 数组的索引（从 0 开始）

### 修改端点：`GET /api/v1/merchants/{merchant_id}/product-prices`

在现有返回数据中，给每个 item 增加 `custom_sort_score` 字段：

```python
# 额外查询：获取当前用户该商家最近 3 天的排序记录
# 按加权规则计算每个商品的综合排序分
# 有排序分的商品 score 为 float，其余为 None
```

后端不改变现有 SQL 和排序逻辑，仅附加分数供前端使用。

**新增查询参数：** 无（`session_date` 由前端计算传过来）

### 新旧 SQL 脚本

分别在 `backend/scripts/sql/` 下生成 SQLite / MySQL / PostgreSQL（无 PostGIS）/ PostgreSQL（有 PostGIS）四个版本的建表脚本。

### Alembic 迁移

新增迁移文件，含 `create_table` 和索引创建。

## 前端变更

### QuickFillView.vue

#### 1. 保存后记录顺序（`saveAll`）

```typescript
// 在 saveAll() 末尾，收集成功的 product_id（按 rowsToSave 的顺序）
const savedProductIds = results
  .filter(r => r.ok && r.pid)
  .map(r => r.pid as number)

if (savedProductIds.length > 0 && selectedMerchantId.value) {
  const sessionDate = new Date().toLocaleDateString('en-CA', {
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  })
  await api.post(`/merchants/${selectedMerchantId.value}/product-orders`, {
    product_ids: savedProductIds,
    session_date: sessionDate,
  })
}
```

#### 2. 排序逻辑调整（`onMerchantChange`）

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

#### 3. 分页调整

快速填写页调用 `product-prices` 时传 `limit=200`，确保一次拉取足够商品用于排序。如果超了 200，加 `loadAllPages()` 合并。

### PasteImportDialog.vue

#### 扩展 `@imported` 事件

```typescript
// doImport() 末尾，按 targets 顺序收集 product_id
const savedProductIds: (number | null)[] = new Array(payloads.length).fill(null)

// 在并发循环中填充（简化示意，实际在 settled handler 中赋值）
// for existing: savedProductIds[i] = p.row.productId
// for new_attach: savedProductIds[i] = res.data.product_id

emit('imported', savedProductIds.filter((id): id is number => id != null))
```

**QuickFillView 响应：**

```typescript
async function onPasteImported(savedProductIds: number[]) {
  if (selectedMerchantId.value && savedProductIds.length > 0) {
    const sessionDate = new Date().toLocaleDateString('en-CA', {
      timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    })
    await api.post(`/merchants/${selectedMerchantId.value}/product-orders`, {
      product_ids: savedProductIds,
      session_date: sessionDate,
    })
  }
  await onMerchantChange(selectedMerchantId.value)
}
```

### 新建商品的处理

如果用户通过「新增商品」行添加了一个全新商品（`isNew`），该行保存时还没有 `product_id`。`saveAll` 中的处理：

- `isNew` 行保存成功后，`results` 中的 `pid` 为 null
- 该行不会进入 `savedProductIds`（因为新商品还没有历史顺序）
- 下次进入时，该商品会出现在历史列表中，后续再保存就能记录顺序了

## 粘贴导入的特殊处理

粘贴导入的 `doImport()` 当前以并发 5 的批量保存商品。需要追踪每个商品对应的 `product_id`：

- **existing 模式：** `row.productId` 已知
- **new_attach 模式：** 从 `api.post('/products', ...)` 响应的 `product_id` 字段获取
- **保存顺序：** `targets` 数组的顺序 = 用户粘贴文本顺序

在并发循环中按 targets 的索引位置收集 product_id：
- `payloads` 的索引 = `targets` 的索引 = 粘贴文本顺序
- 预分配 `savedProductIds: (number|null)[] = new Array(payloads.length).fill(null)`
- existing：`savedProductIds[i] = p.row.productId`
- new_attach：`api.post('/products')` 响应含 `product_id`，在 settled handler 里 `savedProductIds[idx] = res.data.product_id`
- 循环结束后 `.filter(id => id != null)` 排除失败的

确保 `savedProductIds` 的顺序与粘贴文本一致。

## 用户界面

本次改动**不涉及 UI 变化**：
- 没有拖拽排序
- 没有编辑模式
- 没有「编辑排序」按钮
- 排序学习对用户完全透明

用户仅会观察到：在某家超市填过几次价格后，下次进的商品顺序会更贴近自己的路线习惯。

## 数据一致性

- 排序记录只增（同一天同商品更新 `sort_order`）
- 建议定期清理 7 天前的旧记录（可后续加定时任务，首发不做）
- 商品被删除后，排序记录中的 `product_id` 变为孤儿数据，不影响查询（LEFT JOIN 无匹配跳过）

## 依赖关系

- 后端需新增模型、端点、迁移脚本
- 前端 QuickFillView、PasteImportDialog 两处修改
- 无新增前端依赖
- 需要在 `app/models/__init__.py` 中注册新模型
- 需要在 `app/api/merchants.py` 中注册新路由

## 未做（YAGNI）

- ❌ 拖拽排序 UI（后续如需可加）
- ❌ 手动覆盖排序功能
- ❌ 跨设备同步逻辑（数据库存储天然支持）
- ❌ 定期清理旧记录的定时任务
