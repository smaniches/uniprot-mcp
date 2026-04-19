"""Unit tests for formatters — offline, fixture-driven."""

from __future__ import annotations

from uniprot_mcp.formatters import (
    fmt_crossrefs,
    fmt_entry,
    fmt_features,
    fmt_go,
    fmt_idmapping,
    fmt_search,
    fmt_taxonomy,
    fmt_variants,
)


def test_fmt_entry_markdown_contains_core_fields(fixture_loader) -> None:
    entry = fixture_loader("p04637_min")
    out = fmt_entry(entry, "markdown")
    assert "P04637" in out
    assert "Cellular tumor antigen p53" in out
    assert "**Gene:** TP53" in out
    assert "Homo sapiens" in out
    assert "Swiss-Prot" in out


def test_fmt_entry_json_roundtrips(fixture_loader) -> None:
    import json as _json

    entry = fixture_loader("p04637_min")
    out = fmt_entry(entry, "json")
    parsed = _json.loads(out)
    assert parsed["primaryAccession"] == "P04637"


def test_fmt_search_counts_results(fixture_loader) -> None:
    data = fixture_loader("brca1_search_min")
    out = fmt_search(data, "markdown")
    assert "**1 results**" in out
    assert "P38398" in out
    assert "BRCA1" in out


def test_fmt_features_groups_by_type(fixture_loader) -> None:
    entry = fixture_loader("p04637_min")
    out = fmt_features(entry["features"], "P04637", "markdown")
    assert "## Features: P04637" in out
    assert "### Domain" in out
    assert "### Modified residue" in out


def test_fmt_variants_filters_natural_variants(fixture_loader) -> None:
    entry = fixture_loader("p04637_min")
    out = fmt_variants(entry["features"], "P04637", "markdown")
    assert "## Variants: P04637" in out


def test_fmt_go_groups_by_aspect(fixture_loader) -> None:
    entry = fixture_loader("p04637_min")
    out = fmt_go(entry["uniProtKBCrossReferences"], "P04637", None, "markdown")
    assert "## GO: P04637" in out


def test_fmt_go_aspect_filter(fixture_loader) -> None:
    entry = fixture_loader("p04637_min")
    out = fmt_go(entry["uniProtKBCrossReferences"], "P04637", "F", "markdown")
    assert "Biological Process" not in out
    assert "Cellular Component" not in out


def test_fmt_crossrefs_handles_db_filter(fixture_loader) -> None:
    entry = fixture_loader("p04637_min")
    out = fmt_crossrefs(entry["uniProtKBCrossReferences"], "P04637", "PDB", "markdown")
    assert "**PDB**" in out
    assert "**GO**" not in out


def test_fmt_taxonomy_renders_results() -> None:
    data = {
        "results": [
            {
                "taxonId": 9606,
                "scientificName": "Homo sapiens",
                "commonName": "Human",
                "rank": "species",
            }
        ]
    }
    out = fmt_taxonomy(data, "markdown")
    assert "9606" in out
    assert "Homo sapiens" in out
    assert "Human" in out


def test_fmt_idmapping_handles_failed_ids() -> None:
    data = {
        "results": [{"from": "BRCA1", "to": {"primaryAccession": "P38398"}}],
        "failedIds": ["NOT_A_GENE"],
    }
    out = fmt_idmapping(data, "markdown")
    assert "1 mapped" in out
    assert "1 failed" in out
    assert "NOT_A_GENE" in out


def test_formatters_never_raise_on_empty_input() -> None:
    """Defensive: empty shapes must return strings, not crash."""
    assert isinstance(fmt_search({"results": []}), str)
    assert isinstance(fmt_features([], "P00000"), str)
    assert isinstance(fmt_variants([], "P00000"), str)
    assert isinstance(fmt_crossrefs([], "P00000", None), str)
    assert isinstance(fmt_go([], "P00000", None), str)
    assert isinstance(fmt_taxonomy({"results": []}), str)
    assert isinstance(fmt_idmapping({"results": [], "failedIds": []}), str)
