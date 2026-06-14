# 商品别名功能

## 概述

为商品添加了与原料类似的别名功能，支持多个别名，在所有相关搜索中都能通过别名匹配到商品。

## 功能范围

### 后端改动

- **数据库模型**：`Product` 添加 `aliases = Column(JSON)` 字段
- **Pydantic Schema**：`ProductBase`/`ProductUpdate` 添加 `aliases` 字段，含 `None→[]` 验证器处理数据库 NULL
- **商品 CRUD API**（`products_entity.py`）：
  - 创建/更新时自动处理别名字段（通过 `model_dump()`）
  - 列表搜索增加 `Product.aliases.contains(alias_search)` 商品别名匹配
  - 自动完成接口增加商品别名匹配，返回完整别名列表
- **价格记录 API**（`products.py`）：三处搜索均增加 `Product.aliases.contains(alias_search)` 商品别名匹配
- **原料搜索 API**（`ingredient_extended.py`）：原料搜索增加通过商品名称和商品别名找到所属原料（`Ingredient.products.any(Product.name.contains(search))` 和 `Product.aliases.contains`）

### 前端改动

- **商品管理列表**（`ProductsView.vue`）：添加对话框增加别名 `v-combobox`；移动端/桌面端列表显示别名 chip
- **商品详情页**（`ProductDetail.vue`）：基本信息区显示别名 chip；编辑模式支持别名输入
- **原料详情页**（`IngredientDetail.vue`）：添加/编辑商品对话框支持别名输入

### 数据库迁移

```sql
-- SQLite
ALTER TABLE products ADD COLUMN aliases TEXT;
```

详见 `backend/sql_migrations/` 下各引擎的 SQL 脚本，以及 `backend/alembic/versions/` 下的 Alembic 迁移。
