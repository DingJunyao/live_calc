// composables/useUserUnits.ts
// 用户级单位偏好读取 + 能量单位转换。NULL 字段由前端 fallback。
import { computed } from 'vue'
import { useUserStore } from '@/stores/user'

export interface UnitPref {
  id: number
  name: string
  abbreviation: string
}

const FALLBACK_MASS_NAME = '斤'
const FALLBACK_VOLUME_NAME = 'mL'
const FALLBACK_PRICE_NAME = '斤'

export function useUserUnits() {
  const userStore = useUserStore()
  const up = computed(() => (userStore.user as any)?.unit_preferences ?? null)

  const energyUnit = computed<'kcal' | 'kJ'>(() => up.value?.energy_unit ?? 'kcal')
  const massUnit = computed<UnitPref | null>(() => up.value?.mass_unit ?? null)
  const volumeUnit = computed<UnitPref | null>(() => up.value?.volume_unit ?? null)
  const priceUnit = computed<UnitPref | null>(() => up.value?.price_unit ?? null)

  const massUnitName = computed(() => massUnit.value?.name ?? FALLBACK_MASS_NAME)
  const volumeUnitName = computed(() => volumeUnit.value?.name ?? FALLBACK_VOLUME_NAME)
  const priceUnitName = computed(() => priceUnit.value?.name ?? FALLBACK_PRICE_NAME)

  // calorie 转换：库存 kcal，前端按 energyUnit 显示/输入
  const toDisplayCalorie = (kcal: number | null | undefined): number | null => {
    if (kcal === null || kcal === undefined) return null
    return energyUnit.value === 'kJ' ? +(kcal * 4.184).toFixed(0) : kcal
  }
  const fromDisplayCalorie = (v: number | null | undefined): number | null => {
    if (v === null || v === undefined) return null
    return energyUnit.value === 'kJ' ? +(v / 4.184).toFixed(0) : v
  }

  return {
    energyUnit,
    massUnit,
    volumeUnit,
    priceUnit,
    massUnitName,
    volumeUnitName,
    priceUnitName,
    toDisplayCalorie,
    fromDisplayCalorie,
  }
}
