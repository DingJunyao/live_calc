// USDA 营养素名称中英映射 + 食材解析（移植自后端 Python 实现）。
// 仅用于本地模式：把用户上传的原始 USDA zip 解析为可写入 IndexedDB 的结构。
// 与后端 app/services/usda/{nutrient_mapping,parser}.py 保持一致。

// 键 = USDA 原文名；值 = 中文名。来源：后端 nutrient_mapping.py（静态表，不走 AI 翻译）。
const NUTRIENT_TRANSLATIONS: Record<string, string> = {
  "Energy": "能量",
  "Protein": "蛋白质",
  "Total lipid (fat)": "脂肪",
  "Carbohydrate, by difference": "碳水化合物",
  "Fiber, total dietary": "膳食纤维",
  "Sugars, total including NLEA": "糖",
  "Sugars, added": "添加糖",
  "Water": "水分",
  "Ash": "灰分",
  "Alcohol, ethyl": "酒精",
  "Fatty acids, total saturated": "饱和脂肪酸",
  "Fatty acids, total monounsaturated": "单不饱和脂肪酸",
  "Fatty acids, total polyunsaturated": "多不饱和脂肪酸",
  "Fatty acids, total trans": "反式脂肪酸",
  "Fatty acids, total trans-monoenoic": "反式单烯脂肪酸",
  "Fatty acids, total trans-polyenoic": "反式多烯脂肪酸",
  "Sodium, Na": "钠",
  "Cholesterol": "胆固醇",
  "Calcium, Ca": "钙",
  "Iron, Fe": "铁",
  "Potassium, K": "钾",
  "Phosphorus, P": "磷",
  "Magnesium, Mg": "镁",
  "Zinc, Zn": "锌",
  "Selenium, Se": "硒",
  "Copper, Cu": "铜",
  "Manganese, Mn": "锰",
  "Iodine, I": "碘",
  "Fluoride, F": "氟",
  "Chromium, Cr": "铬",
  "Molybdenum, Mo": "钼",
  "Vitamin A, IU": "维生素A (IU)",
  "Vitamin A, RAE": "维生素A (RAE)",
  "Retinol": "视黄醇",
  "Carotene, beta": "β-胡萝卜素",
  "Carotene, alpha": "α-胡萝卜素",
  "Cryptoxanthin, beta": "β-隐黄素",
  "Lycopene": "番茄红素",
  "Lutein + zeaxanthin": "叶黄素+玉米黄质",
  "Vitamin D (D2 + D3), IU": "维生素D (IU)",
  "Vitamin D (D2 + D3)": "维生素D",
  "Vitamin D2 (ergocalciferol)": "维生素D2",
  "Vitamin D3 (cholecalciferol)": "维生素D3",
  "Vitamin E (alpha-tocopherol)": "维生素E",
  "Vitamin K (phylloquinone)": "维生素K",
  "Thiamin": "维生素B1（硫胺素）",
  "Riboflavin": "维生素B2（核黄素）",
  "Niacin": "维生素B3（烟酸）",
  "Pantothenic acid": "维生素B5（泛酸）",
  "Vitamin B-6": "维生素B6",
  "Folate, total": "叶酸",
  "Folate, food": "食物叶酸",
  "Folic acid": "叶酸（合成）",
  "Folate, DFE": "叶酸 (DFE)",
  "Vitamin B-12": "维生素B12",
  "Vitamin C, total ascorbic acid": "维生素C",
  "Choline, total": "胆碱",
  "Betaine": "甜菜碱",
  "Biotin": "生物素",
  "Tryptophan": "色氨酸",
  "Threonine": "苏氨酸",
  "Isoleucine": "异亮氨酸",
  "Leucine": "亮氨酸",
  "Lysine": "赖氨酸",
  "Methionine": "蛋氨酸",
  "Cystine": "胱氨酸",
  "Phenylalanine": "苯丙氨酸",
  "Tyrosine": "酪氨酸",
  "Valine": "缬氨酸",
  "Arginine": "精氨酸",
  "Histidine": "组氨酸",
  "Alanine": "丙氨酸",
  "Aspartic acid": "天冬氨酸",
  "Glutamic acid": "谷氨酸",
  "Glycine": "甘氨酸",
  "Proline": "脯氨酸",
  "Serine": "丝氨酸",
  "Caffeine": "咖啡因",
  "Theobromine": "可可碱",
  "Starch": "淀粉",
  "Sucrose": "蔗糖",
  "Glucose": "葡萄糖",
  "Fructose": "果糖",
  "Lactose": "乳糖",
  "Maltose": "麦芽糖",
  "Sugars, Total": "总糖",
  "Total Sugars": "总糖",
  "Fiber, insoluble": "不溶性膳食纤维",
  "Fiber, soluble": "可溶性膳食纤维",
  "Cysteine": "半胱氨酸",
  "Nitrogen": "氮",
  "Sulfur, S": "硫",
  "Citric acid": "柠檬酸",
  "Malic acid": "苹果酸",
  "Oxalic acid": "草酸",
  "Phytosterols": "植物甾醇",
  "Tocopherol, beta": "β-生育酚",
  "Tocopherol, delta": "δ-生育酚",
  "Tocopherol, gamma": "γ-生育酚",
  "Tocotrienol, alpha": "α-生育三烯酚",
  "Tocotrienol, beta": "β-生育三烯酚",
  "Tocotrienol, delta": "δ-生育三烯酚",
  "Tocotrienol, gamma": "γ-生育三烯酚",
  "Vitamin D (D2 + D3), International Units": "维生素D (IU)",
  "Vitamin D4": "维生素D4",
  "25-hydroxycholecalciferol": "25-羟基维生素D3",
  "Vitamin K (Dihydrophylloquinone)": "维生素K（二氢叶绿醌）",
  "Vitamin K (Menaquinone-4)": "维生素K2（甲萘醌-4）",
  "Vitamin B-12, added": "维生素B12（添加）",
  "Vitamin E, added": "维生素E（添加）",
  "Carotene, gamma": "γ-胡萝卜素",
  "Cryptoxanthin, alpha": "α-隐黄素",
  "Lutein": "叶黄素",
  "Zeaxanthin": "玉米黄质",
  "cis-Lutein/Zeaxanthin": "顺式叶黄素/玉米黄质",
  "cis-Lycopene": "顺式番茄红素",
  "cis-beta-Carotene": "顺式β-胡萝卜素",
  "trans-Lycopene": "反式番茄红素",
  "trans-beta-Carotene": "反式β-胡萝卜素",
  "Phytoene": "八氢番茄红素",
  "Phytofluene": "六氢番茄红素",
  "Hydroxyproline": "羟脯氨酸",
  "Choline, free": "游离胆碱",
  "Choline, from glycerophosphocholine": "甘油磷胆碱来源胆碱",
  "Choline, from phosphocholine": "磷酸胆碱来源胆碱",
  "Choline, from phosphotidyl choline": "磷脂酰胆碱来源胆碱",
  "Choline, from sphingomyelin": "鞘磷脂来源胆碱",
  "Total dietary fiber (AOAC 2011.25)": "总膳食纤维 (AOAC 2011.25)",
  "High Molecular Weight Dietary Fiber (HMWDF)": "高分子量膳食纤维",
  "Low Molecular Weight Dietary Fiber (LMWDF)": "低分子量膳食纤维",
  "Carbohydrate, by summation": "碳水化合物（求和法）",
  "Energy (Atwater General Factors)": "热量（Atwater 通用系数）",
  "Energy (Atwater Specific Factors)": "热量（Atwater 特定系数）",
  "Total fat (NLEA)": "总脂肪 (NLEA)",
  "Specific Gravity": "比重",
  "Pyruvic acid": "丙酮酸",
  "Quinic acid": "奎宁酸",
  "Cobalt, Co": "钴",
  "Nickel, Ni": "镍",
  "Boron, B": "硼",
  "Beta-sitosterol": "β-谷固醇",
  "Beta-sitostanol": "β-谷烷醇",
  "Brassicasterol": "菜籽固醇",
  "Campestanol": "菜烷醇",
  "Campesterol": "菜固醇",
  "Stigmasterol": "豆固醇",
  "Stigmastadiene": "豆甾二烯",
  "Phytosterols, other": "其他植物固醇",
  "Delta-5-avenasterol": "Δ5-燕麦固醇",
  "Delta-7-Stigmastenol": "Δ7-豆甾烷醇",
  "Ergosta-5,7-dienol": "麦角甾-5,7-二烯醇",
  "Ergosta-7,22-dienol": "麦角甾-7,22-二烯醇",
  "Ergosta-7-enol": "麦角甾-7-烯醇",
  "Ergosterol": "麦角固醇",
  "Daidzein": "大豆苷元",
  "Daidzin": "大豆苷",
  "Genistein": "染料木黄酮",
  "Genistin": "染料木苷",
  "Glycitin": "黄豆黄苷",
  "Beta-glucan": "β-葡聚糖",
  "Glutathione": "谷胱甘肽",
  "Ergothioneine": "麦角硫因",
  "Raffinose": "棉子糖",
  "Stachyose": "水苏糖",
  "Verbascose": "毛蕊花糖",
  "Resistant starch": "抗性淀粉",
  "Galactose": "半乳糖",
  "Maltodextrins": "麦芽糊精",
  "Fatty acids, total trans-dienoic": "反式二烯脂肪酸",
  "10-Formyl folic acid (10HCOFA)": "10-甲酰叶酸",
  "5-Formyltetrahydrofolic acid (5-HCOH4": "5-甲酰四氢叶酸",
  "5-methyl tetrahydrofolate (5-MTHF)": "5-甲基四氢叶酸",
}

// 小写化索引，使查找不区分大小写（与后端 _LOWER_INDEX 语义一致）。
const _LOWER_INDEX: Map<string, string> = new Map(
  Object.entries(NUTRIENT_TRANSLATIONS).map(([k, v]) => [k.toLowerCase(), v])
)

/** 把 USDA 营养素英文名映射成中文；未命中返回 null。 */
export function mapNutrientName(nameEn: string): string | null {
  if (!nameEn) return null
  return _LOWER_INDEX.get(nameEn.trim().toLowerCase()) ?? null
}

const _TYPE_PRIORITY: Record<string, number> = { foundation: 0, sr_legacy: 1 }

export interface ParsedNutrient {
  nutrient_no: string | null
  name: string
  name_zh: string | null
  amount: number
  unit_name: string
}

export interface ParsedFood {
  fdc_id: number | null
  data_type: string
  description: string
  publication_date: string | null
  nutrients: ParsedNutrient[]
}

/**
 * 把一条 USDA raw 食材解析为内部结构（含 nutrients 子表）。
 * 兼容新版（foodNutrients 每项含 nutrient 子对象）与旧版/简化（foodComponents）。
 */
export function parseUsdaFood(raw: any, dataType: string): ParsedFood {
  if (raw == null) {
    return { fdc_id: 0, data_type: dataType, description: '', publication_date: null, nutrients: [] }
  }
  const nutrients: ParsedNutrient[] = []
  const foodNutrients: any[] = raw.foodNutrients || raw.foodComponents || []
  for (const fn of foodNutrients) {
    if (typeof fn !== "object" || fn === null) continue
    const nutrient = fn.nutrient || fn
    if (typeof nutrient !== "object" || nutrient === null) continue
    const name: string | undefined = nutrient.name
    if (!name) continue
    const nutrientNo = nutrient.number
    nutrients.push({
      nutrient_no: nutrientNo != null ? String(nutrientNo) : null,
      name,
      name_zh: mapNutrientName(name),
      amount: Number(fn.amount ?? 0) || 0,
      unit_name: fn.unitName || nutrient.unitName || '',
    })
  }
  return {
    fdc_id: raw.fdcId ?? null,
    data_type: dataType,
    description: (raw.description || '').trim(),
    publication_date: raw.publicationDate ?? null,
    nutrients,
  }
}

function foodSortKey(food: ParsedFood): [number, number] {
  return [_TYPE_PRIORITY[food.data_type] ?? 99, -food.nutrients.length]
}

/** 同 description 只留最优一条（foundation 优先，其次营养素更多）。 */
export function dedupeFoods(foods: ParsedFood[]): ParsedFood[] {
  const best = new Map<string, ParsedFood>()
  for (const food of foods) {
    const desc = food.description
    if (!desc) continue
    const cur = best.get(desc)
    if (!cur || cmp(foodSortKey(food), foodSortKey(cur)) < 0) {
      best.set(desc, food)
    }
  }
  return [...best.values()]
}

function cmp(a: [number, number], b: [number, number]): number {
  if (a[0] !== b[0]) return a[0] - b[0]
  return a[1] - b[1]
}

/** 把原始 USDA JSON 顶层结构解析为食材列表（去重后）。
 *  兼容 FoundationFoods / SRLegacyFoods 顶层键，以及顶层 list。 */
export function parseUsdaDataset(data: any): ParsedFood[] {
  const keyMap: Record<string, string> = { FoundationFoods: 'foundation', SRLegacyFoods: 'sr_legacy' }
  const foods: ParsedFood[] = []
  if (Array.isArray(data)) {
    for (const r of data) {
      if (r != null) foods.push(parseUsdaFood(r, 'foundation'))
    }
  } else if (data && typeof data === "object") {
    for (const key of Object.keys(keyMap)) {
      const arr = data[key]
      if (Array.isArray(arr)) {
        const dtype = keyMap[key]
        for (const r of arr) {
          if (r != null) foods.push(parseUsdaFood(r, dtype))
        }
      }
    }
  }
  return dedupeFoods(foods)
}
