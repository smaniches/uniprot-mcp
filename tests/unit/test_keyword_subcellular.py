"""Tests for the controlled-vocabulary tools added in Wave B/1.

Covers the four new tools — `uniprot_get_keyword`,
`uniprot_search_keywords`, `uniprot_get_subcellular_location`,
`uniprot_search_subcellular_locations` — at three layers:

1. **Validation.** Bad IDs are rejected before any HTTP call.
2. **Happy path.** Mocked UniProt responses produce well-formed
   Markdown / JSON envelopes including the provenance footer.
3. **Search shape.** Search results render as bulleted lists capped
   at 50 items, with a "+N more" suffix when truncated.
"""

from __future__ import annotations

import json

import httpx
import respx

from uniprot_mcp.client import KEYWORD_ID_RE, SUBCELLULAR_LOCATION_ID_RE
from uniprot_mcp.formatters import (
    fmt_keyword,
    fmt_keyword_search,
    fmt_subcellular_location,
    fmt_subcellular_location_search,
)
from uniprot_mcp.server import (
    uniprot_get_keyword,
    uniprot_get_subcellular_location,
    uniprot_search_keywords,
    uniprot_search_subcellular_locations,
)

# ---------------------------------------------------------------------------
# Identifier regex shape
# ---------------------------------------------------------------------------


def test_keyword_id_regex_accepts_canonical_form() -> None:
    assert KEYWORD_ID_RE.match("KW-0007")
    assert KEYWORD_ID_RE.match("KW-9999")


def test_keyword_id_regex_rejects_non_canonical() -> None:
    for bad in ("kw-0007", "KW-7", "KW-00007", "KW-ABCD", "0007", "KW0007", ""):
        assert not KEYWORD_ID_RE.match(bad), f"should reject {bad!r}"


def test_subcellular_location_id_regex_accepts_canonical_form() -> None:
    assert SUBCELLULAR_LOCATION_ID_RE.match("SL-0039")
    assert SUBCELLULAR_LOCATION_ID_RE.match("SL-0191")


def test_subcellular_location_id_regex_rejects_non_canonical() -> None:
    for bad in ("sl-0086", "SL-86", "SL-00086", "SL-XXXX", "0086", "SL0086", ""):
        assert not SUBCELLULAR_LOCATION_ID_RE.match(bad), f"should reject {bad!r}"


# ---------------------------------------------------------------------------
# Tool validation rejections (no network)
# ---------------------------------------------------------------------------


async def test_get_keyword_rejects_bad_id_without_network() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_get_keyword("KW-7", "markdown")
    assert "Input error" in out and "KW-0007" in out
    assert not router.calls


async def test_get_keyword_rejects_bad_format() -> None:
    out = await uniprot_get_keyword("KW-0007", "yaml")
    assert "response_format must be one of" in out


async def test_get_subcellular_location_rejects_bad_id_without_network() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_get_subcellular_location("SL-86", "markdown")
    # Error message gives an example canonical ID. Real Cell-membrane = SL-0039.
    assert "Input error" in out and "SL-" in out
    assert not router.calls


async def test_search_keywords_rejects_oversize_query() -> None:
    out = await uniprot_search_keywords("x" * 1000, response_format="markdown")
    assert "Input error" in out and "query" in out


async def test_search_subcellular_locations_rejects_oversize_query() -> None:
    out = await uniprot_search_subcellular_locations("x" * 1000)
    assert "Input error" in out


# ---------------------------------------------------------------------------
# Happy paths through respx
# ---------------------------------------------------------------------------

_KEYWORD_FIXTURE = {
    "keyword": {"id": "KW-0007", "name": "Acetylation"},
    "definition": (
        "Protein modification consisting of adding an acetyl group to specific amino acids."
    ),
    "category": "PTM",
    "synonyms": ["Acetyl", "N-acetylation"],
    "geneOntologies": [{"id": "GO:0006473", "name": "protein acetylation"}],
    "parents": [{"keyword": {"id": "KW-0123", "name": "Protein modification"}}],
    "children": [],
    "statistics": {"reviewedProteinCount": 12345, "unreviewedProteinCount": 678},
}

_SUBCELLULAR_FIXTURE = {
    "id": "SL-0039",
    "name": "Cell membrane",
    "definition": "The membrane that surrounds a cell.",
    "category": "Cellular component",
    "synonyms": ["Plasma membrane", "Plasmalemma"],
    "keyword": {"id": "KW-1003", "name": "Cell membrane"},
    "isA": [{"id": "SL-0162", "name": "Membrane"}],
    "isPartOf": [],
    "parts": [],
    "geneOntologies": [{"id": "GO:0005886", "name": "plasma membrane"}],
    "statistics": {"reviewedProteinCount": 9876, "unreviewedProteinCount": 1234},
}


async def test_get_keyword_happy_path_markdown() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/keywords/KW-0007").mock(
            return_value=httpx.Response(
                200,
                json=_KEYWORD_FIXTURE,
                headers={
                    "X-UniProt-Release": "2026_02",
                    "X-UniProt-Release-Date": "2026-03-05",
                },
            )
        )
        out = await uniprot_get_keyword("KW-0007", "markdown")
    assert "## KW-0007: Acetylation" in out
    assert "**Category:** PTM" in out
    assert "**Definition:**" in out
    assert "Acetyl, N-acetylation" in out
    assert "GO:0006473" in out
    assert "12345 reviewed, 678 unreviewed" in out
    assert "release 2026_02 (2026-03-05)" in out  # provenance footer


async def test_get_keyword_happy_path_json() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/keywords/KW-0007").mock(
            return_value=httpx.Response(
                200,
                json=_KEYWORD_FIXTURE,
                headers={"X-UniProt-Release": "2026_02"},
            )
        )
        out = await uniprot_get_keyword("KW-0007", "json")
    payload = json.loads(out)
    assert payload["data"]["keyword"]["id"] == "KW-0007"
    assert payload["provenance"]["release"] == "2026_02"


async def test_search_keywords_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/keywords/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {"keyword": {"id": "KW-0007", "name": "Acetylation"}, "category": "PTM"},
                        {
                            "keyword": {"id": "KW-0539", "name": "Nucleus"},
                            "category": "Cellular component",
                        },
                    ]
                },
                headers={"X-UniProt-Release": "2026_02"},
            )
        )
        out = await uniprot_search_keywords("nucleus", size=5)
    assert "**2 keywords**" in out
    assert "**KW-0007**: Acetylation [PTM]" in out
    assert "**KW-0539**: Nucleus [Cellular component]" in out
    assert "release 2026_02" in out


async def test_get_subcellular_location_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/locations/SL-0039").mock(
            return_value=httpx.Response(
                200,
                json=_SUBCELLULAR_FIXTURE,
                headers={
                    "X-UniProt-Release": "2026_02",
                    "X-UniProt-Release-Date": "2026-03-05",
                },
            )
        )
        out = await uniprot_get_subcellular_location("SL-0039", "markdown")
    assert "## SL-0039: Cell membrane" in out
    assert "**Category:** Cellular component" in out
    assert "Plasma membrane, Plasmalemma" in out
    assert "**Keyword:** KW-1003 (Cell membrane)" in out
    assert "**Is-a:** Membrane" in out
    assert "GO:0005886" in out
    assert "9876 reviewed, 1234 unreviewed" in out
    assert "release 2026_02 (2026-03-05)" in out


async def test_search_subcellular_locations_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/locations/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "SL-0039",
                            "name": "Cell membrane",
                            "category": "Cellular component",
                        },
                        {"id": "SL-0191", "name": "Nucleus", "category": "Cellular component"},
                    ]
                },
                headers={"X-UniProt-Release": "2026_02"},
            )
        )
        out = await uniprot_search_subcellular_locations("membrane", size=5)
    assert "**2 subcellular locations**" in out
    assert "**SL-0039**: Cell membrane" in out
    assert "**SL-0191**: Nucleus" in out


# ---------------------------------------------------------------------------
# Truncation behaviour (>50 search results)
# ---------------------------------------------------------------------------


def test_keyword_search_truncates_after_fifty() -> None:
    big = {
        "results": [
            {"keyword": {"id": f"KW-{i:04d}", "name": f"Term-{i}"}, "category": "PTM"}
            for i in range(60)
        ]
    }
    out = fmt_keyword_search(big, "markdown")
    assert "**60 keywords**" in out
    assert "+10 more" in out


def test_subcellular_location_search_truncates_after_fifty() -> None:
    big = {
        "results": [
            {"id": f"SL-{i:04d}", "name": f"Loc-{i}", "category": "Cellular component"}
            for i in range(60)
        ]
    }
    out = fmt_subcellular_location_search(big, "markdown")
    assert "**60 subcellular locations**" in out
    assert "+10 more" in out


# ---------------------------------------------------------------------------
# Defensive shape handling — missing fields don't crash
# ---------------------------------------------------------------------------


def test_fmt_keyword_minimal_shape() -> None:
    out = fmt_keyword({"keyword": {"id": "KW-0007", "name": "X"}}, "markdown")
    assert "## KW-0007: X" in out


def test_fmt_keyword_handles_flat_id_form() -> None:
    """Some endpoint variants serialize keyword as a flat string."""
    out = fmt_keyword({"keyword": "KW-0007", "name": "X"}, "markdown")
    assert "## KW-0007: X" in out


def test_fmt_subcellular_location_minimal_shape() -> None:
    out = fmt_subcellular_location({"id": "SL-0039", "name": "X"}, "markdown")
    assert "## SL-0039: X" in out
