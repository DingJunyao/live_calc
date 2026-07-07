# 今日推荐：竖向滚动条 + 老三样随机性修复

## 现象
- 今日推荐页内容不多却出现竖向滚动条。
- 连续几天推荐都是牛奶燕麦 / 烤鱼 / 油泼辣子，随机性差。

## 根因

### 1. 竖向滚动条
`DailyMealsView.vue` 的 `.daily-meals-view` 设 `min-height: 100vh`（原 :134）。该容器渲染在 `AppLayout` 的 `<v-main>` 内，头顶还压着页面自己的 `<v-app-bar>`（:4）。`100vh` 是整个视口高度，而容器实际可用高度 ≈ `100vh − app-bar 高度`。容器偏要撑满 `100vh`，比父容器高出一个 app-bar（约 48~64px）→ 溢出 → 出现竖向滚动条。与内容多少无关。

全局 `grep "min-height: 100vh"` 仅此一处，其他详情页/列表页都不设此属性，照样不溢出——对照面佐证。

### 2. 老三样（确定性 argmax）
`meal_recommender.py` 的 `_pick_best_recipe`（原 :201-211）是确定性 argmax：

```python
for recipe in candidates:
    score, ... = await _score_recipe(...)
    if score > best_score:   # 严格 >，永远只留最高分
        best_recipe = recipe
```

每天喂进去的输入全确定：用户营养目标（`_get_meal_targets`，依赖 `daily_*_target` + 三餐常量占比）、候选池（`_get_candidate_pool`，`is_active`+`category`+黑名单）、营养/成本计算（`calculate_recipe_nutrition`/`calculate_recipe_cost` 确定性）→ 三餐各自最高分菜谱永远同一道。牛奶燕麦=早餐永恒最优、烤鱼=午餐永恒最优、油泼辣子=晚餐永恒最优。

## 修复

### 1. 滚动条
删 `min-height: 100vh`，保留 `max-width: 1200px` 居中与移动端 `max-width: 100%`。与其它页面看齐，高度由内容决定。

### 2. 加权随机（用户选「更刺激」档）
`_pick_best_recipe` 从 argmax 改为按分数加权随机：

- 先收集全部候选的 `(recipe, score, nutrition, cost)`（保留原有每条 `db.rollback()` 释放 SHARED 锁、避免阻塞并发写的逻辑）。
- `weight = score + 0.05`（epsilon）：直接用分数做权重、不放大幂次——高分更易中、低分也有机会（用户要的「更刺激」不可预测性）；epsilon 保证 `score=0`（营养/成本都算不出）的菜也有微机会，且 weights 不全零（`random.choices` 要求非负且非全零）。
- `random.choices(scored, weights=weights, k=1)[0]` 选取。

`refresh_meal_recommendation` 自动受益：它已 `exclude` 当前餐 `recipe_id` + 其他餐已选 id，加权随机必换到不同菜（不会再「换了个寂寞」回到同一道）。

## 验证
- 后端 `py_compile` exit=0。
- 前端 `npm run build` ✓ 33.98s（DailyMealsView chunk 13.38 kB）。
- `backend/tests` 无 meal_recommender 现成测试，不撞老用例。
- 无表结构变更。

## 使用提示（重要）
当天已生成的推荐不会自动重算——`generate_recommendations` 先查 `daily_recommendations` 当天记录，有则直接返回（:413）。所以：

- 今天的「老三样」仍会在，直到点各餐「换一个」（走 refresh 加权随机）或次日首次生成。
- 后端 `--reload` 会自动加载新代码，无需手动重启。

## 遗留 / 可选增强
- 未加「近期去重」（排除最近 N 天推荐过的菜）。若日后觉得多样性仍不够（菜谱池小、加权随机仍偏向少数高分菜），可再加一层历史去重。
- 未加针对 `_pick_best_recipe` 的单测（脱离数据库 mock 成本高，靠逻辑走查 + 运行时验证）。若要防回归（防以后又被改回 argmax），可补一个「运行 N 次结果去重数 > 1」的统计测试。

## 涉及文件
- `frontend/src/views/meals/DailyMealsView.vue`（删 min-height: 100vh）
- `backend/app/services/meal_recommender.py`（import random + `_pick_best_recipe` 改加权随机）
