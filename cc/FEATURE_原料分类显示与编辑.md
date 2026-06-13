# 功能：原料分类显示与编辑

日期：2026-06-13

## 需求

原料详情页基本信息区不显示分类；编辑时也无法修改分类。

## 现状分析

- 前端详情页用 `GET /nutrition/ingredients/{id}`（nutrition 的 `get_ingredient`）加载，该接口 `load_only` 未含 `category_id`，`IngredientResponse` 也无分类字段 —— 后端根本不返回分类。
- 前端 `IngredientDetail.vue` 基本信息显示区与编辑表单均无分类相关代码。
- 编辑保存走 `PUT /ingredients/{id}`（ingredient_extended 的 `update_ingredient`），该接口**已支持** `category_id` 参数并返回 `category_id`/`category`，只是前端未用。
- 分类共 12 个，全部为扁平顶级分类（谷物、蔬菜、水果…），`GET /ingredients/categories` 不传 parent_id 即返回全部，无需递归。

## 实现

### 后端（让详情接口返回分类）

- `backend/app/schemas/nutrition.py` `IngredientResponse`：新增 `category_id: Optional[int]`、`category: Optional[str]`。
- `backend/app/api/nutrition.py` `get_ingredient`：`load_only` 增加 `Ingredient.category_id`；就近 import `IngredientCategory`，按 `category_id` 查 `display_name`；返回补充 `category_id`/`category`。

### 前端（`IngredientDetail.vue`）

- `Ingredient` interface 增加 `category_id?`/`category?`。
- 新增 `categories` ref 与 `loadCategories()`（调 `GET /ingredients/categories`），并在 `onMounted` 调用。
- `basicEditForm` 增加 `category_id`；`startEditBasicInfo` 填充、`saveBasicInfo` payload 携带 `category_id`（提交后由 PUT 接口返回值刷新 `ingredient.value`，分类即时更新）。
- 基本信息显示模式：默认单位之后增加「分类」`v-list-item`（`v-if="ingredient.category"`）。
- 编辑模式：默认单位选择器之后增加「分类」`v-autocomplete`（`items=categories`，`item-title=display_name`，`item-value=id`，`clearable`）。

## 验证

- 后端 `py_compile` 通过；前端 `npm run build` 通过（17.99s）。
- 数据：641 个活跃原料中 618 个带分类。
