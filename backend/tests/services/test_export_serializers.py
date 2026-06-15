from decimal import Decimal
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.export.serializers import (
    to_float,
    to_iso,
    convert_image_path,
    serialize_unit,
)


def test_to_float_decimal():
    assert to_float(Decimal("3.5")) == 3.5


def test_to_float_none():
    assert to_float(None) is None


def test_to_float_string_number():
    assert to_float("2") == 2.0


def test_to_float_invalid_string():
    assert to_float("abc") is None


def test_to_iso_datetime():
    dt = datetime(2026, 6, 15, 14, 30, tzinfo=timezone.utc)
    assert to_iso(dt) == "2026-06-15T14:30:00+00:00"


def test_to_iso_none():
    assert to_iso(None) is None


def test_convert_image_path_strips_static_prefix():
    assert convert_image_path("/static/images/recipes/a.jpg") == "images/recipes/a.jpg"


def test_convert_image_path_keeps_remote_url():
    # 外链不转换，调用方负责跳过
    assert convert_image_path("https://example.com/a.jpg") == "https://example.com/a.jpg"


def test_convert_image_path_none():
    assert convert_image_path(None) is None


def _make_unit(**kw):
    base = dict(
        id=10, name="克", abbreviation="g", plural_form=None,
        unit_type="mass", si_factor=Decimal("0.001"), is_si_base=False,
        is_common=True, display_order=3, unit_system="market",
        default_estimate=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_serialize_unit_howto_cook_fields():
    u = _make_unit()
    out = serialize_unit(u)
    assert out["name"] == "克"
    assert out["aliases"] == []  # 数据库无别名列


def test_serialize_unit_extended_fields():
    u = _make_unit()
    out = serialize_unit(u)
    assert out["id"] == 10
    assert out["abbreviation"] == "g"
    assert out["unit_type"] == "mass"
    assert out["si_factor"] == 0.001
    assert out["unit_system"] == "market"
