# 时区感知 API 使用指南

## 概述

API 现在支持时区感知的日期查询，确保用户查询"今天"、"本周"等数据时能够获得正确的结果。

## 后端 API 变更

### 1. 支出报告 API

**端点：** `GET /api/v1/reports/expense`

**新增参数：**
- `timezone_offset` (可选): 用户时区偏移（秒）
  - 东八区：`28800`
  - 如不提供，默认使用东八区

**请求示例：**
```bash
# 查询北京时间 2026-03-29 的支出报告
GET /api/v1/reports/expense?start_date=2026-03-29&end_date=2026-03-29&timezone_offset=28800
```

**Python 客户端示例：**
```python
import requests
from datetime import date

# 获取时区偏移（东八区）
timezone_offset = 8 * 3600  # 28800 秒

response = requests.get(
    'http://localhost:8000/api/v1/reports/expense',
    params={
        'start_date': '2026-03-29',
        'end_date': '2026-03-29',
        'timezone_offset': timezone_offset
    }
)
```

## 前端使用指南

### 1. 导入时区工具

```typescript
import { addTimezoneOffset } from '@/api/timezone'
// 或
import { addTimezoneToConfig } from '@/api/timezone'
```

### 2. 方式一：使用 addTimezoneOffset（推荐）

适用于直接传递参数对象的场景：

```typescript
import api from '@/api'
import { addTimezoneOffset } from '@/api/timezone'

// 查询支出报告
const response = await api.get('/reports/expense', {
  params: addTimezoneOffset({
    start_date: '2026-03-29',
    end_date: '2026-03-29',
    category: 'all'
  })
})
```

### 3. 方式二：使用 addTimezoneToConfig

适用于已有完整配置对象的场景：

```typescript
import api from '@/api'
import { addTimezoneToConfig } from '@/api/timezone'

const config = {
  params: {
    start_date: '2026-03-01',
    end_date: '2026-03-31'
  }
}

const response = await api.get('/reports/expense',
  addTimezoneToConfig(config)
)
```

### 4. 方式三：自动添加（最简单）

在前端请求拦截器中统一添加时区偏移：

**src/api/index.ts**
```typescript
import axios from 'axios'
import { getTimezoneOffsetSeconds } from '@/utils/timezone'

const api = axios.create({
  baseURL: '/api/v1'
})

// 请求拦截器
api.interceptors.request.use((config) => {
  // 为所有包含日期参数的请求添加时区偏移
  const params = config.params || {}
  const hasDateParams = Object.keys(params).some(
    key => key.includes('date') || key.includes('time')
  )

  if (hasDateParams) {
    params.timezone_offset = getTimezoneOffsetSeconds()
  }

  return config
})

export default api
```

## 工作原理

### 时区转换流程

```
用户视角（北京时间）：
  查询 2026-03-29 的数据
    ↓
前端：
  发送：start_date=2026-03-29, timezone_offset=28800
    ↓
后端：
  转换为 UTC 范围：2026-03-28 16:00:00 到 2026-03-29 15:59:59
    ↓
数据库查询：
  WHERE recorded_at >= '2026-03-28 16:00:00'
    AND recorded_at <= '2026-03-29 15:59:59'
    ↓
结果：
  包含所有北京时间为 2026-03-29 的记录
```

### 关键计算

**北京时间 2026-03-29 00:00:00**
- 对应 UTC：`2026-03-28 16:00:00`

**北京时间 2026-03-29 23:59:59**
- 对应 UTC：`2026-03-29 15:59:59`

## 常见问题

### Q1：为什么需要 timezone_offset 参数？

**A：** 因为数据库存储的是 UTC 时间，而用户查询使用的是本地日期。需要时区偏移来进行正确的日期范围转换。

### Q2：不提供 timezone_offset 会怎样？

**A：** 后端会默认使用东八区（北京时间），对中国用户来说没有问题。

### Q3：如何获取用户的时区偏移？

**A：** 使用 JavaScript 的 `getTimezoneOffset()` 方法：

```typescript
const offsetMinutes = new Date().getTimezoneOffset()  // 分钟
const offsetSeconds = -offsetMinutes * 60  // 秒（注意符号反转）
```

### Q4：支持哪些时区？

**A：** 支持所有时区，只要提供正确的时区偏移（秒）即可：

- UTC-8（太平洋标准时间）：`-28800`
- UTC+0（格林威治标准时间）：`0`
- UTC+8（北京时间）：`28800`
- UTC+9（日本时间）：`32400`

## 测试验证

### 测试场景1：北京时间凌晨查询

**时间：** 北京时间 2026-03-29 01:00
**UTC时间：** 2026-03-28 17:00

**查询：**
```bash
GET /api/v1/reports/expense?start_date=2026-03-29&end_date=2026-03-29&timezone_offset=28800
```

**预期：** 包含这条记录 ✅

### 测试场景2：跨日期查询

**查询范围：** 北京时间 2026-03-01 到 2026-03-31

**后端转换：**
- UTC 开始：`2026-02-28 16:00:00`
- UTC 结束：`2026-03-30 15:59:59`

**预期：** 包含所有北京时间为3月的记录 ✅

## 相关文件

### 后端
- `backend/app/utils/date_range_utils.py` - 时区转换工具
- `backend/app/api/reports.py` - API 端点（已更新）
- `backend/app/services/report_service.py` - 业务逻辑（已更新）

### 前端
- `frontend/src/utils/timezone.ts` - 时区工具
- `frontend/src/api/timezone.ts` - API 时区工具

### 文档
- `cc/TIMEZONE_STANDARDIZATION.md` - 时区统一方案
- `cc/TIMEZONE_DATE_RANGE_ISSUE.md` - 日期范围时区问题分析

## 向后兼容性

✅ **完全向后兼容**

- `timezone_offset` 是可选参数
- 不提供时默认使用东八区
- 旧客户端无需修改即可正常工作
