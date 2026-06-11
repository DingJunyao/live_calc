# 菜谱新增/编辑功能设计

## 概述

为菜谱管理模块新增创建和编辑功能。采用**详情页就地编辑**模式，每个功能区块独立切换查看/编辑状态，与原料详情页的分区编辑模式保持一致。

## 整体架构

### 组件树

```
RecipeDetail.vue (已有，需改造)
├── RecipeBasicCard.vue          ← 新增：基本信息卡片（名称/类别/难度/简介/配图）
│   └── ImageManager.vue        ← 新增：配图网格管理
├── RecipeCostCard.vue           ← 已有：成本估算（只读，不改造）
├── RecipeCostTrendCard.vue      ← 已有：成本趋势（只读，不改造）
├── RecipeIngredientCard.vue     ← 新增：原料列表卡片（含行内表格编辑）
├── RecipeStepCard.vue           ← 新增：步骤列表卡片（含可排序编辑）
├── RecipeTipCard.vue            ← 新增：小贴士卡片（含文本列表编辑）
└── RecipeNutritionCard.vue      ← 已有：营养成分（只读，不改造）
```

### 数据流

1. 详情页加载 → 获取菜谱基本信息 → 渲染所有卡片骨架 → 各卡片自行判断查看/编辑模式
2. 每个可编辑卡片独立管理 `editing` 状态，点击编辑按钮切换，保存后局部刷新卡片数据
3. 新增入口：FAB 按钮 → 对话框填基本信息 → POST 创建 → 跳转详情页

### 编辑模式

- 每个可编辑卡片有独立的编辑/查看模式切换
- 点击"编辑"按钮 → 当前值填入表单 → 显示"保存""取消"按钮
- 保存 → 调用 `PUT /api/v1/recipes/{id}`（仅提交当前卡片相关字段）
- 取消 → 恢复原值，退出编辑模式
- 创建后跳转到详情页为查看模式，用户按需点击各区块编辑按钮

---

## 创建对话框

### 触发

列表页 `RecipesView.vue` 右下角 FAB 按钮，弹出 `v-dialog`。

### 表单字段

| 字段 | 组件 | 必填 | 说明 |
|---|---|---|---|
| 名称 | `v-text-field` | ✅ | 最大 200 字符 |
| 类别 | `v-select` | ✅ | 荤菜/素菜/水产/主食/汤与粥/早餐/甜品/调料/半成品/小食 |
| 难度 | `v-select` | ✅ | easy（默认）/medium/hard/expert/simple |

### 交互流程

```
FAB 点击 → 打开 Dialog
  → 填写表单 → 点击"创建"
  → POST /api/v1/recipes { name, category, difficulty }
  → 成功 → 关闭 Dialog，snackbar "菜谱已创建"
  → router.push(`/recipes/${id}`) 跳转详情页（查看模式）
  → 失败 → 在 Dialog 内显示错误信息
```

---

## 基本信息卡片编辑 (`RecipeBasicCard.vue`)

### 查看模式

显示：名称、类别标签、难度标签、简介文本、配图网格

### 编辑模式

| 字段 | 组件 | 说明 |
|---|---|---|
| 名称 | `v-text-field` | 必填，max 200 |
| 类别 | `v-select` | 下拉选择 |
| 难度 | `v-select` | 下拉选择 |
| 简介 | `v-textarea` | 自动调整高度，纯文本 |
| 配图 | `ImageManager` 子组件 | 网格缩略图 + 上传/删除/排序 |

### 配图管理 (`ImageManager.vue`)

- 图片以缩略图网格展示，支持拖拽排序
- 点击 `+` 触发文件选择上传
- 每张图右上角有删除按钮
- 第一张为封面（可拖拽调整顺序）
- 上传调用 `POST /api/v1/recipes/{id}/images`（multipart/form-data）
- 删除调用 `DELETE /api/v1/recipes/{id}/images/{filename}`

---

## 原料卡片编辑 (`RecipeIngredientCard.vue`)

### 查看模式

展示原料列表，每项显示：原料名称（可跳转详情）、用量（含精确值/区间/文字描述）、单位、备注。

### 编辑模式（行内表格）

| 字段 | 组件 | 说明 |
|---|---|---|
| 原料 | `v-autocomplete` | 搜索已有原料，支持远程搜索 |
| 用量类型 | `v-select` | 三选一（见下方） |
| 精确值 | `v-text-field` | 数字，选填 |
| 区间 min | `v-text-field` | 数字，选填 |
| 区间 max | `v-text-field` | 数字，选填 |
| 单位 | `v-autocomplete` | 搜索已有单位，文字描述时隐藏 |
| 备注 | `v-text-field` | 选填，max 200 |
| 操作 | 删除按钮 + 拖拽手柄 | |

### 用量类型切换

| 选项 | 显示字段 |
|---|---|
| `""` (空，默认) | 精确值 + 区间 min/max + 单位（均选填，可自由组合） |
| `适量` | 仅显示文字，隐藏数值和单位 |
| `少许` | 仅显示文字，隐藏数值和单位 |

- 精确值和区间值不互斥，用户可只填一个、两个或全部
- 文字描述（适量/少许）为预设枚举值，与数值互斥

### 交互

- 每行最后一列：删除按钮 + 拖拽排序手柄
- 底部：`+ 添加原料` 按钮
- 拖拽使用 HTML5 drag（无额外依赖）
- 移动端：表格支持横向滚动

---

## 步骤卡片编辑 (`RecipeStepCard.vue`)

### 查看模式

`v-timeline` 展示步骤，每步显示：序号、内容、时长、备注。

### 编辑模式

每步一个卡片，按序号排列：

| 字段 | 组件 | 说明 |
|---|---|---|
| 序号 | 自动编号 | 随拖拽自动更新 |
| 描述 | `v-textarea` | 必填，自动调整高度 |
| 时长（分钟）| `v-text-field` | 选填，数字 |
| 备注 | `v-text-field` | 选填 |

- 每步右上角：拖拽手柄 + 删除按钮
- 底部：`+ 添加步骤` 按钮
- 保存时打包为 `cooking_steps` JSON 数组（按当前顺序）

---

## 小贴士卡片编辑 (`RecipeTipCard.vue`)

### 查看模式

已有功能，展示小贴士列表。

### 编辑模式

每行一个小贴士：

| 字段 | 组件 | 说明 |
|---|---|---|
| 内容 | `v-textarea` | 单行，自动调整高度 |
| 操作 | 拖拽手柄 + 删除按钮 | |

- 底部：`+ 添加小贴士` 按钮
- 保存时打包为 `tips` JSON 数组（按当前顺序）

---

## 后端 API 变更

### 1. `POST /api/v1/recipes` — 创建菜谱（已有，确认字段）

创建时仅需 `name`、`category`、`difficulty` 三个必填字段，其余字段使用默认值。

### 2. `PUT /api/v1/recipes/{id}` — 更新菜谱（新增）

部分更新端点。前端各卡片独立提交本卡片相关字段，后端使用 `exclude_unset=True` 仅更新传入的字段。

```python
class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    description: Optional[str] = None
    images: Optional[list[str]] = None
    ingredients: Optional[list[RecipeIngredientUpdate]] = None  # 全量替换
    cooking_steps: Optional[list[dict]] = None                 # 全量替换
    tips: Optional[list[str]] = None                           # 全量替换
```

### 3. `POST /api/v1/recipes/{id}/images` — 上传配图（新增）

- 接收 `multipart/form-data`
- 存储图片文件，返回访问路径/URL
- 单次上传一张图片

### 4. `DELETE /api/v1/recipes/{id}/images/{filename}` — 删除配图（新增）

- 删除指定图片文件
- 同时从菜谱的 `images` 列表中移除

### 5. `DELETE /api/v1/recipes/{id}` — 删除菜谱（可选新增）

如果后续需要，可新增删除端点。

---

## 实现要点

### 前端

- 4 个新卡片组件（BasicCard / IngredientCard / StepCard / TipCard）+ 1 个配图管理子组件
- 现有 `RecipeDetail.vue` 中替换对应静态区域为新卡片组件
- `RecipesView.vue` 中替换占位 dialog 为创建对话框
- 新增 API 调用函数（`@/api/recipes.ts`）
- 新增 TypeScript 类型定义

### 后端

- 新增 `PUT /api/v1/recipes/{id}` 端点和服务层方法
- 新增图片上传/删除端点
- 如需：新增图片存储目录及文件管理逻辑
- 更新 Schema 定义

### 数据库

- 现有表结构无需变更，字段已完备
