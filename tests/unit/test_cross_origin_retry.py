"""Bounded retry on the cross-origin GET helper (FIX 2).

``get_clinvar_records`` (NCBI eutils) and ``get_alphafold_summary``
(AlphaFold-DB) open their own short-lived ``httpx.AsyncClient`` and now
route GETs through ``_get_with_retry``, which mirrors ``_req``'s policy:
retry on 429 / >=500 / timeout, return everything else (including 404)
unchanged so the AlphaFold "no model" branch still works.

``asyncio.sleep`` is patched to a no-op so 5xx/timeout back-off
(``1.5 ** (attempt + 1)`` seconds) does not slow the suite.
"""

from __future__ import annotations

from itertools import cycle
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from uniprot_mcp.client import (
    ALPHAFOLD_API_BASE,
    MAX_RETRIES,
    NCBI_EUTILS_BASE,
    UniProtClient,
    _get_with_retry,
)

_ESEARCH = {"esearchresult": {"count": "1", "idlist": ["111"]}}
_ESUMMARY = {"result": {"uids": ["111"], "111": {"uid": "111", "accession": "VCV111"}}}


@pytest.fixture(autouse=True)
def _no_sleep():
    with patch("uniprot_mcp.client.asyncio.sleep", new=AsyncMock(return_value=None)):
        yield


async def test_eutils_retries_on_429_then_succeeds() -> None:
    esearch_responses = cycle(
        [
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json=_ESEARCH),
        ]
    )
    with respx.mock(base_url=NCBI_EUTILS_BASE) as ncbi_router:
        esearch_route = ncbi_router.get("/esearch.fcgi").mock(
            side_effect=lambda req: next(esearch_responses)
        )
        ncbi_router.get("/esummary.fcgi").mock(return_value=httpx.Response(200, json=_ESUMMARY))
        client = UniProtClient()
        try:
            out = await client.get_clinvar_records("BRCA1")
        finally:
            await client.close()
    assert esearch_route.call_count == 2, "should retry once after 429"
    assert out["records"][0]["accession"] == "VCV111"


async def test_eutils_retries_on_503_then_succeeds() -> None:
    esearch_responses = cycle(
        [
            httpx.Response(503),
            httpx.Response(200, json=_ESEARCH),
        ]
    )
    with respx.mock(base_url=NCBI_EUTILS_BASE) as ncbi_router:
        esearch_route = ncbi_router.get("/esearch.fcgi").mock(
            side_effect=lambda req: next(esearch_responses)
        )
        ncbi_router.get("/esummary.fcgi").mock(return_value=httpx.Response(200, json=_ESUMMARY))
        client = UniProtClient()
        try:
            out = await client.get_clinvar_records("BRCA1")
        finally:
            await client.close()
    assert esearch_route.call_count == 2, "should retry once after 503"
    assert out["records"][0]["accession"] == "VCV111"


async def test_get_with_retry_exhausts_on_persistent_timeout() -> None:
    # Covers the ``except httpx.TimeoutException`` arc and the post-loop
    # ``raise RuntimeError`` of the new helper in one shot.
    route = None
    with respx.mock(base_url=NCBI_EUTILS_BASE) as ncbi_router:
        route = ncbi_router.get("/esearch.fcgi").mock(
            side_effect=httpx.TimeoutException("timed out")
        )
        async with httpx.AsyncClient() as ext:
            with pytest.raises(RuntimeError, match="failed after") as exc_info:
                await _get_with_retry(ext, f"{NCBI_EUTILS_BASE}/esearch.fcgi")
    assert "timeout" in str(exc_info.value)
    assert route.call_count == MAX_RETRIES + 1


async def test_alphafold_404_passes_through_without_retry() -> None:
    # 404 is a legitimate "no model" answer (< 500): the helper must return
    # it as-is and the caller's 404 branch yields the empty-record result.
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        route = router.get("/api/prediction/Q8WZ42").mock(return_value=httpx.Response(404))
        client = UniProtClient()
        try:
            out = await client.get_alphafold_summary("Q8WZ42")
        finally:
            await client.close()
    assert route.call_count == 1, "404 must not be retried"
    assert out == {}
