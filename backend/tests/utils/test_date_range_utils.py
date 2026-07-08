from datetime import datetime, timezone, date
from app.utils.date_range_utils import (
    local_date_to_utc_range,
    local_date_range_to_utc_range,
    utc_datetime_to_local_date,
)


def test_local_date_to_utc_range_shanghai():
    # 北京时间 2026-03-29 一天 → UTC 2026-03-28 16:00 ~ 2026-03-29 15:59:59.999999
    start, end = local_date_to_utc_range(date(2026, 3, 29), "Asia/Shanghai")
    assert start == datetime(2026, 3, 28, 16, 0, 0)
    assert end == datetime(2026, 3, 29, 15, 59, 59, 999999)


def test_local_date_to_utc_range_utc():
    # UTC 时区：本地日 == UTC 日
    start, end = local_date_to_utc_range(date(2026, 3, 29), "UTC")
    assert start == datetime(2026, 3, 29, 0, 0, 0)
    assert end == datetime(2026, 3, 29, 23, 59, 59, 999999)


def test_local_date_range_to_utc_range():
    s, e = local_date_range_to_utc_range(date(2026, 3, 1), date(2026, 3, 31), "Asia/Shanghai")
    assert s == datetime(2026, 2, 28, 16, 0, 0)
    assert e == datetime(2026, 3, 31, 15, 59, 59, 999999)


def test_utc_datetime_to_local_date_cross_day():
    # UTC 2026-03-28 17:00 → 北京时间 2026-03-29 01:00 → 本地日 03-29
    assert utc_datetime_to_local_date(datetime(2026, 3, 28, 17, 0, 0), "Asia/Shanghai") == date(2026, 3, 29)


def test_utc_datetime_to_local_date_naive_treated_as_utc():
    # naive datetime 视作 UTC
    assert utc_datetime_to_local_date(datetime(2026, 3, 28, 17, 0, 0), "Asia/Shanghai") == date(2026, 3, 29)


def test_dst_spring_forward():
    # America/New_York 2026-03-08 春令时切换（2:00 → 3:00，一天仅 23 小时）
    # 本地日 2026-03-08 的 UTC 范围起止应正确（不抛错、边界合理）
    start, end = local_date_to_utc_range(date(2026, 3, 8), "America/New_York")
    # 切换前一日 EST(UTC-5)：00:00 EST = 05:00 UTC
    assert start == datetime(2026, 3, 8, 5, 0, 0)


def test_default_tz_is_utc():
    # 不传 tz 默认 UTC
    start, end = local_date_to_utc_range(date(2026, 3, 29))
    assert start == datetime(2026, 3, 29, 0, 0, 0)
