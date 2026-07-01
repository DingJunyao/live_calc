# 菜谱推荐长事务导致 database is locked

> 日期：2026-07-01
> 分支：`feat/multi-user-permissions`
> 相关：[BUGFIX_连接池耗尽.md](BUGFIX_连接池耗尽.md)（同属 SQLite 写锁/并发问题，根因不同）

## 现象

普通用户 POST `/api/v1/products` 创建价格记录时，`INSERT INTO product_merchant_price_summary`（聚合表）报 `database is locked`，请求耗时 **35 秒**（busy_timeout 30 秒 + 开销）后 500。

## 根因

`busy_timeout = 30 秒`（[database.py:12](../backend/app/core/database.py#L12)）。POST /products 等待 SQLite 写锁 30 秒超时——有**别的写事务持锁**。

持锁者：**菜谱推荐后台生成**（[meal_recommender.py](../backend/app/services/meal_recommender.py) `_generate_in_background` → `generate_recommendations`）。

`generate_recommendations` 原实现（L466-482 主分支 + L434-448 黑名单重生成分支）：
```python
for meal_type in ["breakfast", "lunch", "dinner"]:
    best_recipe, ... = await _pick_best_recipe(...)  # 计算密集（扫候选菜谱池 + 算营养/成本/评分）
    if best_recipe:
        db.add(record)
        db.flush()  # ← 第一次 flush 后事务持 SQLite 写锁
# 循环里后续 _pick_best_recipe 在持锁状态下跑（慢计算）
db.commit()  # ← 最后才 commit，写锁持有整个 3 餐循环
```

早餐 `flush` 拿写锁后，午/晚餐的 `_pick_best_recipe`（慢）在持锁状态下跑，写锁一直拿到最后 `commit`。后台生成（独立 SessionLocal + 线程）期间，POST /products 的写（INSERT ProductRecord + 聚合）等写锁至 busy_timeout 30 秒 → database is locked。

> 注：`_generate_in_background` 用独立 `SessionLocal()`（L621）+ 线程，长事务持锁阻塞主请求线程的并发写。

## 修复

改成「**先算后写**」——循环内只 `_pick_best_recipe`（读 + 计算，收集结果，不持写锁），循环后批量 `db.add + commit`（写锁只持有批量写那一下）。

主分支（L463-482）：
```python
    # 先完成所有餐的打分挑选（读 + 计算，不持写锁）
    picks = []
    for meal_type in meal_types:
        best_recipe, ... = await _pick_best_recipe(user, meal_type, exclude_recipe_ids=picked_ids, db=db)
        if best_recipe:
            picked_ids.add(best_recipe.id)
            picks.append((meal_type, best_recipe.id))
    # 批量写入 + commit（写锁持有时间短）
    for meal_type, recipe_id in picks:
        db.add(DailyRecommendation(user_id=user.id, date=today, meal_type=meal_type, recipe_id=recipe_id))
    db.commit()
```

黑名单重生成分支（L434-448）同款改法（先收集 `regen_picks`，再批量 add + commit）。

`refresh_meal_recommendation`（L500）已正确（单餐，先 `_pick_best_recipe` 后 update/add + commit，事务短），无需改。

## 影响

写锁持有时间从「整个 3 餐循环（含 3 次 `_pick_best_recipe` 慢计算）」缩短到「批量 add + commit（毫秒级）」。后台生成不再长阻塞并发写。

## 验证

- `py_compile` 通过
- 修复是等价变换（生成同样的 daily_recommendations，只改事务结构），功能不变
- 手动验收：触发后台推荐生成（GET /meals）期间 POST /products，不再 database is locked
- 无 meal_recommender 自动化测试（并发锁难自动化），靠逻辑等价 + 手动验证

## 不是本次审核框架改动引入

这是**既有 bug**（菜谱推荐后台生成长事务），与 2026-06-30 起的审核框架改造（USDA 匹配 / 营养 / 商品营养走审核）无关——POST /products（价格记录）不走审核框架。审核框架端点事务短（apply + commit），不持锁。
