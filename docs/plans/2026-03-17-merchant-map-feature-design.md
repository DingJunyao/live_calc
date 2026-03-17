# 商家管理地图功能设计文档

**日期：** 2026-03-17
**目标：** 为商家管理添加地图功能，支持通过点击地图选择经纬度，并通过反向地理编码将地址转换为坐标

---

## 1. 整体架构

### 1.1 功能概述

- **地图选择坐标：** 在商家添加/编辑表单中嵌入地图，用户点击或拖拽选择位置
- **多地图引擎支持：** 高德、百度、腾讯、天地图、OpenStreetMap
- **反向地理编码：** 通过地址搜索获取坐标
- **用户偏好：** 保存用户的地图选择偏好到 localStorage
- **全局配置：** 管理员可配置可用的地图服务和 API Key

### 1.2 地图切换优先级

```
用户 localStorage 偏好 (优先)
    ↓ 偏好不在全局可用列表或不存在
全局默认地图
```

---

## 2. 数据模型

### 2.1 地图配置数据结构

```typescript
// 全局地图配置
interface MapConfig {
  // 可显示的地图列表
  availableMaps: string[];  // ['amap', 'baidu', 'tencent', 'tianditu', 'osm']

  // 默认地图
  defaultMap: string;  // 'amap'

  // 地图 API Keys（地图展示）
  mapApiKeys: {
    amap?: string;        // 高德地图 Web 服务 Key
    baidu?: string;       // 百度地图 AK
    tencent?: string;     // 腾讯地图 Key
    tianditu: {          // 天地图（必填）
      token: string;      // tk
      type: 'vec' | 'img'; // 矢量图/影像图
    };
    osm?: never;         // OpenStreetMap 无需 Key
  };

  // 反向地理编码配置
  geocoding: {
    enabledService: 'amap' | 'baidu' | 'tencent' | 'nominatim';
    apiKeys: {
      amap?: string;      // 高德地理编码 Key
      baidu?: string;     // 百度地理编码 AK
      tencent?: string;    // 腾讯地理编码 Key
    };
    nominatimUrl: string; // 自部署的 Nominatim 服务器 URL
  };
}
```

### 2.2 用户偏好数据结构

```typescript
// localStorage 键名: livecalc:mapPreference
interface UserMapPreference {
  currentMap: string;           // 当前选择的地图引擎
  configs: {
    [key: string]: {
      // 保存用户在该地图上的个性化设置（如缩放级别、中心点等）
      zoom?: number;
      center?: [number, number];
    }
  };
  lastUpdated: string;           // ISO 8601 时间戳
}
```

### 2.3 商家数据模型扩展

```python
# 后端已有 Merchant 模型，确保包含：
class Merchant(Base):
    name = Column(String, nullable=False)
    address = Column(String)
    latitude = Column(Float)  # 经度
    longitude = Column(Float)  # 纬度
    # ... 其他字段
```

---

## 3. 前端组件设计

### 3.1 组件层次结构

```
AdminPanel
└── MapSettings (新建)          # 地图设置页面

MerchantMap
├── MerchantForm
│   └── MapPicker (新建)         # 通用地图选择器组件
│       ├── MapEngineSwitcher    # 地图引擎切换按钮组
│       ├── AddressSearchBar      # 地址搜索栏
│       ├── MapContainer         # 地图容器
│       │   └── [AMapEngine | BaiduEngine | ...]
│       └── CoordinateDisplay    # 坐标显示
```

### 3.2 MapPicker 通用组件

**Props:**
```typescript
interface MapPickerProps {
  modelValue?: { lat: number; lng: number };  // v-model 坐标
  height?: string;                           // 地图高度，默认 '300px'
  readonly?: boolean;                       // 只读模式
  showSearch?: boolean;                      // 是否显示地址搜索
  showSwitcher?: boolean;                    // 是否显示地图切换按钮
}
```

**Emits:**
```typescript
interface MapPickerEmits {
  'update:modelValue': { lat: number; lng: number };
  'addressSelected': { address: string; lat: number; lng: number };
}
```

**交互逻辑：**
1. 有初始坐标 → 显示标记，支持拖拽
2. 点击地图 → 更新标记位置
3. 输入地址 + 搜索 → 定位到第一个结果并设置标记
4. 拖拽标记 → 实时更新坐标显示

### 3.3 地图引擎适配器

每个地图服务实现统一的 `MapEngine` 接口：

```typescript
interface MapEngine {
  name: string;
  displayName: string;

  // 初始化地图
  init(container: HTMLElement, options: MapOptions): void;

  // 设置中心点
  setCenter(lat: number, lng: number): void;

  // 添加标记
  addMarker(lat: number, lng: number, options?: MarkerOptions): Marker;

  // 地址搜索（反向地理编码）
  searchAddress(query: string): Promise<SearchResult[]>;

  // 地址解析（地理编码）
  geocode(address: string): Promise<GeocodeResult>;

  // 销毁
  destroy(): void;
}
```

### 3.4 MapSettings 页面

**配置项：**

| 配置分组 | 配置项 | 说明 |
|---------|-------|------|
| 可用地图 | 多选框 | 高德、百度、腾讯、天地图、OSM |
| 默认地图 | 单选框 | 从可用地图中选择 |
| 高德地图 API Key | 输入框 | Web 服务 Key |
| 百度地图 AK | 输入框 | 浏览器端 AK |
| 腾讯地图 Key | 输入框 | Key |
| 天地图 Token | 输入框 | 必填 |
| 反向地理编码服务 | 单选框 | 高德/百度/腾讯/Nominatim |
| Nominatim URL | 输入框 | 自部署服务地址 |

---

## 4. 后端 API 设计

### 4.1 新增 API 端点

```python
# 地图配置管理
GET    /api/v1/admin/map-config          # 获取地图配置
PUT    /api/v1/admin/map-config          # 更新地图配置
```

### 4.2 API 数据结构

```python
class MapConfigResponse(BaseModel):
    available_maps: List[str] = ["amap", "baidu", "tencent", "tianditu", "osm"]
    default_map: str = "amap"
    map_api_keys: Dict[str, Optional[str]]
    geocoding: GeocodingConfig

class GeocodingConfig(BaseModel):
    enabled_service: str = "amap"
    api_keys: Dict[str, Optional[str]]
    nominatim_url: str = ""
```

### 4.3 配置存储

地图配置存储在后端数据库或配置文件中（建议使用数据库，方便管理）：

```python
class MapConfig(Base):
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)  # 配置键名
    value = Column(Text)  # JSON 格式的配置值
    updated_at = Column(DateTime, default=datetime.utcnow)
```

---

## 5. 地图服务集成

### 5.1 地图展示方案

| 地图服务 | 有 API Key 方案 | 无 API Key 方案 |
|---------|---------------|---------------|
| 高德地图 | 高德官方 API | Leaflet + leaflet.chinatmsproviders 插件 |
| 百度地图 | 百度官方 API | Leaflet + leaflet.chinatmsproviders 插件 |
| 腾讯地图 | 腾讯官方 API | Leaflet + leaflet.chinatmsproviders 插件 |
| 天地图 | 天地图官方 API | 不支持（必须配置 Key） |
| OpenStreetMap | - | Leaflet 原生 OSM 瓦片 |

### 5.2 反向地理编码方案

| 地图服务 | API 端点 | 需要 Key |
|---------|---------|---------|
| 高德地图 | `https://restapi.amap.com/v3/geocode/geo` | 是 |
| 百度地图 | `https://api.map.baidu.com/geocoding/v3/` | 是 |
| 腾讯地图 | `https://apis.map.qq.com/ws/geocoder/v1/` | 是 |
| Nominatim | `{自定义URL}/search` | 否（需自部署） |

### 5.3 地图引擎实现清单

**需要实现的引擎类：**

1. `AMapEngine` - 高德地图（官方 API + Leaflet 瓦片）
2. `BaiduMapEngine` - 百度地图（官方 API + Leaflet 瓦片）
3. `TencentMapEngine` - 腾讯地图（官方 API + Leaflet 瓦片）
4. `TiandituEngine` - 天地图（官方 API）
5. `OSMEngine` - OpenStreetMap（Leaflet 原生）

### 5.4 Leaflet 插件依赖

```json
{
  "leaflet": "^1.9.4",
  "leaflet.chinatmsproviders": "^3.2.2"
}
```

---

## 6. 用户界面设计

### 6.1 商家表单中的地图区域

```
┌─────────────────────────────────────────────────────────┐
│ 添加/编辑商家                                      │
├─────────────────────────────────────────────────────────┤
│ 商家名称: [___________________]                     │
│ 地址:     [___________________] [搜索地址]            │
├─────────────────────────────────────────────────────────┤
│ 地图位置:                                          │
│                                                     │
│  [高德] [百度] [腾讯] [天地图] [OSM]  ← 切换按钮    │
│                                                     │
│  ┌─────────────────────────────────────────────────┐  │
│  │                                             │  │
│  │                   (地图区域)                  │  │
│  │                                             │  │
│  │                    📍                        │  │
│  │                                             │  │
│  └─────────────────────────────────────────────────┘  │
│                                                     │
│ 经纬度: 31.2304, 121.4737                          │
└─────────────────────────────────────────────────────────┘
```

### 6.2 地图设置页面

```
┌─────────────────────────────────────────────────────────┐
│ 后台管理 > 地图设置                                  │
├─────────────────────────────────────────────────────────┤
│                                                     │
│ 可用地图:                                           │
│ ☑ 高德地图  ☑ 百度地图  ☑ 腾讯地图                │
│ ☑ 天地图    ☑ OpenStreetMap                         │
│                                                     │
│ 默认地图:  ○ 高德地图 ● 高德地图 (默认)             │
│             ○ 百度地图                               │
│                                                     │
│ ────────────────────────────────────────────────────    │
│                                                     │
│ API 配置:                                           │
│                                                     │
│ 高德地图 Web 服务 Key:  [___________________]           │
│ 百度地图 AK:             [___________________]           │
│ 腾讯地图 Key:            [___________________]           │
│ 天地图 Token (必填):      [___________________]           │
│                                                     │
│ ────────────────────────────────────────────────────    │
│                                                     │
│ 反向地理编码:                                       │
│                                                     │
│ 启用的服务:  ● 高德地图                              │
│             ○ 百度地图                               │
│             ○ 腾讯地图                               │
│             ○ Nominatim                              │
│                                                     │
│ Nominatim 服务器 URL:  [___________________]           │
│                                                     │
│ ────────────────────────────────────────────────────    │
│                                                     │
│                          [保存配置]                  │
│                                                     │
└─────────────────────────────────────────────────────────┘
```

---

## 7. 实施计划

### 阶段 1：基础架构搭建

1. 创建 `MapPicker` 通用组件框架
2. 定义 `MapEngine` 接口
3. 创建地图引擎管理器
4. 实现 localStorage 偏好管理

### 阶段 2：地图引擎实现

1. 实现 `OSMEngine`（最简单，先验证框架）
2. 实现高德地图引擎（官方 API + Leaflet 瓦片）
3. 实现百度地图引擎
4. 实现腾讯地图引擎
5. 实现天地图引擎

### 阶段 3：反向地理编码

1. 实现各服务的地址搜索 API 调用
2. 集成 Nominatim 服务
3. 实现搜索结果解析和定位

### 阶段 4：后端 API

1. 创建 `map_config` 数据表/配置项
2. 实现 `/api/v1/admin/map-config` 端点
3. 添加管理员权限验证

### 阶段 5：管理界面

1. 创建 `MapSettings.vue` 页面
2. 实现配置表单
3. 集成配置保存和验证

### 阶段 6：商家表单集成

1. 修改 `MerchantMap.vue` 或商家相关表单
2. 集成 `MapPicker` 组件
3. 连接表单提交与坐标数据

### 阶段 7：测试与优化

1. 各地图引擎功能测试
2. 反向地理编码准确性测试
3. 移动端兼容性测试
4. 性能优化

---

## 8. 技术依赖

### 前端依赖

```json
{
  "leaflet": "^1.9.4",
  "leaflet.chinatmsproviders": "^3.2.2",
  "@types/leaflet": "^1.9.8"
}
```

### 参考仓库

- https://github.com/DingJunyao/vibe_route （地图设置相关实现）

---

## 9. 注意事项

1. **天地图必须配置 Key**，否则无法显示地图
2. **反向地理编码需要独立的 API Key**，与地图展示的 Key 可能不同
3. **Nominatim 需要自部署**，官方服务器有请求频率限制
4. **百度地图使用 BD09 坐标系**，需要与 WGS84 转换
5. **高德地图使用 GCJ02 坐标系**，需要与 WGS84 转换
6. **Leaflet 默认使用 WGS84**，其他地图引擎需要注意坐标系转换

---

**文档版本：** v1.0
**最后更新：** 2026-03-17
