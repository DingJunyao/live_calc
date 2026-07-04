<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import type { Proposal } from '@/api/proposals'
import type { MapEngineType, MapConfig, MapEngine } from '@/utils/map/mapTypes'
import { defaultMapConfig, mapEngineNames } from '@/utils/map/mapTypes'
import { mapEngineManager } from '@/utils/mapEngineManager'
import { getUserMapPreference } from '@/utils/mapConfig'
import { api } from '@/api/client'
import L from 'leaflet'

const props = defineProps<{ proposal: Proposal }>()

const snap = computed(() => props.proposal.snapshot || {})
const payload = computed(() => props.proposal.payload || {})

const hasBeforeCoord = computed(() => {
  const s = snap.value
  return s.latitude != null && s.longitude != null && !isNaN(Number(s.latitude)) && !isNaN(Number(s.longitude))
})
const hasAfterCoord = computed(() => {
  const p = payload.value
  return p.latitude != null && p.longitude != null && !isNaN(Number(p.latitude)) && !isNaN(Number(p.longitude))
})
const hasAnyCoord = computed(() => hasBeforeCoord.value || hasAfterCoord.value)

const beforeWgs = computed(() => ({ lat: Number(snap.value.latitude), lng: Number(snap.value.longitude) }))
const afterWgs = computed(() => ({
  lat: Number(hasAfterCoord.value ? payload.value.latitude : snap.value.latitude),
  lng: Number(hasAfterCoord.value ? payload.value.longitude : snap.value.longitude),
}))

const isCoordMove = computed(() =>
  hasBeforeCoord.value && hasAfterCoord.value &&
  (beforeWgs.value.lat !== afterWgs.value.lat || beforeWgs.value.lng !== afterWgs.value.lng)
)
const isCoordAdd = computed(() => !hasBeforeCoord.value && hasAfterCoord.value)

const FIELD_META: Record<string, { label: string; format: (v: any) => string }> = {
  name: { label: '名称', format: String },
  address: { label: '地址', format: String },
  is_open: { label: '营业状态', format: (v: any) => v ? '营业中' : '已停用' },
  user_id: { label: '关联用户', format: String },
}
const IGNORE_FIELDS = new Set(['latitude', 'longitude', 'id', 'created_at', 'updated_at'])

const nonCoordRows = computed(() => {
  const before = snap.value || {}; const after = payload.value || {}
  const fields = Array.from(new Set([...Object.keys(before), ...Object.keys(after)]))
    .filter(f => !f.startsWith('_') && !IGNORE_FIELDS.has(f) && f in FIELD_META)
  return fields.map(f => {
    const b = before[f]; const a = after[f]
    const hasB = f in before; const hasA = f in after
    let kind = 'unchanged'
    if (hasB && !hasA) kind = 'removed'
    else if (!hasB && hasA) kind = 'added'
    else if (JSON.stringify(b) !== JSON.stringify(a)) kind = 'changed'
    return { field: f, before: hasB ? b : null, after: hasA ? a : null, kind }
  }).filter(r => r.kind !== 'unchanged')
})

// ── 地图 ──
const mapContainer = ref<HTMLDivElement>()
const loading = ref(true)
const currentEngine = ref<MapEngineType>('osm')
const availableMaps = ref<MapEngineType[]>(['amap', 'baidu', 'tencent', 'tianditu', 'osm'])
const apiKeys = ref<any>({})
let engine: MapEngine | null = null
let engineMarker1: any = null
let engineMarker2: any = null

const switcherOptions = computed(() =>
  availableMaps.value.map(m => ({ value: m, label: mapEngineNames[m] || m }))
)

async function loadConfig() {
  try {
    const cfg = await api.get('/merchants/map-config')
    if (cfg) {
      const enabled = cfg.available_maps || ['amap', 'baidu', 'tencent', 'tianditu', 'osm']
      availableMaps.value = (['amap', 'baidu', 'tencent', 'tianditu', 'osm'] as MapEngineType[])
        .filter(m => enabled.includes(m))
      apiKeys.value = cfg.map_api_keys || {}
      if (cfg.default_map && availableMaps.value.includes(cfg.default_map)) {
        currentEngine.value = cfg.default_map
      }
    }
  } catch { /* keep defaults */ }
}

async function initMap(forceEngine?: MapEngineType) {
  if (!mapContainer.value || !hasAnyCoord.value) return
  loading.value = true

  if (forceEngine) {
    currentEngine.value = forceEngine
  } else {
    await loadConfig()
    const pref = getUserMapPreference()
    if (pref?.currentMap && availableMaps.value.includes(pref.currentMap)) {
      currentEngine.value = pref.currentMap
    }
  }

  // 照搬 MapPicker 的引擎创建
  const config: MapConfig = {
    ...defaultMapConfig,
    availableMaps: availableMaps.value,
    defaultMap: currentEngine.value,
    mapApiKeys: apiKeys.value,
  }
  mapEngineManager.setConfig(config)

  try {
    engine = await mapEngineManager.createEngine(currentEngine.value, mapContainer.value, {
      center: [beforeWgs.value.lat, beforeWgs.value.lng],
      zoom: 15, enableClick: false, enableDrag: true,
    })
  } catch {
    currentEngine.value = 'osm'
    engine = await mapEngineManager.createEngine('osm', mapContainer.value, {
      center: [beforeWgs.value.lat, beforeWgs.value.lng],
      zoom: 15, enableClick: false, enableDrag: true,
    })
  }

  loading.value = false

  // 通过引擎接口加标记（兼容 Leaflet / SDK）
  if (hasBeforeCoord.value) {
    engineMarker1 = engine.addMarker(beforeWgs.value.lat, beforeWgs.value.lng, { draggable: false })
  }
  if (hasAfterCoord.value && (isCoordMove.value || isCoordAdd.value)) {
    engineMarker2 = engine.addMarker(afterWgs.value.lat, afterWgs.value.lng, { draggable: false })
  }

  // Leaflet 引擎：替换为彩色标记 + 虚线 + 自适应视野
  const map = engine.getMap()
  if (map && map instanceof L.Map) {
    setTimeout(() => map.invalidateSize(), 100)

    // 移除引擎默认标记
    if (engineMarker1 != null) engine.removeMarker(engineMarker1)
    if (engineMarker2 != null) engine.removeMarker(engineMarker2)

    const coords: L.LatLngTuple[] = []

    if (hasBeforeCoord.value) {
      L.marker([beforeWgs.value.lat, beforeWgs.value.lng], {
        icon: L.divIcon({
          className: 'merchant-diff-marker',
          html: '<div style="width:14px;height:14px;border-radius:50%;background:#fb8c00;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.45)"></div>',
          iconSize: [14, 14], iconAnchor: [7, 7],
        }),
      }).addTo(map).bindTooltip(isCoordMove.value ? '改前位置' : '原位置', { direction: 'top', offset: [0, -10] })
      coords.push([beforeWgs.value.lat, beforeWgs.value.lng])
    }

    if (hasAfterCoord.value && (isCoordMove.value || isCoordAdd.value)) {
      L.marker([afterWgs.value.lat, afterWgs.value.lng], {
        icon: L.divIcon({
          className: 'merchant-diff-marker',
          html: '<div style="width:14px;height:14px;border-radius:50%;background:#43a047;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.45)"></div>',
          iconSize: [14, 14], iconAnchor: [7, 7],
        }),
      }).addTo(map).bindTooltip(isCoordAdd.value ? '新位置' : '改后位置', { direction: 'top', offset: [0, -10] })
      coords.push([afterWgs.value.lat, afterWgs.value.lng])
    }

    if (isCoordMove.value && coords.length >= 2) {
      L.polyline(coords, { color: '#1976d2', weight: 2, dashArray: '6 4', opacity: 0.7 }).addTo(map)
    }
    if (coords.length >= 2) {
      map.fitBounds(L.latLngBounds(coords), { padding: [30, 30], maxZoom: 16 })
    } else if (coords.length === 1) {
      map.setView(coords[0], 15)
    }
  } else {
    // SDK 引擎：标记已由 addMarker 加上，居中即可
    if (hasAfterCoord.value && isCoordMove.value) {
      engine.setCenter(
        (beforeWgs.value.lat + afterWgs.value.lat) / 2,
        (beforeWgs.value.lng + afterWgs.value.lng) / 2,
      )
    }
  }
}

async function switchMap(type: MapEngineType) {
  if (type === currentEngine.value) return
  if (engine) { engine.destroy(); engine = null; engineMarker1 = null; engineMarker2 = null }
  currentEngine.value = type
  await nextTick()
  await initMap(type)
}

onMounted(async () => {
  await nextTick()
  setTimeout(initMap, 300)
})

onBeforeUnmount(() => {
  if (engine) { engine.destroy(); engine = null }
})
</script>

<template>
  <div>
    <div v-if="hasAnyCoord" class="mb-3">
      <div class="text-subtitle-2 mb-1">
        {{ isCoordAdd ? '位置（新增）' : isCoordMove ? '位置变更' : '位置' }}
      </div>

      <div class="d-flex align-center mb-2" style="gap: 8px; flex-wrap: wrap;">
        <template v-if="hasBeforeCoord">
          <v-chip size="x-small" color="warning" variant="tonal" label>改前</v-chip>
          <span class="text-caption text-medium-emphasis">{{ beforeWgs.lat.toFixed(6) }}, {{ beforeWgs.lng.toFixed(6) }}</span>
        </template>
        <v-icon v-if="isCoordMove" size="small">mdi-arrow-right</v-icon>
        <template v-if="hasAfterCoord && (isCoordMove || isCoordAdd)">
          <v-chip size="x-small" color="success" variant="tonal" label>{{ isCoordAdd ? '新增' : '改后' }}</v-chip>
          <span class="text-caption text-medium-emphasis">{{ afterWgs.lat.toFixed(6) }}, {{ afterWgs.lng.toFixed(6) }}</span>
        </template>
      </div>

      <div v-if="switcherOptions.length > 1" class="mb-1">
        <v-btn-group density="compact">
          <v-btn
            v-for="opt in switcherOptions" :key="opt.value"
            :color="currentEngine === opt.value ? 'primary' : 'default'"
            :variant="currentEngine === opt.value ? 'elevated' : 'text'"
            size="x-small" @click="switchMap(opt.value)"
          >{{ opt.label }}</v-btn>
        </v-btn-group>
      </div>

      <div class="map-wrapper">
        <div v-if="loading" class="map-loading d-flex align-center justify-center">
          <v-progress-circular indeterminate size="28" width="2" />
        </div>
        <div ref="mapContainer" class="merchant-diff-map" :style="{ height: '260px', visibility: loading ? 'hidden' : 'visible' }" />
      </div>

      <div class="d-flex mt-1" style="gap: 16px; font-size: 0.75rem;">
        <span class="d-flex align-center" style="gap:4px">
          <span style="width:10px;height:10px;border-radius:50%;background:#fb8c00;display:inline-block" />
          <span class="text-medium-emphasis">{{ isCoordMove ? '改前' : '原位置' }}</span>
        </span>
        <span v-if="hasAfterCoord && (isCoordMove || isCoordAdd)" class="d-flex align-center" style="gap:4px">
          <span style="width:10px;height:10px;border-radius:50%;background:#43a047;display:inline-block" />
          <span class="text-medium-emphasis">{{ isCoordAdd ? '新增' : '改后' }}</span>
        </span>
        <span v-if="isCoordMove" class="d-flex align-center" style="gap:4px">
          <span style="width:16px;height:2px;border-top:2px dashed #1976d2;display:inline-block" />
          <span class="text-medium-emphasis">位移</span>
        </span>
      </div>
    </div>

    <div v-if="nonCoordRows.length" class="mb-3">
      <div class="text-subtitle-2 mb-1">其他变更</div>
      <v-table density="compact" class="diff-table">
        <tbody>
          <tr v-for="row in nonCoordRows" :key="row.field">
            <td class="text-caption text-medium-emphasis" style="width:28%">{{ FIELD_META[row.field]?.label || row.field }}</td>
            <td :class="['diff-cell', 'before', row.kind]">
              <span v-if="row.before === null" class="text-medium-emphasis">—</span>
              <span v-else>{{ FIELD_META[row.field]?.format(row.before) ?? row.before }}</span>
            </td>
            <td class="text-center text-medium-emphasis" style="width:32px">→</td>
            <td :class="['diff-cell', 'after', row.kind]">
              <span v-if="row.kind === 'removed'" class="text-medium-emphasis">（删除）</span>
              <span v-else-if="row.after === null" class="text-medium-emphasis">—</span>
              <span v-else>{{ FIELD_META[row.field]?.format(row.after) ?? row.after }}</span>
            </td>
          </tr>
        </tbody>
      </v-table>
    </div>

    <div v-if="!hasAnyCoord && !nonCoordRows.length" class="text-caption text-medium-emphasis">
      无可见变更字段。
    </div>
  </div>
</template>

<style scoped>
.map-wrapper { position: relative; border-radius: 8px; overflow: hidden; border: 1px solid rgba(var(--v-border-color), 0.12); }
.map-loading { position: absolute; inset: 0; z-index: 1; background: rgba(var(--v-theme-surface), 0.5); }
.merchant-diff-map { border-radius: 8px; }
.diff-table .diff-cell { font-size: 0.8rem; word-break: break-all; }
.diff-table .diff-cell.changed { background: rgba(255, 193, 7, 0.12); }
.diff-table .diff-cell.added { background: rgba(76, 175, 80, 0.12); }
.diff-table .diff-cell.removed { background: rgba(244, 67, 54, 0.10); }
.diff-table .before.removed { color: rgb(244, 67, 54); }
.diff-table .after.added { color: rgb(76, 175, 80); }
</style>
