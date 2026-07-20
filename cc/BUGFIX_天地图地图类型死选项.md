# 天地图「地图类型」死选项清理

## 问题
后台「地图配置」页天地图折叠面板里有个「地图类型」下拉（矢量/影像/地形），但切换后地图毫无变化——是个误导用户的死选项。

## 根因
trace 全链路确认 `config.map_api_keys.tianditu.type`（vec/img/ter）**无人消费**：
- [TiandituEngine.ts:34](frontend/src/utils/map/engines/TiandituEngine.ts#L34) 硬编码 `L.tileLayer.chinaProvider('TianDiTu.Normal.Map', { key: token })` 矢量底图 + [:42](frontend/src/utils/map/engines/TiandituEngine.ts#L42) `Normal.Annotion` 注记层，只读 `token` 不读 `type`
- [mapAdapters.ts:101](frontend/src/utils/mapAdapters.ts#L101) 另一套适配器也写死 `Tianditu.Normal.Map`
- 无论 UI 选 vec/img/ter，引擎永远加载矢量 Normal.Map

## 修复
KISS + YAGNI，只删 UI 不动数据链路：[MapSettingsView.vue:159](frontend/src/views/admin/MapSettingsView.vue#L159) 天地图折叠面板里的「地图类型」`v-select` 删除，加一行 HTML 注释说明引擎固定矢量层故不暴露。

**保留 `config.map_api_keys.tianditu.type` 默认值 `'vec'` 不动**（reactive 默认值 [:331](frontend/src/views/admin/MapSettingsView.vue#L331) + `MapApiKeys` 接口 [:282](frontend/src/views/admin/MapSettingsView.vue#L282) + [mapTypes.ts:19](frontend/src/utils/map/mapTypes.ts#L19)）。理由：
- 引擎不看 type，删 UI 零行为变化
- config 结构不变 → TS 类型不报错、保存 payload 仍含 type、后端透传无感、向后兼容
- 不扩大到接口定义/后端 schema，改动收在单文件 template

## 验证
- 前端 build 通过（precache 128 entries 不变）
- 无表结构变更，单文件 template 改动（-11 行 v-select + 1 行注释）

## 教训
「配了却不生效」的 UI 选项要 trace 到消费端确认是真死选项再删（避免误删看似无用实则被某分支读取的字段）；删 UI 时若底层字段保留代价更低（结构兼容），不必强行连带删字段——YAGNI，用户只要求去选项。将来若要真支持天地图图层切换，恢复 UI + 让引擎读 type 即可，字段链路还在。
