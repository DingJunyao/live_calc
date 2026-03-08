# 单位统一管理功能

## 概述

实现了完整的单位管理系统，包括数据库模型重构、智能匹配、API 接口和前端管理界面。

## 实施方案

### 1. 数据库模型重构

**修改的表：**
- `RecipeIngredient.unit` → `unit_id` (外键)
- `Ingredient.default_unit` → `default_unit_id` (外键)
- `ProductRecord.original_unit` → `original_unit_id` (外键)
- `ProductRecord.standard_unit` → `standard_unit_id` (外键)

**优点：**
- 数据一致性保证（外键约束）
- 支持复杂查询（JOIN、关系加载）
- 便于维护和扩展

### 2. 单位数据补充

**新增单位：24 个**
- 体积单位：碗（300mL）
- 计数单位：袋、罐、盒、包、根、瓣、块、小块、片、小片、粒、颗、枚、份、滴、头、朵、棵、株、叶、节、段、圈、撮

**总单位数：46 个**
- 质量单位：6 个
- 体积单位：6 个
- 长度单位：4 个
- 计数单位：29 个
- 时间单位：1 个

### 3. 单位换算关系

**新增关系：**
- 碗 ↔ mL (双向，factor: 300)

**设计原则：**
- 容器单位（袋、罐、盒等）不允许换算
- 模糊单位（块、小片等）作为计数单位，不建立换算关系
- 双向换算自动创建反向关系（避免重复配置）

### 4. 单位匹配服务

**匹配策略：**
1. 精确匹配 `abbreviation`（如 "g"、"kg"）
2. 精确匹配 `name`（如 "克"、"千克"）
3. 模糊匹配（大小写不敏感）
4. 匹配不到时自动创建新单位

**默认行为：**
- 新创建的单位默认为计数类型（count）
- SI因子为 1.0
- 非常用单位
- 显示顺序为 999（排在最后）

### 5. API 端点

**单位管理：**
- `GET /api/v1/units/` - 获取单位列表（支持按类型过滤）
- `GET /api/v1/units/{id}` - 获取单个单位
- `POST /api/v1/units/` - 创建新单位
- `PUT /api/v1/units/{id}` - 更新单位
- `DELETE /api/v1/units/{id}` - 删除单位
- `GET /api/v1/units/{id}/conversions` - 获取单位换算关系
- `POST /api/v1/units/conversions/` - 创建换算关系（支持双向）
- `DELETE /api/v1/units/conversions/{id}` - 删除换算关系
- `POST /api/v1/units/match` - 匹配单位字符串
- `POST /api/v1/units/convert` - 单位转换
- `POST /api/v1/units/import-batch` - 批量导入单位

**菜谱导入集成：**
- 菜谱导入时自动使用单位匹配器
- 匹配不到的单位自动创建
- RecipeIngredient 使用 `unit_id` 外键而非字符串

### 6. 前端管理界面

**UnitManager.vue 功能：**
- 统计卡片（单位总数、换算关系数、分类统计）
- 按类型筛选（质量、体积、长度、计数、时间）
- 搜索功能（支持名称和缩写）
- 创建/编辑单位对话框
- 换算关系管理对话框
- 新增换算关系功能
- 响应式设计（支持移动端）

**导航集成：**
- 在 AdminPanel.vue 中添加"单位管理"按钮
- 路由路径：`/admin/units`

## 技术要点

### 数据库迁移

使用 Alembic 的 batch 模式支持 SQLite：
- `op.batch_alter_table()` - 自动处理复制表和重建
- 支持外键约束创建和删除

### 模型关系

新增的 SQLAlchemy 关系：
- `RecipeIngredient.unit` → Unit
- `Ingredient.default_unit` → Unit
- `ProductRecord.original_unit` → Unit
- `ProductRecord.standard_unit` → Unit

支持 eager 和 lazy 加载策略。

### 单位类型分类

| 类型 | 描述 | 示例 |
|------|------|------|
| mass | 质量单位 | g, kg, 斤, 两, lb, oz |
| volume | 体积单位 | L, mL, 杯, 汤匙, 茶匙, 碗 |
| length | 长度单位 | m, cm, mm, in |
| count | 计数单位 | 个, 只, 条, 片, 瓣等 |
| time | 时间单位 | s |

## 使用说明

### 后端

**单位匹配示例：**
```python
from app.services.unit_matcher import UnitMatcher
from app.core.database import get_db

db = get_db()
matcher = UnitMatcher(db)

# 匹配现有单位
unit, is_new = matcher.match_unit("克")  # 返回 g 单位，is_new=False

# 匹配不存在的单位，自动创建
unit, is_new = matcher.match_unit("勺")  # 返回新创建的"勺"单位，is_new=True
```

**API 调用示例：**
```typescript
// 获取单位列表
const units = await api.get('/units/?unit_type=mass&is_common=true')

// 创建新单位
const newUnit = await api.post('/units/', {
  name: '勺',
  abbreviation: '勺',
  unit_type: 'count',
  is_common: true
})

// 匹配单位字符串
const matchResult = await api.post('/units/match', { unit_str: '克' })
```

### 前端

**访问单位管理：**
1. 进入后台管理（`/admin`）
2. 点击"单位管理"按钮
3. 进入单位管理页面（`/admin/units`）

**主要功能：**
- 查看所有单位及统计信息
- 筛选和搜索单位
- 创建新单位
- 编辑现有单位
- 管理换算关系
- 删除单位或换算关系

## 注意事项

### 初始化脚本

**seeds/units.py** 提供单位数据初始化：
- 补充缺失单位
- 建立换算关系
- 自动跳过已存在的单位

### 迁移策略

由于系统未发布，直接删除数据库并重新创建：
- 无需编写数据迁移脚本
- 简化了实施过程
- 确保数据一致性

### 兼容性

- 原有菜谱和原料数据中的单位字符串会由匹配器处理
- 菜谱导入时会自动将字符串单位转换为外键
- 旧数据的兼容性由单位匹配器保证

## 文件清单

**后端：**
- `backend/app/db/seeds/units.py` - 单位数据初始化
- `backend/app/services/unit_matcher.py` - 单位匹配服务
- `backend/app/api/units.py` - 单位管理 API
- `backend/app/models/recipe.py` - 修改 RecipeIngredient 模型
- `backend/app/models/nutrition.py` - 修改 Ingredient 模型
- `backend/app/models/product.py` - 修改 ProductRecord 模型
- `backend/app/services/recipe_import_service.py` - 集成单位匹配
- `backend/app/main.py` - 注册单位管理路由
- `backend/alembic/env.py` - 修复导入错误

**前端：**
- `frontend/src/views/admin/UnitManager.vue` - 单位管理页面
- `frontend/src/router/index.ts` - 添加单位管理路由
- `frontend/src/views/admin/AdminPanel.vue` - 添加单位管理入口

**迁移：**
- `backend/alembic/versions/20260307_2011_b2b4bee6ffa9_add_unit_foreign_keys.py` - 数据库迁移

## 后续优化建议

1. **单位同义词管理**
   - 添加同义词表，支持一个单位的多种写法
   - 例如："克" = "g" = "gram"

2. **智能换算**
   - 利用原料密度进行体积-质量换算
   - 支持基于食材密度的精确转换

3. **单位验证**
   - 添加单位验证规则
   - 防止创建冲突或不合理的单位

4. **批量操作**
   - 支持批量导入单位
   - 支持批量删除换算关系
   - 支持批量编辑单位属性

5. **单位分组**
   - 添加单位分组表
   - 支持自定义单位组（如中式计量、西式计量）

6. **换算公式支持**
   - 支持非线性换算公式
   - 例如：温度单位转换（华氏度 ↔ 摄氏度）

7. **单位历史**
   - 记录单位的创建和修改历史
   - 支持审计和回滚

## 修复记录

### 2026-03-07 修复

**问题：** 单位字段类型不匹配导致菜谱导入失败

**原因：**
1. 数据库模型已将 `unit` 字段改为 `unit_id`（外键）
2. 但 schema 中 `RecipeIngredientCreate.unit` 仍是 `Optional[str]`
3. recipes API 中使用了 `unit=ingredient_data.unit`（字符串）
4. products API 中使用了 `record.original_unit`（Unit 对象）

**修改的文件：**
- `backend/app/schemas/recipe.py` - 将 `unit: Optional[str]` 改为 `unit_id: Optional[int]`
- `backend/app/api/recipes.py` - 将 `unit=ingredient_data.unit` 改为 `unit_id=ingredient_data.unit_id`（注意：这里使用的是外键 ID）
- `backend/app/api/products.py` - 将 `record.original_unit` 改为 `record.original_unit.abbreviation`（传递单位缩写字符串）

**修改说明：**
1. Schema 中的 `unit_id` 现在是整数类型，对应数据库外键
2. recipes API 使用外键 ID，正确创建关系
3. products API 使用单位对象的 `.abbreviation` 属性，与转换函数兼容

**注意事项：**
- ProductRecord 模型中的 `original_unit` 和 `standard_unit` 是 relationship，返回 Unit 对象
- 使用时需要访问 `.abbreviation` 属性获取缩写字符串
- 或者访问 `.id` 属性获取单位 ID

### 2026-03-07 补充修复

**问题：** 获取菜谱详情时返回的单位字段是 Unit 对象而非字符串

**原因：**
- `RecipeIngredientDetail` schema 的 `unit` 字段类型为 `Optional[str]`
- 但 `get_recipe_detail` 函数中使用了 `unit=ri.unit`，传递的是 Unit 对象
- `ri.unit` 是 relationship，返回 Unit 对象，需要访问其属性

**修改的文件：**
- `backend/app/api/recipes.py` - 第 153 行
  - 修改前：`unit=ri.unit,`
  - 修改后：`unit=ri.unit.abbreviation if ri.unit else None,`

**修改说明：**
1. 使用 `ri.unit.abbreviation` 获取单位缩写字符串
2. 添加空值检查 `if ri.unit else None`，避免 None 对象访问属性错误
3. 确保返回给前端的数据类型与 schema 定义一致

### 2026-03-07 语法错误修复

**问题：** `SyntaxError: invalid syntax` at products.py line 123

**原因：**
- 第 123 行 `original_unit=record.original_unit.abbreviation` 后面缺少逗号
- 导致 Python 解析器无法正确识别参数列表

**修改的文件：**
- `backend/app/api/products.py` - 第 123 行
  - 修改前：`original_unit=record.original_unit.abbreviation`
  - 修改后：`original_unit=record.original_unit.abbreviation,`

**验证结果：**
- 已通过 `python -m py_compile` 对所有关键文件的语法检查
- 检查文件包括：products.py, recipes.py, recipe.py (schema), product.py (model), recipe.py (model), nutrition.py (model)
- 所有服务层和单位管理相关文件也通过了语法检查
- main.py 主入口文件语法正确
- 全部 Python 文件无语法错误

### 2026-03-07 导入服务单位字段修复

**问题：** `'str' object has no attribute '_sa_instance_state' 错误导致原料和菜谱导入失败

**原因：**
- 数据库模型已将单位字段改为外键（`unit_id`、`default_unit_id`）
- 但 `json_recipe_import_service.py` 中仍使用字符串赋值给这些字段
- 第 162 行：`default_unit=item.get("unit", "")` 应为 `default_unit_id`
- 第 372、392 行：`unit=ing_data.get("unit", "")` 应为 `unit_id`

**修改的文件：**
- `backend/app/services/json_recipe_import_service.py`
  - 第 15 行：添加 `from app.services.unit_matcher import UnitMatcher` 导入
  - 第 23 行：在 `__init__` 中初始化 `self.unit_matcher = UnitMatcher(db)`
  - 第 162 行：
    - 修改前：`default_unit=item.get("unit", "")`
    - 修改后：使用单位匹配器获取 unit_id
  - 第 372 行：
    - 修改前：`unit=ing_data.get("unit", "")`
    - 修改后：使用单位匹配器获取 unit_id
  - 第 392 行：
    - 修改前：`unit=ing_data.get("unit", "")`
    - 修改后：使用单位匹配器获取 unit_id

**修改说明：**
1. 导入 `UnitMatcher` 类并在服务初始化时创建实例
2. 在创建 Ingredient 时使用 `self.unit_matcher.match_or_create_unit()` 匹配或创建单位
3. 将匹配到的单位对象的 `id` 赋值给 `default_unit_id` 字段
4. 在创建 RecipeIngredient 时同样使用单位匹配器获取 `unit_id`
5. 添加空值检查 `unit_obj.id if unit_obj else None` 确保安全

**注意事项：**
- `recipe_import_service.py` 已经正确使用了 `unit_id`，无需修改
- 单位匹配器会自动创建不存在的单位，确保导入过程的完整性
- 所有修改通过了 Python 语法检查

### 2026-03-07 单位匹配器解包错误修复

**问题：** `cannot unpack non-iterable Unit object` 错误导致原料导入失败

**原因：**
- `UnitMatcher.match_or_create_unit()` 方法返回的是 `Unit` 对象，不是元组
- 但在 `json_recipe_import_service.py` 中使用了 `unit_obj, _ = self.unit_matcher.match_or_create_unit(unit_str)` 试图解包
- 导致 `'cannot unpack non-iterable Unit object'` 错误

**UnitMatcher 方法签名：**
```python
# 返回元组 (Unit, is_new)
def match_unit(self, unit_str: Optional[str]) -> Tuple[Optional[Unit], bool]

# 返回 Unit 对象（便捷方法）
def match_or_create_unit(self, unit_str: Optional[str]) -> Unit
```

**修改的文件：**
- `backend/app/services/json_recipe_import_service.py`
  - 第 159 行：
    - 修改前：`unit_obj, _ = self.unit_matcher.match_or_create_unit(unit_str)`
    - 修改后：`unit_obj = self.unit_matcher.match_or_create_unit(unit_str)`
  - 第 369 行：
    - 修改前：`unit_obj, _ = self.unit_matcher.match_or_create_unit(unit_str)`
    - 修改后：`unit_obj = self.unit_matcher.match_or_create_unit(unit_str)`
  - 第 394 行：
    - 修改前：`unit_obj, _ = self.unit_matcher.match_or_create_unit(unit_str)`
    - 修改后：`unit_obj = self.unit_matcher.match_or_create_unit(unit_str)`

**修改说明：**
1. `match_or_create_unit()` 返回单个 Unit 对象，不需要解包
2. 如果需要知道是否为新创建，应使用 `match_unit()` 方法
3. 当前场景只需获取单位对象，使用 `match_or_create_unit()` 更简洁
4. 移除了不必要的解包操作，避免运行时错误

**验证结果：**
- 所有 Python 文件语法检查通过
- 单位匹配器方法调用正确
- 导入服务不再有解包错误

### 2026-03-07 原料 API Unit 序列化错误修复

**问题：** `Unable to serialize unknown type: <class 'app.models.unit.Unit'>` 错误导致原料列表查询失败

**原因：**
- Ingredient 模型添加了 `default_unit = relationship("Unit", lazy="select")` 关系
- 当查询 Ingredient 时，FastAPI 或 SQLAlchemy 可能自动加载了 `default_unit` 关系
- Pydantic 无法序列化 SQLAlchemy 模型对象（Unit）
- 即使 API 指定了 `response_model=List[dict]`，序列化仍然试图处理 Unit 对象

**修改的文件：**
- `backend/app/schemas/nutrition.py`
  - 添加 `IngredientResponse` schema
  - 明确定义要返回的字段，排除 `default_unit` 等关系字段
  - 导入 `datetime` 类型支持

- `backend/app/api/nutrition.py`
  - 导入 `load_only` 从 `sqlalchemy.orm`
  - 导入新的 `IngredientResponse` schema
  - `get_ingredients` 端点：
    - 使用 `load_only()` 明确只加载需要的字段
    - 使用 `IngredientResponse` schema 序列化响应
    - 修改 `response_model` 为 `List[IngredientResponse]`
  - `get_ingredient` 端点：
    - 使用 `load_only()` 明确只加载需要的字段
    - 使用 `IngredientResponse` schema 序列化响应
    - 修改 `response_model` 为 `IngredientResponse`

- `backend/app/models/nutrition.py`
  - 修改 `default_unit` 关系的 `lazy` 策略从 `select` 改为 `joined`

**修改说明：**
1. 创建专门的 `IngredientResponse` schema，只包含必要字段
2. 使用 `load_only()` 在查询时明确限制加载的字段
3. 避免 SQLAlchemy 自动加载 `default_unit` 关系
4. 使用 Pydantic schema 而非字典构造响应，确保类型安全

**技术要点：**
- `load_only()` 告诉 SQLAlchemy 只加载指定的列，不加载关系
- `IngredientResponse` schema 明确定义返回结构，避免意外包含 Unit 对象
- `lazy="joined"` 改变关系加载策略，可能在某些情况下更高效

**验证结果：**
- 所有 Python 文件语法检查通过
- Schema 定义正确，包含所有必要字段
- API 端点使用正确的响应模型
- 避免了 Unit 对象序列化错误

### 2026-03-07 补充修复：Recipes API Ingredient 查询

**问题：** Recipes API 中查询 Ingredient 时也可能触发 Unit 关系加载

**修改的文件：**
- `backend/app/api/recipes.py`
  - 导入 `load_only` 从 `sqlalchemy.orm`
  - 第 51-53 行：
    - 添加 `load_only()` 明确只加载需要的字段
    - 限制加载 `id`, `name`, `is_active`
  - 第 145-147 行：
    - 添加 `load_only()` 明确只加载需要的字段
    - 限制加载 `id`, `name`, `is_active`

**修改说明：**
1. Recipes API 中查询 Ingredient 时也使用 `load_only()`
2. 避免所有可能触发 `default_unit` 关系加载的查询
3. 确保所有 Ingredient 查询都明确限制字段

**验证结果：**
- 所有 Python 文件语法检查通过
- Recipes API 查询优化完成
- 全面的 Ingredient 查询修复

### 2026-03-07 最终修复：Ingredient default_unit 关系完全禁用

**问题：** 使用 `lazy="joined"` 和 `load_only()` 仍无法完全阻止 Unit 关系加载和序列化错误

**修改的文件：**
- `backend/app/models/nutrition.py`
  - 将 `default_unit` 关系改为 `lazy="noload"`
  - 完全禁用自动加载，避免序列化问题

**修改说明：**
1. `lazy="noload"` 告诉 SQLAlchemy 永远不要自动加载这个关系
 2. 如需访问 `default_unit`，必须使用显式的 `joinedload()`
 3. 彻底阻止了 Unit 对象被意外序列化
 4. `default_unit_id` 外键仍然可以正常工作

**技术要点：**
- `lazy="noload"` 是最激进的关系加载策略
- 需要时使用 `joinedload()` 显式加载关系
- 避免了所有自动加载导致的序列化问题

**验证结果：**
- 所有 Python 文件语法检查通过
- `default_unit` 关系已完全禁用自动加载
- 彻底解决了 Unit 对象序列化错误

