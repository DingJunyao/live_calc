# 价格记录编辑与删除功能

## 背景

商品详情页和原料详情页的价格记录列表，缺少编辑功能。原料详情页还缺少删除功能。

## 改动

### 后端

无改动。后端已有 `PUT /api/v1/products/{record_id}` 和 `DELETE /api/v1/products/{record_id}` 端点，完整支持更新（价格/数量/单位/商家）和软删除。

### 前端

#### ProductDetail.vue

1. **价格记录列表每行新增编辑按钮**（`mdi-pencil`），与删除按钮并排
2. **添加/编辑共用对话框**：`showAddPriceDialog` 对话框标题改为动态切换「添加价格记录」/「编辑价格记录」
3. 新增 `editingPriceRecord` ref 标记当前编辑模式
4. 新增 `openEditPriceDialog(record)` 填充表单并打开对话框
5. `savePriceRecord` 改为双路：有 `editingPriceRecord` 走 `PUT`，否则走原 `POST`

#### IngredientDetail.vue

1. **价格记录列表每行新增编辑和删除按钮**（原来只有日期文本，无操作按钮）
2. **新增编辑对话框** `showEditPriceDialog`：表单包含价格、数量、单位（v-select）、商家（v-autocomplete），参考 ProductDetail 的添加对话框
3. 新增 `editingPriceRecord`、`editPriceForm`、`savingPrice` 状态
4. 新增 `openEditPriceDialog(record)`：回填表单，延迟加载商家列表
5. 新增 `saveEditPriceRecord()`：调用 `PUT /products/{id}` 更新
6. 新增 `deletePriceRecord(id)`：调用 `DELETE /products/{id}` 软删除
7. 新增 `merchants` ref 和 `loadMerchants()` 辅助函数
8. 新增 `unitOptions` 常量（与 ProductDetail 对齐）

## 设计原则

- 编辑对话框的表单布局与添加对话框保持一致（价格、数量+单位行、商家选择）
- 原料页的商家信息延迟加载（打开编辑对话框时才请求），避免无谓的网络请求
- 两个页面统一调用 `PUT/DELETE /products/{record_id}`，价格记录本质属于商品
