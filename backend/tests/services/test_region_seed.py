"""行政区划 seed 服务测试。"""
import pytest

from app.models.administrative_region import AdministrativeRegion
from app.services.region_seed import (
    ensure_administrative_regions,
    need_region_seed,
    upsert_administrative_regions,
)

# ── 测试用小型样本数据 ──

SAMPLE_COUNTRIES = [
    {"alpha-2": "CN", "name": "China"},
    {"alpha-2": "US", "name": "United States of America"},
    {"alpha-2": "JP", "name": "Japan"},
]

SAMPLE_CHINA = [
    {
        "code": "11",
        "name": "北京市",
        "children": [
            {
                "code": "1101",
                "name": "市辖区",
                "children": [
                    {"code": "110101", "name": "东城区"},
                    {"code": "110102", "name": "西城区"},
                    {"code": "110105", "name": "朝阳区"},
                    {"code": "110108", "name": "海淀区"},
                ],
            },
        ],
    },
    {
        "code": "44",
        "name": "广东省",
        "children": [
            {
                "code": "4401",
                "name": "广州市",
                "children": [
                    {"code": "440103", "name": "荔湾区"},
                    {"code": "440104", "name": "越秀区"},
                    {"code": "440105", "name": "海珠区"},
                ],
            },
            {
                "code": "4403",
                "name": "深圳市",
                "children": [
                    {"code": "440303", "name": "罗湖区"},
                    {"code": "440304", "name": "福田区"},
                    {"code": "440305", "name": "南山区"},
                ],
            },
        ],
    },
]


def _clean_table(db):
    """清空 administrative_regions 表，隔离测试。"""
    db.query(AdministrativeRegion).delete()
    db.commit()


@pytest.fixture()
def clean_db(db_session):
    """每个测试前后清空表。"""
    _clean_table(db_session)
    yield db_session
    _clean_table(db_session)


# ── 测试用例 ──


def test_need_region_seed_returns_true_when_empty(clean_db):
    """空表时 need_region_seed 返回 True。"""
    db = clean_db
    assert need_region_seed(db) is True


def test_need_region_seed_returns_false_when_seeded(clean_db):
    """seeded 后 need_region_seed 返回 False。"""
    db = clean_db
    upsert_administrative_regions(
        db,
        china_data=SAMPLE_CHINA,
        countries_data=SAMPLE_COUNTRIES,
    )
    assert need_region_seed(db) is False


def test_upsert_creates_rows(clean_db):
    """全量 upsert 后断言数据量符合预期。"""
    db = clean_db

    result = upsert_administrative_regions(
        db,
        china_data=SAMPLE_CHINA,
        countries_data=SAMPLE_COUNTRIES,
    )

    assert result["errors"] == 0

    # 3 countries + 1 CN auto-created if not in list + 2 provinces
    # + 2 cities + 3 cities + ~7 counties
    total = db.query(AdministrativeRegion).count()
    assert total >= 18  # 3 countries + 2 provinces + 3 cities + 10 counties

    # 验证层级
    cn = db.query(AdministrativeRegion).filter(
        AdministrativeRegion.code == "CN",
    ).first()
    assert cn is not None
    assert cn.level == 0
    assert cn.path == "CN"
    assert cn.iso_country == "CN"

    # 验证省
    beijing = db.query(AdministrativeRegion).filter(
        AdministrativeRegion.code == "11",
    ).first()
    assert beijing is not None
    assert beijing.level == 1
    assert beijing.parent_id == cn.id
    assert beijing.path == "CN/11"

    # 验证市
    chaoyang_district = db.query(AdministrativeRegion).filter(
        AdministrativeRegion.code == "1101",
    ).first()
    assert chaoyang_district is not None
    assert chaoyang_district.level == 2
    assert chaoyang_district.parent_id == beijing.id

    # 验证区
    haidian = db.query(AdministrativeRegion).filter(
        AdministrativeRegion.code == "110108",
    ).first()
    assert haidian is not None
    assert haidian.level == 3
    assert haidian.path == "CN/11/1101/110108"


def test_upsert_idempotent(clean_db):
    """两次 upsert 后行数不变，且 skipped 计数正确。"""
    db = clean_db

    result1 = upsert_administrative_regions(
        db,
        china_data=SAMPLE_CHINA,
        countries_data=SAMPLE_COUNTRIES,
    )
    count1 = db.query(AdministrativeRegion).count()

    result2 = upsert_administrative_regions(
        db,
        china_data=SAMPLE_CHINA,
        countries_data=SAMPLE_COUNTRIES,
    )
    count2 = db.query(AdministrativeRegion).count()

    assert count1 == count2
    assert result2["errors"] == 0
    assert result2["created"] == 0  # 没有新行
    assert result2["skipped"] >= count1  # 全部跳过


def test_upsert_reactivates_soft_deleted(clean_db):
    """软删后 upsert 应复活而非新建。"""
    db = clean_db

    # 首次 upsert
    upsert_administrative_regions(
        db,
        china_data=SAMPLE_CHINA,
        countries_data=SAMPLE_COUNTRIES,
    )
    count1 = db.query(AdministrativeRegion).count()

    # 软删所有中国省份
    provinces = db.query(AdministrativeRegion).filter(
        AdministrativeRegion.level == 1,
        AdministrativeRegion.iso_country == "CN",
    ).all()
    for prov in provinces:
        prov.is_active = False
    db.commit()

    # 再次 upsert（应复活）
    result = upsert_administrative_regions(
        db,
        china_data=SAMPLE_CHINA,
        countries_data=SAMPLE_COUNTRIES,
    )

    count2 = db.query(AdministrativeRegion).count()
    assert count2 == count1  # 未新建行

    # 验证 soft-deleted rows 已复活
    active_provinces = db.query(AdministrativeRegion).filter(
        AdministrativeRegion.level == 1,
        AdministrativeRegion.iso_country == "CN",
        AdministrativeRegion.is_active == True,
    ).count()
    assert active_provinces == 2

    # 验证 reactivated 行计入 created（不是 skipped）
    # 注意：created 不区分新建/复活，所以不会为零
    assert result["created"] > 0


def test_ensure_creates_when_empty(clean_db):
    """ensure 在空表时创建数据。"""
    db = clean_db

    # 覆盖注入数据（让 ensure 使用测试数据而非走网络）
    import app.services.region_seed as rs

    original_fetch_china = rs._fetch_china_data
    original_fetch_countries = rs._fetch_countries_data
    rs._fetch_china_data = lambda: SAMPLE_CHINA
    rs._fetch_countries_data = lambda: SAMPLE_COUNTRIES

    try:
        ensure_administrative_regions(db)
        count = db.query(AdministrativeRegion).count()
        assert count >= 18
    finally:
        rs._fetch_china_data = original_fetch_china
        rs._fetch_countries_data = original_fetch_countries


def test_ensure_skips_when_already_populated(clean_db):
    """ensure 在已有数据时跳过（count 检测）。"""
    db = clean_db

    # 先插入一个占位行
    db.add(AdministrativeRegion(
        code="__test_placeholder",
        name="占位",
        level=1,
        iso_country="CN",
        is_active=True,
    ))
    db.commit()

    ensure_administrative_regions(db)

    # 表仍只有 1 行（ensure 对 level=1 & iso_country=CN 的行计数判断）
    count = db.query(AdministrativeRegion).filter(
        AdministrativeRegion.code != "__test_placeholder",
    ).count()
    assert count == 0  # ensure 不会创建新行


def test_ensure_idempotent(clean_db):
    """两次 ensure 后行数不变。"""
    db = clean_db

    import app.services.region_seed as rs

    original_fetch_china = rs._fetch_china_data
    original_fetch_countries = rs._fetch_countries_data
    rs._fetch_china_data = lambda: SAMPLE_CHINA
    rs._fetch_countries_data = lambda: SAMPLE_COUNTRIES

    try:
        ensure_administrative_regions(db)
        count1 = db.query(AdministrativeRegion).count()

        ensure_administrative_regions(db)
        count2 = db.query(AdministrativeRegion).count()

        assert count1 == count2
    finally:
        rs._fetch_china_data = original_fetch_china
        rs._fetch_countries_data = original_fetch_countries


def test_countries_upsert(clean_db):
    """全球国家插入正确。"""
    db = clean_db

    result = upsert_administrative_regions(
        db,
        china_data=SAMPLE_CHINA,
        countries_data=SAMPLE_COUNTRIES,
    )

    # CN, US, JP + possibly 广东省 duplicated if present in countries
    countries = db.query(AdministrativeRegion).filter(
        AdministrativeRegion.level == 0,
    ).all()
    codes = {c.code for c in countries}
    assert "CN" in codes
    assert "US" in codes
    assert "JP" in codes

    # 验证国家字段
    us = db.query(AdministrativeRegion).filter(
        AdministrativeRegion.code == "US",
    ).first()
    assert us.level == 0
    assert us.iso_country == "US"
    assert us.path == "US"
    assert us.name_en == "United States of America"


def test_path_format(clean_db):
    """验证 path 字段格式正确。"""
    db = clean_db

    upsert_administrative_regions(
        db,
        china_data=SAMPLE_CHINA,
        countries_data=SAMPLE_COUNTRIES,
    )

    # 查深圳南山区 path
    nanshan = db.query(AdministrativeRegion).filter(
        AdministrativeRegion.code == "440305",
    ).first()
    assert nanshan is not None
    assert nanshan.path == "CN/44/4403/440305"
