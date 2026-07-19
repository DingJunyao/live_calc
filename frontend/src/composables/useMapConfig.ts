/**
 * 地图配置单例 composable
 *
 * 模块级缓存 /merchants/map-config 结果，供各页面感知「地图是否启用」。
 * 参考 useTheme.ts 的单例套路：状态提模块顶层，useMapConfig() 仅返回引用。
 * 请求失败时 mapEnabled 默认回退 true（保守，不破坏现有功能）。
 */
import { ref } from 'vue'
import { api } from '@/api/client'

export interface PublicMapConfig {
  map_enabled?: boolean
  available_maps?: string[]
  default_map?: string
  map_api_keys?: Record<string, any>
  [key: string]: any
}

const mapEnabled = ref<boolean>(true)
const config = ref<PublicMapConfig | null>(null)
let loadPromise: Promise<void> | null = null

async function load(): Promise<void> {
  try {
    const data = await api.get('/merchants/map-config')
    config.value = data
    mapEnabled.value = data?.map_enabled !== false
  } catch (e) {
    // 失败回退启用，保持现状
    mapEnabled.value = true
  }
}

function ensureLoaded(): Promise<void> {
  if (!loadPromise) {
    loadPromise = load()
  }
  return loadPromise
}

/** 强制重新加载（管理员改配置后如需刷新可调用） */
function reload(): Promise<void> {
  loadPromise = load()
  return loadPromise
}

export function useMapConfig() {
  return { mapEnabled, config, ensureLoaded, reload }
}
