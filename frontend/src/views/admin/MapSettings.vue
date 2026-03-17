<template>
  <PageHeader title="地图设置" :show-back="true" />

  <div class="map-settings">
    <div class="settings-section">
      <h3>可用地图</h3>
      <p class="help-text">选择系统中可用的地图引擎</p>
      <div class="checkbox-group">
        <label v-for="map in allMaps" :key="map.value">
          <input
            type="checkbox"
            :value="map.value"
            v-model="config.availableMaps"
          />
          {{ map.label }}
        </label>
      </div>
    </div>

    <div class="settings-section">
      <h3>默认地图</h3>
      <p class="help-text">选择默认显示的地图引擎</p>
      <div class="radio-group">
        <label v-for="map in availableMapsForSelect" :key="map.value">
          <input
            type="radio"
            :value="map.value"
            v-model="config.defaultMap"
          />
          {{ map.label }}
        </label>
      </div>
    </div>

    <div class="settings-section">
      <h3>API 配置</h3>

      <div class="form-group">
        <label>高德地图 Web 服务 Key</label>
        <input
          v-model="config.mapApiKeys.amap"
          type="text"
          placeholder="填写高德地图 Key（可选，不填使用免费瓦片）"
        />
      </div>

      <div class="form-group">
        <label>百度地图 AK</label>
        <input
          v-model="config.mapApiKeys.baidu"
          type="text"
          placeholder="填写百度地图 AK（可选，不填使用免费瓦片）"
        />
      </div>

      <div class="form-group">
        <label>腾讯地图 Key</label>
        <input
          v-model="config.mapApiKeys.tencent"
          type="text"
          placeholder="填写腾讯地图 Key（可选，不填使用免费瓦片）"
        />
      </div>

      <div class="form-group">
        <label>天地图 Token (必填)</label>
        <input
          v-model="tiandituToken"
          type="text"
          placeholder="填写天地图 Token（必填）"
          :class="{ 'error': !tiandituToken }"
        />
        <span class="help-text">天地图必须配置 Token 才能使用</span>
      </div>
    </div>

    <div class="settings-section">
      <h3>反向地理编码</h3>

      <div class="form-group">
        <label>启用的服务</label>
        <div class="radio-group">
          <label>
            <input
              type="radio"
              value="amap"
              v-model="config.geocoding.enabledService"
            />
            高德地图
          </label>
          <label>
            <input
              type="radio"
              value="baidu"
              v-model="config.geocoding.enabledService"
            />
            百度地图
          </label>
          <label>
            <input
              type="radio"
              value="tencent"
              v-model="config.geocoding.enabledService"
            />
            腾讯地图
          </label>
          <label>
            <input
              type="radio"
              value="nominatim"
              v-model="config.geocoding.enabledService"
            />
            Nominatim
          </label>
        </div>
      </div>

      <div class="form-group">
        <label>Nominatim 服务器 URL</label>
        <input
          v-model="config.geocoding.nominatimUrl"
          type="text"
          placeholder="如：https://nominatim.example.com（使用官方服务器留空）"
        />
        <span class="help-text">使用自部署的 Nominatim 服务器，官方服务器有请求频率限制</span>
      </div>
    </div>

    <div class="actions">
      <button @click="saveConfig" class="btn-primary" :disabled="saving">
        {{ saving ? '保存中...' : '保存配置' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import { api } from '@/api/client'

const router = useRouter()

// 选项配置
const allMaps = [
  { value: 'amap', label: '高德地图' },
  { value: 'baidu', label: '百度地图' },
  { value: 'tencent', label: '腾讯地图' },
  { value: 'tianditu', label: '天地图' },
  { value: 'osm', label: 'OpenStreetMap' }
]

// 配置数据
const config = ref({
  availableMaps: ['amap', 'baidu', 'tencent', 'tianditu', 'osm'] as string[],
  defaultMap: 'amap',
  mapApiKeys: {
    amap: '',
    baidu: '',
    tencent: '',
    tianditu: { token: '', type: 'vec' }
  },
  geocoding: {
    enabledService: 'amap',
    apiKeys: {
      amap: '',
      baidu: '',
      tencent: ''
    },
    nominatimUrl: ''
  }
})

const tiandituToken = ref('')
const saving = ref(false)

// 可用于默认地图选择（必须在 availableMaps 中）
const availableMapsForSelect = computed(() => {
  return allMaps.filter(m => config.value.availableMaps.includes(m.value))
})

// 加载配置
async function loadConfig() {
  try {
    const data = await api.get('/admin/map-config')
    if (data) {
      config.value = {
        availableMaps: data.available_maps || ['amap', 'baidu', 'tencent', 'tianditu', 'osm'],
        defaultMap: data.default_map || 'amap',
        mapApiKeys: {
          amap: data.map_api_keys?.amap || '',
          baidu: data.map_api_keys?.baidu || '',
          tencent: data.map_api_keys?.tencent || '',
          tianditu: { token: '', type: 'vec' }
        },
        geocoding: {
          enabledService: data.geocoding?.enabled_service || 'amap',
          apiKeys: {
            amap: data.geocoding?.api_keys?.amap || '',
            baidu: data.geocoding?.api_keys?.baidu || '',
            tencent: data.geocoding?.api_keys?.tencent || ''
          },
          nominatimUrl: data.geocoding?.nominatim_url || ''
        }
      }
      tiandituToken.value = data.map_api_keys?.tianditu?.token || ''
    }
  } catch (error) {
    console.error('Failed to load map config:', error)
  }
}

// 保存配置
async function saveConfig() {
  if (!tiandituToken.value) {
    alert('天地图 Token 为必填项')
    return
  }

  saving.value = true
  try {
    const payload = {
      available_maps: config.value.availableMaps,
      default_map: config.value.defaultMap,
      map_api_keys: {
        amap: config.value.mapApiKeys.amap || null,
        baidu: config.value.mapApiKeys.baidu || null,
        tencent: config.value.mapApiKeys.tencent || null,
        tianditu: {
          token: tiandituToken.value,
          type: 'vec'
        }
      },
      geocoding: {
        enabled_service: config.value.geocoding.enabledService,
        api_keys: {
          amap: config.value.geocoding.apiKeys.amap || null,
          baidu: config.value.geocoding.apiKeys.baidu || null,
          tencent: config.value.geocoding.apiKeys.tencent || null
        },
        nominatim_url: config.value.geocoding.nominatimUrl
      }
    }

    await api.put('/admin/map-config', payload)
    alert('配置保存成功')
  } catch (error) {
    console.error('Failed to save map config:', error)
    alert('保存配置失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.map-settings {
  padding: 1rem;
  max-width: 600px;
}

.settings-section {
  background: white;
  padding: 1.5rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.settings-section h3 {
  margin: 0 0 0.5rem 0;
  color: #333;
  font-size: 1.1rem;
}

.help-text {
  color: #666;
  font-size: 0.875rem;
  margin: 0 0 1rem 0;
}

.checkbox-group,
.radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.checkbox-group label,
.radio-group label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #555;
  font-weight: 500;
}

.form-group input[type="text"] {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-group input[type="text"].error {
  border-color: #de350b;
}

.actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.btn-primary {
  padding: 0.75rem 2rem;
  background: #42b883;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 1rem;
}

.btn-primary:hover:not(:disabled) {
  background: #36966d;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .checkbox-group,
  .radio-group {
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>