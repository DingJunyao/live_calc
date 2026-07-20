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
        _id, action = _upsert_region(
            db,
            code=alpha2,
            name=name,
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
