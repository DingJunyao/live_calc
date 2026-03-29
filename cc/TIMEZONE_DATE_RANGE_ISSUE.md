# 日期范围查询的时区问题分析

## 问题描述

系统中使用了"今天"、"每天"、"每周"等基于日期的统计和查询功能，但这些计算**没有考虑用户时区**，导致查询结果不准确。

## 问题场景

### 场景1：查询"今天"的价格记录

**用户视角：**
- 北京时间：2026-03-29 01:00（凌晨）
- 创建了一条价格记录
- 在价格趋势图上查看"今天"的数据

**实际情况：**
- 数据库存储：`2026-03-28 17:00:00`（UTC时间）
- 前端查询：`start_date=2026-03-29`
- 后端SQL：`func.date(recorded_at) = '2026-03-29'`
- **查询结果：找不到这条记录** ❌

### 场景2：支出报告的日期统计

**用户视角：**
- 北京时间：2026-03-29 23:00
- 创建了一笔支出记录
- 生成"今天"的支出报告

**实际情况：**
- 数据库存储：`2026-03-29 15:00:00`（UTC时间）
- 后端查询：`func.date(recorded_at) = '2026-03-29'`
- **查询结果：正确** ✅（因为UTC日期和本地日期重合）

但如果在晚上23点后（UTC第二天）创建记录，就查不到了。

## 根本原因

### 后端问题

**文件：** `backend/app/services/report_service.py`

```python
# 问题代码
func.date(ProductRecord.recorded_at) == current_date
```

**问题：**
- `recorded_at` 存储的是 **UTC 时间**（naive datetime）
- `current_date` 是从API参数传入的 **本地日期**
- `func.date()` 提取的是UTC时间的日期部分
- 直接比较忽略了时区差异

### 数据存储差异

**不同的字段有不同的时区处理：**

1. **ProductRecord.recorded_at** - 存储 UTC 时间
   ```python
   recorded_at = Column(DateTime(timezone=True), server_default=func.now())
   ```

2. **Expense.date** - 存储本地日期
   ```python
   date = Column(Date, nullable=False)  # 仅日期，无时区
   ```

这种不一致性导致了查询逻辑的混乱。

## 影响范围

### 受影响的功能

1. **支出报告** - `GET /api/v1/reports/expense`
   - 按日期统计支出
   - 每日/每周/每月趋势

2. **价格趋势** - `GET /api/v1/reports/price-trend`
   - 按日期聚合价格数据
   - 图表展示

3. **商品价格记录查询** - `GET /api/v1/products/`
   - `start_date` 和 `end_date` 参数
   - `func.date(recorded_at) >= start_date`

4. **菜谱成本历史** - 可能使用时间戳查询

### 受影响的文件

**后端：**
- `backend/app/services/report_service.py`
- `backend/app/api/products.py`
- `backend/app/api/reports.py`
- 其他使用 `func.date()` 或日期范围查询的文件

**前端：**
- `frontend/src/views/products/ProductDetail.vue`
- `frontend/src/views/prices/PricesView.vue`
- `frontend/src/components/charts/PriceTrendChart.vue`
- 其他涉及日期筛选的组件

## 解决方案

### 已完成的工作

#### 1. 后端时区工具

创建了 `backend/app/utils/date_range_utils.py`：

```python
def local_date_to_utc_range(
    local_date: date,
    user_timezone_offset: Optional[int] = None
) -> Tuple[datetime, datetime]:
    """将用户本地日期转换为UTC时间范围"""

def local_date_range_to_utc_range(
    start_date: date,
    end_date: date,
    user_timezone_offset: Optional[int] = None
) -> Tuple[datetime, datetime]:
    """将用户本地日期范围转换为UTC时间范围"""
```

#### 2. 前端时区工具

创建了 `frontend/src/utils/timezone.ts`：

```typescript
export function localDateToUTCRange(localDate: string): [string, string]
export function localDateRangeToUTCRange(startDate: string, endDate: string): [string, string]
export function utcToLocalDate(utcString: string): string
export function formatToLocalDateTime(utcString: string): string
```

#### 3. 更新了 report_service.py

修改了 `generate_expense_report` 函数，使用时区感知的日期范围查询。

### 需要完成的工作

#### 1. API 端点更新

**需要添加时区偏移参数：**

```python
@router.get("/expense")
async def get_expense_report(
    start_date: date,
    end_date: date,
    timezone_offset: Optional[int] = None,  # 新增参数
    ...
):
    result = await generate_expense_report(
        ...,
        user_timezone_offset=timezone_offset
    )
```

#### 2. 前端 API 调用更新

**需要发送时区偏移：**

```typescript
import { getTimezoneOffsetSeconds } from '@/utils/timezone'

// API 调用时添加时区偏移
const response = await api.get('/reports/expense', {
  params: {
    start_date: startDate,
    end_date: endDate,
    timezone_offset: getTimezoneOffsetSeconds()  // 新增
  }
})
```

#### 3. 其他日期范围查询的更新

需要检查并更新所有使用日期范围的地方：

- `backend/app/api/products.py` - 价格记录查询
- `backend/app/api/reports.py` - 价格趋势查询
- 前端所有日期筛选组件

## 临时解决方案

在完整修复之前，可以采取以下措施：

### 方案1：前端调整日期范围（推荐）

前端查询"今天"的数据时：
```typescript
// 调整查询范围为 UTC 日期
const today = new Date()
const utcDate = new Date(today.getTime() - today.getTimezoneOffset() * 60 * 1000)
const queryDate = utcDate.toISOString().split('T')[0]
```

### 方案2：后端统一使用 UTC 日期（不推荐）

在文档中说明所有日期都是 UTC，让用户理解。

### 方案3：添加时区提示

在UI上显示数据基于UTC时间，提醒用户可能的时区差异。

## 最佳实践建议

### 数据库存储

✅ **推荐做法：**
- 所有 datetime 字段统一存储 UTC 时间
- 使用 `server_default=func.now()`
- 字段定义：`Column(DateTime(timezone=True), ...)`

❌ **避免做法：**
- 存储本地时间
- 使用 `CURRENT_TIMESTAMP`（SQLite返回UTC，但其他数据库可能不同）

### API 设计

✅ **推荐做法：**
- 所有 datetime 响应字段包含时区信息（`+00:00`）
- API 接受时区偏移参数
- 文档明确说明日期范围基于用户时区

❌ **避免做法：**
- 返回无时区的 datetime 字符串
- 在API文档中假设用户时区

### 前端处理

✅ **推荐做法：**
- 使用 `new Date(isoString)` 自动解析时区
- 发送日期范围时包含时区偏移
- 使用 `getTimezoneOffset()` 获取用户时区

❌ **避免做法：**
- 手动解析日期字符串
- 假设固定时区（如+8）

## 测试用例

### 测试场景1：跨UTC日期的本地日期

```python
# 北京时间 2026-03-29 01:00
# UTC 时间 2026-03-28 17:00

# 查询
start_date = date(2026, 3, 29)
end_date = date(2026, 3, 29)

# 预期结果
# 应该查询 UTC 范围：2026-03-28 16:00:00 到 2026-03-29 15:59:59
```

### 测试场景2：多日期范围

```python
# 查询北京时间 2026-03-01 到 2026-03-31

start_date = date(2026, 3, 1)
end_date = date(2026, 3, 31)

# 预期 UTC 范围：2026-02-28 16:00:00 到 2026-03-30 15:59:59
```

## 相关文件

### 新增文件
- `backend/app/utils/date_range_utils.py` - 后端时区工具
- `frontend/src/utils/timezone.ts` - 前端时区工具

### 需要更新的文件
- `backend/app/services/report_service.py` - 部分已更新
- `backend/app/api/reports.py` - 待更新
- `backend/app/api/products.py` - 待更新
- `frontend/src/views/**/*.vue` - 待更新

## 参考资料

- SQLite 日期函数：https://www.sqlite.org/lang_datefunc.html
- JavaScript Date 对象：https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date
- Python datetime 时区处理：https://docs.python.org/3/library/datetime.html
