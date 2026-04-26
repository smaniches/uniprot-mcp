"""Tests for the provenance subsystem (§3a.3).

Every successful UniProt response must carry a machine-verifiable
``Provenance`` record — release number, release date, retrieval
timestamp, and the resolved URL — and every public tool must surface
that record in its output. These tests pin:

1. Extraction — headers are parsed into the correct Provenance shape.
2. Client wiring — a successful request updates ``last_provenance``;
   a failed request never leaks a partial or stale value into the
   success path.
3. Formatter wiring — every ``fmt_*`` helper emits the Markdown footer
   and the JSON envelope when (and only when) a provenance record is
   supplied. FASTA output uses PIR-style ``;``-prefix lines.
4. Tool wiring — the full server-side path (tool handler →
   ``client.last_provenance`` → formatter) produces output containing
   the release identifier.
"""

from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime

import httpx
import respx

from uniprot_mcp.client import (
    SOURCE_NAME,
    Provenance,
    UniProtClient,
    _extract_provenance,
)
from uniprot_mcp.formatters import (
    fmt_crossrefs,
    fmt_entry,
    fmt_fasta,
    fmt_features,
    fmt_go,
    fmt_idmapping,
    fmt_search,
    fmt_taxonomy,
    fmt_variants,
)
from uniprot_mcp.server import uniprot_get_entry, uniprot_get_sequence

# Fixed Provenance used throughout the formatter tests so assertions are
# deterministic. Mirrors the shape a live UniProt response would produce
# circa 2026-02.
_FIXED_PROV: Provenance = {
    "source": "UniProt",
    "release": "2026_02",
    "release_date": "2026-03-05",
    "retrieved_at": "2026-04-24T12:00:00Z",
    "url": "https://rest.uniprot.org/uniprotkb/P04637",
    "response_sha256": "a" * 64,
}


# ---------------------------------------------------------------------------
# _extract_provenance — header parsing
# ---------------------------------------------------------------------------


def test_extract_provenance_reads_release_headers() -> None:
    now = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)
    response = httpx.Response(
        200,
        headers={
            "X-UniProt-Release": "2026_02",
            "X-UniProt-Release-Date": "2026-03-05",
        },
        request=httpx.Request("GET", "https://rest.uniprot.org/uniprotkb/P04637"),
    )
    prov = _extract_provenance(response, now=now)
    assert prov["source"] == SOURCE_NAME
    assert prov["release"] == "2026_02"
    assert prov["release_date"] == "2026-03-05"
    assert prov["retrieved_at"] == "2026-04-24T12:00:00Z"
    assert prov["url"] == "https://rest.uniprot.org/uniprotkb/P04637"


def test_extract_provenance_handles_missing_headers() -> None:
    """When UniProt omits the release headers, release fields are ``None``
    but source, retrieved_at, and url are still populated."""
    now = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)
    response = httpx.Response(
        200,
        request=httpx.Request("GET", "https://rest.uniprot.org/taxonomy/search"),
    )
    prov = _extract_provenance(response, now=now)
    assert prov["source"] == SOURCE_NAME
    assert prov["release"] is None
    assert prov["release_date"] is None
    assert prov["retrieved_at"] == "2026-04-24T12:00:00Z"
    assert prov["url"] == "https://rest.uniprot.org/taxonomy/search"


# ---------------------------------------------------------------------------
# Client wiring
# ---------------------------------------------------------------------------


async def test_client_last_provenance_is_none_before_any_request() -> None:
    client = UniProtClient()
    try:
        assert client.last_provenance is None
    finally:
        await client.close()


async def test_client_populates_last_provenance_after_success() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P04637"},
                headers={
                    "X-UniProt-Release": "2026_02",
                    "X-UniProt-Release-Date": "2026-03-05",
                },
            )
        )
        client = UniProtClient()
        try:
            await client.get_entry("P04637")
            prov = client.last_provenance
        finally:
            await client.close()
    assert prov is not None
    assert prov["release"] == "2026_02"
    assert prov["release_date"] == "2026-03-05"
    assert prov["url"].endswith("/uniprotkb/P04637")


async def test_client_last_provenance_unchanged_after_4xx() -> None:
    """A failing request raises before the provenance is recorded — a
    prior successful request's value must not be silently overwritten
    with a partial record built from the error response."""
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P04637"},
                headers={"X-UniProt-Release": "2026_02"},
            )
        )
        router.get("/uniprotkb/QBAD00").mock(return_value=httpx.Response(400))
        client = UniProtClient()
        try:
            await client.get_entry("P04637")
            before = client.last_provenance
            with contextlib.suppress(httpx.HTTPStatusError):
                await client.get_entry("QBAD00")
            after = client.last_provenance
        finally:
            await client.close()
    assert before is not None
    assert after is before, "failed request must not clobber last_provenance"


async def test_id_mapping_submit_populates_last_provenance() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.post("/idmapping/run").mock(
            return_value=httpx.Response(
                200,
                json={"jobId": "J1"},
                headers={"X-UniProt-Release": "2026_02"},
            )
        )
        client = UniProtClient()
        try:
            await client.id_mapping_submit("Gene_Name", "UniProtKB", ["BRCA1"])
            prov = client.last_provenance
        finally:
            await client.close()
    assert prov is not None
    assert prov["release"] == "2026_02"
    assert prov["url"].endswith("/idmapping/run")


# ---------------------------------------------------------------------------
# Formatter Markdown footer
# ---------------------------------------------------------------------------


def _assert_md_footer_present(out: str) -> None:
    assert "---" in out
    assert "Source: UniProt release 2026_02 (2026-03-05)" in out
    assert "Retrieved 2026-04-24T12:00:00Z" in out
    assert "https://rest.uniprot.org/uniprotkb/P04637" in out


def test_fmt_entry_md_footer() -> None:
    out = fmt_entry({"primaryAccession": "P04637"}, "markdown", provenance=_FIXED_PROV)
    _assert_md_footer_present(out)


def test_fmt_search_md_footer() -> None:
    out = fmt_search({"results": []}, "markdown", provenance=_FIXED_PROV)
    _assert_md_footer_present(out)


def test_fmt_features_md_footer() -> None:
    out = fmt_features([], "P04637", "markdown", provenance=_FIXED_PROV)
    _assert_md_footer_present(out)


def test_fmt_go_md_footer() -> None:
    out = fmt_go([], "P04637", None, "markdown", provenance=_FIXED_PROV)
    _assert_md_footer_present(out)


def test_fmt_crossrefs_md_footer() -> None:
    out = fmt_crossrefs([], "P04637", None, "markdown", provenance=_FIXED_PROV)
    _assert_md_footer_present(out)


def test_fmt_variants_md_footer() -> None:
    out = fmt_variants([], "P04637", "markdown", provenance=_FIXED_PROV)
    _assert_md_footer_present(out)


def test_fmt_idmapping_md_footer() -> None:
    out = fmt_idmapping({"results": [], "failedIds": []}, "markdown", provenance=_FIXED_PROV)
    _assert_md_footer_present(out)


def test_fmt_taxonomy_md_footer() -> None:
    out = fmt_taxonomy({"results": []}, "markdown", provenance=_FIXED_PROV)
    _assert_md_footer_present(out)


def test_md_footer_degrades_gracefully_without_release() -> None:
    """When a response omits the release headers, the footer still
    renders but drops the release clause."""
    prov: Provenance = {
        "source": "UniProt",
        "release": None,
        "release_date": None,
        "retrieved_at": "2026-04-24T12:00:00Z",
        "url": "https://rest.uniprot.org/taxonomy/search",
    }
    out = fmt_taxonomy({"results": []}, "markdown", provenance=prov)
    assert "Source: UniProt •" in out
    assert "release" not in out.lower()
    assert "2026-04-24T12:00:00Z" in out


# ---------------------------------------------------------------------------
# Formatter JSON envelope
# ---------------------------------------------------------------------------


def _assert_json_envelope(raw: str, *, data_check) -> None:
    payload = json.loads(raw)
    assert "data" in payload
    assert "provenance" in payload
    assert payload["provenance"]["release"] == "2026_02"
    assert payload["provenance"]["release_date"] == "2026-03-05"
    data_check(payload["data"])


def test_fmt_entry_json_envelope() -> None:
    _assert_json_envelope(
        fmt_entry({"primaryAccession": "P04637"}, "json", provenance=_FIXED_PROV),
        data_check=lambda d: d == {"primaryAccession": "P04637"},
    )


def test_fmt_search_json_envelope() -> None:
    _assert_json_envelope(
        fmt_search({"results": []}, "json", provenance=_FIXED_PROV),
        data_check=lambda d: d["results"] == [],
    )


def test_fmt_features_json_envelope_wraps_list() -> None:
    """Features is a bare list; envelope must still wrap it under ``data``."""
    _assert_json_envelope(
        fmt_features([], "P04637", "json", provenance=_FIXED_PROV),
        data_check=lambda d: d == [],
    )


def test_fmt_go_json_envelope() -> None:
    _assert_json_envelope(
        fmt_go([], "P04637", None, "json", provenance=_FIXED_PROV),
        data_check=lambda d: d == [],
    )


def test_fmt_crossrefs_json_envelope() -> None:
    _assert_json_envelope(
        fmt_crossrefs([], "P04637", None, "json", provenance=_FIXED_PROV),
        data_check=lambda d: d == [],
    )


def test_fmt_variants_json_envelope() -> None:
    _assert_json_envelope(
        fmt_variants([], "P04637", "json", provenance=_FIXED_PROV),
        data_check=lambda d: d == [],
    )


def test_fmt_idmapping_json_envelope() -> None:
    _assert_json_envelope(
        fmt_idmapping({"results": [], "failedIds": []}, "json", provenance=_FIXED_PROV),
        data_check=lambda d: d == {"results": [], "failedIds": []},
    )


def test_fmt_taxonomy_json_envelope() -> None:
    _assert_json_envelope(
        fmt_taxonomy({"results": []}, "json", provenance=_FIXED_PROV),
        data_check=lambda d: d == {"results": []},
    )


def test_json_without_provenance_emits_bare_payload() -> None:
    """Back-compat: when provenance is omitted the old shape is preserved
    — no ``data`` / ``provenance`` wrapper, parsers continue to work."""
    out = fmt_entry({"primaryAccession": "P04637"}, "json")
    parsed = json.loads(out)
    assert parsed == {"primaryAccession": "P04637"}
    assert "provenance" not in parsed


# ---------------------------------------------------------------------------
# FASTA helper
# ---------------------------------------------------------------------------


def test_fmt_fasta_prepends_pir_comment_block() -> None:
    fasta = ">sp|P04637|P53_HUMAN\nMEEPQSD\n"
    out = fmt_fasta(fasta, provenance=_FIXED_PROV)
    lines = out.splitlines()
    assert lines[0].startswith(";Source: UniProt")
    assert any(line.startswith(";Release: 2026_02") for line in lines[:5])
    assert any(line.startswith(";Retrieved: 2026-04-24T12:00:00Z") for line in lines[:5])
    assert ">sp|P04637|P53_HUMAN" in out
    # Every `;` header line must sit *before* the first `>` record.
    first_record = next(i for i, line in enumerate(lines) if line.startswith(">"))
    for line in lines[:first_record]:
        assert line.startswith(";"), f"non-comment line before first record: {line!r}"


def test_fmt_fasta_without_provenance_is_identity() -> None:
    fasta = ">sp|P04637|P53_HUMAN\nMEEPQSD\n"
    assert fmt_fasta(fasta) == fasta


# ---------------------------------------------------------------------------
# End-to-end tool wiring
# ---------------------------------------------------------------------------


async def test_get_entry_tool_surfaces_release_in_markdown() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={
                    "primaryAccession": "P04637",
                    "entryType": "UniProtKB reviewed (Swiss-Prot)",
                    "proteinDescription": {"recommendedName": {"fullName": {"value": "p53"}}},
                    "genes": [{"geneName": {"value": "TP53"}}],
                    "organism": {"scientificName": "Homo sapiens"},
                },
                headers={
                    "X-UniProt-Release": "2026_02",
                    "X-UniProt-Release-Date": "2026-03-05",
                },
            )
        )
        out = await uniprot_get_entry("P04637", "markdown")
    assert "2026_02" in out
    assert "2026-03-05" in out
    assert "https://rest.uniprot.org/uniprotkb/P04637" in out


async def test_get_entry_tool_surfaces_release_in_json() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P04637"},
                headers={
                    "X-UniProt-Release": "2026_02",
                    "X-UniProt-Release-Date": "2026-03-05",
                },
            )
        )
        out = await uniprot_get_entry("P04637", "json")
    payload = json.loads(out)
    assert payload["data"]["primaryAccession"] == "P04637"
    assert payload["provenance"]["release"] == "2026_02"
    assert payload["provenance"]["release_date"] == "2026-03-05"


async def test_get_sequence_tool_prepends_pir_provenance() -> None:
    fasta = ">sp|P04637|P53_HUMAN\nMEEPQSD\n"
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                text=fasta,
                headers={
                    "X-UniProt-Release": "2026_02",
                    "X-UniProt-Release-Date": "2026-03-05",
                },
            )
        )
        out = await uniprot_get_sequence("P04637")
    lines = out.splitlines()
    assert lines[0] == ";Source: UniProt"
    assert ";Release: 2026_02 (2026-03-05)" in out
    assert ">sp|P04637|P53_HUMAN" in out
