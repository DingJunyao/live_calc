# FEATURE：商家地图默认范围（常用地点聚焦）

## 背景

商家管理页面（`MerchantsView`）的地图默认范围由 `MerchantMapView.fitAllMerchants` 决定：Leaflet 引擎用 `fitBounds` 框住**当前页**商家，SDK 引擎（高德/百度/腾讯）仅跳到第一个商家 zoom 13。商家地理跨度大时地图被拉到全国视角、标记挤成一团；翻页/搜索又反复触发 fitAll，视角无法稳定。此外发现遗留的 `FavoriteMerchant` 表（后端有表+API，前端从未接入）语义与「常用地点」重叠，一并清理。

## 目标

- 进页面默认聚焦用户常用地点（家/公司等）周边约 5km
- 支持多个常用地点并快速切换；记住上次选择
- 不自动请求定位权限；保留手动定位按钮，圆半径 1km → 5km
- 没设地点时显示**全部商家**真实分布（非当前页）
- 仅调初始视角，远处商家照常显示，不按距离筛选列表
- 清理遗留 `FavoriteMerchant` + 死的 `POST /merchants/route` 端点 + `calculate_route` 孤儿服务函数

## 非目标（YAGNI）

- 不做按距离筛选商家
- 不接逆地理编码自动填地址（`address` 手填）
- `kind` 固定 home/work/custom 三种
- 切换记忆仅 `localStorage`，不做 last_used 后端持久化

## 数据模型

新建 `user_places` 表（`backend/app/models/user_place.py`，与 `User` 一对多）：

```python
class UserPlace(Base):
    __tablename__ = "user_places"
    id, user_id(FK users.id), name(50), kind(20, default "custom"),
    latitude/longitude(Numeric(10,7)), address(255, nullable),
    is_default(Boolean default False), sort_order(Integer default 0),
    created_at, updated_at
```

「每用户最多一个 `is_default=True`」由应用层在 `_clear_default` 联动置 false。

迁移：`backend/alembic/versions/20260622_0001_add_user_places_drop_favorite_merchants.py`（建 `user_places` + drop `favorite_merchants`；downgrade 重建 `favorite_merchants` 含 audit 字段保链完整）。
SQL：`backend/scripts/sql/20260622_user_places_{sqlite,mysql,postgresql}.sql`（3 引擎，与 PostGIS 无关）。

## 清理 FavoriteMerchant（死代码）

`FavoriteMerchant` 前端零接入、后端 API 为死接口，与 `user_places` 语义重叠，整条线删除：

- 模型：删 `FavoriteMerchant` 类、`User.favorite_merchants` relationship、`__init__` 注册
- schema：删 `FavoriteMerchantCreate/Response` + `RouteCalculateRequest/Response`
- API：删 `GET/POST /merchants/favorites` + `POST /merchants/route`
- 服务：删 `app/services/map_service.py`（`calculate_route` + `_haversine_distance` 孤儿）
- 导出/导入：`favorite_merchants` → `user_places`（reachability/packaging/serializers + importer 全链路迁移，导出 zip 改 `user_places.json`）
- 测试：`test_export_serializers.py` 的 `serialize_favorite_merchant` 用例换 `serialize_user_place`

历史 alembic 迁移（操作 `'favorite_merchants'` 表名字符串）保留不动，迁移链完整。

## API

常用地点挂在 `/api/v1/places`：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/places` | 列表（is_default 优先，其次 sort_order/created_at） |
| POST | `/places` | 新建（is_default=True 时联动清其他） |
| PUT | `/places/{id}` | 改名/坐标/kind |
| DELETE | `/places/{id}` | 删除 |
| PUT | `/places/{id}/default` | 设为默认 |

商家坐标全集（fitAll 用，不分页）：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/merchants/coordinates` | `[{id, latitude, longitude, is_open}]`，支持可选 `search`/`include_closed`（与列表同语义） |

## 前端 — 地图范围逻辑（MerchantMapView）

新增 props：`places` / `currentPlaceId` / `allCoordinates`；emit `update:currentPlaceId`。

- `initialCenter` computed：`currentPlaceId` 命中 `places` 取坐标，否则 null
- 抽 helper：`toDisplayCoord`（WGS84→当前坐标系）、`applyInitialView`（有中心 setCenter+zoom12，否则 fitAll）、`fitSDKBounds`（SDK 真 fitBounds）
- `initMap`：延迟调 `applyInitialView`
- watch `merchants`：有 `initialCenter` 只刷标记保持视角，无才 fitAll（**翻页不飞回全国**）
- watch `initialCenter`：切换地点重新 `applyInitialView`
- `fitAllMerchants`：用 `allCoordinates`（全集）算 bounds，标记仍画当前页
- 修复 SDK `fitAllMerchants`：高德 `setBounds` / 百度 `setViewport` / 腾讯 `fitBounds`，不再只跳第一个
- 定位圆 1km → 5km（radius + popup 文案 + 按钮 title）

## 前端 — 地点切换器（地图控件区）

`MerchantMapView` 右上角控件区 `v-select`（places + 「全部商家」），`places` 为空时隐藏。状态由 `MerchantsView` 持有：

- `currentPlaceId` 优先级：`localStorage` 上次选择（地点仍存在）→ `is_default` → null（fitAll）
- 切换记 `localStorage`（key `merchants_map_current_place_id`），跨会话保留
- onMounted 加载 places + allCoordinates；搜索/切换营业状态时 allCoordinates 跟随重拉

## 前端 — 常用地点管理

- `ProfileView` 设置列表加「我的常用地点」（`mdi-map-marker-multiple`）→ `router.push('/profile/places')`
- 新建 `UserPlacesView.vue`（`views/profile/`）：列表（kind 图标 + name + address + 设默认/编辑/删除）+ 添加/编辑对话框（name + kind 固定下拉「家/公司/其他」+ `MapPicker` 选点 + address）。移动端对话框全屏
- 路由 `/profile/places`

## 涉及文件

后端：`models/user_place.py`(新)、`models/{user,merchant,__init__}.py`、`schemas/{user_place,merchant}.py`、`api/{places,merchants,main}.py`、`services/export/{reachability,packaging,serializers}.py`、`services/importer/importers/export.py`、`services/map_service.py`(删)、`tests/services/test_export_serializers.py`、迁移 + 3 引擎 SQL。

前端：`components/map/MerchantMapView.vue`、`views/data/MerchantsView.vue`、`views/profile/{ProfileView,UserPlacesView}.vue`、`router/index.ts`。

## 验证

- 后端：`py_compile` + `import app.main`（路由 `/api/v1/places*` + `/merchants/coordinates` 注册确认）
- 前端：`npm run build` 通过（19.6s，无 TS 错误）
- 待执行：`alembic upgrade head`（建 `user_places` + drop `favorite_merchants`），需开发者手动跑
