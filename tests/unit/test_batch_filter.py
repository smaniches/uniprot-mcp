"""Locks in the batch_entries partial-failure fix.

Before the fix, mixing one invalid accession into a batch caused UniProt
to return HTTP 400 and the whole batch failed. After the fix, invalid
tokens are filtered client-side and surfaced in the `invalid` list; the
HTTP call only contains well-formed accessions.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from uniprot_mcp.client import UniProtClient


@pytest.fixture
def mock_search():
    with respx.mock(base_url="https://rest.uniprot.org", assert_all_called=False) as router:
        route = router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"primaryAccession": "P04637"},
                        {"primaryAccession": "P38398"},
                    ]
                },
            )
        )
        yield router, route


async def test_partitions_valid_and_invalid(mock_search) -> None:
    _router, route = mock_search
    client = UniProtClient()
    try:
        out = await client.batch_entries(["P04637", "INVALIDXYZ", "P38398"])
    finally:
        await client.close()

    assert {r["primaryAccession"] for r in out["results"]} == {"P04637", "P38398"}
    assert out["invalid"] == ["INVALIDXYZ"]
    assert route.called, "expected a single HTTP call for the valid tokens"
    sent_query = route.calls[0].request.url.params["query"]
    assert "accession:P04637" in sent_query
    assert "accession:P38398" in sent_query
    assert "INVALIDXYZ" not in sent_query


async def test_all_invalid_short_circuits_no_http(mock_search) -> None:
    _router, route = mock_search
    client = UniProtClient()
    try:
        out = await client.batch_entries(["garbage1", "garbage2"])
    finally:
        await client.close()

    assert out == {"results": [], "invalid": ["garbage1", "garbage2"]}
    assert not route.called, "no HTTP request should be sent when all tokens are invalid"


async def test_caps_at_100(mock_search) -> None:
    _router, route = mock_search
    # 150 accessions that match the UniProt 6-char pattern [OPQ][0-9][A-Z0-9]{3}[0-9]
    valid = [f"P{i:05d}" for i in range(150)]
    client = UniProtClient()
    try:
        await client.batch_entries(valid)
    finally:
        await client.close()

    assert route.called, "expected one HTTP call"
    size = int(route.calls[0].request.url.params["size"])
    assert size == 100, f"batch must cap at 100, got {size}"


async def test_empty_input() -> None:
    client = UniProtClient()
    try:
        out = await client.batch_entries([])
    finally:
        await client.close()
    assert out == {"results": [], "invalid": []}
