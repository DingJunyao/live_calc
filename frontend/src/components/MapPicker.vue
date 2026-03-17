<template>
  <div class="map-picker">
    <!-- 地图切换按钮 -->
    <div v-if="showSwitcher && availableMaps.length > 1" class="map-switcher">
      <button
        type="button"
        v-for="map in availableMaps"
        :key="map"
        :class="['map-btn', { active: currentMap === map }]"
        @click="switchMap(map)"
      >
        {{ mapEngineNames[map] }}
      </button>
    </div>

    <!-- 地址搜索栏 -->
    <div v-if="showSearch" class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="输入地址搜索..."
        class="search-input"
        @keyup.enter="searchAddress"
      />
      <button @click="searchAddress" class="search-btn" :disabled="!searchQuery.trim()">
        搜索地址
      </button>
    </div>

    <!-- 搜索结果列表 -->
    <div v-if="searchResults.length > 0" class="search-results">
      <div
        v-for="(result, index) in searchResults"
        :key="index"
        class="search-result-item"
        @click="selectSearchResult(result)"
      >
        <span class="result-name">{{ result.name || result.address }}</span>
        <span class="result-address">{{ result.address }}</span>
      </div>
    </div>

    <!-- 地图容器 -->
    <div
      ref="mapContainer"
      class="map-container"
      :style="{ height: height }"
    ></div>

    <!-- 坐标显示 -->
    <div class="coordinate-display">
      <span v-if="currentCoordinate">
        纬度: {{ currentCoordinate.lat.toFixed(6) }}, 经度: {{ currentCoordinate.lng.toFixed(6) }}
      </span>
      <span v-else class="no-coordinate">点击地图选择位置</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue';
import type { MapEngineType, Coordinate, SearchResult as SearchResultType, MapConfig } from '@/utils/mapTypes';
import { mapEngineNames, defaultMapConfig } from '@/utils/mapTypes';
import { mapEngineManager } from '@/utils/mapEngineManager';
import { getCurrentMapEngine, getUserMapPreference } from '@/utils/mapConfig';

// Props
interface Props {
  modelValue?: Coordinate;
  height?: string;
  readonly?: boolean;
  showSearch?: boolean;
  showSwitcher?: boolean;
  availableMapsProp?: MapEngineType[];
  defaultMapProp?: MapEngineType;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => ({ lat: 39.9042, lng: 116.4074 }),
  height: '300px',
  readonly: false,
  showSearch: true,
  showSwitcher: true,
  availableMapsProp: () => ['amap', 'baidu', 'tencent', 'tianditu', 'osm'],
  defaultMapProp: 'amap'
});

// Emits
const emit = defineEmits<{
  'update:modelValue': [coordinate: Coordinate];
  'addressSelected': [result: { address: string; lat: number; lng: number }];
  'mapChange': [mapEngine: MapEngineType];
}>();

// 响应式数据
const mapContainer = ref<HTMLElement | null>(null);
const currentMap = ref<MapEngineType>('amap');
const currentCoordinate = ref<Coordinate | null>(null);
const searchQuery = ref('');
const searchResults = ref<SearchResultType[]>([]);
const searchLoading = ref(false);
const availableMaps = ref<MapEngineType[]>(props.availableMapsProp);

// 标记引用
let markerId: any = null;
let currentEngine: any = null;

// 初始化
onMounted(async () => {
  // 获取用户偏好
  const preference = getUserMapPreference();
  const userMap = preference?.currentMap;

  // 确定使用的地图
  if (userMap && availableMaps.value.includes(userMap)) {
    currentMap.value = userMap;
  } else {
    currentMap.value = props.defaultMapProp;
  }

  // 初始化地图
  await initMap();

  // 如果有初始坐标，显示标记
  if (props.modelValue && props.modelValue.lat && props.modelValue.lng) {
    setMarker(props.modelValue);
  }
});

// 卸载时销毁
onUnmounted(() => {
  mapEngineManager.destroy();
});

// 初始化地图
async function initMap() {
  if (!mapContainer.value) return;

  // 创建配置
  const config: MapConfig = {
    ...defaultMapConfig,
    availableMaps: availableMaps.value,
    defaultMap: currentMap.value,
    mapApiKeys: {}
  };

  mapEngineManager.setConfig(config);

  // 加载引擎
  currentEngine = await mapEngineManager.loadEngine(
    currentMap.value,
    mapContainer.value,
    {
      center: props.modelValue ? [props.modelValue.lat, props.modelValue.lng] : [39.9042, 116.4074],
      zoom: 13,
      enableClick: !props.readonly,
      enableDrag: !props.readonly
    }
  );

  // 绑定事件
  currentEngine.on('click', handleMapClick);
  currentEngine.on('markerDragend', handleMarkerDrag);
}

// 切换地图
async function switchMap(mapType: MapEngineType) {
  if (mapType === currentMap.value || !mapContainer.value) return;

  currentMap.value = mapType;

  // 保持当前坐标
  const currentCoord = currentCoordinate.value || props.modelValue;

  // 重新初始化地图
  await initMap();

  // 恢复标记
  if (currentCoord && currentCoord.lat && currentCoord.lng) {
    setMarker(currentCoord);
  }

  // 触发地图切换事件
  emit('mapChange', mapType);
}

// 处理地图点击
function handleMapClick(data: { lat: number; lng: number }) {
  if (props.readonly) return;

  setMarker({ lat: data.lat, lng: data.lng });
  emit('update:modelValue', { lat: data.lat, lng: data.lng });
}

// 处理标记拖拽
function handleMarkerDrag(data: { lat: number; lng: number }) {
  if (props.readonly) return;

  currentCoordinate.value = { lat: data.lat, lng: data.lng };
  emit('update:modelValue', { lat: data.lat, lng: data.lng });
}

// 设置标记
function setMarker(coord: Coordinate) {
  if (!currentEngine || !currentEngine.getMap()) return;

  // 移除旧标记
  if (markerId) {
    currentEngine.removeMarker(markerId);
  }

  // 添加新标记
  markerId = currentEngine.addMarker(coord.lat, coord.lng, {
    draggable: !props.readonly
  });

  // 更新坐标显示
  currentCoordinate.value = coord;
}

// 搜索地址
async function searchAddress() {
  if (!searchQuery.value.trim() || !currentEngine) return;

  searchLoading.value = true;
  searchResults.value = [];

  try {
    const results = await currentEngine.searchAddress(searchQuery.value);
    searchResults.value = results;
  } catch (error) {
    console.error('Search error:', error);
  } finally {
    searchLoading.value = false;
  }
}

// 选择搜索结果
function selectSearchResult(result: SearchResultType) {
  // 设置地图中心
  currentEngine.setCenter(result.lat, result.lng);

  // 设置标记
  setMarker({ lat: result.lat, lng: result.lng });

  // 触发事件
  emit('update:modelValue', { lat: result.lat, lng: result.lng });
  emit('addressSelected', {
    address: result.address,
    lat: result.lat,
    lng: result.lng
  });

  // 清除搜索结果
  searchResults.value = [];
  searchQuery.value = '';
}

// 监听 v-model 变化
watch(() => props.modelValue, (newVal) => {
  if (newVal && newVal.lat && newVal.lng) {
    if (!currentCoordinate.value ||
        currentCoordinate.value.lat !== newVal.lat ||
        currentCoordinate.value.lng !== newVal.lng) {
      setMarker(newVal);
    }
  }
}, { deep: true });
</script>

<style scoped>
.map-picker {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.map-switcher {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.map-btn {
  padding: 0.375rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
  background: #fff;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.map-btn:hover {
  background: #f5f5f5;
}

.map-btn.active {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.search-bar {
  display: flex;
  gap: 0.5rem;
}

.search-input {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.search-btn {
  padding: 0.5rem 1rem;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  font-size: 0.875rem;
}

.search-btn:hover:not(:disabled) {
  background: #5a6fd8;
}

.search-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.search-results {
  max-height: 150px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 0.25rem;
}

.search-result-item {
  padding: 0.5rem;
  cursor: pointer;
  border-bottom: 1px solid #eee;
}

.search-result-item:last-child {
  border-bottom: none;
}

.search-result-item:hover {
  background: #f5f5f5;
}

.result-name {
  display: block;
  font-weight: 500;
  color: #333;
  font-size: 0.875rem;
}

.result-address {
  display: block;
  color: #666;
  font-size: 0.75rem;
}

.map-container {
  width: 100%;
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid #ddd;
}

.coordinate-display {
  padding: 0.5rem;
  background: #f5f5f5;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: #666;
  text-align: center;
}

.no-coordinate {
  color: #999;
}

/* 移动端优化 */
@media (max-width: 768px) {
  .map-btn {
    padding: 0.25rem 0.5rem;
    font-size: 0.8125rem;
  }

  .search-bar {
    flex-direction: column;
  }

  .search-btn {
    width: 100%;
  }
}
</style>