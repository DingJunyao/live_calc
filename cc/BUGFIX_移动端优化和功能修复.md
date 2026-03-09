# 移动端优化和功能修复记录

## 修复时间
2026-03-09

## 修复的问题

### 1. 移动端输入框放大问题 ✅

**问题描述：**
在移动端操作时，点击输入框后页面会放大，影响用户体验。

**根本原因：**
- viewport配置不完整，缺少禁止缩放的参数
- input元素字体大小小于16px（iOS浏览器自动放大）

**修复方案：**
1. 修改 `frontend/index.html` 中的viewport配置：
   ```html
   <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
   ```
   - 添加 `maximum-scale=1.0` 禁止放大
   - 添加 `user-scalable=no` 禁止用户手动缩放
   - 添加 `viewport-fit=cover` 适配刘海屏

2. 修改 `frontend/src/App.vue` 添加移动端input样式：
   ```css
   input, textarea, select {
     font-size: 16px !important; /* 关键：防止iOS自动放大 */
     -webkit-text-size-adjust: 100% !important;
     transform: translateZ(0); /* 硬件加速优化 */
     -webkit-backface-visibility: hidden;
   }
   ```

### 2. 菜谱搜索功能无效 ✅

**问题描述：**
菜谱列表页面的搜索功能无效，用户输入关键词后没有反应。

**根本原因：**
搜索输入框没有回车触发功能，只有点击搜索按钮才能搜索。

**修复方案：**
修改 `frontend/src/views/recipes/RecipeList.vue`，为搜索输入框添加回车事件：
```vue
<input
  v-model="searchTerm"
  type="text"
  placeholder="搜索菜谱..."
  class="search-input"
  @keyup.enter="loadRecipes"  <!-- 添加回车触发 -->
/>
```

### 3. 维护价格后菜谱成本未更新 ✅

**问题描述：**
用户更新商品价格记录后，相关菜谱的成本显示没有更新。

**根本原因：**
- 菜谱模型中没有 `estimated_cost` 字段
- 前端代码期望显示菜谱成本，但后端没有提供
- 菜谱成本应该实时计算，而不是存储静态值

**修复方案：**
1. 修改 `backend/app/schemas/recipe.py`，在RecipeResponse中添加成本相关字段：
   ```python
   class RecipeResponse(BaseModel):
       # ... 其他字段 ...
       estimated_cost: Optional[Decimal] = None
       calories: Optional[int] = None
       protein: Optional[Decimal] = None
   ```

2. 修改 `backend/app/api/recipes.py`，实时计算菜谱成本和营养信息：
   - 添加 `include_cost` 查询参数，默认为True
   - 在返回菜谱列表时，为每个菜谱计算成本和营养信息
   - 成本计算失败不影响列表返回

   ```python
   @router.get("", response_model=PaginatedResponse)
   async def get_recipes(
       # ... 其他参数 ...
       include_cost: bool = Query(True, description="是否包含成本和营养信息"),
       # ...
   ):
       # 为每个菜谱计算成本和营养信息
       if include_cost:
           cost_result = await calculate_recipe_cost(recipe.id, current_user.id, db=db)
           nutrition_result = await calculate_recipe_nutrition(recipe.id, db=db)
   ```

**优势：**
- 避免数据冗余，不存储静态成本值
- 总是显示最新的成本，基于最新价格
- 不需要在价格更新时触发复杂的级联更新逻辑

### 4. 商品自动完成功能异常 ✅

**问题描述：**
在维护价格时，输入"鸡蛋"等商品名称，下拉建议列表中没有显示匹配的商品，但商品确实存在于数据库中。

**根本原因：**
- 商品API的limit参数设置为200，不足以覆盖所有商品
- 数据格式转换不正确

**修复方案：**
修改 `frontend/src/views/products/ProductList.vue`，改进 `loadAllProducts` 函数：
```javascript
async function loadAllProducts() {
  try {
    const response = await productAPI.list({ limit: 10000 })  // 增加limit
    console.log('商品API响应:', response)
    const items = (response as any).items || (Array.isArray(response) ? response : [])
    // 确保数据格式正确
    allProducts.value = items.map((item: any) => ({
      id: item.id,
      name: item.name,
      brand: item.brand || ''
    }))
    console.log('处理后的商品列表:', allProducts.value)
  } catch (error) {
    console.error('Failed to load products:', error)
    allProducts.value = []
  }
}
```

**改进：**
- 将limit从200增加到10000，确保覆盖所有商品
- 添加详细的调试日志，方便排查问题
- 改进数据解析逻辑，处理不同的响应格式
- 确保数据字段映射正确

### 5. 菜谱成本计算错误 ✅

**问题描述：**
用户记录鸡蛋价格为18元30个（折合0.6元1个），但"完美水煮蛋"菜谱（使用1个鸡蛋）显示的成本为18元，而不是预期的0.6元。

**根本原因：**
- 成本计算逻辑错误，直接使用价格记录的`price`字段作为单价
- `price`字段存储的是总价（18元30个），而不是单价（0.6元/个）
- 计算公式：`总价 × 菜谱数量 = 错误成本`（18 × 1 = 18元）
- 正确公式应该是：`(总价 ÷ 数量) × 菜谱数量 = 正确成本`（(18 ÷ 30) × 1 = 0.6元）

**数据库调查结果：**
```sql
-- 鸡蛋价格记录
SELECT pr.price, pr.standard_quantity FROM product_records pr WHERE pr.product_name LIKE '%鸡蛋%';
-- 结果：price=18, standard_quantity=30

-- 完美水煮蛋配料
SELECT ri.quantity, ri.unit_id FROM recipe_ingredients ri WHERE ri.recipe_id IN (SELECT id FROM recipes WHERE name='完美水煮蛋');
-- 结果：quantity=1, unit_id=18（个）
```

**修复方案：**
修改 `backend/app/services/recipe_service.py` 中的 `calculate_recipe_cost` 函数：

```python
# 之前的错误逻辑
if latest_record:
    unit_price = Decimal(str(latest_record.price))  # 错误！直接用总价当单价
    # ...

# 修复后的正确逻辑
if latest_record:
    # 计算单价：总价 ÷ 数量
    record_price = Decimal(str(latest_record.price))
    record_quantity = Decimal(str(latest_record.standard_quantity))
    unit_price = record_price / record_quantity  # 18 ÷ 30 = 0.6元/个

    # 计算成本：单价 × 菜谱数量
    ingredient_quantity = recipe_ingredient.quantity
    if ingredient_quantity:
        quantity = Decimal(str(ingredient_quantity))
        cost = unit_price * quantity  # 0.6 × 1 = 0.6元
```

**修复位置：**
1. product 查找分支（通过ingredient_id查找商品）
2. fallback 分支（通过名称匹配商品）

**验证：**
- 输入：鸡蛋价格18元30个，菜谱使用1个鸡蛋
- 计算：单价 = 18 ÷ 30 = 0.6元/个，成本 = 0.6 × 1 = 0.6元
- 输出：菜谱成本应该显示为0.6元

**改进：**
- 修复了总价/单价混淆的计算错误
- 删除了重复的unit_price计算代码
- 确保两个查找路径都正确计算单价
- 代码逻辑更清晰，避免混淆

## 技术要点

### 移动端开发最佳实践
1. **viewport配置**：必须包含 `maximum-scale=1.0` 和 `user-scalable=no`
2. **字体大小**：input元素字体大小不小于16px
3. **硬件加速**：使用 `transform: translateZ(0)` 提升性能
4. **刘海屏适配**：使用 `viewport-fit=cover` 参数

### 数据一致性设计原则
1. **实时计算优先**：避免存储静态值，优先实时计算
2. **容错处理**：计算失败不应影响主要功能
3. **性能考虑**：提供参数控制是否包含复杂计算
4. **数据溯源**：成本基于最新价格，保证准确性

### 前端调试策略
1. **详细日志**：在关键逻辑处添加console.log
2. **数据验证**：检查API响应的数据格式
3. **逐步修复**：每个问题独立验证

## 影响范围

### 用户体验改进
- 移动端输入不再自动放大，提升操作体验
- 菜谱搜索功能正常，支持回车快速搜索
- 菜谱成本实时更新，数据更准确
- 商品自动完成功能稳定，提高输入效率

### 系统架构改进
- 菜谱成本计算改为实时模式，避免数据不一致
- API响应更完善，提供更多有用信息
- 前端数据处理更健壮，容错性更强

## 后续优化建议

### 性能优化
1. 菜谱成本计算可以考虑缓存机制
2. 批量计算菜谱成本，减少API调用
3. 前端分批加载菜谱信息

### 功能增强
1. 添加成本变化提示，告知用户价格更新影响
2. 提供成本历史查看功能
3. 优化商品搜索算法，支持模糊匹配

### 代码质量
1. 添加更多单元测试，覆盖边界情况
2. 完善API文档，说明参数含义
3. 统一错误处理机制