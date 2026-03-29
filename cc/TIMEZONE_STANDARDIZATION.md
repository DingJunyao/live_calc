# 时区统一方案

## 概述

统一了整个应用的时区处理方案，确保数据存储和显示的一致性。

## 核心原则

1. **数据库存储**：统一使用 UTC 时间（naive datetime，不带时区信息）
2. **API 响应**：所有 datetime 字段序列化时添加 UTC 时区标记（`+00:00`）
3. **前端显示**：浏览器自动将 UTC 时间转换为用户本地时区显示

## 技术实现

### 1. 时区工具模块

创建了 `app/utils/datetime_utils.py`，提供统一的时区处理功能：

```python
def serialize_datetime(dt: Union[datetime, None]) -> Union[str, None]:
    """序列化 datetime 对象为 ISO 8601 格式字符串，包含时区信息"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 数据库存储的 naive datetime 视为 UTC 时间
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

class TimeZoneAwareModel(BaseModel):
    """自动处理datetime字段的时区序列化的基类"""

    @field_serializer('*')
    def serialize_datetime_fields(self, value: Any, _info) -> Any:
        """自动序列化所有datetime字段"""
        if isinstance(value, datetime):
            return serialize_datetime(value)
        return value
```

### 2. Schema 更新

所有包含 datetime 字段的 Response Schema 都继承 `TimeZoneAwareModel`：

- `ProductRecordResponse`（产品价格记录）
- `IngredientResponse`（食材）
- `MerchantResponse`（商家）
- `RecipeResponse`（菜谱）
- `ProductResponse`（商品）
- `ProductBarcodeResponse`（商品条码）

**示例：**

```python
from app.utils.datetime_utils import TimeZoneAwareModel

class MerchantResponse(TimeZoneAwareModel):
    id: int
    name: str
    created_at: datetime  # 自动序列化为带时区的ISO格式

    class Config:
        from_attributes = True
```

### 3. 数据迁移

#### 问题背景

- **旧数据（3月19日及之前）**：`recorded_at` 存储的是本地时间
- **新数据（3月19日后）**：`recorded_at` 存储的是UTC时间
- 统一处理时导致旧数据显示多了8小时

#### 迁移方案

创建了 `backend/migrate_old_records_to_utc.py` 脚本：

```bash
# 试运行（不修改数据）
python migrate_old_records_to_utc.py

# 执行迁移
python migrate_old_records_to_utc.py --execute
```

**迁移结果：**
- 成功迁移：475 条记录
- 将旧数据的 `recorded_at` 减8小时，转换为UTC时间
- 备份文件：`data/livecalc.db.backup.YYYYMMDD_HHMMSS`

## 数据格式对比

### 修复前

```
数据库：2026-03-28 09:46:00（UTC时间）
后端返回：2026-03-28T09:46:00（无时区信息）
前端解析：被浏览器当作UTC，显示为 09:46（错误）

旧数据问题：
数据库：2026-03-18 17:09:00（本地时间）
后端返回：2026-03-18T17:09:00+00:00（被错误标记为UTC）
前端显示：03-19 01:09（多了8小时！）
```

### 修复后

```
数据库：2026-03-28 09:46:00（UTC时间）
后端返回：2026-03-28T09:46:00+00:00（带UTC时区）
前端显示：03-28 17:46（自动转换为北京时间，正确）

旧数据迁移后：
数据库：2026-03-18 09:09:00（转换为UTC）
后端返回：2026-03-18T09:09:00+00:00（带UTC时区）
前端显示：03-18 17:09（自动转换为北京时间，正确）
```

## 用户体验

- **数据录入**：用户输入的是本地时间，后端自动转换为UTC存储
- **数据显示**：API 返回 UTC 时间，前端自动转换为用户本地时区显示
- **跨时区支持**：理论上支持不同时区的用户（未来功能）

## 相关文件

### 新增文件
- `backend/app/utils/datetime_utils.py` - 时区处理工具
- `backend/migrate_old_records_to_utc.py` - 数据迁移脚本

### 修改文件
- `backend/app/schemas/product.py`
- `backend/app/schemas/nutrition.py`
- `backend/app/schemas/merchant.py`
- `backend/app/schemas/product_entity.py`
- `backend/app/schemas/recipe.py`

## 注意事项

1. **数据库默认值**：
   - SQLite：`CURRENT_TIMESTAMP` 返回 UTC 时间
   - SQLAlchemy：`func.now()` 返回 UTC 时间

2. **前端处理**：
   - 使用 `new Date(isoString)` 自动解析时区
   - 使用 `date.getHours()` 等方法获取本地时区的时间

3. **API 设计**：
   - 所有 datetime 字段统一返回 ISO 8601 格式
   - 包含时区信息（`+00:00` 或 `Z`）

## 未来改进

- [ ] 支持用户自定义时区设置
- [ ] 前端显示时区信息
- [ ] API 支持按不同时区返回数据
- [ ] 定时任务处理时区问题

## 参考资料

- ISO 8601 标准：https://en.wikipedia.org/wiki/ISO_8601
- Python datetime 时区处理：https://docs.python.org/3/library/datetime.html
- SQLite 时区支持：https://www.sqlite.org/lang_datefunc.html
