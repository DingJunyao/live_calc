from decimal import Decimal
from datetime import datetime, timezone

from app.services.export.serializers import (
    to_float,
    to_iso,
    convert_image_path,
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
