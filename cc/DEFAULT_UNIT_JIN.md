# 默认单位改为斤

## 修改内容

将系统中商品（原料）的默认单位从无/克改为**斤**，确保新创建的原料自动以斤作为默认单位。

## 修改文件

### 后端

1. **`backend/app/api/ingredient_extended.py`**
   - 添加 `_get_default_mass_unit_id()` 辅助函数，查询斤单位的 ID
   - `create_ingredient` 接口：当未指定 `default_unit` 时，自动默认使用斤

2. **`backend/app/api/nutrition.py`**
   - `create_ingredient` 接口：当未指定 `default_unit_id` 时，自动默认使用斤
   - 返回结果增加 `default_unit_id` 和 `default_unit_name` 字段

3. **`backend/app/services/enhanced_recipe_import_service.py`**
   - 导入原料时，若 `ingredients_raw.json` 中未指定单位，默认使用斤

4. **`backend/app/services/json_recipe_import_service.py`**
   - 导入原料时，若 JSON 数据中未指定单位，默认使用斤

5. **`backend/app/main.py`**
   - 修复种子数据 Bug：`Unit.abbreviation == "jin"` → `Unit.abbreviation == "斤"`（中文缩写正确查询）

### 前端

1. **`frontend/src/views/data/IngredientsView.vue`**
   - 加载单位列表后自动查找"斤"单位并预设为默认选中
   - 创建原料对话框初始化时默认选中斤
   - 保存后重置表单时保留斤为默认值

2. **`frontend/src/views/ingredients/IngredientDetail.vue`**
   - 加载单位列表后自动查找并存储斤单位的 ID
   - 编辑原料对话框打开时，若原料无默认单位，自动选中斤
   - 价格展示的默认单位回退值从 `'g'` 改为 `'斤'`
   - 图表数据聚合的单位回退值从 `'g'` 改为 `'斤'`

3. **`frontend/src/views/products/ProductDetail.vue`**
   - 添加价格记录对话框的默认单位从 `'g'` 改为 `'斤'`
