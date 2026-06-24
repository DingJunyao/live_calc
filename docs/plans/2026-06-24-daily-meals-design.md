# 每日饮食推荐 - 设计文档

> 日期：2026-06-24 | 状态：待实现

## 概述

新增首页「今日推荐」，替代当前根路径 `/` → `/prices` 的重定向。按用户营养目标和预算，每天自动生成早/午/晚三餐菜谱推荐。当日首次访问生成、后续读缓存，支持单餐刷新（上限 5 次/天/餐）。

---

## 数据模型

### 新表：`daily_recommendations`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int (PK) | 自增 |
| `user_id` | int (FK → users) | 所属用户 |
| `date` | date | 推荐日期 |
| `meal_type` | enum | `breakfast` / `lunch` / `dinner` |
| `recipe_id` | int (FK → recipes) | 推荐菜谱 |
| `created_at` | datetime | 生成时间 |

联合唯一索引：`(user_id, date, meal_type)`

### 用户设置新增字段（挂在已有 `users` 表或 `user_config`）

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `daily_calorie_target` | float | 2000 | 每日热量目标 (kcal) |
| `daily_protein_target` | float | 60 | 蛋白质 (g) |
| `daily_carb_target` | float | 300 | 碳水 (g) |
| `daily_fat_target` | float | 65 | 脂肪 (g) |
| `daily_budget` | float | null | 每日预算 (元)，null = 不限 |

---

## 推荐算法

### 打分公式

```
score = nutrition_score × weight_n + cost_score × weight_c
```

- `weight_n` / `weight_c` 默认各 0.5，用户可在设置里调整
- 营养分和成本分均在 [0, 1] 区间

### 营养分 (nutrition_score)

将用户营养目标按三餐占比拆分：

| 餐类 | 热量 | 蛋白质 | 碳水 | 脂肪 |
|---|---|---|---|---|
| 早餐 | 25% | 25% | 25% | 25% |
| 午餐 | 40% | 40% | 40% | 40% |
| 晚餐 | 35% | 35% | 35% | 35% |

对每项营养素：`偏差 = 1 - |实际值 - 期望值| / max(期望值, 1)`

`nutrition_score = (calorie_dev + protein_dev + carb_dev + fat_dev) / 4`

### 成本分 (cost_score)

`meal_budget = daily_budget × 餐类占比`

`cost_score = 1 - min(recipe_cost / meal_budget, 1)`

- 菜谱成本 ≤ 该餐预算 → 高分；超预算按比例降至 0
- `daily_budget` 为 null 时，跳过成本分，仅用营养分

### 候选池

- 只选 `is_active=true`、`meal_type` 匹配的菜谱
- 优先有营养数据 + 有成本数据的菜谱
- 刷新时排除当前推荐菜谱

---

## API 设计

### `GET /api/v1/meals/recommendations`

获取今日三餐推荐。

**响应：**
```json
{
  "date": "2026-06-24",
  "recommendations": [
    {
      "meal_type": "breakfast",
      "recipe": {
        "id": 12,
        "name": "鸡蛋灌饼",
        "image_url": "...",
        "cost_estimate": 3.5,
        "nutrition_per_serving": {
          "calories": 380, "protein_g": 12, "carbs_g": 45, "fat_g": 18
        }
      },
      "is_current_meal": true
    }
  ],
  "totals": {
    "cost": 22.5,
    "calories": 1850,
    "protein_g": 68,
    "carbs_g": 240,
    "fat_g": 62
  }
}
```

- 首次访问：执行推荐算法，写入 `daily_recommendations`，返回结果
- 再次访问：直接读表返回
- `is_current_meal`：根据服务端时间判断，只有一个为 `true`

### `POST /api/v1/meals/recommendations/refresh`

刷新某一餐。

**请求：**
```json
{ "meal_type": "breakfast" }
```

- 排除当前推荐，重新打分取第一名
- 覆盖 `daily_recommendations` 中该餐记录
- 每餐每天最多 5 次，超出返回 `429 Too Many Requests`

### 用户设置（复用已有接口）

`PATCH /api/v1/auth/me` 扩展支持 `nutrition_goals` 和 `daily_budget` 字段。
`GET /api/v1/auth/me` 扩展返回这些字段。

### 后端文件结构

```
backend/app/
├── api/meals.py                        # 新路由
├── schemas/meal.py                     # 请求/响应 schema
├── services/meal_recommender.py        # 推荐算法
└── models/daily_recommendation.py      # 数据库模型
```

---

## 前端设计

### 路由变更

- `/` 不再重定向到 `/prices`，改为加载 `DailyMealsView.vue`
- 导航菜单新增「今日推荐」作为第一项（图标 `mdi-silverware-fork-knife`）

### 页面结构

```
┌──────────────────────────────────┐
│  App Bar: "今日推荐"              │
│  副标题: 2026年6月24日 星期三      │
│  右侧: ⚙️ 设置按钮                │
├──────────────────────────────────┤
│  今日汇总条                       │
│  💰 ¥22.5  🔥1850kcal           │
│  🥩 68g  🍚 240g  🥑 62g       │
│  进度条: 接近目标                 │
├──────────────────────────────────┤
│  横向时间线（桌面端）              │
│  - 早餐 · 07:30 ─ [卡片]         │
│  - 午餐 · 12:00 ─ [卡片]         │
│  - 晚餐 · 18:30 ─ [卡片]         │
└──────────────────────────────────┘
```

### 交互

| 功能 | 行为 |
|---|---|
| 当前时段高亮 | 5-10 点高亮早餐、10-14 高亮午餐、14-22 高亮晚餐、22-5 全缩小 |
| 刷新按钮 | 每餐独立 🔄，loading 动画防连点 |
| 点击卡片 | 跳转到菜谱详情页 |
| 汇总条 | 刷新某餐后实时更新汇总数字 |
| 首次加载 | 骨架屏 loading |
| 数据缓存 | 当天已有推荐直接读缓存，不重复生成 |

### 前端文件

| 文件 | 说明 |
|---|---|
| `views/meals/DailyMealsView.vue` | 首页主页面 |
| `components/meals/MealCard.vue` | 单餐推荐卡片 |
| `components/meals/DailySummaryBar.vue` | 顶部汇总条 |
| `components/meals/MealTimeline.vue` | 时间线布局容器 |
| `api/meals.ts` | 前端 API 封装 |
| `stores/meals.ts` | Pinia store |

---

## 响应式布局

### 桌面端（≥960px）：横向时间线

- 三个节点水平排列，CSS 伪元素画连线
- 当前餐放大 1.2× + 脉冲光晕
- 卡片 `max-width: 380px`

### 移动端（<960px）：纵向时间线

- 左侧竖线 + 圆点，卡片 `margin-left: 24px`
- 当前餐左侧边框加粗 + 主题色高亮，不放大
- 当前餐自动 `scrollIntoView({ block: 'center' })`

---

## 边界情况

| 场景 | 处理 |
|---|---|
| 某餐类型没有菜谱 | 占位卡片：「请完整维护菜谱，以获取推荐信息」+「去添加」按钮 |
| 有菜谱但缺营养数据 | 显示菜谱名/图片，营养栏显示「--」，底部浅色提示 |
| 三餐全部缺失 | 整页空状态插图 + 引导文案 + 链接 |
| 刷新次数超限（5 次） | toast：「今天已经换了好几次啦，明天再来吧～」 |
| 网络错误 | snackbar + 重试按钮 |
| 未登录 | 路由守卫自动跳转（已有逻辑） |

---

## 测试策略

| 层级 | 内容 |
|---|---|
| 后端单元测试 | `MealRecommender` 打分逻辑、空菜谱/全无营养/预算为 0 |
| 后端 API 测试 | 首次生成 & 缓存命中；正常刷新 & 超限 429 |
| 前端组件测试 | 三种卡片状态（正常/占位/loading）、汇总条计算 |
| E2E（可选） | 首页首次加载 → 刷新早餐 → 跳转详情 → 返回 |

---

## 依赖与前置条件

- 菜谱已有 `meal_type` 字段（区分早/午/晚餐）
- 已有菜谱成本/营养计算能力（`GET /recipes/:id/cost`、`GET /recipes/:id/nutrition`）
- 用户认证体系已有（JWT）

## 影响范围

- 后端：新增 `meals` 模块（路由 + schema + service + model），扩展 `auth/me` 接口
- 前端：新增首页模块（4 组件 + 1 API + 1 store），修改路由和 3 个导航组件
- 数据库：新增 `daily_recommendations` 表，`users` 表新增 5 个字段
