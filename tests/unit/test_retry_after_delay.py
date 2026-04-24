"""Integration tests for the client's Retry-After honour path.

``test_retry_after.py`` verifies the header parser in isolation. What
was missing per AUDIT §T5 / follow-up #5 was proof that the client
actually *waits* for the duration the parser returns — i.e. a
``Retry-After: <HTTP-date>`` five seconds out produces a ~5 s sleep
before the retry fires, not the exponential-back-off fallback.

These tests mock ``asyncio.sleep`` so the suite stays fast while still
asserting on the exact duration the client asks the event loop to
wait for.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from uniprot_mcp.client import UniProtClient

# Capture the real sleep once, before any monkey-patching. The recorder
# uses it to yield briefly without recursing into itself.
_ORIGINAL_SLEEP = asyncio.sleep


class _SleepRecorder:
    """Drop-in replacement for ``asyncio.sleep`` that records every
    requested duration and still yields control to the event loop."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        await _ORIGINAL_SLEEP(0)


async def test_client_sleeps_per_http_date_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 429 with ``Retry-After: <HTTP-date 5 s out>`` must trigger a
    sleep close to five seconds, not the fallback."""
    recorder = _SleepRecorder()
    monkeypatch.setattr("uniprot_mcp.client.asyncio.sleep", recorder)

    future = datetime.now(tz=UTC) + timedelta(seconds=5)
    header = future.strftime("%a, %d %b %Y %H:%M:%S GMT")

    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/P04637").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": header}),
                httpx.Response(200, json={"primaryAccession": "P04637"}),
            ]
        )
        client = UniProtClient()
        try:
            result = await client.get_entry("P04637")
        finally:
            await client.close()

    assert result["primaryAccession"] == "P04637"
    assert route.call_count == 2, "expected one 429 followed by one 200"
    assert len(recorder.calls) == 1, (
        f"expected exactly one sleep before retry, got {recorder.calls!r}"
    )
    slept = recorder.calls[0]
    # The parser computes ``dt - now()`` at call time, shortly after
    # we computed ``future``. Allow a generous ±1.5 s tolerance for
    # scheduler jitter.
    assert 3.5 <= slept <= 5.5, (
        f"expected ~5 s sleep for HTTP-date Retry-After, got {slept}"
    )


async def test_client_sleeps_per_delta_seconds_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 429 with ``Retry-After: 7`` must produce an exact 7 s sleep."""
    recorder = _SleepRecorder()
    monkeypatch.setattr("uniprot_mcp.client.asyncio.sleep", recorder)

    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "7"}),
                httpx.Response(200, json={"primaryAccession": "P04637"}),
            ]
        )
        client = UniProtClient()
        try:
            await client.get_entry("P04637")
        finally:
            await client.close()

    assert len(recorder.calls) == 1
    assert recorder.calls[0] == 7.0, (
        f"delta-seconds Retry-After not honoured exactly: {recorder.calls!r}"
    )


async def test_client_sleeps_fallback_when_retry_after_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 429 with no Retry-After header falls back to exponential
    back-off: ``1.5 ** (attempt + 1) == 1.5`` on the first retry."""
    recorder = _SleepRecorder()
    monkeypatch.setattr("uniprot_mcp.client.asyncio.sleep", recorder)

    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(200, json={"primaryAccession": "P04637"}),
            ]
        )
        client = UniProtClient()
        try:
            await client.get_entry("P04637")
        finally:
            await client.close()

    assert len(recorder.calls) == 1
    assert recorder.calls[0] == pytest.approx(1.5)


async def test_client_sleeps_zero_for_past_http_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An HTTP-date already in the past must yield a zero-second sleep —
    i.e. retry immediately without waiting."""
    recorder = _SleepRecorder()
    monkeypatch.setattr("uniprot_mcp.client.asyncio.sleep", recorder)

    past = datetime.now(tz=UTC) - timedelta(seconds=10)
    header = past.strftime("%a, %d %b %Y %H:%M:%S GMT")

    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": header}),
                httpx.Response(200, json={"primaryAccession": "P04637"}),
            ]
        )
        client = UniProtClient()
        try:
            await client.get_entry("P04637")
        finally:
            await client.close()

    assert recorder.calls == [0.0], (
        f"past HTTP-date must clamp to 0, got {recorder.calls!r}"
    )
