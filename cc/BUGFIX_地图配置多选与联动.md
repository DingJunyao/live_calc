# 地图配置：启用服务多选失效 + 默认地图不联动 + 保存 422

## 症状

后台管理「地图配置」页（[MapSettingsView.vue](frontend/src/views/admin/MapSettingsView.vue)）三个连锁问题：

1. **启用的地图服务没法多选**：chip-group 点一个之后，再点其它只是换值，永远单选。
2. **默认地图下拉不联动**：「默认地图」下拉项固定是全部 5 个地图，不随「启用的地图服务」变化；启用的服务里移除当前默认地图后，下拉仍保留那个孤儿值。
3. **保存报 422**：
   ```
   PUT /api/v1/admin/map-config
   body.available_maps: Input should be a valid list (type: list_type)
   请求体: {"available_maps": "amap", ...}   ← 传了字符串而非数组
   ```

## 根因

全在前端 [MapSettingsView.vue](frontend/src/views/admin/MapSettingsView.vue)，后端 schema 没问题（[admin.py:46](backend/app/api/admin.py#L46) `available_maps: List[str]`）。

### 问题 1 + 3 同根因：v-chip-group 漏 multiple

[MapSettingsView.vue:38](frontend/src/views/admin/MapSettingsView.vue#L38)：

```vue
<v-chip-group v-model="config.available_maps" column>
```

Vuetify 3 的 `v-chip-group` **默认是单选**，v-model 是单值。选中一个 chip 会把 `config.available_maps`（本该是 `string[]`）整个替换成该 chip 的 value 字符串。所以点「高德」→ `available_maps` 变成 `"amap"`（字符串）→ 保存时后端 `List[str]` 拒收 → 422 `list_type`。

迷惑点：`:color="config.available_maps.includes(map.value)"` ——字符串也有 `.includes()`，`'amap'.includes('amap')` 为 true，所以视觉选中态还在，更难发现。这正是「看着选中却没法多选」的真相。

### 问题 2：默认地图下拉写死全部

[MapSettingsView.vue:327](frontend/src/views/admin/MapSettingsView.vue#L327) `availableMaps = ref(allMaps)` 是固定的全部 5 个地图，没跟启用列表挂钩，`default_map` 也没有自动回退逻辑。

注：库里数据没被污染——422 把请求挡在了门外，`map_configurations.available_maps` 始终是合法数组。

## 修复

单文件 4 处改动，后端零动。

1. **多选**：v-chip-group 加 `multiple` 属性，v-model 恢复为数组语义。
2. **联动**：`availableMaps` 改 `computed`，按 `config.available_maps` 过滤 `allMaps`。
3. **自动回退**：抽 `ensureDefaultMapValid()`（默认地图不在启用列表时回退首个），`watch(() => [...config.available_maps], ...)` 在启用列表变化时触发；`fetchConfig` 拉取后也调一次兜底库里脏数据。
4. import 补 `computed, watch`。

`watch` 用 `() => [...config.available_maps]` 而非直接监听属性，防御 Vuetify 内部 mutate 数组（替换/增删都能捕获）。

## 验证

- 前端 build 通过（37.95s，PWA precache 128 entries 不变）。
- 后端无改动，无需 py_compile。
- 待手动核验（开发者）：① 多选/取消 chip 正确增删；② 移除当前默认地图后下拉自动回退首个；③ 保存返回 200、刷新后配置持久。

## 教训

Vuetify 3 `v-chip-group` 默认单选是经典坑——v-model 被替成单值后，凡是「数组方法」兜底（如字符串也有的 `.includes`）会让 UI 选中态看着正常、却悄悄把数组类型改了，前端 TypeScript 类型在 reactive 下挡不住运行时赋值。多选场景永远记得 `multiple`。
