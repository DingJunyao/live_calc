"""Test country Chinese names in region_seed."""
import pytest


def test_country_names_zh_covers_common():
    """COUNTRY_NAMES_ZH 覆盖常见国家 + 数量足。"""
    from app.services.region_seed import COUNTRY_NAMES_ZH

    for alpha2, zh in [("CN", "中国"), ("US", "美国"), ("JP", "日本"), ("GB", "英国"), ("FR", "法国")]:
        assert COUNTRY_NAMES_ZH.get(alpha2) == zh, f"{alpha2} 缺中文映射"

    # 至少覆盖 ISO 3166-1 大部分成员
    assert len(COUNTRY_NAMES_ZH) >= 200


def test_process_countries_uses_zh_name(monkeypatch):
    """_process_countries：name 用中文，name_en 用英文；缺中文回落英文。"""
    from app.services import region_seed

    countries = [
        {"alpha-2": "CN", "name": "China"},
        {"alpha-2": "ZZ", "name": "Zzzland"},  # 无中文映射，回落英文
    ]

    captured = []

    def fake_upsert(db, code, name, level, **kw):
        captured.append((code, name, kw.get("name_en")))
        return 1, "created"

    monkeypatch.setattr(region_seed, "_upsert_region", fake_upsert)
    region_seed._process_countries(db=None, countries_data=countries, created=0, skipped=0)

    codes = {c[0]: c for c in captured}
    assert codes["CN"][1] == "中国"  # name 中文
    assert codes["CN"][2] == "China"  # name_en 英文
    assert codes["ZZ"][1] == "Zzzland"  # 缺中文回落英文
