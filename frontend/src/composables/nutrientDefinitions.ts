// composables/nutrientDefinitions.ts
// 营养素定义公共模块（DRY）：从 ProductDetail/IngredientDetail 抽离。
// 能量行的 defaultUnit 由 buildNutrientDefinitions 参数化，跟随用户能量单位偏好；
// 其它营养素保持各自习惯单位（蛋白质 g、钙 mg、硒 μg…）。

export interface NutrientDef {
  key: string
  label: string
  units: string[]
  defaultUnit: string
}

// 基础定义（defaultUnit 在 buildNutrientDefinitions 中填充）
const BASE_DEFS: Omit<NutrientDef, 'defaultUnit'>[] = [
  { key: 'energy', label: '能量', units: ['kcal', 'kJ'] },
  { key: 'protein', label: '蛋白质', units: ['g', 'mg'] },
  { key: 'fat', label: '脂肪', units: ['g', 'mg'] },
  { key: 'carbohydrate', label: '碳水化合物', units: ['g', 'mg'] },
  { key: 'fiber', label: '膳食纤维', units: ['g'] },
  { key: 'calcium', label: '钙', units: ['mg', 'μg', 'g'] },
  { key: 'iron', label: '铁', units: ['mg', 'μg'] },
  { key: 'sodium', label: '钠', units: ['mg', 'g'] },
  { key: 'potassium', label: '钾', units: ['mg', 'g'] },
  { key: 'vitamin_a_rae', label: '维生素A', units: ['μg', 'IU', 'mg'] },
  { key: 'vitamin_c', label: '维生素C', units: ['mg', 'g'] },
  { key: 'vitamin_b1', label: '维生素B1', units: ['mg', 'μg'] },
  { key: 'vitamin_b2', label: '维生素B2', units: ['mg', 'μg'] },
  { key: 'vitamin_b12', label: '维生素B12', units: ['μg', 'mg'] },
  { key: 'vitamin_d', label: '维生素D', units: ['μg', 'IU'] },
  { key: 'vitamin_e', label: '维生素E', units: ['mg', 'IU'] },
  { key: 'vitamin_k', label: '维生素K', units: ['μg', 'mg'] },
  { key: 'magnesium', label: '镁', units: ['mg', 'g'] },
  { key: 'zinc', label: '锌', units: ['mg', 'μg'] },
  { key: 'selenium', label: '硒', units: ['μg', 'mg'] },
  { key: 'cholesterol', label: '胆固醇', units: ['mg', 'g'] },
  { key: 'saturated_fat', label: '饱和脂肪', units: ['g', 'mg'] },
  { key: 'folate', label: '叶酸', units: ['μg', 'mg'] },
  { key: 'phosphorus', label: '磷', units: ['mg', 'g'] },
  { key: 'copper', label: '铜', units: ['mg', 'μg'] },
  { key: 'manganese', label: '锰', units: ['mg', 'μg'] },
  { key: 'vitamin_b6', label: '维生素B6', units: ['mg', 'μg'] },
  { key: 'pantothenic_acid', label: '维生素B5', units: ['mg'] },
  { key: 'monounsaturated_fat', label: '单不饱和脂肪', units: ['g', 'mg'] },
  { key: 'polyunsaturated_fat', label: '多不饱和脂肪', units: ['g', 'mg'] },
]

const DEFAULT_UNIT_BY_KEY: Record<string, string> = {
  energy: 'kcal',
  protein: 'g', fat: 'g', carbohydrate: 'g', fiber: 'g',
  calcium: 'mg', iron: 'mg', sodium: 'mg', potassium: 'mg',
  vitamin_a_rae: 'μg', vitamin_c: 'mg', vitamin_b1: 'mg', vitamin_b2: 'mg',
  vitamin_b12: 'μg', vitamin_d: 'μg', vitamin_e: 'mg', vitamin_k: 'μg',
  magnesium: 'mg', zinc: 'mg', selenium: 'μg', cholesterol: 'mg',
  saturated_fat: 'g', folate: 'μg', phosphorus: 'mg', copper: 'mg',
  manganese: 'mg', vitamin_b6: 'mg', pantothenic_acid: 'mg',
  monounsaturated_fat: 'g', polyunsaturated_fat: 'g',
}

export function buildNutrientDefinitions(energyUnit: 'kcal' | 'kJ' = 'kcal'): NutrientDef[] {
  return BASE_DEFS.map(d => ({
    ...d,
    defaultUnit: d.key === 'energy' ? energyUnit : DEFAULT_UNIT_BY_KEY[d.key],
  }))
}
