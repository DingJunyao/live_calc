"""行政区划种子数据与服务。

在启动时或管理接口调用时，将中国的省级/市级/县级行政区划数据
及全球 ISO 3166-1 国家数据写入 administrative_regions 表。

模式参考 ``allergen_seed.py``：
- ``ensure_administrative_regions`` 供启动时幂等调用（空表才创建）；
- ``need_region_seed`` 供管理按钮显隐判断。
"""

import json
import logging
import urllib.request
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.administrative_region import AdministrativeRegion

logger = logging.getLogger(__name__)

# ── ISO 3166-1 国家中文名称 ──
COUNTRY_NAMES_ZH: dict[str, str] = {
    "AF": "阿富汗", "AX": "奥兰", "AL": "阿尔巴尼亚", "DZ": "阿尔及利亚",
    "AS": "美属萨摩亚", "AD": "安道尔", "AO": "安哥拉", "AI": "安圭拉",
    "AQ": "南极洲", "AG": "安提瓜和巴布达", "AR": "阿根廷", "AM": "亚美尼亚",
    "AW": "阿鲁巴", "AU": "澳大利亚", "AT": "奥地利", "AZ": "阿塞拜疆",
    "BS": "巴哈马", "BH": "巴林", "BD": "孟加拉国", "BB": "巴巴多斯",
    "BY": "白俄罗斯", "BE": "比利时", "BZ": "伯利兹", "BJ": "贝宁",
    "BM": "百慕大", "BT": "不丹", "BO": "玻利维亚", "BQ": "荷兰加勒比区",
    "BA": "波斯尼亚和黑塞哥维那", "BW": "波札那", "BV": "布韦岛", "BR": "巴西",
    "IO": "英属印度洋领地", "BN": "汶莱", "BG": "保加利亚", "BF": "布基纳法索",
    "BI": "布隆迪", "CV": "佛得角", "KH": "柬埔寨", "CM": "喀麦隆",
    "CA": "加拿大", "KY": "开曼群岛", "CF": "中非共和国", "TD": "乍得",
    "CL": "智利", "CN": "中国", "CX": "圣诞岛", "CC": "科科斯（基林）群岛",
    "CO": "哥伦比亚", "KM": "葛摩", "CG": "刚果", "CD": "刚果（金）",
    "CK": "库克群岛", "CR": "哥斯达黎加", "CI": "科特迪瓦", "HR": "克罗地亚",
    "CU": "古巴", "CW": "库拉索", "CY": "塞浦路斯", "CZ": "捷克",
    "DK": "丹麦", "DJ": "吉布提", "DM": "多米尼克", "DO": "多米尼加",
    "EC": "厄瓜多尔", "EG": "埃及", "SV": "萨尔瓦多", "GQ": "赤道几内亚",
    "ER": "厄立特里亚", "EE": "爱沙尼亚", "SZ": "斯威士兰", "ET": "埃塞俄比亚",
    "FK": "福克兰群岛", "FO": "法罗群岛", "FJ": "斐济", "FI": "芬兰",
    "FR": "法国", "GF": "法属圭亚那", "PF": "法属波利尼西亚", "TF": "法属南部领地",
    "GA": "加蓬", "GM": "冈比亚", "GE": "格鲁吉亚", "DE": "德国",
    "GH": "加纳", "GI": "直布罗陀", "GR": "希腊", "GL": "格陵兰",
    "GD": "格林纳达", "GP": "瓜德罗普", "GU": "关岛", "GT": "危地马拉",
    "GG": "根西", "GN": "几内亚", "GW": "几内亚比绍", "GY": "圭亚那",
    "HT": "海地", "HM": "赫德岛和麦克唐纳群岛", "VA": "梵蒂冈", "HN": "洪都拉斯",
    "HK": "中国香港", "HU": "匈牙利", "IS": "冰岛", "IN": "印度",
    "ID": "印度尼西亚", "IR": "伊朗", "IQ": "伊拉克", "IE": "爱尔兰",
    "IM": "曼岛", "IL": "以色列", "IT": "意大利", "JM": "牙买加",
    "JP": "日本", "JE": "泽西", "JO": "约旦", "KZ": "哈萨克斯坦",
    "KE": "肯尼亚", "KI": "基里巴斯", "KP": "朝鲜", "KR": "韩国",
    "KW": "科威特", "KG": "吉尔吉斯斯坦", "LA": "老挝", "LV": "拉脱维亚",
    "LB": "黎巴嫩", "LS": "莱索托", "LR": "利比里亚", "LY": "利比亚",
    "LI": "列支敦士登", "LT": "立陶宛", "LU": "卢森堡", "MO": "中国澳门",
    "MG": "马达加斯加", "MW": "马拉维", "MY": "马来西亚", "MV": "马尔代夫",
    "ML": "马里", "MT": "马耳他", "MH": "马绍尔群岛", "MQ": "马提尼克",
    "MR": "毛里塔尼亚", "MU": "毛里求斯", "YT": "马约特", "MX": "墨西哥",
    "FM": "密克罗尼西亚联邦", "MD": "摩尔多瓦", "MC": "摩纳哥", "MN": "蒙古",
    "ME": "黑山", "MS": "蒙特塞拉特", "MA": "摩洛哥", "MZ": "莫桑比克",
    "MM": "缅甸", "NA": "纳米比亚", "NR": "诺鲁", "NP": "尼泊尔",
    "NC": "新喀里多尼亚", "NZ": "新西兰", "NI": "尼加拉瓜", "NE": "尼日尔",
    "NG": "尼日利亚", "NU": "纽埃", "NF": "诺福克岛", "MK": "北马其顿",
    "MP": "北马里亚纳群岛", "NO": "挪威", "OM": "阿曼", "PK": "巴基斯坦",
    "PW": "帛琉", "PS": "巴勒斯坦", "PA": "巴拿马", "PG": "巴布亚新几内亚",
    "PY": "巴拉圭", "PE": "秘鲁", "PH": "菲律宾", "PN": "皮特凯恩群岛",
    "PL": "波兰", "PT": "葡萄牙", "PR": "波多黎各", "QA": "卡塔尔",
    "RE": "留尼汪", "RO": "罗马尼亚", "RU": "俄罗斯", "RW": "卢旺达",
    "BL": "圣巴泰勒米", "SH": "圣赫勒拿", "KN": "圣克里斯多福及尼维斯", "LC": "圣卢西亚",
    "MF": "法属圣马丁", "PM": "圣皮埃尔和密克隆", "VC": "圣文森特和格林纳丁斯", "WS": "萨摩亚",
    "SM": "圣马力诺", "ST": "圣多美和普林西比", "SA": "沙特阿拉伯", "SN": "塞内加尔",
    "RS": "塞尔维亚", "SC": "塞舌尔", "SL": "塞拉利昂", "SG": "新加坡",
    "SX": "荷属圣马丁", "SK": "斯洛伐克", "SI": "斯洛文尼亚", "SB": "所罗门群岛",
    "SO": "索马里", "ZA": "南非", "GS": "南乔治亚岛和南桑威奇群岛", "SS": "南苏丹",
    "ES": "西班牙", "LK": "斯里兰卡", "SD": "苏丹", "SR": "苏里南",
    "SJ": "斯瓦尔巴德群岛", "SE": "瑞典", "CH": "瑞士", "SY": "叙利亚",
    "TW": "中国台湾", "TZ": "坦桑尼亚", "TH": "泰国", "TL": "东帝汶",
    "TG": "多哥", "TK": "托克劳", "TO": "汤加", "TT": "特立尼达和多巴哥",
    "TN": "突尼斯", "TR": "土耳其", "TM": "土库曼斯坦", "TC": "特克斯和凯科斯群岛",
    "TV": "图瓦卢", "UG": "乌干达", "UA": "乌克兰", "AE": "阿联酋",
    "GB": "英国", "US": "美国", "UM": "美属小离岛", "UY": "乌拉圭",
    "UZ": "乌兹别克斯坦", "VU": "瓦努阿图", "VE": "委内瑞拉", "VN": "越南",
    "VG": "英属维尔京群岛", "VI": "美属维尔京群岛", "WF": "瓦利斯群岛和富图纳群岛",
    "EH": "西撒哈拉", "YE": "也门", "ZM": "赞比亚", "ZW": "津巴布韦",
}

# ── 数据源 URLs ──
CHINA_DATA_URL = (
    "https://raw.githubusercontent.com/modood/Administrative-divisions"
    "-of-China/master/dist/pca-code.json"
)
COUNTRIES_DATA_URL = (
    "https://raw.githubusercontent.com/lukes/ISO-3166-Countries-with"
    "-Regional-Codes/master/all/all.json"
)

# ── 本地缓存路径 ──
CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "regions"
CHINA_CACHE = CACHE_DIR / "china_pca.json"
COUNTRIES_CACHE = CACHE_DIR / "countries.json"


# ═══════════════════════════════════════════════════════════════════
#  数据获取
# ═══════════════════════════════════════════════════════════════════

def _ensure_cache_dir() -> None:
    """确保缓存目录存在。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _fetch_json(url: str, cache_path: Path, timeout: int = 15):
    """从 URL 获取 JSON，缓存到本地；URL 失败时尝试读缓存。

    返回 Python 对象（list / dict），或 ``None``（全部失败时）。
    """
    # 1) 尝试从 URL 获取
    if url:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; RegionSeed/1.0)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            # 写入缓存
            _ensure_cache_dir()
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except Exception as exc:
            logger.warning("从 %s 获取失败: %s，尝试本地缓存", url, exc)

    # 2) 尝试从本地缓存读取
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("读取缓存 %s 失败: %s", cache_path, exc)
    else:
        logger.info("缓存文件不存在: %s", cache_path)

    return None


def _fetch_china_data():
    """获取中国三级行政区划数据（省/市/区县）。"""
    return _fetch_json(CHINA_DATA_URL, CHINA_CACHE)


def _fetch_countries_data():
    """获取 ISO 3166-1 全球国家列表。"""
    return _fetch_json(COUNTRIES_DATA_URL, COUNTRIES_CACHE)


# ═══════════════════════════════════════════════════════════════════
#  核心 upsert
# ═══════════════════════════════════════════════════════════════════

def _upsert_region(
    db: Session,
    code: str,
    name: str,
    level: int,
    parent_id: int | None = None,
    iso_country: str | None = None,
    path: str | None = None,
    name_en: str | None = None,
) -> tuple[int, str]:
    """Upsert 单条行政区划记录。

    按 ``code`` 去重：存在且 ``is_active`` → skip；
    存在但软删 → reactivate（更新字段）；
    不存在 → create。

    Returns
        (id, action) 其中 action ∈ {"created", "reactivated", "skipped"}
    """
    existing = (
        db.query(AdministrativeRegion)
        .filter(AdministrativeRegion.code == code)
        .first()
    )

    if existing:
        if not existing.is_active:
            # 复活软删行
            existing.is_active = True
            existing.name = name
            existing.level = level
            if parent_id is not None:
                existing.parent_id = parent_id
            if iso_country is not None:
                existing.iso_country = iso_country
            if path is not None:
                existing.path = path
            if name_en is not None:
                existing.name_en = name_en
            db.flush()
            return existing.id, "reactivated"

        # active 行：字段变化则刷新（支持 re-seed，如英文 name → 中文）
        if name and existing.name != name:
            existing.name = name
        if name_en is not None and existing.name_en != name_en:
            existing.name_en = name_en
        if level is not None and existing.level != level:
            existing.level = level
        if parent_id is not None and existing.parent_id != parent_id:
            existing.parent_id = parent_id
        if iso_country is not None and existing.iso_country != iso_country:
            existing.iso_country = iso_country
        if path is not None and existing.path != path:
            existing.path = path
        db.flush()
        return existing.id, "skipped"

    region = AdministrativeRegion(
        code=code,
        name=name,
        name_en=name_en,
        parent_id=parent_id,
        level=level,
        iso_country=iso_country,
        path=path,
        is_active=True,
    )
    db.add(region)
    db.flush()
    return region.id, "created"


def _process_countries(db: Session, countries_data: list | None, created: int,
                       skipped: int) -> tuple[dict[str, int], int, int]:
    """Upsert 全球国家列表。返回 {alpha2->id}, created, skipped。"""
    country_id_map: dict[str, int] = {}

    if not countries_data:
        return country_id_map, created, skipped

    for entry in countries_data:
        alpha2 = entry.get("alpha-2", "") or ""
        name = entry.get("name", "") or ""
        if not alpha2 or not name:
            continue
        name_zh = COUNTRY_NAMES_ZH.get(alpha2, name)  # 缺中文映射回落英文
        _id, action = _upsert_region(
            db,
            code=alpha2,
            name=name_zh,
            level=0,
            iso_country=alpha2,
            path=alpha2,
            name_en=name,
        )
        country_id_map[alpha2] = _id
        if action in ("created", "reactivated"):
            created += 1
        elif action == "skipped":
            skipped += 1

    return country_id_map, created, skipped


def _process_china_provinces(db: Session, china_data: list | None,
                             cn_id: int, created: int, skipped: int,
                             ) -> tuple[int, int]:
    """处理中国省/市/区县三级数据。返回 (created, skipped)。"""
    if not china_data:
        return created, skipped

    for prov in china_data:
        prov_code: str = prov["code"]
        prov_name: str = prov["name"]

        # 省（level=1）
        prov_id, action = _upsert_region(
            db,
            code=prov_code,
            name=prov_name,
            level=1,
            parent_id=cn_id,
            iso_country="CN",
            path=f"CN/{prov_code}",
        )
        if action in ("created", "reactivated"):
            created += 1
        elif action == "skipped":
            skipped += 1

        # 市（level=2）
        for city in prov.get("children", []):
            city_code: str = city["code"]
            city_name: str = city["name"]

            city_id, action = _upsert_region(
                db,
                code=city_code,
                name=city_name,
                level=2,
                parent_id=prov_id,
                iso_country="CN",
                path=f"CN/{prov_code}/{city_code}",
            )
            if action == "created":
                created += 1
            elif action == "skipped":
                skipped += 1

            # 区/县（level=3）
            for county in city.get("children", []):
                county_code: str = county["code"]
                county_name: str = county["name"]

                _, action = _upsert_region(
                    db,
                    code=county_code,
                    name=county_name,
                    level=3,
                    parent_id=city_id,
                    iso_country="CN",
                    path=f"CN/{prov_code}/{city_code}/{county_code}",
                )
                if action == "created":
                    created += 1
                elif action == "skipped":
                    skipped += 1

    return created, skipped


def upsert_administrative_regions(
    db: Session,
    china_data: list | None = None,
    countries_data: list | None = None,
) -> dict:
    """幂等写入行政区划数据。

    参数
    ----------
    china_data, countries_data :
        可选注入的数据（用于测试），为 ``None`` 时自动从 URL 或本地缓存获取。

    返回
    -------
    ``{created, skipped, errors}``
    """
    created = 0
    skipped = 0
    errors = 0

    # 1) 加载数据
    if china_data is None:
        china_data = _fetch_china_data()
    if countries_data is None:
        countries_data = _fetch_countries_data()

    if not china_data:
        logger.error("中国行政区划数据不可用，跳过 seed")
        errors += 1
        return {"created": created, "skipped": skipped, "errors": errors}

    # 2) 全球国家
    country_id_map, created, skipped = _process_countries(
        db, countries_data, created, skipped,
    )

    # 3) 确保中国存在
    cn_id = country_id_map.get("CN")
    if not cn_id:
        cn_id, action = _upsert_region(
            db,
            code="CN",
            name="中国",
            level=0,
            iso_country="CN",
            path="CN",
            name_en="China",
        )
        if action in ("created", "reactivated"):
            created += 1
        elif action == "skipped":
            skipped += 1

    # 4) 中国省/市/区县
    created, skipped = _process_china_provinces(
        db, china_data, cn_id, created, skipped,
    )

    db.commit()
    logger.info(
        "行政区划 upsert 完成：新建 %s，跳过 %s，错误 %s",
        created, skipped, errors,
    )
    return {"created": created, "skipped": skipped, "errors": errors}


# ═══════════════════════════════════════════════════════════════════
#  启动 & 判断
# ═══════════════════════════════════════════════════════════════════

def ensure_administrative_regions(db: Session) -> None:
    """启动时调用：中国省级数据缺失则补齐。

    幂等——首次启动时（表空）全量 seed，之后只做 count 检查即跳过。
    """
    existing = (
        db.query(AdministrativeRegion)
        .filter(
            AdministrativeRegion.level == 1,
            AdministrativeRegion.iso_country == "CN",
            AdministrativeRegion.is_active == True,
        )
        .count()
    )
    if existing > 0:
        logger.info("中国省级行政区划已存在（%s 个），跳过初始化", existing)
        return
    result = upsert_administrative_regions(db)
    logger.info("行政区划初始化完成：%s", result)


def need_region_seed(db: Session) -> bool:
    """判断是否需要 seed（中国省级数据缺失即需要）。"""
    count = (
        db.query(AdministrativeRegion)
        .filter(
            AdministrativeRegion.level == 1,
            AdministrativeRegion.iso_country == "CN",
            AdministrativeRegion.is_active == True,
        )
        .count()
    )
    return count == 0
