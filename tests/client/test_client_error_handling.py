"""Regression tests for client error-handling edge cases.

Three independent ``client.py`` behaviors, each with branch coverage for
the relevant arms:

  ``parse_retry_after`` numeric branch — non-finite (nan/inf) and
  negative delta-seconds must not propagate: a non-finite value falls
  back to the exponential-backoff delay and a negative value clamps to
  0.0, rather than yielding a NaN sleep or a zero-backoff hot retry.

  ``id_mapping_results`` terminal-status branch — a job that comes back
  HTTP 200 with a terminal ``jobStatus`` other than NEW/RUNNING (e.g.
  "ERROR") raises immediately rather than polling 30 times into a
  misleading ``TimeoutError``.

  ``get_alphafold_summary`` 404 handling — the prediction endpoint
  returns 404 for accessions with no model; that is a graceful
  "no model" answer (empty record), not an opaque error.

Every expected value below is derived from an authoritative contract
(RFC 7231, the documented fallback formula, UniProt's reference
id-mapping client, the AlphaFold prediction API contract), never from
running the current code.
"""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from uniprot_mcp.client import (
    ALPHAFOLD_API_BASE,
    BASE_URL,
    MAX_RETRY_AFTER_SECONDS,
    UniProtClient,
    parse_retry_after,
)

# ---------------------------------------------------------------------------
# parse_retry_after numeric branch: non-finite + negative
# ---------------------------------------------------------------------------


def test_retry_after_nan_falls_back_to_backoff() -> None:
    """``Retry-After: nan`` must NOT propagate NaN.

    ``float("nan")`` parses without raising, so the value reaches the
    numeric branch. ``min(nan, 120.0)`` is ``nan`` (verified: Python's
    ``min`` returns its first arg when it is NaN), and a ``nan`` delay then
    reaches ``asyncio.sleep`` — which on CPython 3.12 treats it as a
    non-positive (immediate) wait, i.e. zero-effective-backoff hot-retry
    against a rate-limited server. The fix rejects non-finite via
    ``math.isfinite`` and returns the documented exponential-backoff
    fallback. Expected value derived from the function's own docstring
    formula ``1.5 ** (attempt + 1)`` with attempt=0 -> 1.5**1 == 1.5.
    """
    result = parse_retry_after("nan", 0)
    assert math.isfinite(result), "non-finite Retry-After must not propagate NaN/inf"
    assert result == 1.5  # 1.5 ** (0 + 1)


def test_retry_after_inf_falls_back_to_backoff() -> None:
    """``Retry-After: inf`` parses (``float("inf")``) and must be rejected
    as non-finite, falling back to backoff rather than being clamped to
    the 120 s cap. ``math.isfinite(inf)`` is ``False``. Expected derived
    from ``1.5 ** (attempt + 1)`` with attempt=2 -> 1.5**3 == 3.375.
    """
    result = parse_retry_after("inf", 2)
    assert math.isfinite(result)
    assert result == pytest.approx(1.5**3)


def test_retry_after_negative_delta_clamps_to_zero() -> None:
    """A negative delta-seconds must clamp to 0.0 (retry immediately),
    never yield a negative sleep duration.

    RFC 7231 §7.1.3 defines delta-seconds as a non-negative integer, so a
    negative value is malformed; the symmetric, already-correct HTTP-date
    branch clamps with ``max(delta, 0.0)``. Buggy numeric branch returned
    ``-5.0`` -> ``asyncio.sleep(-5.0)`` returns immediately -> zero-backoff
    hot retry against a rate-limited server. Expected: exactly 0.0.
    """
    assert parse_retry_after("-5", 0) == 0.0


def test_retry_after_large_finite_still_clamped_to_cap() -> None:
    """Guard the False arm of the new ``isfinite`` check together with the
    existing cap: a huge *finite* value is still capped at
    ``MAX_RETRY_AFTER_SECONDS`` (120.0), unchanged behaviour.
    """
    assert parse_retry_after("99999", 0) == MAX_RETRY_AFTER_SECONDS


async def test_client_sleeps_finite_duration_on_nan_retry_after() -> None:
    """End-to-end: a 429 carrying ``Retry-After: nan`` must make the client
    sleep a *finite, non-negative* duration before retrying.

    We record the exact duration the client asks the event loop to wait.
    Against the buggy parser the recorded value is ``nan`` (``min(nan, 120)``
    is ``nan``); against the fix it is the finite backoff fallback ``1.5``
    (``1.5 ** (0 + 1)``, from the documented formula). The recorder is what
    makes this discriminating: ``asyncio.sleep(nan)`` happens to return
    immediately on CPython 3.12 rather than raising, so a "did it complete"
    assertion alone would pass against the bug — asserting on the duration
    does not.
    """
    recorded: list[float] = []

    async def _record(seconds: float) -> None:
        recorded.append(seconds)

    with respx.mock(base_url=BASE_URL) as router:
        router.get("/uniprotkb/P04637").mock(
            side_effect=[
                httpx.Response(429, headers={"Retry-After": "nan"}),
                httpx.Response(200, json={"primaryAccession": "P04637"}),
            ]
        )
        with patch("uniprot_mcp.client.asyncio.sleep", new=_record):
            client = UniProtClient()
            try:
                out = await client.get_entry("P04637")
            finally:
                await client.close()
    assert out["primaryAccession"] == "P04637"
    assert len(recorded) == 1
    slept = recorded[0]
    assert math.isfinite(slept) and slept >= 0.0, f"Retry-After: nan produced {slept!r}"
    assert slept == 1.5  # documented fallback 1.5 ** (attempt 0 + 1)


# ---------------------------------------------------------------------------
# id_mapping_results terminal jobStatus branch
# ---------------------------------------------------------------------------


async def test_id_mapping_results_raises_on_terminal_error_status() -> None:
    """A terminal ``{"jobStatus": "ERROR"}`` returned with HTTP 200 must
    raise immediately on the first poll, not spin 30 iterations.

    Oracle: UniProt's reference id-mapping client
    (``check_id_mapping_results_ready``) polls only while ``jobStatus`` is
    in ``{"NEW", "RUNNING"}`` and raises for any other value. The
    discriminating assertion is ``call_count == 1`` — the buggy loop polls
    all 30 times and raises ``TimeoutError`` (disjoint from
    ``RuntimeError``); the fix raises ``RuntimeError`` after one request.
    ``asyncio.sleep`` is patched to instant so a regression-to-spin still
    completes fast but trips the call-count assertion.
    """
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/idmapping/status/JOBERR").mock(
            return_value=httpx.Response(
                200, json={"jobStatus": "ERROR", "messages": ["Invalid from/to database pair"]}
            )
        )
        with patch("uniprot_mcp.client.asyncio.sleep", new=AsyncMock(return_value=None)):
            client = UniProtClient()
            try:
                with pytest.raises(RuntimeError) as excinfo:
                    await client.id_mapping_results("JOBERR")
            finally:
                await client.close()

    assert route.call_count == 1, "terminal status must short-circuit on the first poll"
    # The upstream status and message must be surfaced, not hidden.
    assert "ERROR" in str(excinfo.value)
    assert "Invalid from/to database pair" in str(excinfo.value)
    # The list-valued ``messages`` must read as text, not a raw list repr.
    assert "['" not in str(excinfo.value)


async def test_id_mapping_results_joins_list_detail() -> None:
    """A terminal status whose ``messages`` is a multi-element JSON array
    must render as semicolon-joined text, not a Python list repr.

    Oracle: UniProt returns ``messages``/``errors`` as arrays; the readable
    surface is ``a; b`` rather than ``['a', 'b']``. Fail-on-unfixed guard for
    the list-join arm — the pre-fix code emits the bracketed repr.
    """
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/idmapping/status/JOBLIST").mock(
            return_value=httpx.Response(
                200,
                json={"jobStatus": "ERROR", "messages": ["first problem", "second problem"]},
            )
        )
        with patch("uniprot_mcp.client.asyncio.sleep", new=AsyncMock(return_value=None)):
            client = UniProtClient()
            try:
                with pytest.raises(RuntimeError) as excinfo:
                    await client.id_mapping_results("JOBLIST")
            finally:
                await client.close()

    msg = str(excinfo.value)
    assert "first problem; second problem" in msg
    # Not a raw Python list repr (the pre-fix bug surfaces ``['a', 'b']``); the
    # ``'`` quotes around the repr'd ``jobStatus`` are expected and fine.
    assert "['" not in msg


async def test_id_mapping_results_terminal_status_without_detail() -> None:
    """Terminal status with no messages/errors/message key still raises a
    descriptive ``RuntimeError`` carrying the status. Covers the
    ``detail`` falsy arm (no ``: <detail>`` suffix).
    """
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/idmapping/status/JOBFAIL").mock(
            return_value=httpx.Response(200, json={"jobStatus": "FAILED"})
        )
        with patch("uniprot_mcp.client.asyncio.sleep", new=AsyncMock(return_value=None)):
            client = UniProtClient()
            try:
                with pytest.raises(RuntimeError, match="FAILED"):
                    await client.id_mapping_results("JOBFAIL")
            finally:
                await client.close()

    assert route.call_count == 1


async def test_id_mapping_results_new_status_still_polls_to_timeout() -> None:
    """Regression guard for the False arm of the terminal branch: a job
    stuck in ``NEW`` (a documented transient state) must keep polling and
    ultimately raise ``TimeoutError`` — NOT be misclassified as terminal.

    This mirrors the long-standing ``test_id_mapping_results_raises_on_timeout``
    contract and is the branch that breaks if the transient set is wrong.
    """
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/idmapping/status/JOBNEW").mock(
            return_value=httpx.Response(200, json={"jobStatus": "NEW"})
        )
        with patch("uniprot_mcp.client.asyncio.sleep", new=AsyncMock(return_value=None)):
            client = UniProtClient()
            try:
                with pytest.raises(TimeoutError, match="did not complete"):
                    await client.id_mapping_results("JOBNEW")
            finally:
                await client.close()

    assert route.call_count == 30, "NEW is transient — must poll the full budget"


# ---------------------------------------------------------------------------
# get_alphafold_summary 404 -> graceful empty record
# ---------------------------------------------------------------------------


async def test_get_alphafold_summary_404_returns_empty_record() -> None:
    """A 404 from the AlphaFold prediction endpoint (accession with no
    model, e.g. Q8WZ42) must be rendered as the graceful empty record
    ``{}``, identical to the documented empty-``[]`` case — not raise an
    opaque ``HTTPStatusError``.

    Oracle: AlphaFold-DB's prediction API returns HTTP 404 for accessions
    without a deposited model; the function's documented contract for
    "no model" is an empty record. Expected: ``{}`` and provenance with
    ``release=None`` (no model version to report).
    """
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/Q8WZ42").mock(return_value=httpx.Response(404))
        client = UniProtClient()
        try:
            record = await client.get_alphafold_summary("Q8WZ42")
        finally:
            await client.close()
    assert record == {}
    assert client.last_provenance is not None
    assert client.last_provenance["source"] == "AlphaFoldDB"
    assert client.last_provenance["release"] is None


async def test_get_alphafold_summary_500_still_raises() -> None:
    """Contract guard for the else-arm: a non-404 error status from the
    prediction endpoint must still raise ``HTTPStatusError`` (the 404
    interception must not broaden into a catch-all). Derived from the
    task contract: "let other statuses still raise."
    """
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(return_value=httpx.Response(500))
        client = UniProtClient()
        try:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_alphafold_summary("P04637")
        finally:
            await client.close()
