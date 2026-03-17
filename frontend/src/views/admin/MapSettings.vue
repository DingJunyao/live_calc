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
      <h3>地图 API 配置</h3>
      <p class="help-text">各地图服务商的 API 凭证配置（可选，不填使用免费瓦片）</p>

      <!-- 高德地图 -->
      <div class="map-config-card">
        <h4>高德地图</h4>
        <div class="form-group">
          <label>API Key (JS API Key)</label>
          <input
            v-model="config.mapApiKeys.amap"
            type="text"
            placeholder="高德地图 JS API Key"
          />
        </div>
        <div class="form-group">
          <label>安全密钥 (security_js_code)</label>
          <input
            v-model="config.mapApiKeys.amapSecurity"
            type="text"
            placeholder="高德地图安全密钥（可选）"
          />
        </div>
      </div>

      <!-- 百度地图 -->
      <div class="map-config-card">
        <h4>百度地图</h4>
        <div class="form-group">
          <label>AK (API Key)</label>
          <input
            v-model="config.mapApiKeys.baidu"
            type="text"
            placeholder="百度地图 AK"
          />
        </div>
      </div>

      <!-- 腾讯地图 -->
      <div class="map-config-card">
        <h4>腾讯地图</h4>
        <div class="form-group">
          <label>API Key</label>
          <input
            v-model="config.mapApiKeys.tencent"
            type="text"
            placeholder="腾讯地图 API Key"
          />
        </div>
      </div>

      <!-- 天地图 -->
      <div class="map-config-card">
        <h4>天地图 (必填)</h4>
        <div class="form-group">
          <label>Token (tk)</label>
          <input
            v-model="config.mapApiKeys.tiandituToken"
            type="text"
            placeholder="天地图 Token（必填）"
            :class="{ 'error': !config.mapApiKeys.tiandituToken }"
          />
        </div>
        <div class="form-group">
          <label>地图类型</label>
          <select v-model="config.mapApiKeys.tiandituType">
            <option value="vec">矢量图</option>
            <option value="img">影像图</option>
          </select>
        </div>
      </div>
    </div>

    <div class="settings-section">
      <h3>反向地理编码配置</h3>
      <p class="help-text">地址转坐标（根据地址查询经纬度）使用的服务</p>

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
            <input type="radio"
              value="baidu"
              v-model="config.geocoding.enabledService"
            />
            百度地图
          </label>
          <label>
            <input type="radio"
              value="tencent"
              v-model="config.geocoding.enabledService"
            />
            腾讯地图
          </label>
          <label>
            <input type="radio"
              value="nominatim"
              v-model="config.geocoding.enabledService"
            />
            Nominatim
          </label>
        </div>
      </div>

      <!-- 高德反向地理编码配置 -->
      <div v-if="config.geocoding.enabledService === 'amap'" class="geocoding-config">
        <div class="form-group">
          <label>高德地图 API Key (Web 服务 API Key)</label>
          <input
            v-model="config.geocoding.amapKey"
            type="text"
            placeholder="高德地图 Web 服务 API Key"
          />
        </div>
      </div>

      <!-- 百度反向地理编码配置 -->
      <div v-if="config.geocoding.enabledService === 'baidu'" class="geocoding-config">
        <div class="form-group">
          <label>百度地图 AK</label>
          <input
            v-model="config.geocoding.baiduKey"
            type="text"
            placeholder="百度地图 AK"
          />
        </div>
      </div>

      <!-- 腾讯反向地理编码配置 -->
      <div v-if="config.geocoding.enabledService === 'tencent'" class="geocoding-config">
        <div class="form-group">
          <label>腾讯地图 Key</label>
          <input
            v-model="config.geocoding.tencentKey"
            type="text"
            placeholder="腾讯地图 Key"
          />
        </div>
      </div>

      <!-- Nominatim 配置 -->
      <div v-if="config.geocoding.enabledService === 'nominatim'" class="geocoding-config">
        <div class="form-group">
          <label>服务器 URL</label>
          <input
            v-model="config.geocoding.nominatimUrl"
            type="text"
            placeholder="https://nominatim.example.com（使用官方留空）"
          />
        </div>
        <div class="form-group">
          <label>联系邮箱 (Email)</label>
          <input
            v-model="config.geocoding.nominatimEmail"
            type="email"
            placeholder="用于 Nominatim 服务请求头（可选）"
          />
        </div>
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
import PageHeader from '@/components/PageHeader.vue'
import { api } from '@/api/client'

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
    amapSecurity: '',
    baidu: '',
    tencent: '',
    tiandituToken: '',
    tiandituType: 'vec'
  },
  geocoding: {
    enabledService: 'amap',
    amapKey: '',
    baiduKey: '',
    tencentKey: '',
    nominatimUrl: '',
    nominatimEmail: ''
  }
})

const saving = ref(false)

// 可用于默认地图选择
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
          amapSecurity: data.map_api_keys?.amap_security || '',
          baidu: data.map_api_keys?.baidu || '',
          tencent: data.map_api_keys?.tencent || '',
          tiandituToken: data.map_api_keys?.tianditu?.token || '',
          tiandituType: data.map_api_keys?.tianditu?.type || 'vec'
        },
        geocoding: {
          enabledService: data.geocoding?.enabled_service || 'amap',
          amapKey: data.geocoding?.amap_key || '',
          baiduKey: data.geocoding?.baidu_key || '',
          tencentKey: data.geocoding?.tencent_key || '',
          nominatimUrl: data.geocoding?.nominatim_url || '',
          nominatimEmail: data.geocoding?.nominatim_email || ''
        }
      }
    }
  } catch (error) {
    console.error('Failed to load map config:', error)
  }
}

// 保存配置
async function saveConfig() {
  if (!config.value.mapApiKeys.tiandituToken) {
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
        amap_security: config.value.mapApiKeys.amapSecurity || null,
        baidu: config.value.mapApiKeys.baidu || null,
        tencent: config.value.mapApiKeys.tencent || null,
        tianditu: {
          token: config.value.mapApiKeys.tiandituToken,
          type: config.value.mapApiKeys.tiandituType
        }
      },
      geocoding: {
        enabled_service: config.value.geocoding.enabledService,
        amap_key: config.value.geocoding.amapKey || null,
        baidu_key: config.value.geocoding.baiduKey || null,
        tencent_key: config.value.geocoding.tencentKey || null,
        nominatim_url: config.value.geocoding.nominatimUrl,
        nominatim_email: config.value.geocoding.nominatimEmail || null
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
  max-width: 700px;
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

.map-config-card {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
}

.map-config-card h4 {
  margin: 0 0 0.75rem 0;
  color: #333;
  font-size: 1rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  color: #555;
  font-weight: 500;
  font-size: 0.875rem;
}

.form-group input[type="text"],
.form-group input[type="email"],
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 0.5rem;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-group input.error {
  border-color: #de350b;
}

.geocoding-config {
  background: #f0f7ff;
  padding: 1rem;
  border-radius: 0.5rem;
  margin-top: 1rem;
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