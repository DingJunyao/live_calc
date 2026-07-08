# 时间口径统一为用户本地日

## 背景

系统"把记录归到某一天"的判定口径原不一致，三种并存：

| 口径 | 用在哪 |
|---|---|
| 用户本地日（时区感知） | 支出报告商品支出逐日、Expense |
| 服务器本地日 | 菜谱成本趋势起止日、今日推荐"今天"（`datetime.now().date()`，不收 timezone） |
| UTC 日 | 价格记录日期展示、最新价日期判定、sparkline、老 price-trend（`func.date(recorded_at)` / `.date()`） |

根因：`recorded_at` 存 UTC naive，部分代码直接取 `.date()` 得 UTC 日、部分用 `datetime.now().date()` 得服务器本地日、仅支出报告显式走 `timezone_offset`。同一记录在不同功能归到不同日。

## 决策（brainstorming）

| 决策点 | 选择 | 理由 |
|---|---|---|
| 聚合策略 | 丙·按场景混合 | 逐日查询走 `local_date_range_to_utc_range` 切 SQL 区间；多记录归日走 Python 层 `utc_datetime_to_local_date`；as_of 前向填充不变。三库一致、性能不退、复用现成工具 |
| 时区表达 | IANA（`zoneinfo`） | 比秒偏移准（夏令时）、标准。SQL 层不碰时区函数绕开三库差异 |
| 传递载体 | `X-Timezone` 请求头 | 时区是环境元数据走 header，所有请求统一带，URL 干净 |
| 检查点 | `Depends(get_timezone)` 挂涉及时区的端点 | 精准，健康检查/登录免影响 |
| 默认时区 | UTC（兜底） | 中立，前端强制注入几乎不触发 |
| 向后兼容 | 不兼容旧 `timezone_offset` | 单一契约，前端同步切，无外部消费者 |
| 老 price-trend | 删除 | 前端未用，YAGNI |

## 改造面

- **`backend/app/utils/date_range_utils.py`**：三函数 `user_timezone_offset: Optional[int]` → `tz: str = "UTC"`，内部 `timezone(timedelta(...))` → `ZoneInfo(tz)`
- **新建 `backend/app/api/deps.py`**：`get_timezone` 依赖，`Header(None, alias="X-Timezone")`，缺失/非法返回 400（非 422，用 `Header(None)` + 手动 raise）
- **`backend/app/services/recipe_service.py`**：整条成本计算链加 `tz`——`_get_price_record_with_fallback`/`_get_price_records_with_fallback`/`_get_price_records_for_date`/`_get_child_price_per_gram`/`_get_aggregated_cost_from_children`/`_get_cost_from_recipe`/`calculate_recipe_cost`(async)/`_range_as_of`/`_as_of`/`_range_trend`/`_trend`，所有 `datetime.now().date()`→`utc_datetime_to_local_date(now(UTC),tz)`、`recorded_at.date()`→`utc_datetime_to_local_date`、`datetime.combine`→`local_date_range_to_utc_range`，趋势函数内部闭包 `_find_day_records`/`_find_forward_fill_records` 同改
- **`backend/app/services/ingredient_price_service.py`**：`_collect_recent_records`/`get_weighted_ingredient_price`/`resolve_direct_weighted_for_cost` 加 `tz`，当天记录判定改本地日
- **端点接入 `Depends(get_timezone)`**：菜谱成本趋势（recipes）、sparklines 三端点、nutrition latest-price + sparkline 注入函数、products_entity get_product、meals 三端点、reports expense
- **`backend/app/services/report_service.py`**：`generate_expense_report` offset→tz、删冗余 `group_by(func.date)` 预查询；删 `generate_price_trend`
- **`backend/app/services/meal_recommender.py`**：`_build_response_from_records`/`generate_recommendations`/`refresh_meal_recommendation`/`check_today_status`/`_generate_in_background`/`trigger_background_generation`/`_refresh_in_background`/`trigger_background_refresh` 全加 `tz`（含后台线程 args 透传），`today`/`now` 改本地日
- **前端**：`api/client.ts` 拦截器注入 `X-Timezone`；删 `api/timezone.ts`（整文件 dead code）、`utils/timezone.ts` 的 offset 函数 + `localDateToUTCRange`/`localDateRangeToUTCRange`（后端凭 X-Timezone 自算，前端只传本地日期）
- **依赖**：加 `tzdata`（Windows zoneinfo 需要），改 `requirements.txt` + `pyproject.toml` + `uv.lock` + 装 `.venv`
- **测试**：新建 `tests/utils/test_date_range_utils.py`（7 例，含 DST 春调日）、`tests/api/test_deps_timezone.py`（4 例：合法/缺失/非法）；`conftest.py` 模块级 `app.dependency_overrides[get_timezone] = lambda: "UTC"`（既有端点测试无需逐个带头，deps 校验测试用独立 app 不受影响）；`test_reports.py` 删 price-trend 测试、expense 测试加头

## 验证

- 后端 `compileall` 通过；全量 pytest **482 passed**（+11 新 tz 测试），25 failed **经抽查全为预存**（default_unit_id 弃用、鉴权 401、`product_merchant_price_summary` 表缺、网络下载、格式检测等，与改造无关；4 个可疑项单独验证均非引入）
- 前端 `npm run build` 通过
- grep 确认后端零残留：`timezone_offset`/`user_timezone_offset`/`func.date(recorded_at)`/`datetime.now().date()`/`datetime.date.today()`
- SQL 层永不碰时区函数，三库安全；无表结构变更、无 alembic、无 SQL 脚本
- 未 commit（按项目规矩）

## 遗留 / 注意

- `calculate_recipe_cost`(async) 加了 `tz` 参数但内部只用 `as_of_date` 比较（不直接用 tz 判归属），tz 参数无害保留（调用方透传）
- 单数 `_get_price_record_with_fallback` 同样收 tz 但内部不用（返回单条记录，无"当天"聚合）
- 跨日时段浏览器手测留开发者（服务已起，network 面板可见每个请求带 `X-Timezone`）
- 详细设计见 [spec](../docs/superpowers/specs/2026-07-07-时间口径统一为用户本地日-design.md) + [plan](../docs/superpowers/plans/2026-07-08-时间口径统一为用户本地日.md)

## 衔接

改造完成后重启文档项目，`docs/concepts.md` 的"时间与一天"节只写"用户本地日 + X-Timezone"一种口径，不标注不一致。见 [[FEATURE_系统文档]]
