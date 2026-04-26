"""Tests for the UniRef cluster tools added in Wave B/2.

Covers `uniprot_get_uniref` and `uniprot_search_uniref` plus the
identifier regex and the identity-tier query-folding logic.
"""

from __future__ import annotations

import json

import httpx
import respx

from uniprot_mcp.client import UNIREF_ID_RE
from uniprot_mcp.formatters import (
    _uniref_representative,
    _uniref_tier,
    fmt_uniref,
    fmt_uniref_search,
)
from uniprot_mcp.server import uniprot_get_uniref, uniprot_search_uniref

# ---------------------------------------------------------------------------
# Identifier regex
# ---------------------------------------------------------------------------


def test_uniref_id_regex_accepts_all_three_tiers() -> None:
    assert UNIREF_ID_RE.match("UniRef50_P04637")
    assert UNIREF_ID_RE.match("UniRef90_P04637")
    assert UNIREF_ID_RE.match("UniRef100_P04637")


def test_uniref_id_regex_accepts_long_accession_form() -> None:
    assert UNIREF_ID_RE.match("UniRef50_A0A1B2C3D4")


def test_uniref_id_regex_accepts_uniparc_upi_suffix() -> None:
    assert UNIREF_ID_RE.match("UniRef100_UPI0000000ABC")


def test_uniref_id_regex_rejects_non_canonical() -> None:
    for bad in (
        "uniref50_P04637",  # lowercase prefix
        "UniRef25_P04637",  # invalid tier
        "UniRef50P04637",  # missing underscore
        "UniRef50_p04637",  # lowercase accession
        "UniRef50_P046",  # truncated accession
        "P04637",  # bare accession
        "",
    ):
        assert not UNIREF_ID_RE.match(bad), f"should reject {bad!r}"


# ---------------------------------------------------------------------------
# Tool validation rejections
# ---------------------------------------------------------------------------


async def test_get_uniref_rejects_bad_id_without_network() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_get_uniref("UniRef25_P04637", "markdown")
    assert "Input error" in out and "UniRef" in out
    assert not router.calls


async def test_search_uniref_rejects_bad_identity_tier() -> None:
    out = await uniprot_search_uniref("kinase", identity_tier="42")
    assert "identity_tier must be" in out


async def test_search_uniref_rejects_oversize_query() -> None:
    out = await uniprot_search_uniref("x" * 1000)
    assert "Input error" in out


# ---------------------------------------------------------------------------
# Identity-tier folding into UniProt query syntax
# ---------------------------------------------------------------------------


async def test_search_uniref_folds_50_into_query_as_decimal() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniref/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        await uniprot_search_uniref("kinase", identity_tier="50")
    sent = route.calls[0].request.url.params["query"]
    assert "identity:0.5" in sent
    assert "kinase" in sent


async def test_search_uniref_folds_90_into_query_as_decimal() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniref/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        await uniprot_search_uniref("kinase", identity_tier="90")
    sent = route.calls[0].request.url.params["query"]
    assert "identity:0.9" in sent


async def test_search_uniref_folds_100_into_query_as_decimal() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniref/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        await uniprot_search_uniref("kinase", identity_tier="100")
    sent = route.calls[0].request.url.params["query"]
    assert "identity:1.0" in sent


async def test_search_uniref_no_tier_means_no_identity_clause() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniref/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        await uniprot_search_uniref("kinase")
    sent = route.calls[0].request.url.params["query"]
    assert "identity:" not in sent


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

_UNIREF_FIXTURE = {
    "id": "UniRef50_P04637",
    "name": "Cluster: Cellular tumor antigen p53",
    "entryType": "UniRef50",
    "representativeMember": {
        "memberId": "P04637",
        "uniprotKBId": "P53_HUMAN",
        "memberIdType": "UniProtKB ID",
    },
    "memberCount": 247,
    "commonTaxon": {"scientificName": "Eukaryota", "taxonId": 2759},
    "updated": "2026-03-01",
    "members": [
        {"memberId": "P04637"},
        {"memberId": "P02340"},
        {"memberId": "P10361"},
    ],
}


async def test_get_uniref_happy_path_markdown() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniref/UniRef50_P04637").mock(
            return_value=httpx.Response(
                200,
                json=_UNIREF_FIXTURE,
                headers={
                    "X-UniProt-Release": "2026_02",
                    "X-UniProt-Release-Date": "2026-03-05",
                },
            )
        )
        out = await uniprot_get_uniref("UniRef50_P04637", "markdown")
    assert "## UniRef50_P04637: Cluster: Cellular tumor antigen p53" in out
    assert "**Identity tier:** 50%" in out
    assert "**Representative:** P04637 (P53_HUMAN)" in out
    assert "**Member count:** 247" in out
    assert "Eukaryota (taxId 2759)" in out
    assert "**Last updated:** 2026-03-01" in out
    assert "P04637, P02340, P10361" in out
    assert "release 2026_02 (2026-03-05)" in out


async def test_get_uniref_happy_path_json() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniref/UniRef50_P04637").mock(
            return_value=httpx.Response(
                200,
                json=_UNIREF_FIXTURE,
                headers={"X-UniProt-Release": "2026_02"},
            )
        )
        out = await uniprot_get_uniref("UniRef50_P04637", "json")
    payload = json.loads(out)
    assert payload["data"]["id"] == "UniRef50_P04637"
    assert payload["provenance"]["release"] == "2026_02"


async def test_search_uniref_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniref/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "UniRef50_P04637",
                            "name": "TP53 cluster",
                            "entryType": "UniRef50",
                            "memberCount": 247,
                            "representativeMember": {
                                "memberId": "P04637",
                                "uniprotKBId": "P53_HUMAN",
                            },
                        },
                        {
                            "id": "UniRef90_P04637",
                            "name": "TP53 cluster (90%)",
                            "entryType": "UniRef90",
                            "memberCount": 73,
                            "representativeMember": {"memberId": "P04637"},
                        },
                    ]
                },
                headers={"X-UniProt-Release": "2026_02"},
            )
        )
        out = await uniprot_search_uniref("p53", identity_tier="50", size=5)
    assert "**2 UniRef clusters**" in out
    assert "UniRef50_P04637" in out
    assert "UniRef90_P04637" in out
    assert "247 members" in out
    assert "73 members" in out
    assert "rep P04637" in out


# ---------------------------------------------------------------------------
# Helper resilience
# ---------------------------------------------------------------------------


def test_uniref_tier_prefers_entry_type() -> None:
    assert _uniref_tier({"entryType": "UniRef90", "id": "UniRef50_X"}) == "90"


def test_uniref_tier_falls_back_to_id_prefix() -> None:
    assert _uniref_tier({"id": "UniRef100_P04637"}) == "100"


def test_uniref_tier_unknown_returns_question_mark() -> None:
    assert _uniref_tier({}) == "?"


def test_uniref_representative_handles_missing_fields() -> None:
    assert _uniref_representative({}) == ""
    assert _uniref_representative({"representativeMember": {"memberId": "P04637"}}) == "P04637"


def test_fmt_uniref_minimal_shape() -> None:
    out = fmt_uniref({"id": "UniRef50_P04637"}, "markdown")
    assert "## UniRef50_P04637" in out


def test_fmt_uniref_search_truncates_after_fifty() -> None:
    big = {
        "results": [
            {
                "id": f"UniRef50_P{i:05d}",
                "name": f"Cluster {i}",
                "entryType": "UniRef50",
                "memberCount": 10,
            }
            for i in range(60)
        ]
    }
    out = fmt_uniref_search(big, "markdown")
    assert "**60 UniRef clusters**" in out
    assert "+10 more" in out
