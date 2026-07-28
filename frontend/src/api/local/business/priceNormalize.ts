// 价格归一化模块 — 把不同单位（质量/体积/计数）的价格记录统一折算到可比口径。
// 核心问题：质量记录（¥/斤）与计数记录（¥/个）若直接平均会得到荒谬值
// （如鸡蛋 ¥0.23/个、¥108/斤），必须先按 unit_type 分组并借助
// weight_per_unit 把计数单位折算到质量基准。
//
// 注意：历史 entity_unit_overrides 数据存在系统性脏数据：
//   weight_unit_id=3（斤, si=0.5）但 weight_unit_name="克"、weight_per_unit 为
//   合理克数（如鸡蛋 55）。真实意图是克，weight_unit_id 是 off-by-one 错误。
// 本模块对 weight_unit 解析做容错：id 指向的单位 si_factor 过大（>0.1，显然
// 非克/毫克）时，改用 weight_unit_name 重解析，避免计数->质量折算产生荒谬单价。

import { type UnitInfo, type EntityOverride, type DensityInfo } from './unitConverter'

const JIN_UNIT_ID = 3
const JIN_GRAMS = 500

export interface PriceRecordLike {
  price: number
  quantity?: number | null
  standard_quantity?: number | null
  unit_id?: number | null
  standard_unit_id?: number | null
  recorded_at?: string | null
}

export interface NormalizedPrice {
  pricePerJin: number | null
  unitType: 'mass' | 'volume' | 'count' | 'unknown'
  rawUnitPrice: number
}

/**
 * 解析实体单位覆盖里的 weight_per_unit（克数）。
 * 容错：weight_unit_id 与 weight_unit_name 不一致时（系统性脏数据），
 * 若 id 指向的单位 si_factor 过大（>0.1，显然非克/毫克），改用 name 重解析。
 */
export function resolveWeightGrams(
  override: EntityOverride | undefined | null,
  units: UnitInfo[],
): number | null {
  if (!override || override.weight_per_unit == null) return null
  const wpu = override.weight_per_unit

  const byId = units.find(u => u.id === override.weight_unit_id)
  if (byId?.si_factor != null && byId.si_factor <= 0.1) {
    return wpu * byId.si_factor * 1000
  }

  const wname = (override as any).weight_unit_name as string | undefined
  if (wname) {
    const byName = units.find(u => u.name === wname || u.abbreviation === wname)
    if (byName?.si_factor != null && byName.si_factor <= 0.1) {
      return wpu * byName.si_factor * 1000
    }
  }

  return null
}

/**
 * 把一条价格记录折算为 ¥/斤（质量基准）。无法折算时返回 null，
 * 调用方应将其归入「按个」口径单独展示，不要混入质量平均。
 */
export function normalizeRecordToJin(
  record: PriceRecordLike,
  units: UnitInfo[],
  overrides: EntityOverride[],
  _densities: DensityInfo[],
  entityType: string,
  entityId: number,
): NormalizedPrice {
  const price = Number(record.price) || 0
  const stdQty = Number(record.standard_quantity) || Number(record.quantity) || 1
  const unitId = record.standard_unit_id ?? record.unit_id
  const unit = unitId != null ? units.find(u => u.id === unitId) : undefined
  const unitType = (unit?.unit_type as NormalizedPrice['unitType']) || 'unknown'
  const rawUnitPrice = stdQty > 0 ? price / stdQty : price

  if (!unit || unit.si_factor == null) {
    return { pricePerJin: null, unitType, rawUnitPrice }
  }

 if (unit.unit_type === 'mass') {
   const jin = units.find(u => u.id === JIN_UNIT_ID)
   if (jin?.si_factor) {
      // rawUnitPrice 为 [price/unit]，1斤 = jin.si_factor/unit.si_factor 个 unit
      // （克：0.5/0.001 = 500，即 1斤=500克）。方向与 si 比值相反。
      return { pricePerJin: rawUnitPrice * jin.si_factor / unit.si_factor, unitType: 'mass', rawUnitPrice }
   }
 }

  if (unit.unit_type === 'count') {
    const override = overrides.find(
      o => o.entity_type === entityType && o.entity_id === entityId,
    )
    const gramsPerUnit = resolveWeightGrams(override, units)
    if (gramsPerUnit != null && gramsPerUnit > 0) {
      return {
        pricePerJin: rawUnitPrice / gramsPerUnit * JIN_GRAMS,
        unitType: 'count',
        rawUnitPrice,
      }
    }
    return { pricePerJin: null, unitType: 'count', rawUnitPrice }
  }

  return { pricePerJin: null, unitType: unit.unit_type as NormalizedPrice['unitType'], rawUnitPrice }
}

export interface AggregatePrice {
  average_price: number | null
  unit: string
  records: number
  min_price: number | null
  max_price: number | null
}

/**
 * 聚合一组价格记录：
 * - 若存在可归一化到质量的记录，只在质量记录内平均，返回 ¥/斤
 * - 否则若全是同一计数单位，返回该单位的 ¥/个
 * - 混杂且无可比口径时返回 null
 */
export function aggregatePrices(
  records: PriceRecordLike[],
  units: UnitInfo[],
  overrides: EntityOverride[],
  densities: DensityInfo[],
  entityType: string,
  entityId: number,
): AggregatePrice {
  if (records.length === 0) {
    return { average_price: null, unit: '斤', records: 0, min_price: null, max_price: null }
  }

  const massPrices: number[] = []
  const countPricesByUnit: Record<string, number[]> = {}

  for (const r of records) {
    const np = normalizeRecordToJin(r, units, overrides, densities, entityType, entityId)
    if (np.pricePerJin != null && np.unitType === 'mass') {
      massPrices.push(np.pricePerJin)
    } else if (np.unitType === 'count') {
      const uid = r.standard_unit_id ?? r.unit_id
      const key = String(uid)
      if (!countPricesByUnit[key]) countPricesByUnit[key] = []
      countPricesByUnit[key].push(np.rawUnitPrice)
    } else if (np.pricePerJin != null) {
      massPrices.push(np.pricePerJin)
    }
  }

  if (massPrices.length > 0) {
    const sum = massPrices.reduce((a, b) => a + b, 0)
    return {
      average_price: Math.round((sum / massPrices.length) * 10000) / 10000,
      unit: '斤',
      records: massPrices.length,
      min_price: Math.round(Math.min(...massPrices) * 10000) / 10000,
      max_price: Math.round(Math.max(...massPrices) * 10000) / 10000,
    }
  }

  const countKeys = Object.keys(countPricesByUnit)
  if (countKeys.length > 0) {
    const bestKey = countKeys.sort((a, b) => countPricesByUnit[b].length - countPricesByUnit[a].length)[0]
    const prices = countPricesByUnit[bestKey]
    const unit = units.find(u => u.id === Number(bestKey))
    const sum = prices.reduce((a, b) => a + b, 0)
    return {
      average_price: Math.round((sum / prices.length) * 10000) / 10000,
      unit: unit?.name || '个',
      records: prices.length,
      min_price: Math.round(Math.min(...prices) * 10000) / 10000,
      max_price: Math.round(Math.max(...prices) * 10000) / 10000,
    }
  }

  return { average_price: null, unit: '斤', records: 0, min_price: null, max_price: null }
}

export { JIN_UNIT_ID, JIN_GRAMS }
