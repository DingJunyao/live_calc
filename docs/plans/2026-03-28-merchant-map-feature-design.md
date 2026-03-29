# 商家管理地图功能设计

**日期**: 2026-03-28
**状态**: 设计阶段
**优先级**: 高

## 概述

为商家管理页面添加地图功能，在列表页面展示商家位置，在编辑对话框中支持点击地图选择坐标。需要兼容高德地图、百度地图、腾讯地图、天地图、OpenStreetMap 等多种地图引擎。

## 功能需求

### 1. 商家列表地图展示
- 桌面端：地图在页面右边，占 2/3 区域
- 移动端：地图在页面下方，占 1/2 区域
- 显示所有商家的位置标记
- 点击列表项时高亮对应商家
- 点击地图标记时高亮对应列表项

### 2. 对话框地图选点
- 在添加/编辑商家对话框中嵌入地图
- 对话框宽度 500px，地图高度 300px（紧凑尺寸）
- 点击地图获取坐标
- 坐标显示为只读，不允许手动输入
- 实时显示选中的坐标值

### 3. 地图引擎兼容性
- 高德地图：有 API Key 时用自有 SDK，否则用 Leaflet
- 百度地图：有 API Key 时用自有 SDK，否则用 Leaflet
- 腾讯地图：有 API Key 时用自有 SDK，否则用 Leaflet
- 天地图：仅使用 Leaflet
- OpenStreetMap：仅使用 Leaflet

## 技术架构

### 组件结构

```
frontend/src/
├── components/
│   └── map/
│       ├── MerchantMapView.vue      # 商家地图视图
│       ├── MapPicker.vue            # 地图选点组件
│       └── MapMarker.vue            # 地图标记组件（可选）
├── composables/
│   └── useMapEngine.ts              # 地图引擎 composable
├── utils/
│   ├── mapAdapters.ts               # 地图引擎适配器
│   └── coordTransform.ts            # 坐标转换工具
└── types/
    └── map.ts                       # 地图相关类型定义
```

### 核心组件

#### MerchantMapView.vue
- **职责**: 商家列表页面的地图展示
- **Props**: `merchants: Merchant[]`, `selectedMerchant?: Merchant`
- **功能**:
  - 渲染所有商家位置标记
  - 高亮选中商家
  - 响应式布局适配
  - 标记聚合（商家数量 > 20）

#### MapPicker.vue
- **职责**: 对话框中的坐标选择
- **Props**: `initialCoords?: { lat, lng }`
- **Emits**: `update:coords: { lat, lng }`
- **功能**:
  - 点击地图获取坐标
  - 显示当前选中坐标
  - 临时标记反馈

#### useMapEngine.ts (Composable)
- **职责**: 地图引擎初始化和管理
- **返回**:
  - `mapInstance` - 地图实例
  - `currentEngine` - 当前引擎
  - `isLoading` - 加载状态
  - `initMap()` - 初始化地图
  - `addMarker()` - 添加标记
  - `removeMarker()` - 移除标记
  - `highlightMarker()` - 高亮标记

### 数据流

```
MerchantsView (父组件)
    ↓
    ├── 商家列表 → MerchantListView
    │       └── 点击 → selectedMerchant 变更
    │
    └── 地图展示 → MerchantMapView
            └── 监听 selectedMerchant → 高亮标记
```

### 地图引擎适配器

```typescript
interface MapAdapter {
  init(container: HTMLElement, options: MapOptions): Promise<MapInstance>
  addMarker(position: LatLng, options?: MarkerOptions): Marker
  removeMarker(marker: Marker): void
  setCenter(position: LatLng): void
  setZoom(level: number): void
  on(event: string, handler: Function): void
  destroy(): void
}
```

**适配器实现**:
- `LeafletAdapter`: 基于 Leaflet 统一封装
- `SDKAdapter`: 封装高德/百度/腾讯自有 SDK
- `MapAdapterFactory`: 根据配置创建适配器

### 坐标系转换

| 地图引擎 | 坐标系 | 转换需求 |
|---------|--------|---------|
| 高德地图 | GCJ-02 | ↔ WGS-84 |
| 百度地图 | BD-09 | ↔ GCJ-02 |
| 腾讯地图 | GCJ-02 | ↔ WGS-84 |
| 天地图 | WGS-84 | - |
| OSM | WGS-84 | - |

## 实施步骤

### Phase 1: 基础架构 (1-2天)
- [ ] 创建目录结构
- [ ] 实现 LeafletAdapter
- [ ] 实现 MapAdapterFactory
- [ ] 实现坐标转换工具

### Phase 2: 核心组件 (3-4天)
- [ ] 实现 useMapEngine composable
- [ ] 实现 MapPicker.vue
- [ ] 修改商家表单对话框集成选点

### Phase 3: 商家地图视图 (5-6天)
- [ ] 实现 MerchantMapView.vue
- [ ] 修改 MerchantsView.vue 布局
- [ ] 实现列表-地图联动

### Phase 4: SDK 集成 (7-8天)
- [ ] 实现 SDKAdapter
- [ ] 集成高德/百度/腾讯 SDK
- [ ] 实现动态加载和降级机制

### Phase 5: 优化与测试 (9-10天)
- [ ] 性能优化（聚合、懒加载）
- [ ] 错误处理和边界情况
- [ ] 响应式优化
- [ ] 完整测试

## 技术要点

### 响应式布局

```scss
// 桌面端：v-col cols="12" md="8"
// 移动端：占 50vh 高度
.map-wrapper {
  height: 100%;
  &.mobile-layout {
    height: 50vh;
  }
}
```

### SDK 动态加载

```typescript
const loadSDKScript = (engine: string, apiKey: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    const scriptUrls = {
      amap: `https://webapi.amap.com/maps?v=2.0&key=${apiKey}`,
      baidu: `https://api.map.baidu.com/api?v=3.0&ak=${apiKey}`,
      tencent: `https://map.qq.com/api/gljs?v=1.exp&key=${apiKey}`
    }
    // 创建 script 标签并监听加载完成
  })
}
```

### 降级机制

```typescript
const getMapEngine = async (engine: string) => {
  const config = await api.get('/admin/map-config')
  const hasApiKey = !!config.map_api_keys[engine]

  if (['amap', 'baidu', 'tencent'].includes(engine) && hasApiKey) {
    try {
      await loadSDKScript(engine, config.map_api_keys[engine])
      return new SDKAdapter(engine)
    } catch {
      console.warn('SDK 加载失败，降级到 Leaflet')
    }
  }

  return new LeafletAdapter(engine)
}
```

## 测试策略

### 功能测试
- [ ] 商家列表地图正确显示所有标记
- [ ] 点击列表项地图高亮对应商家
- [ ] 点击地图标记列表项高亮
- [ ] 对话框点击地图正确获取坐标
- [ ] 保存商家后地图标记更新
- [ ] 删除商家后地图标记移除

### 兼容性测试
- [ ] 高德地图（SDK + Leaflet）
- [ ] 百度地图（SDK + Leaflet）
- [ ] 腾讯地图（SDK + Leaflet）
- [ ] 天地图（Leaflet）
- [ ] OSM（Leaflet）

### 响应式测试
- [ ] 桌面端布局（>960px）
- [ ] 平板端布局（600px-960px）
- [ ] 移动端布局（<600px）
- [ ] 横竖屏切换

### 浏览器测试
- [ ] Chrome / Edge
- [ ] Firefox
- [ ] Safari (iOS)
- [ ] Chrome (Android)

## 后续优化

### 性能优化
- 标记聚合（Leaflet.markercluster）
- 懒加载 SDK
- 虚拟滚动（大量商家）
- 地图缓存

### 功能扩展
- 商家搜索（地图周边）
- 路线规划
- 商家分类标记
- 热力图
- 地图样式自定义

## 参考资源

- [Leaflet 文档](https://leafletjs.com/)
- [leaflet.chinatmsproviders](https://github.com/htoooth/Leaflet.ChineseTmsProviders)
- [高德地图 API](https://lbs.amap.com/api/jsapi-v2/summary)
- [百度地图 API](https://lbsyun.baidu.com/index.php?title=jspopular3.0)
- [腾讯地图 API](https://lbs.qq.com/webApi/javascriptGL/glGuide/glBasic)
