# 菜谱成本区间计算功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现菜谱成本区间计算功能，在成本趋势图表中展示每天的成本波动范围（最小值、最大值、平均值）

**Architecture:** 新增后端 API 端点返回每天的成本区间数据，前端复用现有的 CostChartSection 组件，直接使用 API 返回的数据绘制区间带

**Tech Stack:** Python (FastAPI), SQLAlchemy, Vue 3, TypeScript, ECharts

---

## Task 1: 创建 RecipeCostRangeResponse Schema

**Files:**
- Create: `backend/app/schemas/recipe.py` (追加到现有文件)
- Test: `backend/tests/schemas/test_recipe_cost_range.py`

**Step 1: Write the failing test**

```python
from app.schemas.recipe import RecipeCostRangeResponse

def test_recipe_cost_range_response():
    data = {
        "id": 1,
        "recipe_id": 123,
        "recipe_name": "红烧肉",
        "date": "2024-03-15",
        "min_cost": 21.00,
        "max_cost": 25.60,
        "avg_cost": 23.30,
        "recorded_at": 1710460800
    }
    response = RecipeCostRangeResponse(**data)
    assert response.id == 1
    assert response.min_cost == 21.00
    assert response.max_cost == 25.60
    assert response.avg_cost == 23.30
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/schemas/test_recipe_cost_range.py::test_recipe_cost_range_response -v`
Expected: FAIL with "RecipeCostRangeResponse not defined"

**Step 3: Write minimal implementation**

在 `backend/app/schemas/recipe.py` 文件末尾追加：

```python
class RecipeCostRangeResponse(BaseModel):
    """菜谱成本区间响应模型"""
    id: int
    recipe_id: int
    recipe_name: str
    date: str  # 日期 (YYYY-MM-DD)
    min_cost: float  # 最小成本（元）
    max_cost: float  # 最大成本（元）
    avg_cost: float  # 平均成本（元）
    recorded_at: int  # Unix 时间戳（秒）
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/schemas/test_recipe_cost_range.py::test_recipe_cost_range_response -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/schemas/recipe.py backend/tests/schemas/test_recipe_cost_range.py
git commit -m "feat(schemas): 添加 RecipeCostRangeResponse 响应模型"
```

---

## Task 2: 实现 _get_price_records_for_date 辅助函数

**Files:**
- Create: `backend/app/services/recipe_service.py` (_get_price_records_for_date 函数)
- Test: `backend/tests/services/test_recipe_service.py`

**Step 1: Write the failing test**

```python
from datetime import datetime
from app.services.recipe_service import _get_price_records_for_date

def test_get_price_records_for_date():
    db = get_db()
    user_id = 1
    ingredient_id = 1
    as_of_date = datetime(2024, 3, 15, 23, 59, 59)

    records = _get_price_records_for_date(db, user_id, ingredient_id, as_of_date)

    # 验证返回的是当天的所有价格记录
    assert all(r.recorded_at.date() == as_of_date.date() for r in records)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_recipe_service.py::test_get_price_records_for_date -v`
Expected: FAIL with "_get_price_records_for_date not defined"

**Step 3: Write minimal implementation**

在 `backend/app/services/recipe_service.py` 文件中，在 `_get_price_record_with_fallback` 函数之后添加：

```python
def _get_price_records_for_date(
    db: Session,
    user_id: int,
    ingredient_id: int,
    as_of_date: datetime
) -> List[ProductRecord]:
    """获取某食材在指定日期的所有价格记录

    Args:
        db: 数据库会话
        user_id: 用户ID
        ingredient_id: 食材ID
        as_of_date: 指定日期

    Returns:
        当天的所有价格记录列表
    """
    # 计算当天的开始和结束时间
    day_start = as_of_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)

    # 获取食材对应的商品
    product = db.query(Product).filter(
        Product.ingredient_id == ingredient_id,
        Product.is_active == True
    ).first()

    if not product:
        return []

    # 查询当天的所有价格记录
    records = db.query(ProductRecord).filter(
        ProductRecord.user_id == user_id,
        ProductRecord.product_id == product.id,
        ProductRecord.recorded_at >= day_start,
        ProductRecord.recorded_at <= day_end
    ).all()

    return records
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/services/test_recipe_service.py::test_get_price_records_for_date -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/recipe_service.py backend/tests/services/test_recipe_service.py
git commit -m "feat(services): 添加获取指定日期价格记录的辅助函数"
```

---

## Task 3: 实现 calculate_recipe_cost_range_as_of 函数

**Files:**
- Create: `backend/app/services/recipe_service.py` (calculate_recipe_cost_range_as_of 函数)
- Test: `backend/tests/services/test_recipe_service.py`

**Step 1: Write the failing test**

```python
from datetime import datetime
from decimal import Decimal
from app.services.recipe_service import calculate_recipe_cost_range_as_of

def test_calculate_recipe_cost_range_as_of():
    db = get_db()
    recipe_id = 1
    user_id = 1
    as_of_date = datetime(2024, 3, 15, 23, 59, 59)

    result = calculate_recipe_cost_range_as_of(recipe_id, user_id, as_of_date, db)

    assert result is not None
    assert "min_cost" in result
    assert "max_cost" in result
    assert "avg_cost" in result
    assert result["min_cost"] >= 0
    assert result["max_cost"] >= result["min_cost"]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_recipe_service.py::test_calculate_recipe_cost_range_as_of -v`
Expected: FAIL with "calculate_recipe_cost_range_as_of not defined"

**Step 3: Write minimal implementation**

在 `backend/app/services/recipe_service.py` 文件中，在 `calculate_recipe_cost` 函数之后添加：

```python
def calculate_recipe_cost_range_as_of(
    recipe_id: int,
    user_id: int,
    as_of_date: datetime,
    db: Session
) -> Dict:
    """计算菜谱在指定日期的成本区间

    Args:
        recipe_id: 菜谱ID
        user_id: 用户ID
        as_of_date: 指定日期
        db: 数据库会话

    Returns:
        成本区间数据，包含 min_cost, max_cost, avg_cost（单位：元）
    """
    from decimal import Decimal

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return None

    total_min_cost = Decimal("0.00")
    total_max_cost = Decimal("0.00")
    total_avg_cost = Decimal("0.00")
    valid_ingredients = 0

    # 获取菜谱中的所有食材（包括可选食材）
    for recipe_ingredient in recipe.ingredients:
        ingredient = recipe_ingredient.ingredient

        # 检查食材是否已被合并，如果是，使用合并后的目标食材
        if ingredient and ingredient.is_merged and ingredient.merged_into_id:
            ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient.merged_into_id).first()

        if not ingredient:
            continue

        # 获取食材对应的商品
        product = db.query(Product).filter(
            Product.ingredient_id == ingredient.id,
            Product.is_active == True
        ).first()

        if not product:
            continue

        # 获取当天的所有价格记录
        day_records = _get_price_records_for_date(db, user_id, ingredient.id, as_of_date)

        # 如果当天无记录，使用前向填充
        if not day_records:
            fallback_record = _get_price_record_with_fallback(
                db=db,
                user_id=user_id,
                product_id=product.id,
                as_of_date=as_of_date
            )
            if fallback_record:
                day_records = [fallback_record]

        # 如果仍然没有记录，跳过该食材
        if not day_records:
            continue

        # 计算当天的单价列表
        unit_prices = []
        for record in day_records:
            record_price = Decimal(str(record.price))
            std_qty = record.standard_quantity
            if std_qty is None or std_qty == 0:
                unit_price = record_price
            else:
                record_quantity = Decimal(str(std_qty))
                unit_price = record_price / record_quantity
            unit_prices.append(unit_price)

        if not unit_prices:
            continue

        # 计算统计值
        min_unit_price = min(unit_prices)
        max_unit_price = max(unit_prices)
        avg_unit_price = sum(unit_prices) / len(unit_prices)

        # 计算该食材的成本
        ingredient_quantity = recipe_ingredient.quantity
        if ingredient_quantity is None or (isinstance(ingredient_quantity, str) and ingredient_quantity.lower() == "none"):
            ingredient_quantity = 0

        if ingredient_quantity:
            try:
                quantity = Decimal(str(ingredient_quantity))
                ingredient_min_cost = min_unit_price * quantity
                ingredient_max_cost = max_unit_price * quantity
                ingredient_avg_cost = avg_unit_price * quantity

                total_min_cost += ingredient_min_cost
                total_max_cost += ingredient_max_cost
                total_avg_cost += ingredient_avg_cost
                valid_ingredients += 1
            except Exception as e:
                # 数量解析失败，跳过该食材
                continue

    return {
        "min_cost": float(total_min_cost),
        "max_cost": float(total_max_cost),
        "avg_cost": float(total_avg_cost),
        "currency": "CNY",
        "valid_ingredients": valid_ingredients
    }
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/services/test_recipe_service.py::test_calculate_recipe_cost_range_as_of -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/recipe_service.py backend/tests/services/test_recipe_service.py
git commit -m "feat(services): 实现计算菜谱成本区间的函数"
```

---

## Task 4: 实现 calculate_recipe_cost_range_trend 函数

**Files:**
- Create: `backend/app/services/recipe_service.py` (calculate_recipe_cost_range_trend 函数)
- Test: `backend/tests/services/test_recipe_service.py`

**Step 1: Write the failing test**

```python
from app.services.recipe_service import calculate_recipe_cost_range_trend

def test_calculate_recipe_cost_range_trend():
    db = get_db()
    recipe_id = 1
    user_id = 1
    days = 7

    trend = calculate_recipe_cost_range_trend(recipe_id, user_id, db, days)

    assert isinstance(trend, list)
    assert len(trend) > 0
    # 验证返回数据结构
    for item in trend:
        assert "date" in item
        assert "min_cost" in item
        assert "max_cost" in item
        assert "avg_cost" in item
        assert "recorded_at" in item
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_recipe_service.py::test_calculate_recipe_cost_range_trend -v`
Expected: FAIL with "calculate_recipe_cost_range_trend not defined"

**Step 3: Write minimal implementation**

在 `backend/app/services/recipe_service.py` 文件中，在 `calculate_recipe_cost_range_as_of` 函数之后添加：

```python
def calculate_recipe_cost_range_trend(
    recipe_id: int,
    user_id: int,
    db: Session,
    days: int = 90
) -> List[Dict]:
    """计算菜谱的成本区间趋势

    遍历指定日期范围，对于每一天，计算菜谱在该日期的成本区间。

    Args:
        recipe_id: 菜谱ID
        user_id: 用户ID
        db: 数据库会话
        days: 查询天数（默认90天）

    Returns:
        成本区间趋势数据列表，每条记录包含：
        - date: 日期 (YYYY-MM-DD)
        - recorded_at: Unix 时间戳（秒）
        - min_cost: 最小成本（元）
        - max_cost: 最大成本（元）
        - avg_cost: 平均成本（元）
    """
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        return []

    # 获取最早的价格记录日期
    earliest_record = db.query(ProductRecord).filter(
        ProductRecord.user_id == user_id
    ).order_by(ProductRecord.recorded_at.asc()).first()

    if not earliest_record:
        return []

    # 确定日期范围
    end_date = datetime.now().date()
    start_date = max(earliest_record.recorded_at.date(), end_date - timedelta(days=days))

    # 生成日期列表
    date_list = []
    current_date = start_date
    while current_date <= end_date:
        date_list.append(current_date)
        current_date += timedelta(days=1)

    # 计算每一天的成本区间
    cost_range_trend = []
    for date in date_list:
        # 计算该日期 23:59:59 的成本区间（使用截至当天的最新价格）
        as_of_datetime = datetime.combine(date, datetime.max.time()) - timedelta(seconds=1)

        # 调用成本区间计算函数
        cost_result = calculate_recipe_cost_range_as_of(
            recipe_id, user_id, as_of_datetime, db
        )

        if cost_result and cost_result["avg_cost"] > 0:
            # 转换为 Unix 时间戳（使用当天 12:00）
            recorded_at_dt = datetime.combine(date, datetime.min.time()) + timedelta(hours=12)
            recorded_at = int(recorded_at_dt.timestamp())

            cost_range_trend.append({
                "date": date.strftime("%Y-%m-%d"),
                "recorded_at": recorded_at,
                "min_cost": cost_result["min_cost"],
                "max_cost": cost_result["max_cost"],
                "avg_cost": cost_result["avg_cost"]
            })

    return cost_range_trend
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/services/test_recipe_service.py::test_calculate_recipe_cost_range_trend -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/recipe_service.py backend/tests/services/test_recipe_service.py
git commit -m "feat(services): 实现计算菜谱成本区间趋势的函数"
```

---

## Task 5: 创建 API 端点 get_recipe_cost_history_range

**Files:**
- Modify: `backend/app/api/recipes.py` (添加新的端点)
- Test: `backend/tests/api/test_recipes.py`

**Step 1: Write the failing test**

```python
def test_get_recipe_cost_history_range(client, auth_headers, test_recipe):
    response = client.get(
        f"/api/v1/recipes/{test_recipe.id}/cost-history-range",
        params={"days": 7},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "min_cost" in data[0]
        assert "max_cost" in data[0]
        assert "avg_cost" in data[0]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/api/test_recipes.py::test_get_recipe_cost_history_range -v`
Expected: FAIL with "404 Not Found"

**Step 3: Write minimal implementation**

在 `backend/app/api/recipes.py` 文件中，在 `get_recipe_cost_history` 端点之后添加：

```python
@router.get("/{recipe_id}/cost-history-range", response_model=List[RecipeCostRangeResponse])
async def get_recipe_cost_history_range(
    recipe_id: int,
    days: int = Query(90, ge=7, le=365, description="查询天数"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """获取菜谱成本区间趋势

    返回菜谱在指定日期范围内的成本区间数据（最小值、最大值、平均值）。
    反映当天不同商家价格波动对菜谱总成本的影响。

    计算规则：
    - 区间最大值：每道食材在当天的最高价格之和
    - 区间最小值：每道食材在当天的最低价格之和
    - 平均值：每道食材在当天的平均价格之和

    使用前向填充机制处理缺失的价格记录。
    """
    try:
        # 验证菜谱存在且属于当前用户
        recipe = db.query(Recipe).filter(
            Recipe.id == recipe_id,
            Recipe.user_id == current_user.id
        ).first()

        if not recipe:
            raise HTTPException(status_code=404, detail="菜谱不存在")

        # 计算成本区间趋势
        cost_range_trend = calculate_recipe_cost_range_trend(recipe_id, current_user.id, db, days)

        # 转换为响应模型（按时间倒序）
        return [
            RecipeCostRangeResponse(
                id=i,  # 使用索引作为临时 ID
                recipe_id=recipe_id,
                recipe_name=recipe.name,
                min_cost=item["min_cost"],
                max_cost=item["max_cost"],
                avg_cost=item["avg_cost"],
                date=item["date"],
                recorded_at=item["recorded_at"]
            )
            for i, item in enumerate(reversed(cost_range_trend))
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取成本区间历史失败：{str(e)}")
```

确保在文件顶部导入 `calculate_recipe_cost_range_trend`：

```python
from app.services.recipe_service import calculate_recipe_cost_range_trend
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/api/test_recipes.py::test_get_recipe_cost_history_range -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/recipes.py backend/tests/api/test_recipes.py
git commit -m "feat(api): 添加获取菜谱成本区间历史的 API 端点"
```

---

## Task 6: 前端添加 getRecipeCostHistoryRange API 方法

**Files:**
- Modify: `frontend/src/api/recipes.ts`

**Step 1: 在文件中添加新的 API 方法**

找到 `recipes.ts` 文件，添加以下方法：

```typescript
/**
 * 获取菜谱成本区间历史
 * @param recipeId 菜谱ID
 * @param days 查询天数
 * @returns 成本区间历史数据
 */
export async function getRecipeCostHistoryRange(
  recipeId: number,
  days: number = 90
): Promise<CostRangeRecord[]> {
  const response = await client.get<CostRangeRecord[]>(`/recipes/${recipeId}/cost-history-range`, {
    params: { days }
  })
  return response.data
}

/**
 * 成本区间记录接口
 */
export interface CostRangeRecord {
  id: number
  recipe_id: number
  recipe_name: string
  date: string
  min_cost: number
  max_cost: number
  avg_cost: number
  recorded_at: number
}
```

**Step 2: Commit**

```bash
git add frontend/src/api/recipes.ts
git commit -m "feat(frontend): 添加获取菜谱成本区间历史的 API 方法"
```

---

## Task 7: 修改 CostChartSection 组件 Props 类型

**Files:**
- Modify: `frontend/src/views/recipes/components/CostChartSection.vue`

**Step 1: 更新 Props 类型定义**

在 `<script setup>` 部分，找到 Props 定义，修改为：

```typescript
// 从 api 导入 CostRangeRecord
import type { CostRangeRecord } from '@/api/recipes'

const props = defineProps<{
  records: CostRangeRecord[]
}>()
```

移除旧的类型导入（如果有的话）：
```typescript
// 删除这行
// import type { CostHistoryRecord } from '../types'
```

**Step 2: Commit**

```bash
git add frontend/src/views/recipes/components/CostChartSection.vue
git commit -m "refactor(frontend): 更新 CostChartSection 组件的 Props 类型"
```

---

## Task 8: 简化 CostChartSection 组件的 updateChart 函数

**Files:**
- Modify: `frontend/src/views/recipes/components/CostChartSection.vue`

**Step 1: 简化 updateChart 函数**

找到 `updateChart()` 函数，替换为：

```typescript
// 更新图表数据
function updateChart() {
  if (!chart) return

  // 直接使用后端返回的数据，无需聚合计算
  const dailyData = props.records.map(record => ({
    date: record.date,
    dateObj: new Date(`${record.date}T00:00:00`),
    min: record.min_cost,
    max: record.max_cost,
    avg: record.avg_cost,
    count: 1  // 固定为1，因为是API已计算好的区间
  }))

  if (dailyData.length === 0) {
    chart.setOption({
      series: []
    })
    return
  }

  const minCostInDataset = Math.min(...dailyData.map(d => d.min))
  const base = Math.min(0, minCostInDataset - 0.1)

  const option: EChartsOption = {
    title: {
      text: '成本趋势（元）',
      textStyle: {
        fontSize: 16,
        fontWeight: 600
      },
      left: 0
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        animation: false,
        label: {
          backgroundColor: '#42b883',
          borderColor: '#42b883',
          borderWidth: 1,
          color: '#fff'
        }
      },
      formatter: (params: any) => {
        const dateIndex = params[2]?.dataIndex ?? -1
        if (dateIndex < 0 || dateIndex >= dailyData.length) return ''
        const data = dailyData[dateIndex]
        const dateStr = data.dateObj.toLocaleDateString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit'
        })

        return `
          <div style="padding: 8px 12px;">
            <div style="font-weight: 600; margin-bottom: 8px;">${dateStr}</div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #42b883;"></span>
              <span>平均成本: ¥${data.avg.toFixed(2)}</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
              <span style="display: inline-block; width: 12px; height: 12px; background-color: rgba(66, 184, 131, 0.3); border-radius: 2px;"></span>
              <span>成本范围: ¥${data.min.toFixed(2)} - ¥${data.max.toFixed(2)}</span>
            </div>
          </div>
        `
      }
    },
    grid: {
      left: '5%',
      right: '4%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dailyData.map(d => d.date),
      boundaryGap: false,
      axisLabel: {
        formatter: (value: string) => {
          const parts = value.split('-')
          if (parts.length === 3) {
            return `${parts[1]}/${parts[2]}`
          }
          return value
        }
      },
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        formatter: (value: number) => `¥${value.toFixed(2)}`
      },
      splitLine: {
        lineStyle: {
          type: 'dashed',
          color: '#e5e5e5'
        }
      },
      axisPointer: {
        label: {
          formatter: (params: any) => {
            return `¥${params.value.toFixed(2)}`
          }
        }
      }
    },
    series: [
      // L 系列：下限
      {
        name: 'L',
        type: 'line',
        data: dailyData.map(d => d.min - base),
        lineStyle: {
          opacity: 0
        },
        stack: 'confidence-band',
        symbol: 'none',
        showSymbol: false
      },
      // U 系列：上限（使用 stack 堆叠，areaStyle 绘制范围带）
      {
        name: 'U',
        type: 'line',
        data: dailyData.map(d => d.max - d.min),
        lineStyle: {
          opacity: 0
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(66, 184, 131, 0.4)' },
              { offset: 1, color: 'rgba(66, 184, 131, 0.1)' }
            ]
          }
        },
        stack: 'confidence-band',
        symbol: 'none',
        showSymbol: false
      },
      // 平均成本线
      {
        name: '平均成本',
        type: 'line',
        data: dailyData.map(d => d.avg),
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: '#66b883',
          width: 2.5
        },
        itemStyle: {
          color: '#66b883',
          borderColor: '#fff',
          borderWidth: 2
        },
        emphasis: {
          scale: true,
          itemStyle: {
            color: '#66b883',
            borderColor: '#fff',
            borderWidth: 3,
            shadowBlur: 10,
            shadowColor: 'rgba(102, 184, 131, 0.5)'
          }
        }
      }
    ]
  }

  chart.setOption(option)
}
```

**Step 2: 移除 aggregateDailyCosts 函数**

找到并删除 `aggregateDailyCosts()` 函数（大约在第 47-112 行）

**Step 3: Commit**

```bash
git add frontend/src/views/recipes/components/CostChartSection.vue
git commit -m "refactor(frontend): 简化 CostChartSection 的数据处理逻辑"
```

---

## Task 9: 更新 RecipeDetail 页面调用新 API

**Files:**
- Modify: `frontend/src/views/recipes/RecipeDetail.vue`

**Step 1: 修改成本历史数据获取**

找到获取成本历史数据的代码，修改为使用新的区间 API：

```typescript
// 修改导入
import { getRecipeCostHistoryRange, type CostRangeRecord } from '@/api/recipes'

// 修改状态类型
const costHistoryRecords = ref<CostRangeRecord[]>([])

// 修改获取函数
async function fetchCostHistory() {
  if (!recipe.value) return

  try {
    costHistoryRecords.value = await getRecipeCostHistoryRange(recipe.value.id, 90)
  } catch (error) {
    console.error('Failed to fetch cost history:', error)
  }
}
```

**Step 2: Commit**

```bash
git add frontend/src/views/recipes/RecipeDetail.vue
git commit -m "feat(frontend): 更新菜谱详情页使用成本区间 API"
```

---

## Task 10: 构建验证

**Files:**
- Build: Frontend

**Step 1: 构建前端验证**

```bash
cd frontend
npm run build
```

**Step 2: 验证构建成功**

Expected: 构建成功，无错误

**Step 3: Commit**

如果构建成功，不需要提交（这是验证步骤）

---

## Task 11: 集成测试验证

**Step 1: 启动服务**

确保后端和前端服务已启动（使用自动重载）

**Step 2: 测试 API**

使用 curl 或浏览器访问：
```
GET /api/v1/recipes/{recipe_id}/cost-history-range?days=30
```

Expected: 返回成本区间数据

**Step 3: 测试前端**

1. 打开菜谱详情页
2. 查看成本趋势图表
3. 验证：
   - 图表显示区间带（绿色半透明区域）
   - 平均成本线显示为实线
   - Tooltip 显示正确的 min/max/avg 值

**Step 4: Commit**

```bash
git add .
git commit -m "test: 验证菜谱成本区间功能集成测试通过"
```

---

## 完成检查清单

- [ ] 后端 Schema 模型创建并测试通过
- [ ] _get_price_records_for_date 函数实现并测试通过
- [ ] calculate_recipe_cost_range_as_of 函数实现并测试通过
- [ ] calculate_recipe_cost_range_trend 函数实现并测试通过
- [ ] API 端点创建并测试通过
- [ ] 前端 API 方法添加
- [ ] 前端组件 Props 类型更新
- [ ] 前端组件数据处理简化
- [ ] 前端页面调用新 API
- [ ] 前端构建成功
- [ ] 集成测试验证通过

---

## 相关文档

- 设计文档: [docs/plans/2026-03-17-recipe-cost-range-design.md](../plans/2026-03-17-recipe-cost-range-design.md)
- 价格图表 confidence-band 实现: [MEMORY.md](../../.claude/projects/-home-ding-code-live-calc/memory/MEMORY.md#价格图表-confidence-band-实现)
