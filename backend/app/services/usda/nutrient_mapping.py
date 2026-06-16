"""USDA 营养素名称中英映射表。

导入 USDA 营养素时，把英文 nutrient name 映射成中文。
营养素名不走 AI 翻译，统一查这张静态表。

数据来源：HowToCook_json_organizer/scripts/build_usda_data.py 中的
NUTRIENT_TRANSLATIONS 字典（完整复制，保持参考项目的键格式与中文用词）。

注：与 live_calc 核心营养素对应的条目，中文值已对齐到 live_calc 用词
（见 nutrition_import_service.py 的 CORE_DISPLAY_MAP）。主要差异：
参考项目把 "Energy" 译为「热量」，live_calc 体系统一用「能量」，此处改为「能量」。
Atwater 通用/特定系数等变体仍保留「热量（...）」字样，作为别名供
nutrition_import_service 的 CORE_DISPLAY_MAP 归一化到「能量」。
"""

# 键 = USDA 原文名（保持参考项目的键格式）；
# 值 = 中文名。
NUTRIENT_TRANSLATIONS: dict[str, str] = {
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

    # ---- 生育酚和生育三烯酚（维生素E家族） ----
    "Tocopherol, beta": "β-生育酚",
    "Tocopherol, delta": "δ-生育酚",
    "Tocopherol, gamma": "γ-生育酚",
    "Tocotrienol, alpha": "α-生育三烯酚",
    "Tocotrienol, beta": "β-生育三烯酚",
    "Tocotrienol, delta": "δ-生育三烯酚",
    "Tocotrienol, gamma": "γ-生育三烯酚",

    # ---- 维生素D补充 ----
    "Vitamin D (D2 + D3), International Units": "维生素D (IU)",
    "Vitamin D4": "维生素D4",
    "25-hydroxycholecalciferol": "25-羟基维生素D3",
    "Vitamin K (Dihydrophylloquinone)": "维生素K（二氢叶绿醌）",
    "Vitamin K (Menaquinone-4)": "维生素K2（甲萘醌-4）",
    "Vitamin B-12, added": "维生素B12（添加）",
    "Vitamin E, added": "维生素E（添加）",

    # ---- 类胡萝卜素补充 ----
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

    # ---- 氨基酸补充 ----
    "Hydroxyproline": "羟脯氨酸",

    # ---- 胆碱补充 ----
    "Choline, free": "游离胆碱",
    "Choline, from glycerophosphocholine": "甘油磷胆碱来源胆碱",
    "Choline, from phosphocholine": "磷酸胆碱来源胆碱",
    "Choline, from phosphotidyl choline": "磷脂酰胆碱来源胆碱",
    "Choline, from sphingomyelin": "鞘磷脂来源胆碱",

    # ---- 膳食纤维补充 ----
    "Total dietary fiber (AOAC 2011.25)": "总膳食纤维 (AOAC 2011.25)",
    "High Molecular Weight Dietary Fiber (HMWDF)": "高分子量膳食纤维",
    "Low Molecular Weight Dietary Fiber (LMWDF)": "低分子量膳食纤维",

    # ---- 碳水化合物/能量补充 ----
    "Carbohydrate, by summation": "碳水化合物（求和法）",
    "Energy (Atwater General Factors)": "热量（Atwater 通用系数）",
    "Energy (Atwater Specific Factors)": "热量（Atwater 特定系数）",
    "Total fat (NLEA)": "总脂肪 (NLEA)",
    "Specific Gravity": "比重",

    # ---- 有机酸补充 ----
    "Pyruvic acid": "丙酮酸",
    "Quinic acid": "奎宁酸",

    # ---- 矿物质补充 ----
    "Cobalt, Co": "钴",
    "Nickel, Ni": "镍",
    "Boron, B": "硼",

    # ---- 植物甾醇 ----
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

    # ---- 大豆异黄酮 ----
    "Daidzein": "大豆苷元",
    "Daidzin": "大豆苷",
    "Genistein": "染料木黄酮",
    "Genistin": "染料木苷",
    "Glycitin": "黄豆黄苷",

    # ---- 其他 ----
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

    # ---- 叶酸补充 ----
    "10-Formyl folic acid (10HCOFA)": "10-甲酰叶酸",
    "5-Formyltetrahydrofolic acid (5-HCOH4": "5-甲酰四氢叶酸",
    "5-methyl tetrahydrofolate (5-MTHF)": "5-甲基四氢叶酸",
}

# 小写化索引，使查找不区分大小写。
# 注意：若参考项目存在仅大小写不同的键（如 "Lutein" 与 "lutein"），
# 后出现的会覆盖前者；当前表中无此类冲突。
_LOWER_INDEX: dict[str, str] = {k.lower(): v for k, v in NUTRIENT_TRANSLATIONS.items()}


def map_nutrient_name(name_en: str) -> str | None:
    """把 USDA 营养素英文名映射成中文。

    对输入 ``.strip().lower()`` 后查小写索引，命中返回中文名，
    未命中返回 ``None``（调用方可自行回退，例如 AI 翻译或保留英文）。

    Args:
        name_en: USDA 营养素英文原名（如 ``"Energy"``、``"Fiber, total dietary"``）。

    Returns:
        中文名，或 ``None``（未在映射表中）。
    """
    if not name_en:
        return None
    return _LOWER_INDEX.get(name_en.strip().lower())
