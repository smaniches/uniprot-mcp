"""Unit tests for the Retry-After header parser."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from uniprot_mcp.client import MAX_RETRY_AFTER_SECONDS, parse_retry_after


def test_numeric_seconds() -> None:
    assert parse_retry_after("30", 0) == 30.0


def test_numeric_seconds_is_clamped() -> None:
    assert parse_retry_after("99999", 0) == MAX_RETRY_AFTER_SECONDS


def test_http_date_in_the_future() -> None:
    future = datetime.now(tz=timezone.utc) + timedelta(seconds=10)
    header = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
    delay = parse_retry_after(header, 0)
    assert 0 < delay <= MAX_RETRY_AFTER_SECONDS


def test_http_date_in_the_past_returns_zero() -> None:
    past = datetime.now(tz=timezone.utc) - timedelta(seconds=10)
    header = past.strftime("%a, %d %b %Y %H:%M:%S GMT")
    assert parse_retry_after(header, 0) == 0.0


def test_missing_header_uses_backoff() -> None:
    a0 = parse_retry_after(None, 0)
    a3 = parse_retry_after(None, 3)
    assert a3 > a0, "back-off must grow with attempt number"


def test_garbage_header_uses_backoff() -> None:
    assert parse_retry_after("not a valid header", 0) > 0
