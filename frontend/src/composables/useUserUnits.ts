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

  // 从「元/斤」折算到用户质量偏好单位（用于价格趋势/单价显示）。
  // si_factor：1 单位 = ? kg。元/X = 元/斤 × (si_factor_X / si_factor_斤)。
  // 只覆盖常见质量单位；未知单位不转（保持斤），避免误算。
  const JIN_SI_FACTOR = 0.5 // 1 斤 = 0.5 kg
  const COMMON_SI_FACTORS: Record<string, number> = {
    kg: 1, g: 0.001, 斤: 0.5, 两: 0.05, 磅: 0.453592,
  }
  const convertFromJin = (valuePerJin: number | null | undefined): number | null => {
    if (valuePerJin === null || valuePerJin === undefined) return null
    const abbr = massUnit.value?.abbreviation
    const f = abbr ? COMMON_SI_FACTORS[abbr] : undefined
    if (f === undefined) return valuePerJin // 未知单位不转
    return valuePerJin * (f / JIN_SI_FACTOR)
  }

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
    convertFromJin,
  }
}
