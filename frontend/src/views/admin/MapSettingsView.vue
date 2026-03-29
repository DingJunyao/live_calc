<template>
  <!-- 顶部导航栏 - 移到 container 外面以便固定 -->
  <v-app-bar elevation="0" color="background" density="comfortable" fixed>
    <v-app-bar-nav-icon @click="toggleSidebar(isDesktop)" />
    <v-btn icon="mdi-arrow-left" variant="text" @click="goBack" />
    <v-app-bar-title class="text-h6">地图配置</v-app-bar-title>
    <template #append>
      <v-btn color="primary" variant="tonal" :loading="saving" @click="saveConfig">
        <v-icon start>mdi-content-save</v-icon>
        保存配置
      </v-btn>
    </template>
  </v-app-bar>

  <v-container class="pa-4">

    <v-row>
      <!-- 可用地图 -->
      <v-col cols="12" md="6">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2">mdi-map</v-icon>
            <span>可用地图</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-4">
            <v-select
              v-model="config.default_map"
              :items="availableMaps"
              label="默认地图"
              variant="outlined"
              prepend-icon="mdi-star"
              hint="默认使用的地图服务"
              persistent-hint
            />
            <v-divider class="my-4" />
            <div class="text-caption text-medium-emphasis mb-2">启用的地图服务</div>
            <v-chip-group v-model="config.available_maps" column>
              <v-chip
                v-for="map in allMaps"
                :key="map.value"
                :value="map.value"
                filter
                :color="config.available_maps.includes(map.value) ? 'primary' : undefined"
              >
                <v-icon start>{{ map.icon }}</v-icon>
                {{ map.title }}
              </v-chip>
            </v-chip-group>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- API 密钥配置 -->
      <v-col cols="12" md="6">
        <v-card class="rounded-lg h-100">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2">mdi-key</v-icon>
            <span>API 密钥配置</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-4">
            <v-expansion-panels variant="accordion">
              <!-- 高德地图 -->
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="success">mdi-map-marker</v-icon>
                  高德地图
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-text-field
                    v-model="config.map_api_keys.amap"
                    label="API Key"
                    variant="outlined"
                    type="password"
                    persistent-placeholder
                    placeholder="留空则使用默认密钥"
                  />
                  <v-text-field
                    v-model="config.map_api_keys.amap_security"
                    label="安全密钥 (JSAPI)"
                    variant="outlined"
                    type="password"
                    persistent-placeholder
                    class="mt-2"
                    hint="用于 Web 端调用的安全密钥"
                  />
                </v-expansion-panel-text>
              </v-expansion-panel>

              <!-- 百度地图 -->
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="primary">mdi-map-marker-radius</v-icon>
                  百度地图
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-text-field
                    v-model="config.map_api_keys.baidu"
                    label="API Key (AK)"
                    variant="outlined"
                    type="password"
                    persistent-placeholder
                    placeholder="留空则使用默认密钥"
                  />
                </v-expansion-panel-text>
              </v-expansion-panel>

              <!-- 腾讯地图 -->
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="info">mdi-map-marker-plus</v-icon>
                  腾讯地图
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-text-field
                    v-model="config.map_api_keys.tencent"
                    label="API Key"
                    variant="outlined"
                    type="password"
                    persistent-placeholder
                    placeholder="留空则使用默认密钥"
                  />
                </v-expansion-panel-text>
              </v-expansion-panel>

              <!-- 天地图 -->
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="warning">mdi-earth</v-icon>
                  天地图
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-text-field
                    v-model="config.map_api_keys.tianditu.token"
                    label="Token"
                    variant="outlined"
                    type="password"
                    persistent-placeholder
                    placeholder="留空则使用默认密钥"
                  />
                  <v-select
                    v-model="config.map_api_keys.tianditu.type"
                    :items="[
                      { title: '矢量地图', value: 'vec' },
                      { title: '影像地图', value: 'img' },
                      { title: '地形地图', value: 'ter' },
                    ]"
                    label="地图类型"
                    variant="outlined"
                    class="mt-2"
                  />
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 地理编码配置 -->
      <v-col cols="12">
        <v-card class="rounded-lg">
          <v-card-title class="d-flex align-center py-4">
            <v-icon class="mr-2">mdi-crosshairs-gps</v-icon>
            <span>地理编码服务</span>
          </v-card-title>
          <v-divider />
          <v-card-text class="pt-4">
            <v-row>
              <v-col cols="12" sm="6" md="4">
                <v-select
                  v-model="config.geocoding.enabled_service"
                  :items="geocodingServices"
                  label="启用的地理编码服务"
                  variant="outlined"
                  prepend-icon="mdi-server"
                  hint="用于地址解析和逆地理编码的服务"
                  persistent-hint
                />
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <v-text-field
                  v-model="config.geocoding.amap_key"
                  label="高德地图密钥"
                  variant="outlined"
                  type="password"
                  persistent-placeholder
                  placeholder="留空则使用默认密钥"
                />
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <v-text-field
                  v-model="config.geocoding.baidu_key"
                  label="百度地图密钥"
                  variant="outlined"
                  type="password"
                  persistent-placeholder
                  placeholder="留空则使用默认密钥"
                />
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <v-text-field
                  v-model="config.geocoding.tencent_key"
                  label="腾讯地图密钥"
                  variant="outlined"
                  type="password"
                  persistent-placeholder
                  placeholder="留空则使用默认密钥"
                />
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <v-text-field
                  v-model="config.geocoding.nominatim_url"
                  label="Nominatim URL"
                  variant="outlined"
                  persistent-placeholder
                  placeholder="https://nominatim.openstreetmap.org/search"
                  hint="OpenStreetMap 的 Nominatim 服务地址"
                />
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <v-text-field
                  v-model="config.geocoding.nominatim_email"
                  label="Nominatim Email"
                  variant="outlined"
                  type="email"
                  persistent-placeholder
                  placeholder="your@email.com"
                  hint="使用 Nominatim API 时需要提供邮箱"
                />
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 保存成功提示 -->
    <v-snackbar v-model="showSuccess" color="success" timeout="3000">
      <v-icon start>mdi-check-circle</v-icon>
      配置保存成功
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMobileDrawerControl } from '@/composables/useMobileDrawer'
import api from '@/api/client'

const { isDesktop, toggleSidebar } = useMobileDrawerControl()
const router = useRouter()

const goBack = () => {
  router.back()
}

interface MapApiKeys {
  amap: string | null
  amap_security: string | null
  baidu: string | null
  tencent: string | null
  tianditu: {
    token: string
    type: string
  }
}

interface GeocodingConfig {
  enabled_service: string
  amap_key: string | null
  baidu_key: string | null
  tencent_key: string | null
  nominatim_url: string
  nominatim_email: string | null
}

interface MapConfig {
  available_maps: string[]
  default_map: string
  map_api_keys: MapApiKeys
  geocoding: GeocodingConfig
}

const allMaps = [
  { title: '高德地图', value: 'amap', icon: 'mdi-map-marker' },
  { title: '百度地图', value: 'baidu', icon: 'mdi-map-marker-radius' },
  { title: '腾讯地图', value: 'tencent', icon: 'mdi-map-marker-plus' },
  { title: '天地图', value: 'tianditu', icon: 'mdi-earth' },
  { title: 'OpenStreetMap', value: 'osm', icon: 'mdi-open-in-new' },
]

const geocodingServices = [
  { title: '高德地图', value: 'amap' },
  { title: '百度地图', value: 'baidu' },
  { title: '腾讯地图', value: 'tencent' },
  { title: 'Nominatim (OSM)', value: 'nominatim' },
]

const config = reactive<MapConfig>({
  available_maps: ['amap', 'baidu', 'tencent', 'tianditu', 'osm'],
  default_map: 'amap',
  map_api_keys: {
    amap: null,
    amap_security: null,
    baidu: null,
    tencent: null,
    tianditu: {
      token: '',
      type: 'vec',
    },
  },
  geocoding: {
    enabled_service: 'amap',
    amap_key: null,
    baidu_key: null,
    tencent_key: null,
    nominatim_url: '',
    nominatim_email: null,
  },
})

const saving = ref(false)
const showSuccess = ref(false)

const availableMaps = ref(allMaps)

const fetchConfig = async () => {
  try {
    const data = await api.get('/admin/map-config')
    Object.assign(config, data)
  } catch (error) {
    console.error('获取地图配置失败:', error)
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    await api.put('/admin/map-config', config)
    showSuccess.value = true
  } catch (error) {
    console.error('保存地图配置失败:', error)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.h-100 {
  height: 100%;
}
</style>
