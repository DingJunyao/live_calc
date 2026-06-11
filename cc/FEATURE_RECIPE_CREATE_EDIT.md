# 菜谱新增/编辑功能

## 概述

为菜谱管理模块新增创建和编辑功能。采用**详情页就地编辑**模式，每个功能区块独立切换查看/编辑状态。

## 后端变更

### 新增 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `PUT` | `/api/v1/recipes/{id}` | 部分更新菜谱，使用 `exclude_unset=True` 仅修改传入字段 |
| `POST` | `/api/v1/recipes/{id}/images` | 上传配图（multipart/form-data），保存至 `backend/static/images/recipes/` |
| `DELETE` | `/api/v1/recipes/{id}/images/{filename}` | 删除指定配图及文件 |

### Schema 变更

- 新增 `RecipeIngredientUpdate` — 支持按 `ingredient_name` 匹配的全量替换
- 更新 `RecipeUpdate` — 新增 `ingredients` 字段（全量替换）

### 已有端点

- `POST /api/v1/recipes` — 创建菜谱（已有，创建对话框使用）

## 前端变更

### 新增组件

| 组件 | 路径 | 功能 |
|------|------|------|
| `ImageManager.vue` | `frontend/src/components/recipes/` | 配图网格管理：缩略图展示、上传、删除、封面标记 |
| `RecipeBasicCard.vue` | `frontend/src/components/recipes/` | 基本信息卡片：名称/分类/难度/简介，含编辑模式 |
| `RecipeIngredientCard.vue` | `frontend/src/components/recipes/` | 原料列表卡片：行内表格编辑，原料搜索自动补全 |
| `RecipeStepCard.vue` | `frontend/src/components/recipes/` | 步骤卡片：描述/时长/小贴士编辑 |
| `RecipeTipCard.vue` | `frontend/src/components/recipes/` | 小贴士卡片：文本列表编辑 |
| `types.ts` | `frontend/src/components/recipes/` | 共享类型定义 |

### 修改组件

| 组件 | 变更 |
|------|------|
| `RecipeDetail.vue` | 保持原有布局结构不变，内联内容替换为新卡片组件；添加保存事件处理（自动重新加载成本数据） |
| `RecipesView.vue` | 替换占位创建对话框为实际表单（名称/分类/难度；创建后跳转详情页） |

## 编辑模式设计

- 每个可编辑卡片有独立的编辑/查看模式切换
- 点击「编辑」→ 当前值填入表单 → 显示「保存」「取消」按钮
- 保存 → 调用 `PUT /api/v1/recipes/{id}`（仅提交当前卡片相关字段）
- 取消 → 恢复原值，退出编辑模式
- 创建后跳转到详情页为查看模式，用户按需点击各区块编辑按钮

## 关键设计决策

1. **布局保持不变**：详情页的 recipe-top-grid、v-row/v-col 结构完全保留，仅将内联内容替换为组件
2. **独立保存**：各卡片独立提交各自的 PUT 请求，后端用 `exclude_unset=True` 仅更新传入字段
3. **原料全量替换**：编辑原料时使用全量替换模式，简化后端逻辑
4. **触发词保存判断**：当编辑内容与原始数据一致时跳过 API 调用
