# 数据结构重构设计文档

**日期:** 2026-03-05
**版本:** 1.0
**状态:** 已确认

## 概述

本文档描述生计项目的数据结构重构方案，旨在完善商品、食材、菜谱、营养、地点、价格之间的关联关系，并补充前端缺失的功能。

---

## 1. 核心实体与关系

### 1.1 新增实体

#### Product（商品）

商品实体，代表可在商店购买的具体商品。

**表名:** `products`

**字段:**
- `id` - 主键
- `name` - 商品名称（必填）
- `brand` - 品牌名称（可选）
- `barcode` - 条码（可选，唯一）
- `image_url` - 商品图片URL（可选）
- `ingredient_id` - 关联食材（必填，外键 → `ingredients.id`）
- `tags` - 商品标签（JSON，如 `["有机", "进口", "促销"]`）
- 审计字段（从 `AuditMixin` 继承）

**关系:**
- `ingredient` - 关联的食材
- `price_records` - 价格记录（一对多）

#### UserIngredientPreference（用户食材偏好）

用户对食材的默认选择偏好设置。

**表名:** `user_ingredient_preferences`

**字段:**
- `id` - 主键
- `user_id` - 用户ID（必填，外键 → `users.id`）
- `ingredient_id` - 食材ID（必填，外键 → `ingredients.id`）
- `default_product_id` - 默认商品（可选，外键 → `products.id`）
- `default_recipe_id` - 默认食谱（可选，外键 → `recipes.id`）
- `preference_type` - 偏好类型（`product` 或 `recipe`，默认 `product`）
- `is_favorite` - 是否收藏（默认 `false`）
- 审计字段（从 `AuditMixin` 继承）

**约束:**
- `(user_id, ingredient_id)` 唯一约束

**关系:**
- `user` - 关联用户
- `ingredient` - 关联食材
- `default_product` - 默认商品
- `default_recipe` - 默认食谱

### 1.2 修改实体

#### Recipe（菜谱）

**新增字段:**
- `result_ingredient_id` - 成品对应食材（可选，外键 → `ingredients.id`）

**关系:**
- `result_ingredient` - 成品食材

#### ProductRecord（价格记录）

**新增字段:**
- `product_id` - 关联商品（必填，外键 → `products.id`）

**关系:**
- `product` - 关联商品

#### ProductIngredientLink（商品-食材关联）

**修改:**
- `product_id` - 改为外键 → `products.id`（原为 `product_record_id`）
- 移除冗余字段（`match_confidence`, `match_method`, `verified_by_user` 等）

#### Ingredient（食材）

**新增关系:**
- `products` - 关联的商品列表
- `product_links` - 商品-食材关联列表

### 1.3 关系图

```
Recipe
  ├── RecipeIngredient（食谱中使用的食材，一对多）
  └── result_ingredient_id → Ingredient（成品食材）

Ingredient
  ├── products（关联的商品，一对多）
  ├── recipe_ingredients（被哪些食谱使用，一对多）
  ├── nutrition_data（营养数据，多对一）
  └── product_links（商品关联）

Product
  ├── ingredient_id → Ingredient（对应食材）
  └── price_records（价格记录，一对多）

ProductRecord
  ├── product_id → Product（关联商品）
  └── location_id → Location（购买地点）

UserIngredientPreference
  ├── user_id → User
  ├── ingredient_id → Ingredient
  ├── default_product_id → Product
  └── default_recipe_id → Recipe
```

---

## 2. 成本计算逻辑

### 2.1 成本计算优先级

**场景:** 某菜谱需要"薯条"作为原料

**计算流程:**

1. **优先查找商品价格**
   - 查找关联了"薯条"食材的所有商品
   - 获取最近在用户常用地点的价格记录
   - 按优先级排序：用户标记"常用" > 最近购买 > 价格最低 > 最近更新
   - 选择排名第一的商品价格

2. **备选计算自制成本**
   - 查找"薯条"食材对应的食谱（如有"自制薯条"食谱）
   - 递归计算该食谱的成本（基于其原料的商品价格）
   - 避免循环依赖（A食谱成品→B食材→B食谱成品→A食材）

3. **同时展示两种成本**
   ```
   薯条成本：
     ├─ 购买成本: ¥8.50（某品牌冷冻薯条，500g）
     └─ 自制成本: ¥5.20（自制薯条食谱）
   ```

4. **用户选择**
   - 默认使用购买成本
   - 用户可切换到自制成本

### 2.2 商品价格查询优先级

**排序规则（按优先级降序）:**
1. 用户标记"常用"的商品
2. 最近购买过的商品（基于 ProductRecord 时间）
3. 价格最低的商品
4. 最近更新的价格记录

### 2.3 缓存策略

- 商品价格每日缓存一次（避免频繁查询）
- 价格变更时更新缓存

---

## 3. 数据库表结构

### 3.1 Product 表

```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    brand VARCHAR(100),
    barcode VARCHAR(50) UNIQUE,
    image_url VARCHAR(500),
    ingredient_id INTEGER NOT NULL,
    tags JSON,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER,
    updated_by INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

CREATE INDEX ix_products_name ON products(name);
CREATE INDEX ix_products_ingredient_id ON products(ingredient_id);
```

### 3.2 UserIngredientPreference 表

```sql
CREATE TABLE user_ingredient_preferences (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    default_product_id INTEGER,
    default_recipe_id INTEGER,
    preference_type VARCHAR(20) DEFAULT 'product',
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by INTEGER,
    updated_by INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
    FOREIGN KEY (default_product_id) REFERENCES products(id),
    FOREIGN KEY (default_recipe_id) REFERENCES recipes(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    FOREIGN KEY (updated_by) REFERENCES users(id),
    UNIQUE (user_id, ingredient_id)
);

CREATE INDEX ix_user_ingredient_preferences_user_id ON user_ingredient_preferences(user_id);
CREATE INDEX ix_user_ingredient_preferences_ingredient_id ON user_ingredient_preferences(ingredient_id);
```

### 3.3 Recipe 表修改

```sql
ALTER TABLE recipes ADD COLUMN result_ingredient_id INTEGER;
ALTER TABLE recipes ADD CONSTRAINT fk_recipes_result_ingredient FOREIGN KEY (result_ingredient_id) REFERENCES ingredients(id);
```

### 3.4 ProductRecord 表修改

```sql
ALTER TABLE product_records ADD COLUMN product_id INTEGER NOT NULL;
ALTER TABLE product_records ADD CONSTRAINT fk_product_records_product FOREIGN KEY (product_id) REFERENCES products(id);
```

### 3.5 ProductIngredientLink 表修改

```sql
-- 删除旧的外键和字段
ALTER TABLE product_ingredient_links DROP CONSTRAINT IF EXISTS fk_product_ingredient_links_product_record;
ALTER TABLE product_ingredient_links DROP COLUMN IF EXISTS product_record_id;
ALTER TABLE product_ingredient_links DROP COLUMN IF EXISTS match_confidence;
ALTER TABLE product_ingredient_links DROP COLUMN IF EXISTS match_method;
ALTER TABLE product_ingredient_links DROP COLUMN IF EXISTS verified_by_user;
ALTER TABLE product_ingredient_links DROP COLUMN IF EXISTS verification_notes;

-- 添加新的外键
ALTER TABLE product_ingredient_links ADD COLUMN product_id INTEGER NOT NULL;
ALTER TABLE product_ingredient_links ADD CONSTRAINT fk_product_ingredient_links_product FOREIGN KEY (product_id) REFERENCES products(id);
```

---

## 4. 前端界面设计

### 4.1 商品管理页面（新增）

**路由:** `/products/manage`

**核心功能:**

1. **商品列表展示**
   - 商品名称、品牌、条码
   - 关联食材、标签
   - 最近价格、购买地点

2. **添加/编辑商品**
   - 名称、品牌、条码、图片
   - 选择关联食材（带搜索和自动补全）
   - 添加标签

3. **查看商品详情**
   - 完整信息展示
   - 价格历史图表
   - 关联食材信息

4. **快速操作**
   - 添加价格记录
   - 编辑商品信息
   - 删除商品（软删除）

### 4.2 价格记录页面（重构）

**原路由:** `/products/list`
**新路由:** `/prices/records`

**核心变更:**

1. **价格记录关联商品而非食材**
   - 商品选择器（带搜索和自动补全）
   - 展示商品详细信息（品牌、条码）

2. **表单流程**
   ```
   选择商品 → 选择地点 → 输入价格 → 输入数量 → 提交
   ```

3. **价格历史按商品分组展示**

### 4.3 食材管理页面（增强）

**路由:** `/ingredients/list`

**新增功能:**

1. **查看关联的商品**
   - 展示所有关联该食材的商品列表
   - 点击可查看商品详情

2. **查看关联的食谱（作为成品）**
   - 展示以该食材为成品的食谱列表
   - 显示食谱成本对比

3. **设置默认偏好**
   - 设置该食材的默认商品或食谱
   - 标记常用选项

### 4.4 导航菜单更新

在主导航中添加：
- **商品管理** (`/products/manage`)
- **价格记录** (`/prices/records`)
- **原料管理** (`/ingredients/list`) - 保持现有路由

---

## 5. 隐式识别与智能匹配

### 5.1 食谱成品自动匹配算法

**触发时机:** 食谱创建/更新时

**匹配流程:**

1. **提取候选名称**
   ```python
   # 食谱名称："自制薯条"
   candidates = ["自制薯条", "薯条"]  # 去除"自制"、"家庭"、"做法"等前缀后缀
   ```

2. **模糊匹配食材**
   - 首先精确匹配名称和别名
   - 如果没有精确匹配，使用模糊匹配（相似度 > 70%）
   - 返回按匹配度排序的候选列表

3. **置信度计算**
   ```python
   match_confidence = (name_similarity * 0.6) + (alias_similarity * 0.4)
   # 精确匹配 = 1.0，模糊匹配 = 0.7-0.9
   ```

4. **用户确认弹窗**
   ```
   检测到食谱"自制薯条"可能对应以下食材:

   推荐匹配（置信度 0.95）：
   ✓ 薯条（成品购买）

   其他候选（点击选择）：
   ○ 薯条（冷冻油炸）  [置信度 0.85]
   ○ 薯条（自制油炸）  [置信度 0.80]

   或创建新食材：
   [创建新食材"薯条"]

   [确认] [跳过] [手动选择]
   ```

### 5.2 成本计算智能选择

**触发时机:** 菜谱成本计算

**选择逻辑:**

1. **查找用户偏好**
   ```python
   preference = UserIngredientPreference.get(user_id, ingredient_id)
   if preference:
       if preference.preference_type == "product":
           return preference.default_product
       elif preference.preference_type == "recipe":
           return preference.default_recipe
   ```

2. **无偏好时使用默认策略**
   - 商品价格优先（按最近购买时间、常用标记、价格排序）
   - 备选自制成本（递归计算食谱成本）

3. **同时展示两种成本**
   ```
   原料"薯条"成本：
     ☑ 购买成本: ¥8.50（某品牌薯条，500g）
     ☐ 自制成本: ¥5.20（自制薯条食谱）
   ```

4. **用户可切换选择**

### 5.3 AI 解析增强（后续优化）

**说明:** 鉴于当前成本限制，此功能作为后续优化项。

**规划功能:**
- 用户导入菜谱时，AI 自动识别原料
- 识别原料名称（如"薯条"）
- 查找匹配的食材（考虑别名）
- 识别制作方式关键词（如"冷冻"、"自制"、"空气炸"）
- 精确匹配到对应的子类食材
- 提供用户确认

---

## 6. 技术实现要点

### 6.1 审计字段强制要求

**所有数据表必须包含以下审计字段（通过 AuditMixin 继承）:**
- `created_at` - 创建时间
- `updated_at` - 更新时间
- `created_by` - 创建人
- `updated_by` - 更新人
- `is_active` - 是否激活（软删除）

### 6.2 模糊匹配实现

使用 `thefuzz` 库（FuzzyWuzzy 的分支）进行字符串相似度匹配:

```python
from thefuzz import fuzz

# 计算相似度（0-100）
similarity = fuzz.ratio(str1, str2)
if similarity >= 70:  # 相似度阈值
    return True
```

### 6.3 循环依赖检测

成本计算时需检测循环依赖:

```python
def detect_cycle(ingredient_ids: set[int]) -> bool:
    """检测是否出现循环依赖"""
    return ingredient_ids.size() > len(ingredient_ids)
```

### 6.4 前端组件复用

使用以下现有组件:
- `PageHeader` - 页面头部
- `Pagination` - 分页
- 模态框组件（自定义）

---

## 7. 实施优先级

### 阶段 1：后端数据模型（核心）
1. 创建 Product 模型
2. 创建 UserIngredientPreference 模型
3. 修改 Recipe 模型
4. 修改 ProductRecord 模型
5. 修改 ProductIngredientLink 模型
6. 编写数据库迁移脚本

### 阶段 2：后端 API 接口
1. 商品管理 API（CRUD）
2. 用户偏好 API（CRUD）
3. 成本计算 API
4. 自动匹配 API

### 阶段 3：前端页面
1. 商品管理页面
2. 价格记录页面重构
3. 食材管理页面增强

### 阶段 4：智能功能
1. 食谱成品自动匹配
2. 成本计算智能选择

---

## 8. 注意事项

1. **数据库迁移:** 由于未发布正式版本，直接使用全新数据库，无需考虑数据迁移。

2. **商品与食材关系:** 商品必须关联一个食材，食材可以关联多个商品（一对多）。

3. **食谱成品:** 一个食谱对应一个成品食材，通过 `result_ingredient_id` 字段关联。

4. **隐式识别:** 支持食谱名称智能匹配食材，考虑别名和模糊匹配。

5. **成本计算:** 优先使用商品价格，同时提供自制成本备选，用户可切换。

6. **用户偏好:** 用户可为每种食材设置默认商品或食谱，系统优先使用用户偏好。

---

## 附录

### A. 相关文件

- 后端模型: `backend/app/models/`
- 前端页面: `frontend/src/views/`
- 路由配置: `frontend/src/router/`
- API 客户端: `frontend/src/api/`

### B. 参考文档

- [项目 CLAUDE.md](../../CLAUDE.md)
- [后端 CLAUDE.md](../../backend/CLAUDE.md)
- [前端 CLAUDE.md](../../frontend/CLAUDE.md)

### C. 修订历史

| 日期 | 版本 | 修订内容 | 作者 |
|------|------|----------|------|
| 2026-03-05 | 1.0 | 初始版本 | Claude |

---

**文档结束**
