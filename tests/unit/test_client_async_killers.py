"""respx-mocked async tests killing the mutations the sync killer file
cannot reach.

The 2026-04-28 mutation-matrix run (25049571013) on
fix/client-mutation-uplift with the full ``tests/unit + tests/property``
scope reported 234/370 = 63.24 % raw kill rate on
``src/uniprot_mcp/client.py`` — only +0.5 pp above the narrow-scope
prior run, because expanding scope did not exercise the async method
bodies. Decoded survivors cluster in:

  - every thin async wrapper (``get_entry``, ``get_fasta``, ``search``,
    ``get_keyword``, ``get_subcellular_location``, ``get_uniparc``,
    ``get_proteome``, ``get_citation``, ``get_uniref``, plus all the
    ``*_search`` siblings) — each one is a one-line
    ``await self._req("GET", "/path/{id}").json()`` whose URL/method/
    path-template mutmut targets but no test invokes
  - the ``_req`` retry loop (status 429 → ``parse_retry_after`` sleep,
    status 5xx → exponential back-off, ``TimeoutException`` →
    same back-off, raise after ``MAX_RETRIES + 1`` attempts)
  - the ``_req`` pin-release branch (``ReleaseMismatchError`` on
    header drift)
  - ``id_mapping_submit`` + ``id_mapping_results`` (the polling loop
    plus the ``redirectURL`` branch)
  - ``batch_entries`` (client-side accession filtering, 100-entry
    cap, ``OR``-join query construction)
  - ``get_clinvar_records`` (cross-origin AsyncClient,
    ``esearch.fcgi`` + ``esummary.fcgi`` two-step)
  - ``get_alphafold_summary`` (cross-origin AlphaFoldDB call,
    ``latestVersion`` extraction)
  - ``ReleaseMismatchError.__init__`` field assignments

Each test below pins exactly one decision point: a URL string, an
HTTP method, a path template, a query-parameter dict, a retry count,
or a fall-through branch. Hardcoded literals computed against the
unmutated source on 2026-04-28; importing source-derived values
would defeat the kill.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from uniprot_mcp.client import (
    ALPHAFOLD_API_BASE,
    BASE_URL,
    NCBI_EUTILS_BASE,
    ReleaseMismatchError,
    UniProtClient,
)

# ---------------------------------------------------------------------------
# ReleaseMismatchError __init__ field assignments (mutants on lines 118-121)
# ---------------------------------------------------------------------------


def test_release_mismatch_error_pinned_field_is_assigned_correctly() -> None:
    """Mutating ``self.pinned = pinned`` (e.g., to ``self.pinned = url``)
    breaks this exact-equality check."""
    err = ReleaseMismatchError(pinned="2026_02", observed="2026_03", url="https://x.test")
    assert err.pinned == "2026_02"
    assert err.pinned != "2026_03"
    assert err.pinned != "https://x.test"


def test_release_mismatch_error_url_field_is_assigned_correctly() -> None:
    """Mutating ``self.url = url`` similarly."""
    err = ReleaseMismatchError(pinned="2026_02", observed="2026_03", url="https://x.test/y")
    assert err.url == "https://x.test/y"
    assert err.url != "2026_02"
    assert err.url != "2026_03"


def test_release_mismatch_error_observed_disp_branch_uses_observed_when_present() -> None:
    """When observed is non-None, ``observed_disp = observed``; the
    message must contain the observed value (not '(absent)')."""
    err = ReleaseMismatchError(pinned="A", observed="B", url="https://x.test")
    msg = str(err)
    assert "'B'" in msg
    assert "(absent)" not in msg


def test_release_mismatch_error_observed_disp_branch_uses_absent_when_none() -> None:
    """When observed is None, ``observed_disp = '(absent)'``; message
    must contain '(absent)' (and NOT 'None')."""
    err = ReleaseMismatchError(pinned="A", observed=None, url="https://x.test")
    msg = str(err)
    assert "(absent)" in msg
    assert "None" not in msg


# ---------------------------------------------------------------------------
# Thin async wrappers — pin URL + method + path template
# ---------------------------------------------------------------------------

# Each test mocks the upstream endpoint with an exact-URL match (respx
# raises on mismatch), then asserts the wrapper returned the parsed
# JSON body. Mutating the path string, the HTTP method, or the {id}
# interpolation breaks the URL match → the mocked route is not hit →
# respx raises → test fails → mutant killed.


@pytest.mark.asyncio
@respx.mock
async def test_get_entry_calls_uniprotkb_path_with_accession() -> None:
    route = respx.get(f"{BASE_URL}/uniprotkb/P04637").mock(
        return_value=httpx.Response(200, json={"primaryAccession": "P04637"})
    )
    c = UniProtClient()
    try:
        result = await c.get_entry("P04637")
    finally:
        await c.close()
    assert route.called
    assert route.call_count == 1
    assert result == {"primaryAccession": "P04637"}


@pytest.mark.asyncio
@respx.mock
async def test_get_fasta_calls_uniprotkb_path_with_accept_fasta() -> None:
    """get_fasta must request /uniprotkb/{accession} with
    Accept=text/plain;format=fasta — mutating either the path or the
    accept header breaks the route match."""
    route = respx.get(f"{BASE_URL}/uniprotkb/P04637").mock(
        return_value=httpx.Response(200, text=">sp|P04637\nMEEPQ\n")
    )
    c = UniProtClient()
    try:
        text = await c.get_fasta("P04637")
    finally:
        await c.close()
    assert route.called
    assert text.startswith(">sp|P04637")
    # The Accept header sent must request fasta. Inspect the actual request.
    accept = route.calls[0].request.headers.get("Accept")
    assert accept is not None and "fasta" in accept.lower()


@pytest.mark.asyncio
@respx.mock
async def test_search_calls_uniprotkb_search_with_query() -> None:
    """search builds /uniprotkb/search?query=...&size=...  size is
    clamped to 500 by min(size, 500)."""
    route = respx.get(f"{BASE_URL}/uniprotkb/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.search("p53", size=10)
    finally:
        await c.close()
    assert route.called
    qs = dict(route.calls[0].request.url.params)
    assert qs.get("query") == "p53"
    assert qs.get("size") == "10"


@pytest.mark.asyncio
@respx.mock
async def test_search_clamps_size_to_500() -> None:
    """size > 500 must be clamped to 500."""
    route = respx.get(f"{BASE_URL}/uniprotkb/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.search("p53", size=999)
    finally:
        await c.close()
    qs = dict(route.calls[0].request.url.params)
    assert qs.get("size") == "500"


@pytest.mark.asyncio
@respx.mock
async def test_search_passes_fields_as_comma_joined() -> None:
    """When fields=['accession', 'gene_names'], the query string
    must contain fields=accession,gene_names."""
    route = respx.get(f"{BASE_URL}/uniprotkb/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.search("x", fields=["accession", "gene_names"])
    finally:
        await c.close()
    qs = dict(route.calls[0].request.url.params)
    assert qs.get("fields") == "accession,gene_names"


@pytest.mark.asyncio
@respx.mock
async def test_taxonomy_search_calls_correct_path() -> None:
    route = respx.get(f"{BASE_URL}/taxonomy/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.taxonomy_search("homo sapiens", size=5)
    finally:
        await c.close()
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_get_keyword_calls_keywords_path() -> None:
    route = respx.get(f"{BASE_URL}/keywords/KW-0007").mock(
        return_value=httpx.Response(200, json={"keyword": "Acetylation"})
    )
    c = UniProtClient()
    try:
        result = await c.get_keyword("KW-0007")
    finally:
        await c.close()
    assert route.called
    assert result == {"keyword": "Acetylation"}


@pytest.mark.asyncio
@respx.mock
async def test_search_keywords_calls_keywords_search_path() -> None:
    route = respx.get(f"{BASE_URL}/keywords/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.search_keywords("kinase", size=5)
    finally:
        await c.close()
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_search_keywords_clamps_size_to_500() -> None:
    route = respx.get(f"{BASE_URL}/keywords/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.search_keywords("x", size=9999)
    finally:
        await c.close()
    qs = dict(route.calls[0].request.url.params)
    assert qs.get("size") == "500"


@pytest.mark.asyncio
@respx.mock
async def test_get_subcellular_location_calls_locations_path() -> None:
    route = respx.get(f"{BASE_URL}/locations/SL-0086").mock(
        return_value=httpx.Response(200, json={"name": "Cytoplasm"})
    )
    c = UniProtClient()
    try:
        result = await c.get_subcellular_location("SL-0086")
    finally:
        await c.close()
    assert route.called
    assert result == {"name": "Cytoplasm"}


@pytest.mark.asyncio
@respx.mock
async def test_search_subcellular_locations_calls_correct_path() -> None:
    route = respx.get(f"{BASE_URL}/locations/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.search_subcellular_locations("nucleus")
    finally:
        await c.close()
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_get_uniparc_calls_uniparc_path() -> None:
    route = respx.get(f"{BASE_URL}/uniparc/UPI0000123456").mock(
        return_value=httpx.Response(200, json={"uniParcId": "UPI0000123456"})
    )
    c = UniProtClient()
    try:
        await c.get_uniparc("UPI0000123456")
    finally:
        await c.close()
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_search_uniparc_calls_uniparc_search() -> None:
    route = respx.get(f"{BASE_URL}/uniparc/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.search_uniparc("xxx")
    finally:
        await c.close()
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_get_proteome_calls_proteomes_path() -> None:
    route = respx.get(f"{BASE_URL}/proteomes/UP000005640").mock(
        return_value=httpx.Response(200, json={"id": "UP000005640"})
    )
    c = UniProtClient()
    try:
        await c.get_proteome("UP000005640")
    finally:
        await c.close()
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_search_proteomes_calls_proteomes_search() -> None:
    route = respx.get(f"{BASE_URL}/proteomes/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.search_proteomes("human")
    finally:
        await c.close()
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_get_citation_calls_citations_path() -> None:
    route = respx.get(f"{BASE_URL}/citations/12345").mock(
        return_value=httpx.Response(200, json={"id": "12345"})
    )
    c = UniProtClient()
    try:
        await c.get_citation("12345")
    finally:
        await c.close()
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_search_citations_calls_citations_search() -> None:
    route = respx.get(f"{BASE_URL}/citations/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.search_citations("p53")
    finally:
        await c.close()
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_get_uniref_calls_uniref_path() -> None:
    route = respx.get(f"{BASE_URL}/uniref/UniRef50_P04637").mock(
        return_value=httpx.Response(200, json={"id": "UniRef50_P04637"})
    )
    c = UniProtClient()
    try:
        await c.get_uniref("UniRef50_P04637")
    finally:
        await c.close()
    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_search_uniref_calls_uniref_search() -> None:
    route = respx.get(f"{BASE_URL}/uniref/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.search_uniref("identity:0.5")
    finally:
        await c.close()
    assert route.called


# ---------------------------------------------------------------------------
# _req retry loop — pin 429, 5xx, timeout, attempts cap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_req_retries_on_429_then_succeeds() -> None:
    """429 → sleep parse_retry_after → retry. After retry, 200 →
    return. Mutating the ``status_code == 429`` check or the
    ``continue`` would break the retry."""
    route = respx.get(f"{BASE_URL}/uniprotkb/P04637").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"primaryAccession": "P04637"}),
        ]
    )
    c = UniProtClient()
    try:
        result = await c.get_entry("P04637")
    finally:
        await c.close()
    assert route.call_count == 2
    assert result == {"primaryAccession": "P04637"}


@pytest.mark.asyncio
@respx.mock
async def test_req_retries_on_5xx_then_succeeds() -> None:
    """500 → exponential back-off → retry. After retry, 200 → return.
    Mutating the ``status_code >= 500`` check breaks this."""
    route = respx.get(f"{BASE_URL}/uniprotkb/P04637").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    c = UniProtClient()
    try:
        await c.get_entry("P04637")
    finally:
        await c.close()
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_req_raises_runtime_error_after_max_retries_exhausted() -> None:
    """All MAX_RETRIES + 1 attempts return 5xx → RuntimeError raised.
    Mutating the loop bound, the 'await self._req' arg list, or the
    final 'raise RuntimeError' breaks one of the assertions below."""
    # 4 = MAX_RETRIES (3) + 1 = 4 attempts total.
    route = respx.get(f"{BASE_URL}/uniprotkb/P04637").mock(return_value=httpx.Response(500))
    c = UniProtClient()
    try:
        with pytest.raises(RuntimeError, match="failed after 4 attempts"):
            await c.get_entry("P04637")
    finally:
        await c.close()
    # Each retry calls the upstream once; total = MAX_RETRIES + 1 = 4.
    assert route.call_count == 4


@pytest.mark.asyncio
@respx.mock
async def test_req_records_provenance_on_success() -> None:
    """A successful response must populate last_provenance with
    release/release_date headers and the resolved URL."""
    respx.get(f"{BASE_URL}/uniprotkb/P04637").mock(
        return_value=httpx.Response(
            200,
            json={"primaryAccession": "P04637"},
            headers={
                "X-UniProt-Release": "2026_02",
                "X-UniProt-Release-Date": "2026-04-15",
            },
        )
    )
    c = UniProtClient()
    try:
        await c.get_entry("P04637")
        assert c.last_provenance is not None
        assert c.last_provenance["release"] == "2026_02"
        assert c.last_provenance["release_date"] == "2026-04-15"
        assert c.last_provenance["source"] == "UniProt"
        assert c.last_provenance["url"].endswith("/uniprotkb/P04637")
    finally:
        await c.close()


@pytest.mark.asyncio
@respx.mock
async def test_req_raises_release_mismatch_when_pinned_disagrees() -> None:
    """A pinned client receiving a different release header must raise
    ReleaseMismatchError. Mutating the 'pin_release != provenance' guard
    breaks this."""
    respx.get(f"{BASE_URL}/uniprotkb/P04637").mock(
        return_value=httpx.Response(
            200,
            json={"x": 1},
            headers={"X-UniProt-Release": "2026_03"},
        )
    )
    c = UniProtClient(pin_release="2026_02")
    try:
        with pytest.raises(ReleaseMismatchError) as exc_info:
            await c.get_entry("P04637")
        assert exc_info.value.pinned == "2026_02"
        assert exc_info.value.observed == "2026_03"
    finally:
        await c.close()


@pytest.mark.asyncio
@respx.mock
async def test_req_does_not_raise_when_pinned_release_matches() -> None:
    """Same release as the pin → no error, request succeeds."""
    respx.get(f"{BASE_URL}/uniprotkb/P04637").mock(
        return_value=httpx.Response(
            200, json={"ok": True}, headers={"X-UniProt-Release": "2026_02"}
        )
    )
    c = UniProtClient(pin_release="2026_02")
    try:
        result = await c.get_entry("P04637")
        assert result == {"ok": True}
    finally:
        await c.close()


# ---------------------------------------------------------------------------
# id_mapping_submit + id_mapping_results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_id_mapping_submit_posts_to_idmapping_run() -> None:
    """id_mapping_submit POSTs to /idmapping/run with from/to/ids form
    fields and returns the jobId from the JSON response."""
    route = respx.post(f"{BASE_URL}/idmapping/run").mock(
        return_value=httpx.Response(200, json={"jobId": "abc123"})
    )
    c = UniProtClient()
    try:
        job_id = await c.id_mapping_submit("UniProtKB_AC-ID", "EMBL", ["P04637"])
    finally:
        await c.close()
    assert route.called
    assert job_id == "abc123"


@pytest.mark.asyncio
@respx.mock
async def test_id_mapping_submit_joins_ids_with_comma() -> None:
    """Multiple ids → comma-separated 'ids' form field."""
    route = respx.post(f"{BASE_URL}/idmapping/run").mock(
        return_value=httpx.Response(200, json={"jobId": "x"})
    )
    c = UniProtClient()
    try:
        await c.id_mapping_submit("UniProtKB_AC-ID", "EMBL", ["P04637", "P12345"])
    finally:
        await c.close()
    body = route.calls[0].request.content.decode()
    assert "ids=P04637%2CP12345" in body or "ids=P04637,P12345" in body


@pytest.mark.asyncio
@respx.mock
async def test_id_mapping_results_returns_immediate_results() -> None:
    """If 'results' key is present in status JSON, return it
    immediately (no further calls)."""
    route = respx.get(f"{BASE_URL}/idmapping/status/job1").mock(
        return_value=httpx.Response(200, json={"results": [{"from": "P04637", "to": "X"}]})
    )
    c = UniProtClient()
    try:
        out = await c.id_mapping_results("job1")
    finally:
        await c.close()
    assert route.call_count == 1
    assert out["results"] == [{"from": "P04637", "to": "X"}]


@pytest.mark.asyncio
@respx.mock
async def test_id_mapping_results_follows_redirect_url() -> None:
    """When status has 'redirectURL' (no results yet), follow it with
    a size param."""
    respx.get(f"{BASE_URL}/idmapping/status/job1").mock(
        return_value=httpx.Response(
            200, json={"redirectURL": "https://rest.uniprot.org/idmapping/results/job1"}
        )
    )
    redirect_route = respx.get("https://rest.uniprot.org/idmapping/results/job1").mock(
        return_value=httpx.Response(200, json={"results": [{"from": "X", "to": "Y"}]})
    )
    c = UniProtClient()
    try:
        out = await c.id_mapping_results("job1", size=200)
    finally:
        await c.close()
    assert redirect_route.called
    qs = dict(redirect_route.calls[0].request.url.params)
    assert qs.get("size") == "200"
    assert out["results"] == [{"from": "X", "to": "Y"}]


# ---------------------------------------------------------------------------
# batch_entries — client-side accession filter, OR-join, 100-entry cap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_batch_entries_filters_invalid_accessions_client_side() -> None:
    """Accessions failing ACCESSION_RE.match must be moved to the
    'invalid' return key, not sent upstream."""
    route = respx.get(f"{BASE_URL}/uniprotkb/search").mock(
        return_value=httpx.Response(200, json={"results": [{"primaryAccession": "P04637"}]})
    )
    c = UniProtClient()
    try:
        result = await c.batch_entries(["P04637", "not-an-accession", "P12345"])
    finally:
        await c.close()
    assert route.called
    assert "not-an-accession" in result["invalid"]
    assert len(result["results"]) == 1
    # The query string sent to upstream must contain only the valid IDs.
    qs = dict(route.calls[0].request.url.params)
    query = qs.get("query", "")
    assert "P04637" in query
    assert "not-an-accession" not in query


@pytest.mark.asyncio
@respx.mock
async def test_batch_entries_caps_at_100_accessions() -> None:
    """If >100 valid accessions are passed, only the first 100 are
    sent. Mutating the 100 cap or the slicing bounds breaks this."""
    route = respx.get(f"{BASE_URL}/uniprotkb/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    # 120 valid-shape accessions (4 distinct x 30 dupes); ACCESSION_RE accepts
    # all four, so all 120 are valid -> the 100-cap path is exercised.
    real = ["P04637", "Q9Y6K9", "O00187", "P12345"] * 30
    try:
        await c.batch_entries(real)
    finally:
        await c.close()
    qs = dict(route.calls[0].request.url.params)
    # The upstream `size` param must be <= 100.
    assert int(qs.get("size", "0")) <= 100


@pytest.mark.asyncio
@respx.mock
async def test_batch_entries_returns_empty_when_all_invalid() -> None:
    """All invalid → no upstream call, empty results, full invalid list."""
    route = respx.get(f"{BASE_URL}/uniprotkb/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        out = await c.batch_entries(["abc", "xyz", "123"])
    finally:
        await c.close()
    assert not route.called
    assert out["results"] == []
    assert out["invalid"] == ["abc", "xyz", "123"]


@pytest.mark.asyncio
@respx.mock
async def test_batch_entries_query_uses_or_join() -> None:
    """Multiple valid accessions are joined with ' OR ' as
    'accession:X OR accession:Y'."""
    route = respx.get(f"{BASE_URL}/uniprotkb/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )
    c = UniProtClient()
    try:
        await c.batch_entries(["P04637", "Q9Y6K9"])
    finally:
        await c.close()
    qs = dict(route.calls[0].request.url.params)
    query = qs.get("query", "")
    assert "accession:P04637" in query
    assert "accession:Q9Y6K9" in query
    assert " OR " in query


# ---------------------------------------------------------------------------
# get_clinvar_records — cross-origin to NCBI eutils
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_get_clinvar_records_calls_esearch_and_esummary() -> None:
    """Two-step flow: esearch.fcgi returns idlist, then esummary.fcgi
    returns the records. Mutating either path breaks one of the routes."""
    esearch = respx.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(
            200,
            json={"esearchresult": {"idlist": ["111", "222"], "count": "2"}},
        )
    )
    esummary = respx.get(f"{NCBI_EUTILS_BASE}/esummary.fcgi").mock(
        return_value=httpx.Response(
            200,
            json={
                "result": {
                    "uids": ["111", "222"],
                    "111": {"uid": "111", "title": "X"},
                    "222": {"uid": "222", "title": "Y"},
                }
            },
        )
    )
    c = UniProtClient()
    try:
        out = await c.get_clinvar_records("TP53", change="R175H")
    finally:
        await c.close()
    assert esearch.called
    assert esummary.called
    assert out["total"] == 2
    assert len(out["records"]) == 2
    assert out["records"][0]["uid"] == "111"


@pytest.mark.asyncio
@respx.mock
async def test_get_clinvar_records_skips_esummary_when_no_idlist() -> None:
    """If esearch returns an empty idlist, esummary is NOT called and
    total is preserved."""
    esearch = respx.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(
            200,
            json={"esearchresult": {"idlist": [], "count": "0"}},
        )
    )
    esummary = respx.get(f"{NCBI_EUTILS_BASE}/esummary.fcgi").mock(
        return_value=httpx.Response(200, json={})
    )
    c = UniProtClient()
    try:
        out = await c.get_clinvar_records("UNKNOWN_GENE")
    finally:
        await c.close()
    assert esearch.called
    assert not esummary.called
    assert out["total"] == 0
    assert out["records"] == []


@pytest.mark.asyncio
@respx.mock
async def test_get_clinvar_records_term_includes_gene_qualifier() -> None:
    """The esearch term must include '{gene}[Gene]' — pins the term
    construction string."""
    route = respx.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": [], "count": "0"}})
    )
    c = UniProtClient()
    try:
        await c.get_clinvar_records("BRCA1")
    finally:
        await c.close()
    qs = dict(route.calls[0].request.url.params)
    assert qs.get("term") == "BRCA1[Gene]"


@pytest.mark.asyncio
@respx.mock
async def test_get_clinvar_records_term_includes_variant_when_change_given() -> None:
    """When change is non-empty, term has ' AND "<change>"[Variant Name]'."""
    route = respx.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": [], "count": "0"}})
    )
    c = UniProtClient()
    try:
        await c.get_clinvar_records("TP53", change="R175H")
    finally:
        await c.close()
    qs = dict(route.calls[0].request.url.params)
    term = qs.get("term", "")
    assert "TP53[Gene]" in term
    assert '"R175H"[Variant Name]' in term


@pytest.mark.asyncio
@respx.mock
async def test_get_clinvar_records_db_param_is_clinvar() -> None:
    """db=clinvar must be in both calls' query strings."""
    es = respx.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(200, json={"esearchresult": {"idlist": [], "count": "0"}})
    )
    c = UniProtClient()
    try:
        await c.get_clinvar_records("TP53")
    finally:
        await c.close()
    qs = dict(es.calls[0].request.url.params)
    assert qs.get("db") == "clinvar"


# ---------------------------------------------------------------------------
# get_alphafold_summary — cross-origin to AlphaFold DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_get_alphafold_summary_calls_prediction_path() -> None:
    """The endpoint is /api/prediction/{accession} on AlphaFold DB."""
    route = respx.get(f"{ALPHAFOLD_API_BASE}/api/prediction/P04637").mock(
        return_value=httpx.Response(
            200,
            json=[{"latestVersion": 4, "modelCreatedDate": "2024-09-15"}],
        )
    )
    c = UniProtClient()
    try:
        record = await c.get_alphafold_summary("P04637")
    finally:
        await c.close()
    assert route.called
    assert record["latestVersion"] == 4
    assert c.last_provenance is not None
    assert c.last_provenance["source"] == "AlphaFoldDB"
    # version is rendered as 'v<N>'
    assert c.last_provenance["release"] == "v4"
    assert c.last_provenance["release_date"] == "2024-09-15"


@pytest.mark.asyncio
@respx.mock
async def test_get_alphafold_summary_returns_empty_when_no_payload() -> None:
    """Empty list → return {} and provenance with release=None."""
    respx.get(f"{ALPHAFOLD_API_BASE}/api/prediction/UNKNOWN").mock(
        return_value=httpx.Response(200, json=[])
    )
    c = UniProtClient()
    try:
        record = await c.get_alphafold_summary("UNKNOWN")
    finally:
        await c.close()
    assert record == {}
    assert c.last_provenance is not None
    assert c.last_provenance["release"] is None


@pytest.mark.asyncio
@respx.mock
async def test_get_alphafold_summary_handles_missing_latest_version() -> None:
    """If latestVersion is absent, release falls through to None."""
    respx.get(f"{ALPHAFOLD_API_BASE}/api/prediction/X").mock(
        return_value=httpx.Response(200, json=[{"modelCreatedDate": "2024-09-15"}])
    )
    c = UniProtClient()
    try:
        await c.get_alphafold_summary("X")
    finally:
        await c.close()
    assert c.last_provenance is not None
    assert c.last_provenance["release"] is None


# ---------------------------------------------------------------------------
# UniProtClient lazy client construction + close idempotence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_close_is_idempotent_when_no_client_yet() -> None:
    """close() must not error when called on a fresh client that
    never made a request. Mutating the 'is None or is_closed' guard
    in close() would cause an AttributeError."""
    c = UniProtClient()
    await c.close()  # must not raise
    await c.close()  # second call must also not raise


@pytest.mark.asyncio
@respx.mock
async def test_close_is_idempotent_after_a_request() -> None:
    """After one request, close() works once and subsequent close()
    calls also work (the is_closed branch)."""
    respx.get(f"{BASE_URL}/uniprotkb/P04637").mock(return_value=httpx.Response(200, json={}))
    c = UniProtClient()
    await c.get_entry("P04637")
    await c.close()
    await c.close()  # second call must not raise


# ---------------------------------------------------------------------------
# canonical_response_hash via _extract_provenance + parse_retry_after
# HTTP-date branch (lines 212, 236, 247)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_provenance_records_canonical_hash_for_json_body() -> None:
    """A successful JSON request populates last_provenance with a
    SHA-256 hex digest of length 64 — exercises canonical_response_hash
    path (line 236) inside _req's success path."""
    respx.get(f"{BASE_URL}/uniprotkb/P04637").mock(return_value=httpx.Response(200, json={"a": 1}))
    c = UniProtClient()
    try:
        await c.get_entry("P04637")
        assert c.last_provenance is not None
        h = c.last_provenance["response_sha256"]
        assert len(h) == 64
        assert all(ch in "0123456789abcdef" for ch in h)
    finally:
        await c.close()


@pytest.mark.asyncio
@respx.mock
async def test_provenance_retrieved_at_is_recent() -> None:
    """retrieved_at is captured at extraction time (line 247:
    ``moment = now if now is not None else datetime.now(tz=UTC)``).
    The format must end in 'Z' and parse as a recent ISO-8601."""
    from datetime import UTC as _UTC
    from datetime import datetime

    respx.get(f"{BASE_URL}/uniprotkb/P04637").mock(return_value=httpx.Response(200, json={}))
    c = UniProtClient()
    try:
        await c.get_entry("P04637")
        assert c.last_provenance is not None
        ra = c.last_provenance["retrieved_at"]
        assert ra.endswith("Z")
        # Parse and verify it's within the last minute.
        ts = datetime.strptime(ra, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_UTC)
        delta_seconds = abs((datetime.now(tz=_UTC) - ts).total_seconds())
        assert delta_seconds < 60
    finally:
        await c.close()
