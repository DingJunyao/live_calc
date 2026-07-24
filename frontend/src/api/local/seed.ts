// 本地模式初始数据种子模块。
// 提供基础单位、单位换算、食材分类等系统运行必需的最简种子数据。
// 调用方在首次启动向导中调用 seedBasicData() 填充这些数据。

import { batchAdd, hasData } from './database'

/**
 * 基础单位列表（ID 固定，确保后续代码按 ID 引用正确）
 * - id 1-15: 千克/克/斤/升/毫升/个/两/磅/盎司/cc/茶匙/汤匙/杯/份/包
 * - is_si_base: 千克、升、个 为 SI 基准单位
 * - is_common: 高频使用单位（磅/盎司在中文场景不常用）
 * - unit_system: metric/market/imperial/count/vague
 */
export const BASE_UNITS = [
  { id: 1, name: '千克', abbreviation: 'kg', unit_type: 'mass', unit_system: 'metric', si_factor: 1, is_si_base: true, is_common: true, display_order: 1, plural_form: null },
  { id: 2, name: '克', abbreviation: 'g', unit_type: 'mass', unit_system: 'metric', si_factor: 0.001, is_si_base: false, is_common: true, display_order: 2, plural_form: null },
  { id: 3, name: '斤', abbreviation: '斤', unit_type: 'mass', unit_system: 'market', si_factor: 0.5, is_si_base: false, is_common: true, display_order: 3, plural_form: null },
  { id: 4, name: '升', abbreviation: 'L', unit_type: 'volume', unit_system: 'metric', si_factor: 1, is_si_base: true, is_common: true, display_order: 4, plural_form: null },
  { id: 5, name: '毫升', abbreviation: 'mL', unit_type: 'volume', unit_system: 'metric', si_factor: 0.001, is_si_base: false, is_common: true, display_order: 5, plural_form: null },
  { id: 6, name: '个', abbreviation: '个', unit_type: 'count', unit_system: 'count', si_factor: 1, is_si_base: true, is_common: true, display_order: 6, plural_form: null },
  { id: 7, name: '两', abbreviation: '两', unit_type: 'mass', unit_system: 'market', si_factor: 0.05, is_si_base: false, is_common: true, display_order: 7, plural_form: null },
  { id: 8, name: '磅', abbreviation: 'lb', unit_type: 'mass', unit_system: 'imperial', si_factor: 0.453592, is_si_base: false, is_common: false, display_order: 8, plural_form: null },
  { id: 9, name: '盎司', abbreviation: 'oz', unit_type: 'mass', unit_system: 'imperial', si_factor: 0.0283495, is_si_base: false, is_common: false, display_order: 9, plural_form: null },
  { id: 10, name: '毫升', abbreviation: 'cc', unit_type: 'volume', unit_system: 'metric', si_factor: 0.001, is_si_base: false, is_common: true, display_order: 10, plural_form: null },
  { id: 11, name: '茶匙', abbreviation: 'tsp', unit_type: 'volume', unit_system: 'vague', si_factor: 0.005, is_si_base: false, is_common: true, display_order: 11, plural_form: null },
  { id: 12, name: '汤匙', abbreviation: 'tbsp', unit_type: 'volume', unit_system: 'vague', si_factor: 0.015, is_si_base: false, is_common: true, display_order: 12, plural_form: null },
  { id: 13, name: '杯', abbreviation: 'cup', unit_type: 'volume', unit_system: 'vague', si_factor: 0.24, is_si_base: false, is_common: true, display_order: 13, plural_form: null },
  { id: 14, name: '份', abbreviation: '份', unit_type: 'count', unit_system: 'count', si_factor: 1, is_si_base: false, is_common: true, display_order: 14, plural_form: null },
  { id: 15, name: '包', abbreviation: '包', unit_type: 'count', unit_system: 'count', si_factor: 1, is_si_base: false, is_common: true, display_order: 15, plural_form: null },
]

/**
 * 基础单位换算关系（覆盖常用的质量/体积/模糊量单位间互转）。
 * is_bidirectional: true 表示双向换算，反向换算时为倒数。
 * precision: 建议保留的小数位数（前端展示用）。
 */
export const BASE_UNIT_CONVERSIONS = [
  { from_unit_id: 2, to_unit_id: 1, conversion_factor: 0.001, precision: 6, formula: null, is_bidirectional: true },
  { from_unit_id: 3, to_unit_id: 1, conversion_factor: 0.5, precision: 6, formula: null, is_bidirectional: true },
  { from_unit_id: 3, to_unit_id: 2, conversion_factor: 500, precision: 0, formula: null, is_bidirectional: true },
  { from_unit_id: 5, to_unit_id: 4, conversion_factor: 0.001, precision: 6, formula: null, is_bidirectional: true },
  { from_unit_id: 7, to_unit_id: 1, conversion_factor: 0.05, precision: 6, formula: null, is_bidirectional: true },
  { from_unit_id: 7, to_unit_id: 2, conversion_factor: 50, precision: 0, formula: null, is_bidirectional: true },
  { from_unit_id: 7, to_unit_id: 3, conversion_factor: 0.1, precision: 2, formula: null, is_bidirectional: true },
  { from_unit_id: 8, to_unit_id: 1, conversion_factor: 0.453592, precision: 4, formula: null, is_bidirectional: true },
  { from_unit_id: 9, to_unit_id: 2, conversion_factor: 28.3495, precision: 2, formula: null, is_bidirectional: true },
  { from_unit_id: 11, to_unit_id: 5, conversion_factor: 5, precision: 0, formula: null, is_bidirectional: true },
  { from_unit_id: 12, to_unit_id: 5, conversion_factor: 15, precision: 0, formula: null, is_bidirectional: true },
  { from_unit_id: 13, to_unit_id: 5, conversion_factor: 240, precision: 0, formula: null, is_bidirectional: true },
]

/**
 * 基础食材分类列表。
 * name 为英文标识符（与后端 seed 数据对齐），display_name 为中文展示名。
 */
export const BASE_CATEGORIES = [
  { id: 1, name: 'grains', display_name: '米面粮油', description: '谷物、米、面、油等', sort_order: 1 },
  { id: 2, name: 'vegetables', display_name: '蔬菜', description: '各类蔬菜', sort_order: 2 },
  { id: 3, name: 'fruits', display_name: '水果', description: '各类水果', sort_order: 3 },
  { id: 4, name: 'meat', display_name: '肉禽蛋', description: '猪牛羊肉、禽肉、蛋类', sort_order: 4 },
  { id: 5, name: 'seafood', display_name: '水产', description: '鱼虾蟹贝类', sort_order: 5 },
  { id: 6, name: 'dairy', display_name: '乳制品', description: '牛奶、酸奶、奶酪等', sort_order: 6 },
  { id: 7, name: 'soy', display_name: '豆制品', description: '豆腐、豆皮、豆奶等', sort_order: 7 },
  { id: 8, name: 'seasoning', display_name: '调味品', description: '盐、酱油、醋、香料等', sort_order: 8 },
  { id: 9, name: 'oil', display_name: '食用油', description: '植物油、动物油', sort_order: 9 },
  { id: 10, name: 'nuts', display_name: '坚果种子', description: '各类坚果和种子', sort_order: 10 },
  { id: 11, name: 'beverages', display_name: '饮料', description: '饮品、酒水', sort_order: 11 },
  { id: 12, name: 'others', display_name: '其他', description: '其他食材', sort_order: 12 },
  { id: 13, name: 'premade', display_name: '半成品', description: '预制菜、半成品', sort_order: 13 },
]

/**
 * 种子数据全量导入。
 * 幂等：检查 units 表是否有数据，已存在则跳过。
 */
export async function seedBasicData(): Promise<void> {
  if (await hasData('units')) {
    console.log('[seed] units already exist, skipping')
    return
  }
  console.log('[seed] importing basic units and categories...')

  await batchAdd('units', BASE_UNITS)
  await batchAdd('unit_conversions', BASE_UNIT_CONVERSIONS)
  await batchAdd('ingredient_categories', BASE_CATEGORIES)

  console.log('[seed] basic data imported successfully')
}

/**
 * 检查是否已完成初始化。
 * 以 units 表是否有数据为判据。
 */
export async function isInitialized(): Promise<boolean> {
  return hasData('units')
}
