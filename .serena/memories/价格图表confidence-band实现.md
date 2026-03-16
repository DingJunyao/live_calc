# 价格图表 Confidence Band 实现

## 需求
修改原料、商品详情的价格趋势图表，将一天内的多条价格记录合并为单个横轴数据点，同时显示价格范围（最小值到最大值）和平均价格。

## 技术方案

### ECharts Confidence Band 模式
使用 ECharts 的 stack（堆叠）机制来实现 confidence band 效果：

1. **L 系列（下限）**: 存储下限值，透明线条
2. **U 系列（上限）**: 存储上限与下限的差值，配合 areaStyle 显示范围
3. **Avg 系列（平均线）**: 独立的折线显示平均价格

### X-Axis 类型选择
必须使用 `type: 'category'` 而非 `type: 'time'`，因为 stack 机制在 category 类型下才正常工作。

## 实现细节

### 数据聚合函数 `aggregateDailyPrices()`

```typescript
function aggregateDailyPrices(records: PriceRecord[]) {
  const dailyMap = new Map<string, number[]>()

  // 按日期分组
  for (const record of records) {
    const date = new Date(record.recorded_at)
    if (!isValidDate(date)) continue

    const dateKey = formatDate(date)
    dailyMap.set(dateKey, (dailyMap.get(dateKey) || []).push(record.price))
  }

  // 计算每日统计
  return Array.from(dailyMap.entries()).map(([dateKey, prices]) => {
    // 转换为数字数组，过滤无效值
    const numericPrices = prices.map(p => Number(p)).filter(p => !isNaN(p) && p !== null)
    
    return {
      date: dateKey,
      min: Math.min(...numericPrices),
      max: Math.max(...numericPrices),
      avg: numericPrices.reduce((a, b) => a + b, 0) / numericPrices.length,
      count: prices.length
    }
  }).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
}
```

### ECharts 配置

```typescript
series: [
  // L 系列：下限
  {
    name: 'L',
    type: 'line',
    data: dailyData.map(d => d.min - base),
    lineStyle: { opacity: 0 },
    stack: 'confidence-band',
    symbol: 'none'
  },
  // U 系列：上限（堆叠在 L 之上）
  {
    name: 'U',
    type: 'line',
    data: dailyData.map(d => d.max - d.min),
    lineStyle: { opacity: 0 },
    areaStyle: {
      color: {
        type: 'linear',
        colorStops: [
          { offset: 0, color: 'rgba(66, 184, 131, 0.4)' },
          { offset: 1, color: 'rgba(66, 184, 131, 0.1)' }
        ]
      }
    },
    stack: 'confidence-band',
    symbol: 'none'
  },
  // 平均价格线
  {
    name: '平均价格',
    type: 'line',
    data: dailyData.map(d => d.avg),
    smooth: true,
    lineStyle: {
      color: '#42b883',
      width: 2.5
    },
    itemStyle: {
      color: '#42b883',
      borderColor: '#fff',
      borderWidth: 2
    }
  }
]
```

## 修复的问题

### 1. 日期无效问题
**症状**: 图表所有点显示为 1970-01-01
**原因**: 部分记录的 `recorded_at` 为无效日期
**解决**: 添加 `isValidDate()` 函数验证日期，跳过无效记录

### 2. 字符串类型导致 NaN
**症状**: 控制台显示 `Avg series data: [2.18, 2.18, "NaN"]`
**原因**: 后端返回的 `price` 是字符串类型，字符串相加产生 `"NaN"` 字符串
```javascript
// 错误行为
"2.18" + "1.98" = "02.181.98"  // 字符串连接
"2.18" / 1 = "NaN"  // 字符串除法产生字符串 "NaN"
```
**解决**: 使用 `Number(p).filter(p => !isNaN(p))` 转换并过滤无效值

### 3. 颜色不一致问题
**症状**: 平均价格线显示为红色
**解决**: 统一使用绿色 `#42b883` 作为主题色
- lineStyle.color: `#42b883`
- itemStyle.color: `#42b883`
- emphasis.itemStyle.color: `#42b883`
- tooltip 图标颜色: `#42b883`

### 4. ECharts 弃用警告
**症状**: textStyle hierarchy, hoverAnimation 警告
**解决**: 
- 移除嵌套的 textStyle 配置
- 使用 emphasis.scale 替代 hoverAnimation

## 修改文件
- `frontend/src/views/items/components/PriceChartSection.vue`
  - 新增 `aggregateDailyPrices()` 函数
  - 新增 `isValidDate()` 函数
  - 修改图表配置为 confidence band 模式
  - 调整 x-axis 类型为 category

## 提交记录
Commit: `ad6657e feat(frontend): 添加价格趋势图表的 confidence band 效果`
