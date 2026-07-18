# 价格记录页点击跳转商品/商家详情

## 背景

价格记录页 [PricesView.vue](frontend/src/views/prices/PricesView.vue)（路由 `/prices`）列表项整行/整卡**不可点击**，用户想看某条记录对应的商品或商家详情只能手动翻「数据管理」。每条记录现成携带 `product_id`/`product_name` + `merchant_id`/`merchant_name`（PriceRecord 接口），跳转**零后端改动**。

## 方案

- 整行/整卡点空白 → 商品明细（`goToProduct` → `/data/products/:id`）
- 行内商家点 → 商家详情（`goToMerchant` → `/data/merchants/:id`）
- 三层 `.stop` 隔离：整行 `@click`（商品）/ 商家 `@click.stop`（商家）/ 6 处按钮 `@click.stop`（再记·编辑·删除 × 移动+桌面）
- 对齐既有 [MerchantsView.vue](frontend/src/views/data/MerchantsView.vue) 范式（整行 `@click` + `router.push` 字符串路径 + 按钮 `.stop`），交互方式用户从「整行/整卡可点 / 新增查看按钮 / 商品名可点」三案中拍板选整行可点

spec：[docs/superpowers/specs/2026-07-18-价格记录跳转详情-design.md](../docs/superpowers/specs/2026-07-18-价格记录跳转详情-design.md)
plan：[docs/superpowers/plans/2026-07-18-价格记录跳转详情.md](../docs/superpowers/plans/2026-07-18-价格记录跳转详情.md)

## 实现（单文件 PricesView.vue +42 行）

- 新增 `goToProduct` / `goToMerchant` 两方法，各带 id guard（`if (!record.product_id) return` / `if (!record.merchant_id) return`）
- **移动端 v-list-item**：加 `@click="goToProduct(record)"`；商家行改条件渲染——`v-if="record.merchant_id"` → `<span class="text-primary cursor-pointer" @click.stop="goToMerchant(record)">` / `v-else` 灰字「未知商家」；append 3 按钮 `@click` → `@click.stop`
- **桌面端 v-card**：加 `@click="goToProduct(record)"` + `cursor-pointer`；商家 chip 动态 `:color="record.merchant_id ? 'primary' : 'default'"` + `:variant="record.merchant_id ? 'tonal' : 'outlined'"` + `@click.stop="goToMerchant(record)"`；card-actions 3 按钮 `@click` → `@click.stop`
- **状态保持**：分页/搜索本就 `syncToUrl` 同步 URL，跳详情返回自动恢复，无需额外开发

## 验证

- `npm run build` 通过（34.06s，precache 128 entries，PricesView chunk 16.45 kB）
- **subagent-driven 双审**：
  - spec 合规 ✅（9 条要求全对，无缺漏/误解；审查员标的「Extra」CLAUDE.md + vite.config.ts 经核实为会话前既有改动误报，非本次 implementer 所为）
  - 代码质量：**Critical 无**；Strengths 为一致性 / 三层冒泡隔离 / guard 防御 / YAGNI
- 手测待开发者核（7 条清单见 plan Task 4 Step 2）

## 设计决策点（reviewer 建议、经评估保持现状）

- **桌面 chip 用「动态 color/variant + 方法内 guard」而非 v-if 条件渲染**：保持桌面形态统一（有/无商家都是 chip、靠颜色区分），guard 已兜底无 id 不跳。改 v-if 会让桌面「chip / 纯文本」形态不统一。spec 认可，保持。若后续用户要求「行为绝对一致」（无商家点击不产生 ripple），再改。
- **移动 cursor-pointer 已加**：触屏无 cursor 概念但无害。

## 不做（YAGNI）

- 不改 [QuickFillView.vue](frontend/src/views/prices/QuickFillView.vue)（填价场景无「点记录商家」语义）
- 不动后端 API、不动路由（`product-detail` / `merchant-detail` 均既有）
- 不写自动测试（前端无单测框架，build 验证即可）

## 文件清单

- `frontend/src/views/prices/PricesView.vue`（单文件 +42）
- `docs/superpowers/specs/2026-07-18-价格记录跳转详情-design.md`
- `docs/superpowers/plans/2026-07-18-价格记录跳转详情.md`
- `cc/FEATURE_价格记录跳转详情.md`（本文）

无表结构变更、无后端改动、无新依赖。未 commit（按项目 CLAUDE.md 规矩，git 操作由开发者决定）。
