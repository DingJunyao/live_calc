# 地图配置持久化实现文档

## 问题背景

在之前的实现中，地图配置（包括各地图API密钥、默认地图设置、地理编码配置等）是通过全局变量存储在内存中的。这导致每当后端服务重启后，所有配置都会丢失，需要重新配置。

## 解决方案

实现了地图配置的数据库持久化存储，主要包括：

1. 创建了专门的地图配置数据模型
2. 实现了数据库的CRUD操作
3. 更新了API端点以使用数据库存储
4. 创建了数据库迁移脚本

## 技术实现

### 数据模型

创建了 `MapConfiguration` 模型，包含以下字段：
- `id`: 主键
- `available_maps`: 可用地图列表 (JSON)
- `default_map`: 默认地图 (String)
- `map_api_keys`: 地图API密钥配置 (JSON)
- `geocoding`: 地理编码配置 (JSON)
- `created_at`: 创建时间
- `updated_at`: 更新时间

### API 变更

更新了 `/api/v1/admin/map-config` 端点：
- `GET` 现在从数据库获取配置
- `PUT` 现在将配置保存到数据库

### 数据库迁移

创建了迁移脚本 `20260318_0001_add_map_configuration_table.py`，用于创建 `map_configurations` 表。

## 文件变更

- `backend/app/models/map_config.py` - 新增地图配置数据模型
- `backend/app/api/admin.py` - 更新API端点使用数据库操作
- `backend/alembic/env.py` - 更新模型导入
- `backend/alembic/versions/20260318_0001_add_map_configuration_table.py` - 新增数据库迁移脚本
- `CLAUDE.md` - 更新项目索引

## 测试验证

通过 `test_map_config_db.py` 验证了数据库操作的正确性：
- 首次获取配置（创建默认配置）
- 更新配置
- 重新获取配置（验证更新）
- 数据正确性验证

## 影响

- 管理员配置的地图API密钥现在会在服务重启后保持
- 所有地图相关配置都是持久化的
- 用户不再需要在每次重启后重新配置地图设置