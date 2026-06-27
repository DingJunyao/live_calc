# 修复：快速填写排序写入失败（product-orders 500）

日期：2026-06-27

## 现象

快速填写页「按填写顺序排序」从未生效，历史商品始终按拼音排序。用户填写价格后，下次进入仍只见拼音序。

## 根因

后端 [merchants.py](../backend/app/api/merchants.py) `save_product_orders`（`POST /merchants/{id}/product-orders`）的 upsert 循环有缺陷：它只在请求**开始时**查一次当天已有记录塞进 `existing` 字典，循环里 `db.add` 新记录后，并未把本轮新增的对象登记回 `existing` 字典。

当请求体 `product_ids` 含重复 product_id 时（粘贴导入时两行匹配到同一商品，实测 product_id=622 出现两次），第二次遇到同一 pid 时 `existing` 里仍没有它（只含 db 已有，不含本轮刚 add 的），于是又走 `db.add` 分支 → 同 `(user, merchant, product, session_date)` 两条记录 → commit 触发 UNIQUE 约束 → `IntegrityError` → 500。

前端 [QuickFillView.vue](../frontend/src/views/prices/QuickFillView.vue) 的 `saveAll` / `onPasteImported` 对该调用做了 `try/catch + console.warn` 静默吞错，用户无感。后果：`user_merchant_product_orders` 表 count 恒为 0，`get_merchant_product_prices` 算不出 `custom_sort_score`（全 undefined），前端排序全部回退「分类 + 拼音」分支。

## 取证链

- `user_merchant_product_orders` count = 0；表/schema 正确，alembic 已到 `20260626_0003`（含建表迁移 `20260623_0001`）。
- DB 层直写 + TestClient 小量请求（5 个**不重复** pid + 远期日期）均 200 → 排除表结构/鉴权/路由/序列化问题。
- `backend/logs/error.log` 实锤：`UNIQUE constraint failed ... [parameters: (1,1,622,'2026-06-27',26)]`，对应请求体 `product_ids` 中 622 出现两次。
- TestClient 复现：`[325,78,325,1,30]` → 500（325 重复，同参数冲突）。
- 全历史日志 `product-orders` 仅在今天调试期间出现 2 次（用户现场操作），且都是 500 —— 印证「从未成功写入」。

## 修复

[merchants.py](../backend/app/api/merchants.py) `save_product_orders` 的 upsert：

- `existing` 简化为以 `product_id` 为键（本请求内 user/merchant/session_date 固定，四元组冗余）。
- 新增 `seen` 字典跟踪**本轮**新增的记录。
- 循环里 `record = seen.get(pid) or existing.get(pid)`：重复 pid 时更新已有对象的 `sort_order`（后者覆盖前者位置），不再重复 `db.add`，从根上消除同请求内 UNIQUE 冲突。

## 验证

- TestClient：`[325,78,325,1,30]` → **200**（修复前 500），写入 4 条（325 去重），325 `sort_order=2`（最后出现位置）。
- 同日 upsert 再发 `[78,325]` → 200，条数不新增（更新而非重复插入）。
- 静态：import 通过（语法 OK）。
- 单测因 .venv 未装 pytest 未跑；运行时由后端自动重载生效，用户重新填写一次即可让排序记录开始累积。

## 前端配套修复（按填写顺序）

手动快速填写（`saveAll`）原本记录的 `savedProductIds` 顺序来自 `visibleHistoryRows`（**页面显示顺序 = 拼音序**），并非「用户实际填写顺序」。经确认需求为严格「填写顺序」，已一并修复 [QuickFillView.vue](../frontend/src/views/prices/QuickFillView.vue)：

- `FillRow` 新增 `filledAt?: number`（首次填上有效价格的时间戳）。
- 历史行价格输入框改 `:model-value` + `@update:model-value` → 新增 `onPriceChange`：有效价格（>0）时记 `filledAt`（首次记、后续不覆盖；清空/无效则重置）。
- `saveAll` 收集 `savedProductIds` 时按 `filledAt` 升序排序（无 `filledAt` 的排末尾），写入 `product-orders` 的 `sort_order` 即反映填写顺序，而非显示顺序。

粘贴导入（`onPasteImported`）的顺序本就是粘贴文本顺序（=填写顺序），后端 500 修复后即生效，无需改。前端 `npm run build` 通过。
