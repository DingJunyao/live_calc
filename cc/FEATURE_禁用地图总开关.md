# 禁用地图总开关

## 背景

部分地图服务需要授权费用。需要管理员能一键禁用全部地图功能：前端所有地图隐藏、商家经纬度不必填、常用地点功能隐藏（数据保留）。

## 字段方案

采用**新增 `map_enabled` 布尔字段**（非复用 `available_maps` 空列表）。理由：语义清晰（「要不要用地图」与「用哪几张」正交）；临时关闭不丢 `available_maps` 配置，重开原地恢复；`default_map` 联动逻辑不受影响（空列表方案会让 `ensureDefaultMapValid` 不触发回退、`default_map` 残留无意义）。

## 后端改动

- [map_config.py](backend/app/models/map_config.py)：`MapConfiguration` 加 `map_enabled = Column(Boolean, nullable=False, default=True, server_default=sa.text("true"))`（三库通吃，对齐项目 boolean server_default 规矩），`to_dict()` 带上。
- [admin.py](backend/app/api/admin.py)：`MapConfig` schema + `DEFAULT_MAP_CONFIG` + `update_map_config` 三处加 `map_enabled`（GET 端点靠 `MapConfig(**to_dict())` 自动带，无需单独改）。
- [merchants.py](backend/app/api/merchants.py)：公开端点 `get_public_map_config` 默认分支（无配置时）补 `map_enabled: True`；有配置走 `config.to_dict()`（已含）。
- [places.py](backend/app/api/places.py)：抽 `_ensure_map_enabled(db)` helper（读 `MapConfiguration.map_enabled`，无配置默认 True），四个写端点（POST/PUT/DELETE/设默认）try 内第一行调用，`map_enabled=False` 时 403；`GET` 读接口不拦（数据保留可读）。
- 迁移：[alembic 20260719_0001](backend/alembic/versions/20260719_0001_add_map_enabled.py) + 三引擎 SQL（[sqlite](backend/scripts/sql/20260719_map_enabled_sqlite.sql)/[mysql](backend/scripts/sql/20260719_map_enabled_mysql.sql)/[postgresql](backend/scripts/sql/20260719_map_enabled_postgresql.sql)，PostGIS 无关不另出）。**开发库应用由开发者手动执行**（遵循 CLAUDE.md 不自行改库；测试走内存库 create_all 自动建字段，不依赖开发库迁移）。

## 前端改动

- [useMapConfig.ts](frontend/src/composables/useMapConfig.ts)（新）：模块级单例 composable（参考 useTheme 套路），缓存 `/merchants/map-config`，暴露 `{ mapEnabled, config, ensureLoaded, reload }`；`ensureLoaded` 用 `loadPromise` 幂等；请求失败回退 `mapEnabled=true`（保守，不破坏现有功能）。
- [MapSettingsView.vue](frontend/src/views/admin/MapSettingsView.vue)：顶部 `v-switch` 绑 `config.map_enabled`；三块配置区 `v-card` 加 `:class="{ 'config-disabled': !config.map_enabled }"`（CSS `opacity:0.5; pointer-events:none` 灰显，**不用 v-card disabled**——Vuetify 3 透传不可靠）；interface/reactive 加 `map_enabled`。
- [MerchantsView.vue](frontend/src/views/data/MerchantsView.vue)：`mapEnabled` 切两套布局——`v-if="mapEnabled"` 保留原「左列表+右地图」双栏，`v-else` 卡片网格（桌面 v-row+v-col cols 12/sm6/md4/lg3/xl2）/列表（移动 v-list three lines，参考 PricesView）；定位按钮禁用态隐藏；表单 MapPicker `v-if="mapEnabled"`；`saveItem` 坐标条件 `if (mapEnabled.value && pickerCoords.value)`；禁用态独立 FAB。
- [MerchantDetail.vue](frontend/src/views/merchants/MerchantDetail.vue)：坐标行两分支加 `mapEnabled &&`/`v-else-if="mapEnabled"`；位置（地图）卡片 `v-if="mapEnabled && 有坐标"`；表单 MapPicker `v-if="mapEnabled"`；`saveItem` 同款坐标条件。
- [ProfileView.vue](frontend/src/views/profile/ProfileView.vue)：「我的常用地点」入口 `v-if="mapEnabled"`。
- [router/index.ts](frontend/src/router/index.ts)：`beforeEach`（async）加 `profile-places` 分支——`await ensureLoaded()` 后 `!mapEnabled.value` 重定向 `/profile`。
- [UserPlacesView.vue](frontend/src/views/profile/UserPlacesView.vue)：兜底（防守卫与配置读取竞态）——`!mapEnabled` 顶部 v-alert 提示 + FAB/三按钮（设默认/编辑/删除）`:disabled`。

## 关键设计

- **禁用地图时 payload 不带坐标**：前端 `saveItem` 仅 `mapEnabled.value && pickerCoords.value` 才传 lat/lng；后端 `MerchantUpdate` 走 `model_dump(exclude_unset=True)`，不传即保留原值——编辑有坐标商家不受影响、新建 null、编辑无坐标仍 null。
- **无坐标开启后修改不给默认值**：`openEditDialog` 对无坐标商家 `pickerCoords=undefined`，MapPicker 不预填，用户不选则不传。不在禁用↔启用切换时偷塞默认值（不 0,0、不给默认城市）。
- **详情页地图双条件**：`mapEnabled && 有坐标`——地图关了不显示、地图开但无坐标也不显示。
- **mapEnabled 读取时机**：页面 `onMounted` 读一次、期间不变；管理员改开关后其他页面/用户下次进入或刷新生效（低频操作，不做实时推送，YAGNI）。
- **MapPicker/MerchantMapView 内部不改**：外层 `v-if="mapEnabled"` 挡住不渲染，内部 map-config 调用不触发。
- **常用地点数据保留**：写接口挡、读接口不挡，user_places 表不动，重开即用。

## 验证

- 后端：[test_map_enabled_admin.py](backend/tests/test_map_enabled_admin.py)（2）+ [test_map_enabled_public.py](backend/tests/test_map_enabled_public.py)（3）+ [test_places_map_disabled.py](backend/tests/test_places_map_disabled.py)（5）= **10 passed**；既有 test_merchant_merge_proposals + test_ingredient_merchant_weighted 回归 **4 passed** 无新失败；compileall 通过。
- 前端：多次 build 通过（最终 1m8s，precache 128 entries 不变）。
- final 整体审查（独立 reviewer）：通过，无 Critical/Important/Minor，链路完整、命名一致、5 需求全覆盖。

## 遗留 / 待开发者

1. **迁移应用开发库**：项目当前开发库由 `backend/.env` 的 `DATABASE_URL` 决定。需开发者备份后手动执行对应引擎 SQL（或 alembic），不自行跑。
2. **手动验收 5 场景**：管理员开关切换（配置区灰显/恢复）；启用态商家列表双栏+详情地图+常用地点入口；禁用态商家卡片网格/列表、表单无 MapPicker 且有坐标保存不变、详情无地图、常用地点入口隐藏+路由重定向+直接访问兜底、后端写接口 403/读 200。
3. **git 提交**：遵循 CLAUDE.md「不主动 commit」，改动留工作区，提交时机由开发者定。

## 文档

- spec：[docs/superpowers/specs/2026-07-19-禁用地图总开关-design.md](../docs/superpowers/specs/2026-07-19-禁用地图总开关-design.md)
- 计划：[docs/superpowers/plans/2026-07-19-禁用地图总开关.md](../docs/superpowers/plans/2026-07-19-禁用地图总开关.md)（13 任务，subagent 驱动 + 两阶段审查执行）
