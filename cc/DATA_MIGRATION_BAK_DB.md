# 旧版数据库迁移记录

## 概述

将旧版本数据库 `livecalc_bak.db` 的数据迁移到新版本数据库 `livecalc.db`。

## 迁移范围

| 数据类型 | 旧库数量 | 迁移数量 | 说明 |
|---------|---------|---------|------|
| 用户 (users) | 1 | 1 | billding |
| 商家 (merchants) | 4 | 4 | 美道家梦之城店、千禧量贩、丹尼斯、美道家万达广场店 |
| 新建原料 (ingredients) | - | 2 | 干燕麦片、鲜鸭血 |
| 新建商品 (products) | - | 2 | 干燕麦片、鲜鸭血 |
| 价格记录 (product_records) | 475 | 475 | 全部迁移成功，0 条跳过 |

## 匹配策略

商品匹配优先级：
1. **商品名称直接匹配** → 147 个商品通过此方式匹配
2. **原料名称/别名匹配** → 通过 `ingredients.aliases` JSON 字段匹配
3. **语义匹配** → 无法通过名称和别名匹配时，创建新的原料和商品

## ID 映射

### 商家映射
| 旧 ID | 新 ID | 名称 |
|-------|-------|------|
| 1 | 1 | 美道家梦之城店 |
| 2 | 2 | 千禧量贩 |
| 3 | 3 | 丹尼斯 |
| 5 | 4 | 美道家万达广场店 |

### 新创建的原料
| ID | 名称 |
|----|------|
| 641 | 干燕麦片 |
| 642 | 鲜鸭血 |

### 新创建的商品
| ID | 名称 | 原料 ID |
|----|------|---------|
| 619 | 干燕麦片 | 641 |
| 620 | 鲜鸭血 | 642 |

## 关键发现

- **单位 ID**：新旧库在 product_records 使用的范围（ID 2-18）完全一致，无需映射
- **用户**：旧库用户 billding 直接迁移，新 ID = 1
- **无数据丢失**：475 条价格记录全部成功迁移

## 文件清单

| 文件 | 说明 |
|------|------|
| `backend/scripts/do_migrate.py` | 迁移执行脚本 |
| `backend/scripts/migration_data.sql` | 可移植 SQL 脚本（兼容 SQLite/MySQL/PostgreSQL） |
| `backend/scripts/migration_mapping.json` | ID 映射关系 JSON |
| `backend/data/livecalc_pre_migration_*.db` | 迁移前自动备份 |

## SQL 脚本使用

SQL 脚本 `migration_data.sql` 包含所有 INSERT 语句，可直接用于：
- SQLite：直接执行
- MySQL：需注意 `LAST_INSERT_ID()` 用法
- PostgreSQL：需注意 `RETURNING id` 用法
