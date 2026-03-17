# 菜谱成本区间计算功能设计

## 概述

为菜谱成本趋势图表添加区间展示功能，反映当天不同商家价格波动对菜谱总成本的影响。

## 需求背景

当前成本计算只返回一个数值，但当天各家商家的价格可能不一样。通过展示成本区间，用户可以更全面地了解菜谱成本的波动范围。

## 核心需求

### 计算逻辑

- **区间最大值**：每道食材在当天的最高价格之和
- **区间最小值**：每道食材在当天的最低价格之和
- **平均值**：每道食材在当天的平均价格之和

### 价格统计规则

1. **严格按日期分组**：所有当天的价格记录都参与统计
2. **包含所有食材**：包括可选食材
3. **前向填充机制**：当天无价格时使用之前最新价格，如无历史价格则使用最早价格

## API 设计

### 新增端点

```
GET /api/v1/recipes/{recipe_id}/cost-history-range?days=90
```

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| recipe_id | int | 是 | 菜谱ID |
| days | int | 否 | 查询天数，默认90，范围7-365 |

### 响应格式

```json
{
  "id": 1,
  "recipe_id": 123,
  "recipe_name": "红烧肉",
  "date": "2024-03-15",
  "min_cost": 21.00,
  "max_cost": 25.60,
  "avg_cost": 23.30,
  "recorded_at": 1710460800
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 记录ID |
| recipe_id | int | 菜谱ID |
| recipe_name | string | 菜谱名称 |
| date | string | 日期（YYYY-MM-DD） |
| min_cost | float | 最小成本（元） |
| max_cost | float | 最大成本（元） |
| avg_cost | float | 平均成本（元） |
| recorded_at | int | Unix时间戳（秒） |

## 后端实现

### 文件变更

#### 1. `backend/app/api/recipes.py`

新增 API 端点：

```python
@router.get("/{recipe_id}/cost-history-range", response_model=List[RecipeCostRangeResponse])
async def get_recipe_cost_history_range(
    recipe_id: int,
    days: int = Query(90, ge=7, le=365, description="查询天数"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱成本区间趋势"""
    # 验证菜谱存在且属于当前用户
    # 计算成本区间趋势
    # 返回响应
```

#### 2. `backend/app/services/recipe_service.py`

新增核心计算函数：

```python
def calculate_recipe_cost_range_trend(
    recipe_id: int,
    user_id: int,
    db: Session,
    days: int = 90
) -> List[Dict]:
    """计算菜谱的成本区间趋势

    对每一天，计算菜谱的成本区间（最小值、最大值、平均值）。
    使用前向填充机制处理缺失的价格记录。

    Returns:
        成本区间趋势数据列表，每条记录包含：
        - date: 日期 (YYYY-MM-DD)
        - recorded_at: Unix 时间戳（秒）
        - min_cost: 最小成本（元）
        - max_cost: 最大成本（元）
        - avg_cost: 平均成本（元）
    """
    # 实现逻辑...
```

```python
def calculate_recipe_cost_range_as_of(
    recipe_id: int,
    user_id: int,
    as_of_date: datetime,
    db: Session
) -> Dict:
    """计算菜谱在指定日期的成本区间"""
    # 实现逻辑...
```

```python
def _get_price_records_for_date(
    db: Session,
    user_id: int,
    ingredient_id: int,
    as_of_date: datetime
) -> List[ProductRecord]:
    """获取某食材在指定日期的所有价格记录"""
    # 实现逻辑...
```

#### 3. `backend/app/schemas/recipe.py`

新增响应模型：

```python
class RecipeCostRangeResponse(BaseModel):
    id: int
    recipe_id: int
    recipe_name: str
    date: str
    min_cost: float
    max_cost: float
    avg_cost: float
    recorded_at: int
```

### 计算流程

1. 获取日期范围（与 `calculate_recipe_cost_trend` 逻辑相同）
2. 遍历每一天：
   - 获取菜谱的所有食材（包括可选食材）
   - 对每个食材：
     - 查找该食材当天的所有价格记录
     - 如果当天无记录，使用前向填充（`_get_price_record_with_fallback()`）
     - 计算当天的单价列表
     - 得到：最低单价、最高单价、平均单价
   - 汇总所有食材：
     - `min_cost = Σ(最低单价 × 菜谱数量)`
     - `max_cost = Σ(最高单价 × 菜谱数量)`
     - `avg_cost = Σ(平均单价 × 菜谱数量)`
3. 返回按日期排序的区间数据列表

### 边界情况处理

1. **某食材当天无价格记录**
   - 使用前向填充：查找该食材当天的历史最新记录
   - 如果当天之前也没有记录，取该食材最早的价格记录

2. **某食材在整个时间段都无价格记录**
   - 该食材不计入当天成本（数量视为0）

3. **某天所有食材都无有效价格**
   - 返回 `min_cost = 0, max_cost = 0, avg_cost = 0`

4. **计算过程中的除零错误**
   - 在计算平均单价时，如果价格列表为空，跳过该食材或使用默认值 0

5. **Decimal 精度问题**
   - 使用 Python 的 `Decimal` 进行精确计算
   - 最后转换为浮点数返回

6. **API 参数验证**
   - `days` 参数范围：7-365
   - `recipe_id` 必须存在且属于当前用户

## 前端实现

### 文件变更

#### 1. `frontend/src/api/recipes.ts`

新增 API 方法：

```typescript
async getRecipeCostHistoryRange(recipeId: number, days: number = 90) {
  const response = await client.get(`/recipes/${recipeId}/cost-history-range`, {
    params: { days }
  })
  return response.data
}
```

#### 2. `frontend/src/views/recipes/components/CostChartSection.vue`

简化数据处理逻辑：

**Props 类型更新：**

```typescript
interface CostRangeRecord {
  id: number
  recipe_id: number
  recipe_name: string
  date: string
  min_cost: number      // 元
  max_cost: number      // 元
  avg_cost: number      // 元
  recorded_at: number
}

const props = defineProps<{
  records: CostRangeRecord[]
}>()
```

**简化 `updateChart()` 函数：**

```typescript
function updateChart() {
  if (!chart) return

  // 直接使用后端返回的数据，无需聚合计算
  const dailyData = props.records.map(record => ({
    date: record.date,
    min: record.min_cost,
    max: record.max_cost,
    avg: record.avg_cost,
    count: 1  // 固定为1，因为是API已计算好的区间
  }))

  // 其余图表配置保持不变...
}
```

**移除 `aggregateDailyCosts()` 函数**：不再需要，因为后端已经返回了聚合好的数据。

## 测试策略

### 单元测试

1. **后端服务函数测试**
   - `calculate_recipe_cost_range_as_of()` - 测试各种价格场景
   - `_get_price_records_for_date()` - 测试价格记录获取
   - 边界情况：无价格记录、单条记录、多条记录

2. **API 端点测试**
   - 正常请求：返回正确的区间数据
   - 无效参数：`days` 超出范围、`recipe_id` 不存在
   - 空数据：菜谱无食材、无价格记录

### 集成测试

1. **前后端联调**
   - 前端调用新 API，图表正确展示区间带
   - Tooltip 显示正确的 min/max/avg 值

2. **数据一致性验证**
   - 与现有 `calculate_recipe_cost_trend` 的 `total_cost` 对比
   - 验证 `avg_cost` 接近 `total_cost`（同一计算逻辑）

### 端到端测试

1. **完整流程测试**
   - 创建菜谱 → 添加食材 → 添加多天多商家的价格 → 查看成本趋势图表

## 数据流程图

```
用户请求
  ↓
GET /api/v1/recipes/{id}/cost-history-range
  ↓
验证菜谱权限
  ↓
遍历日期范围
  ↓
对每一天：
  ├─ 获取所有食材
  ├─ 对每个食材：
  │   ├─ 获取当天所有价格记录
  │   ├─ 如无记录，前向填充或取最早记录
  │   └─ 计算 min/max/avg 单价
  └─ 汇总得到菜谱成本区间
  ↓
返回区间数据
  ↓
前端展示（复用 CostChartSection）
```

## 实现优先级

1. **高优先级**：后端 API 和核心计算逻辑
2. **高优先级**：前端 API 集成和图表更新
3. **中优先级**：单元测试
4. **中优先级**：集成测试
5. **低优先级**：端到端测试

## 风险与注意事项

1. **性能风险**：大量数据时数据库查询可能较慢，需要优化批量查询
2. **数据一致性**：确保与现有成本计算逻辑保持一致
3. **向后兼容**：不影响现有 API，新增独立端点
4. **边界情况**：充分测试各种数据缺失场景

## 后续优化方向

1. **缓存机制**：对常用查询结果进行缓存
2. **增量更新**：只计算新增日期的成本区间
3. **批量查询优化**：减少数据库查询次数
4. **异步计算**：对大数据量使用异步任务队列
