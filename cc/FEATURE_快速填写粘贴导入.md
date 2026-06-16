# 快速填写 - 粘贴文本导入价格

## 功能概述

在快速填写页面导航栏新增「粘贴导入」按钮，打开对话框，用户粘贴一段价格文本（如从超市小票/备忘录复制），系统解析出商品名、价格、数量、单位，逐条匹配商品并批量创建价格记录（不计入支出）。不存在的商品由用户手动处理。

第一版为纯手动模式，不含 AI 匹配（AI 智能匹配与后台 AI 配置留待后续版本）。

## 交互流程

1. 快速填写页选好商家 → 点导航栏「粘贴导入」按钮（`mdi-content-paste`，未选商家时禁用）
2. 对话框：日期时间（默认当前）、粘贴文本框、「解析并匹配」按钮
3. 解析后预览表格：状态图标（✅已匹配 / ⚠️待处理 / ❌无法识别）+ 商品 / 价格 / 数量 / 单位
4. 未匹配行点商品名展开菜单：关联已有商品 / 创建同名原料+商品 / 挂靠已有原料
5. 点「全部导入」→ 并发创建（并发数 5）→ 进度条 → 成功 / 失败数 + 失败项目
6. 全部成功后自动关闭并刷新历史商品列表

## 解析规则

支持的格式（名称与价格用空格或 tab 分隔）：

| 格式 | 示例 | 解析结果 |
|------|------|---------|
| 名称 价格 | `芹菜 1.88` | 1 斤 |
| 名称 价格/单位 | `芽菇 4/袋` | 1 袋 |
| 名称 价格/缩写单位 | `嫩豆腐 5.18/kg` | 1 kg |
| 名称 价格/数量+单位 | `土豆粉 2.5/200g` | 200 g |

单位别名归一化：`克→g`、`公斤/千克→kg`；`g`/`kg` 原样；其余（如「袋」）原样交后端 `UnitMatcher` 自动匹配或创建。空行、`#` 注释行跳过。

解析逻辑在 `frontend/src/utils/pastePriceParser.ts`（纯函数，可独立验证；项目暂无前端测试框架）。

## 商品匹配（手动模式）

- **精确匹配**：解析后自动调 `/products/autocomplete`，名字完全相等则标 ✅（同时缓存候选，供展开菜单复用，避免重复请求）
- **未匹配行手动处理三种模式**：
  1. 关联已有商品（传 `product_id`）
  2. 创建同名原料 + 同名商品（传 `product_name`，后端 `_get_or_create_product` 自动建同名原料）
  3. 挂靠已有原料创建商品（传 `product_name` + `ingredient_id`，在指定原料下建商品）
- 创建商品必须挂靠原料，不允许悬空

## 后端改动

`POST /products`（`ProductRecordCreate`）增加可选 `ingredient_id` 字段；`_get_or_create_product` 支持 `ingredient_id`：传了在指定原料下建商品（原料不存在或未激活则 404），不传维持原「同名原料+同名商品」行为。**向后兼容，无表结构变更**（无需 alembic 迁移或 SQL 脚本）。

## 技术要点

- **不计入支出**：统一 `record_type='price'`（后端无 `include_in_spending` 字段；`purchase` 才计入支出）
- 商家沿用快速填写页已选商家；日期时间默认当前，可改
- 并发导入并发数 5（`Promise.allSettled` 分批），进度条 `current/total`
- 导入完成后 emit `imported` → QuickFillView 调 `onMerchantChange` 刷新，已导入商品按现有「近 1h 隐藏」逻辑隐藏
- 响应式适配移动端

## 文件清单

前端：
- 新增 `frontend/src/utils/pastePriceParser.ts`（解析纯函数）
- 新增 `frontend/src/components/prices/PasteImportDialog.vue`（对话框组件）
- 修改 `frontend/src/views/prices/QuickFillView.vue`（导航栏按钮 + 接入对话框）

后端：
- 修改 `backend/app/schemas/product.py`（`ProductRecordCreate` 加 `ingredient_id`）
- 修改 `backend/app/api/products.py`（`_get_or_create_product` 支持 `ingredient_id`）

## 不做的事（第一版）

- AI 智能匹配（后续版本）
- 后台 AI 配置页面
- 带商家名的文本格式
- 价格区间、逗号分隔格式
