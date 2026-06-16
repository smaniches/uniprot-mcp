"""Unit tests for formatters — offline, fixture-driven."""

from __future__ import annotations

from uniprot_mcp.formatters import (
    fmt_citation,
    fmt_citation_search,
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


def test_fmt_citation_handles_empty_cross_references() -> None:
    """A citation whose ``citationCrossReferences`` is an explicit empty
    list must still render. The id falls back to the cross-ref id only
    when that list is non-empty; an empty list must not raise IndexError
    (the bug fmt_citation_search already guarded against)."""
    data = {"citation": {"id": "12345678", "title": "T", "citationCrossReferences": []}}
    out = fmt_citation(data, "markdown")
    assert "## Citation 12345678" in out
    # Same defensive guard at the search layer.
    sdata = {"results": [data]}
    assert "12345678" in fmt_citation_search(sdata, "markdown")


def test_fmt_citation_derives_id_from_cross_reference() -> None:
    """When the citation has no top-level ``id`` the PubMed cross-ref id
    is used as the heading identifier."""
    data = {
        "citation": {
            "title": "T",
            "citationCrossReferences": [{"database": "PubMed", "id": "7649814"}],
        }
    }
    assert "## Citation 7649814" in fmt_citation(data, "markdown")


def test_fmt_go_json_applies_aspect_filter(fixture_loader) -> None:
    """M5: JSON output must be narrowed by ``aspect_filter`` exactly as the
    markdown path is, instead of returning every GO ref."""
    import json

    from uniprot_mcp.formatters import fmt_go

    entry = fixture_loader("p04637_min")
    xrefs = entry["uniProtKBCrossReferences"]

    out = fmt_go(xrefs, "P04637", "C", "json")
    ids = [r["id"] for r in json.loads(out)]

    assert ids == ["GO:0005634"]
    assert "GO:0003700" not in ids  # F aspect must be excluded
    assert "GO:0006915" not in ids  # P aspect must be excluded


def test_fmt_go_aspect_filter_drops_unprefixed_refs() -> None:
    """M5: a GO ref whose ``GoTerm`` carries no recognized aspect prefix is
    dropped by an active aspect filter in JSON output, so the JSON and
    markdown paths agree (markdown already discards such refs because they
    never enter ``by_aspect``)."""
    import json

    from uniprot_mcp.formatters import fmt_go

    xrefs = [
        {
            "database": "GO",
            "id": "GO:0005634",
            "properties": [{"key": "GoTerm", "value": "C:nucleus"}],
        },
        {
            "database": "GO",
            "id": "GO:9999999",
            "properties": [{"key": "GoTerm", "value": "no-prefix term"}],
        },
    ]

    out = fmt_go(xrefs, "P00000", "C", "json")
    ids = [r["id"] for r in json.loads(out)]
    assert ids == ["GO:0005634"]
    assert "GO:9999999" not in ids


def test_fmt_features_null_boundary_renders_question_mark() -> None:
    """M6: a feature whose start (or end) boundary is the UniProt unknown
    sentinel ``{"value": null, "modifier": "UNKNOWN"}`` must render as ``"?"``
    not the literal string ``"None"``."""
    from uniprot_mcp.formatters import fmt_features

    feats = [
        {
            "type": "Chain",
            "location": {
                "start": {"value": None, "modifier": "UNKNOWN"},
                "end": {"value": 50, "modifier": "EXACT"},
            },
            "description": "incomplete chain",
        },
        {
            "type": "Chain",
            "location": {
                "start": {"value": 10, "modifier": "EXACT"},
                "end": {"value": None, "modifier": "UNKNOWN"},
            },
            "description": "ragged C-terminus",
        },
    ]
    out = fmt_features(feats, "P00000", "markdown")

    assert "?-50: incomplete chain" in out
    assert "10-?: ragged C-terminus" in out
    assert "None" not in out


def test_fmt_variants_null_position_renders_question_mark() -> None:
    """M6: a natural-variant feature with a null start boundary must render
    the mutation position as ``"?"`` not ``"None"``."""
    from uniprot_mcp.formatters import fmt_variants

    feats = [
        {
            "type": "Natural variant",
            "location": {"start": {"value": None, "modifier": "UNKNOWN"}},
            "description": "position-uncertain variant",
            "alternativeSequence": {
                "originalSequence": "A",
                "alternativeSequences": ["V"],
            },
        }
    ]
    out = fmt_variants(feats, "P00000", "markdown")

    assert "**A?V**" in out
    assert "None" not in out


def test_fmt_active_sites_null_boundary_renders_question_mark() -> None:
    """M6: the shared ``_fmt_filtered_features`` path (here via
    ``fmt_active_sites``) must render a null boundary as ``"?"`` not
    ``"None"``. With BOTH boundaries unknown, ``start == end`` (both ``"?"``)
    so the renderer collapses the range to a single ``**?**``."""
    from uniprot_mcp.formatters import fmt_active_sites

    feats = [
        {
            "type": "Active site",
            "location": {
                "start": {"value": None, "modifier": "UNKNOWN"},
                "end": {"value": None, "modifier": "UNKNOWN"},
            },
            "description": "proton acceptor (position uncertain)",
        }
    ]
    out = fmt_active_sites(feats, "P00000", "markdown")

    assert "**?**" in out
    assert "None" not in out


def test_fmt_active_sites_missing_boundary_key_renders_question_mark() -> None:
    """M6 coverage: a location object that omits the ``start``/``end`` key
    entirely (so ``loc.get(boundary)`` is falsy) must still render ``"?"`` --
    covering the ``(loc.get(boundary) or {})`` fallback arc of the shared
    helper introduced by the M6 fix."""
    from uniprot_mcp.formatters import fmt_active_sites

    feats = [
        {
            "type": "Active site",
            "location": {},
            "description": "boundary-less site",
        }
    ]
    out = fmt_active_sites(feats, "P00000", "markdown")

    assert "**?**" in out
    assert "None" not in out
