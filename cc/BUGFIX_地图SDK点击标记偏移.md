# 地图 SDK 点击标记偏移修复

## 现象

商家管理 → 添加商家（及修改商家）时，使用各地图 SDK（高德 / 百度 / 腾讯）选点，点击地图后**标记不在点击处**，有偏移（典型的「火星偏移」量级，几百米），保存的经纬度也是错的。Leaflet 系（OSM / 天地图）无此问题。

## 根因

SDK 引擎（`AMapSDKEngine` / `BaiduSDKEngine` / `TencentSDKEngine`）违背了「引擎与调用方之间传递地图坐标系原始坐标」的契约。

- **Leaflet 系引擎（契约正确）**：`click` emit 原始坐标（`e.latlng`），`addMarker` 直接用传入坐标，click 与 addMarker 同一套坐标系，点击哪标记就在哪。
- **SDK 系引擎（契约错乱）**：`click` 内部多做了一次 `convertCoordinate(..., 'gcj02'/'bd09', 'wgs84')` 再 emit，但 `addMarker` 的注释却说「已由调用方转 GCJ02/BD09，直接使用」——click 像「返 WGS84」契约，addMarker 像「收地图坐标」契约，自相矛盾。

`MapPicker.vue` 是按「传啥用啥」契约设计的（自己 `convertToWGS84` 转换），于是在 SDK 引擎下出现双重转换链（以高德为例）：

1. 点击像素 P（对应 GCJ02 坐标 G）
2. SDK click 把 G 转 WGS84 得 W1，emit W1
3. MapPicker `convertToWGS84(W1)`：把 W1（WGS84）当 GCJ02 再转一次 → 错误坐标 E1，存入 `wgs84Coordinate`
4. `setLeafletMarker(W1)` → `addMarker(W1)`：SDK 把 W1（WGS84）当 GCJ02 画在偏移底图上 → **标记偏离点击点约一个 GCJ02↔WGS84 差值**

百度/腾讯连 `init` 的 center 也多转了一次（`convertCoordinate(center, 'wgs84', 'bd09'/'gcj02')`），而 MapPicker 传入的 center 已是 `displayCoordinate`（转换过的地图坐标系坐标），导致**初始中心点也双重偏移**。

## 修复

统一三个 SDK 引擎为「传啥用啥」契约（与 Leaflet 引擎对齐），去掉引擎内部所有 `convertCoordinate`，坐标转换职责回归调用方（`MapPicker` 已具备 `convertToWGS84` / `displayCoordinate`）。

### 改动点（每个 SDK 引擎相同套路）

- `init` center：去掉 `convertCoordinate(center, 'wgs84', ...)`，直接用调用方传入的地图坐标系坐标（高德本就没转，仅修正误导注释）
- `click`（init 内 + `on('click')` 内）：去掉 `→WGS84` 转换，原样 emit 当前地图坐标系坐标
- `markerDragend`：去掉 `→WGS84` 转换，原样 emit 拖拽后的地图坐标系坐标
- 清除不再使用的 `convertCoordinate` / `getCoordinateSystem` import

### 修复后数据流（高德为例）

1. 点击像素 P → SDK emit 原始 GCJ02 坐标 G
2. MapPicker `convertToWGS84(G)` → 正确 WGS84 W1，存 `wgs84Coordinate`
3. `setLeafletMarker(G)` → `addMarker(G)` → GCJ02 画在 GCJ02 底图 → 标记精准落在 P
4. `emit('update:modelValue', W1)` → 正确 WGS84 传出

标记落在点击处，存储坐标正确。

## 影响面

- **MapPicker**：唯一监听 SDK 引擎 `click` / `markerDragend` 的组件，本次修复的直接受益方。
- **MerchantMapView**：不监听 `click` / `markerDragend`；SDK 分支下商家标记走原生 SDK API（`new window.AMap.Marker` 等），不走引擎 `addMarker`。仅用 `setCenter` / `getMap` / `destroy`，本次未改这些方法，无回归。
  - 唯一细微变化：百度/腾讯 SDK 的 `init` center 不再转换，而 `MerchantMapView` 传入的是 WGS84 天安门（`[39.9042, 116.4074]`），改后初始中心会有轻微偏移；但该 center 随即被 `fitAllMerchants()` 覆盖，不影响商家标记位置（标记用 `displayCoord` 已转换坐标），实际无感知影响。

## 涉及文件

- `frontend/src/utils/map/engines/AMapSDKEngine.ts`
- `frontend/src/utils/map/engines/BaiduSDKEngine.ts`
- `frontend/src/utils/map/engines/TencentSDKEngine.ts`

## 验证

- `npm run build` 通过（9.68s），三个 SDK 引擎正常打包。
- 白盒推演确认：click → convertToWGS84 → addMarker 全链路坐标系自洽，标记位置与点击位置一致。

## 未处理的相邻问题（非本次范围，记录备查）

- 三个 SDK 引擎的 `on('click')` 方法仍重复绑定一次 map click（init 内绑一次 + on 内绑一次），导致单次点击回调触发两次（视觉无差异，仅多余一次 setMarker）。Leaflet 引擎同样如此，属既有结构问题，未在本次处理。
- `MerchantMapView.fitAllMerchants` 在 SDK 分支用 `currentEngine.setCenter(firstMerchant.latitude, firstMerchant.longitude)` 传 WGS84（应为地图坐标系坐标），既有偏移 bug，非本次引入。
