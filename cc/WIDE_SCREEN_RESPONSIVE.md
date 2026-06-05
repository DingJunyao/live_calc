# 宽屏响应式布局优化（列表页）

## 改动内容

### 列表页
- PricesView、ProductsView、IngredientsView：`v-list` 单列 → `v-row`/`v-col` 卡片网格
- RecipesView：固定两列 → 响应式断点
- 断点：xs(1列) / sm(2列) / md(3列) / lg(4列) / xl(6列)

### 共享 CSS
- 新增 `frontend/src/assets/css/responsive.css`
- 提供 `.list-grid-container`、`.list-grid-card` 等类名
- 超宽屏 `max-width: 1600px` 限制可读性

## 涉及文件
- `frontend/src/assets/css/responsive.css` — 新建
- `frontend/src/main.ts` — import
- `frontend/src/views/prices/PricesView.vue`
- `frontend/src/views/data/ProductsView.vue`
- `frontend/src/views/data/IngredientsView.vue`
- `frontend/src/views/recipes/RecipesView.vue`

## 验证
- `npm run build` 通过，无新增 warning
- 移动端（< 960px）布局不变
