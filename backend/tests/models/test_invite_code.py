"""邀请码过期时间相关测试。

核心防护：SQLite 读回的 DateTime(timezone=True) 实际是 naive datetime，
而旧版 is_expired 直接与 aware UTC 比较 → TypeError。这里的用例确保
ensure_utc / is_expired / 序列化对 naive 和 aware 两种读法都鲁棒。
"""
import datetime

from app.models.invite_code import InviteCode, ensure_utc, generate_invite_code
from app.api.invite_codes import _serialize_invite_code


# ---------------- ensure_utc ----------------

def test_ensure_utc_naive_treated_as_utc():
    """SQLite 读回的 naive datetime 应被视作 UTC。"""
    naive = datetime.datetime(2026, 6, 30, 16, 0, 0)
    result = ensure_utc(naive)
    assert result.tzinfo is not None
    assert result.utcoffset() == datetime.timedelta(0)


def test_ensure_utc_aware_converted_to_utc():
    """带时区的 datetime 应换算到 UTC（东八区 00:00 → UTC 前一日 16:00）。"""
    cst = datetime.datetime(2026, 6, 30, 0, 0, 0,
                            tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
    result = ensure_utc(cst)
    assert result.utcoffset() == datetime.timedelta(0)
    assert (result.day, result.hour) == (29, 16)


def test_ensure_utc_already_utc_unchanged():
    utc_dt = datetime.datetime(2026, 6, 30, 16, 0, 0, tzinfo=datetime.timezone.utc)
    assert ensure_utc(utc_dt) == utc_dt


# ---------------- is_expired（防 TypeError 是核心） ----------------

def test_is_expired_none_not_expired():
    assert InviteCode(expires_at=None).is_expired is False


def test_is_expired_naive_future_no_typeerror():
    """模拟 SQLite 读回的 naive datetime（未来时刻），不得抛 TypeError。"""
    future_naive = (datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(days=1)).replace(tzinfo=None)
    assert InviteCode(expires_at=future_naive).is_expired is False


def test_is_expired_naive_past_no_typeerror():
    """模拟 SQLite 读回的 naive datetime（过去时刻），不得抛 TypeError 且判定过期。"""
    past_naive = (datetime.datetime.now(datetime.timezone.utc)
                  - datetime.timedelta(days=1)).replace(tzinfo=None)
    assert InviteCode(expires_at=past_naive).is_expired is True


def test_is_expired_aware_past():
    past_aware = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    assert InviteCode(expires_at=past_aware).is_expired is True


# ---------------- 序列化带时区 ----------------

def test_serialize_outputs_timezone_aware_iso():
    """序列化必须带时区后缀（+00:00），前端 new Date() 才能按本地时区解析。"""
    naive = datetime.datetime(2026, 6, 30, 16, 0, 0)  # 模拟 SQLite 读回
    code = InviteCode(
        id=1, code="ABC12345", created_by=1, used_count=0, max_uses=None,
        created_at=naive, expires_at=naive,
    )
    data = _serialize_invite_code(code)
    assert data["expiresAt"] == "2026-06-30T16:00:00+00:00"
    assert data["createdAt"] == "2026-06-30T16:00:00+00:00"


def test_serialize_expires_at_none():
    code = InviteCode(
        id=1, code="ABC12345", created_by=1, used_count=0, max_uses=None,
        created_at=datetime.datetime(2026, 6, 30, 16, 0, 0), expires_at=None,
    )
    assert _serialize_invite_code(code)["expiresAt"] is None


# ---------------- 其他（回归保护） ----------------

def test_generate_invite_code_shape():
    code = generate_invite_code(8)
    assert len(code) == 8
    assert code.isalnum()
