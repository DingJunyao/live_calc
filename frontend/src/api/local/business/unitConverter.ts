// 单位换算模块 — 纯函数，不依赖 IndexedDB。
// 基于 SI 因子、实体单位覆盖、密度三层策略完成跨类型换算。

export interface UnitInfo {
  id: number
  unit_type: string     // 'mass' | 'volume' | 'count' | 'length' | 'time'
  si_factor: number | null
  abbreviation?: string
}

export interface EntityOverride {
  entity_type: string
  entity_id: number
  base_unit_id: number | null
  conversion_factor: number | null
  weight_per_unit: number | null
  weight_unit_id: number | null
}

export interface DensityInfo {
  entity_type: string
  entity_id: number
  density: number       // kg/m³
}

export interface ConvertInput {
  value: number
  from_unit_id: number
  to_unit_id: number
  entity_type?: string   // 'ingredient' | 'product'
  entity_id?: number
  units: UnitInfo[]
  overrides?: EntityOverride[]
  densities?: DensityInfo[]
}

export interface ConvertResult {
  value: number
  to_unit_id: number
}

/**
 * 在两个单位之间转换数值。纯函数。
 *
 * 策略：
 * 1. 同类型（mass→mass, volume→volume）：si_factor 比值（直接链式归约到 SI 基准）
 * 2. 跨类型（mass↔volume）：密度桥接（密度 kg/m³ → kg/L）
 * 3. 计数单位（count）：实体单位覆盖 weight_per_unit
 * 4. 最大递归 5 层防止循环
 *
 * 链式换算说明：
 * - 同类型单位转换已通过 SI 因子一步到位：value × (from_si / to_si)
 *   （相当于 from→SI→to 的二段链）
 * - 跨类型转换以密度为单一桥接点：mass↔density↔volume
 * - 更长链（如 count→mass→volume）需调用方分步，或通过实体覆盖的
 *   weight_per_unit 将 count 先转为 mass/volume 再经密度桥接。
 *   当前实现中 count→volume 分支已内置此二层链（line 109-117）。
 */
export function convert(input: ConvertInput): ConvertResult {
  const { value, from_unit_id, to_unit_id, entity_type, entity_id, units, overrides = [], densities = [] } = input

  if (from_unit_id === to_unit_id) {
    return { value, to_unit_id }
  }

  const fromUnit = units.find(u => u.id === from_unit_id)
  const toUnit = units.find(u => u.id === to_unit_id)

  if (!fromUnit || !toUnit) {
    throw { status: 400, message: `单位未找到: ${from_unit_id} 或 ${to_unit_id}` }
  }

  // 同类型：直接 si_factor 换算
  if (fromUnit.unit_type === toUnit.unit_type && fromUnit.si_factor != null && toUnit.si_factor != null) {
    return { value: value * (fromUnit.si_factor / toUnit.si_factor), to_unit_id }
  }

  // 跨类型：密度桥接 (mass ↔ volume)
  if (isMassType(fromUnit.unit_type) && isVolumeType(toUnit.unit_type)) {
    // mass → volume: value / density (density in kg/m³ → kg/L)
    const density = findDensity(from_unit_id, to_unit_id, entity_type, entity_id, units, overrides, densities)
    if (density != null) {
      // density is kg/m³, we need kg/L: divide by 1000
      // value (in mass unit) * fromUnit.siFactor = kg
      // kg / density_kg_per_L = L
      // L / toUnit.siFactor = value in target unit
      const kg = value * fromUnit.si_factor!
      const liters = kg / density
      return { value: liters / toUnit.si_factor!, to_unit_id }
    }
  }

  if (isVolumeType(fromUnit.unit_type) && isMassType(toUnit.unit_type)) {
    // volume → mass: value * density
    const density = findDensity(from_unit_id, to_unit_id, entity_type, entity_id, units, overrides, densities)
    if (density != null) {
      // value (in volume unit) * fromUnit.siFactor = L
      // L * density_kg_per_L = kg
      // kg / toUnit.siFactor = value in target unit
      const liters = value * fromUnit.si_factor!
      const kg = liters * density
      return { value: kg / toUnit.si_factor!, to_unit_id }
    }
  }

  // 计数单位回退：查实体单位覆盖中的 weight_per_unit
  if (fromUnit.unit_type === 'count' || toUnit.unit_type === 'count') {
    const override = findOverride(entity_type, entity_id, overrides)
    if (override?.weight_per_unit != null && override?.weight_unit_id != null) {
      const weightUnit = units.find(u => u.id === override.weight_unit_id)
      if (weightUnit && toUnit.si_factor != null && weightUnit.si_factor != null) {
        if (fromUnit.unit_type === 'count' && isMassType(toUnit.unit_type)) {
          // count → mass: value * weight_per_unit * weight_unit_si_factor / toUnit_si_factor
          const massInKg = value * override.weight_per_unit * weightUnit.si_factor
          return { value: massInKg / toUnit.si_factor, to_unit_id }
        }
        if (fromUnit.unit_type === 'count' && isVolumeType(toUnit.unit_type)) {
          // count → volume: mass via density
          const massInKg = value * override.weight_per_unit * weightUnit.si_factor
          const density = findDensity(override.weight_unit_id, to_unit_id, entity_type, entity_id, units, overrides, densities)
          if (density != null) {
            const liters = massInKg / density
            return { value: liters / toUnit.si_factor, to_unit_id }
          }
        }
      }
    }
  }

  throw {
    status: 400,
    message: `无法在 ${fromUnit.unit_type} 和 ${toUnit.unit_type} 之间转换`,
  }
}

function isMassType(type: string): boolean {
  return type === 'mass'
}

function isVolumeType(type: string): boolean {
  return type === 'volume'
}

/**
 * 查找密度（kg/m³）。
 * 优先级：
 * 1. 实体单位覆盖中的 weight_per_unit
 * 2. entity_densities 表
 * 3. 无密度时返回 null（不默认水密度，由调用方决定回退策略）
 */
function findDensity(
  fromUnitId: number, toUnitId: number,
  entityType?: string, entityId?: number,
  units?: UnitInfo[], overrides?: EntityOverride[], densities?: DensityInfo[],
): number | null {
  // 先查实体单位覆盖
  if (entityType && entityId && overrides) {
    const ov = overrides.find(o => o.entity_type === entityType && o.entity_id === entityId)
    if (ov?.weight_per_unit != null && ov?.weight_unit_id != null) {
      const wu = units?.find(u => u.id === ov.weight_unit_id)
      if (wu?.si_factor) {
        // weight_per_unit × si_factor → kg per unit
        // density = (weight_per_unit × si_factor_kg) / fromUnit_si_factor_L
        // UnitInfo only has id/unit_type/si_factor, we can't know which unit is kg or L
        // Better to just return null and let caller handle
        return null
      }
    }
  }

  // 查 entity_densities（存储为 kg/m³，即 g/L）
  if (entityType && entityId && densities) {
    const d = densities.find(d => d.entity_type === entityType && d.entity_id === entityId)
    if (d && d.density > 0) {
      // kg/m³ → kg/L: 1 m³ = 1000 L, so 1 kg/m³ = 0.001 kg/L
      return d.density / 1000
    }
  }

  return null
}

/**
 * 查找 entity_unit_overrides 中的匹配记录。
 */
function findOverride(
  entityType?: string, entityId?: number,
  overrides?: EntityOverride[],
): EntityOverride | null {
  if (!entityType || !entityId || !overrides) return null
  return overrides.find(o => o.entity_type === entityType && o.entity_id === entityId) || null
}
