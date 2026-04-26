"""Tests for the v1.1.0 biomedical-features tools.

Three tools project the same UniProt ``features`` array into three
research-relevant buckets:

  uniprot_get_active_sites          — catalysis and ligand binding
  uniprot_get_processing_features   — signal peptide, propeptide, chain
  uniprot_get_ptms                  — modified residue, glycan, disulfide

Each tool is a pure filter; the formatters render structured output and
emit an honest empty-set advisory pointing at adjacent databases. These
tests pin:

- the bucket membership (every UniProt feature type is in at most one
  bucket);
- the filtering correctness (an entry with five overlapping types yields
  three disjoint, non-overlapping responses);
- the rendering shape (Markdown title, count, ranges, descriptions,
  provenance footer);
- the JSON envelope (``data``/``provenance`` shape) and the "no
  features" advisory text;
- the input validation (bad accession / bad format both rejected before
  the upstream call).
"""

from __future__ import annotations

import json

import httpx
import respx

from uniprot_mcp.formatters import (
    ACTIVE_SITE_FEATURE_TYPES,
    PROCESSING_FEATURE_TYPES,
    PTM_FEATURE_TYPES,
    fmt_active_sites,
    fmt_processing_features,
    fmt_ptms,
)
from uniprot_mcp.server import (
    _filter_features_by_type,
    uniprot_get_active_sites,
    uniprot_get_processing_features,
    uniprot_get_ptms,
)

# ---------------------------------------------------------------------------
# Bucket-membership invariants — the buckets are disjoint
# ---------------------------------------------------------------------------


def test_buckets_are_pairwise_disjoint() -> None:
    """Critical invariant: a feature can show up in at most one tool's
    output. Otherwise users would see the same residue twice and the
    UI math (counts, summaries) would be wrong."""
    assert ACTIVE_SITE_FEATURE_TYPES.isdisjoint(PROCESSING_FEATURE_TYPES)
    assert ACTIVE_SITE_FEATURE_TYPES.isdisjoint(PTM_FEATURE_TYPES)
    assert PROCESSING_FEATURE_TYPES.isdisjoint(PTM_FEATURE_TYPES)


def test_buckets_have_expected_members() -> None:
    """Pin the canonical UniProt feature-type names. UniProt's annotation
    manual is the upstream source; if these change, our buckets must
    change in the same commit."""
    assert "Active site" in ACTIVE_SITE_FEATURE_TYPES
    assert "Binding site" in ACTIVE_SITE_FEATURE_TYPES
    assert "Metal binding" in ACTIVE_SITE_FEATURE_TYPES
    assert "DNA binding" in ACTIVE_SITE_FEATURE_TYPES
    assert "Site" in ACTIVE_SITE_FEATURE_TYPES

    assert "Signal peptide" in PROCESSING_FEATURE_TYPES
    assert "Propeptide" in PROCESSING_FEATURE_TYPES
    assert "Transit peptide" in PROCESSING_FEATURE_TYPES
    assert "Initiator methionine" in PROCESSING_FEATURE_TYPES
    assert "Chain" in PROCESSING_FEATURE_TYPES
    assert "Peptide" in PROCESSING_FEATURE_TYPES

    assert "Modified residue" in PTM_FEATURE_TYPES
    assert "Glycosylation" in PTM_FEATURE_TYPES
    assert "Lipidation" in PTM_FEATURE_TYPES
    assert "Disulfide bond" in PTM_FEATURE_TYPES
    assert "Cross-link" in PTM_FEATURE_TYPES


# ---------------------------------------------------------------------------
# Pure filter helper — independent of network
# ---------------------------------------------------------------------------


def test_filter_features_by_type_partitions_disjointly() -> None:
    """Filter a mixed feature list with all three bucket-type sets and
    confirm the partition: every input feature ends up in exactly one
    bucket (or none, if its type is in none of the buckets)."""
    features = [
        {"type": "Active site", "location": {"start": {"value": 100}, "end": {"value": 100}}},
        {"type": "Signal peptide", "location": {"start": {"value": 1}, "end": {"value": 22}}},
        {"type": "Modified residue", "location": {"start": {"value": 175}, "end": {"value": 175}}},
        {"type": "Domain", "location": {"start": {"value": 50}, "end": {"value": 200}}},  # neither
    ]
    a = _filter_features_by_type(features, ACTIVE_SITE_FEATURE_TYPES)
    p = _filter_features_by_type(features, PROCESSING_FEATURE_TYPES)
    m = _filter_features_by_type(features, PTM_FEATURE_TYPES)
    assert len(a) == 1 and a[0]["type"] == "Active site"
    assert len(p) == 1 and p[0]["type"] == "Signal peptide"
    assert len(m) == 1 and m[0]["type"] == "Modified residue"
    # The Domain feature is in none of the buckets — confirms no
    # accidental over-collection.
    assert sum(len(x) for x in (a, p, m)) == 3


def test_filter_features_by_type_handles_missing_type_gracefully() -> None:
    """A feature without a ``type`` key falls into none of the buckets —
    we cannot guess. The filter must not raise on malformed upstream
    data."""
    features = [{"location": {"start": {"value": 1}, "end": {"value": 1}}}]
    assert _filter_features_by_type(features, ACTIVE_SITE_FEATURE_TYPES) == []
    assert _filter_features_by_type(features, PROCESSING_FEATURE_TYPES) == []
    assert _filter_features_by_type(features, PTM_FEATURE_TYPES) == []


# ---------------------------------------------------------------------------
# Fixture: a synthetic entry covering all three buckets + extras
# ---------------------------------------------------------------------------

_ENTRY_RICH = {
    "primaryAccession": "P12345",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "features": [
        # Active sites
        {
            "type": "Active site",
            "description": "Proton acceptor",
            "location": {"start": {"value": 78}, "end": {"value": 78}},
        },
        {
            "type": "Binding site",
            "description": "ATP",
            "location": {"start": {"value": 110}, "end": {"value": 110}},
            "ligand": {"name": "ATP", "id": "ChEBI:CHEBI:30616"},
        },
        {
            "type": "Metal binding",
            "description": "Zn(2+)",
            "location": {"start": {"value": 142}, "end": {"value": 142}},
            "ligand": {"name": "Zn(2+)", "id": "ChEBI:CHEBI:29105"},
        },
        # Processing
        {
            "type": "Signal peptide",
            "location": {"start": {"value": 1}, "end": {"value": 22}},
        },
        {
            "type": "Chain",
            "description": "Mature protein",
            "location": {"start": {"value": 23}, "end": {"value": 393}},
        },
        # PTMs
        {
            "type": "Modified residue",
            "description": "Phosphoserine; by PKA",
            "location": {"start": {"value": 175}, "end": {"value": 175}},
        },
        {
            "type": "Disulfide bond",
            "description": "Interchain (with C-201)",
            "location": {"start": {"value": 47}, "end": {"value": 201}},
        },
        # Outside all three buckets — must not appear in any output
        {
            "type": "Domain",
            "description": "Protein kinase",
            "location": {"start": {"value": 50}, "end": {"value": 350}},
        },
    ],
}


def _mock_entry(router: respx.MockRouter) -> None:
    router.get("/uniprotkb/P12345").mock(
        return_value=httpx.Response(
            200, json=_ENTRY_RICH, headers={"X-UniProt-Release": "2026_01"}
        )
    )


# ---------------------------------------------------------------------------
# uniprot_get_active_sites
# ---------------------------------------------------------------------------


async def test_active_sites_renders_three_features_grouped_by_type() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        _mock_entry(router)
        out = await uniprot_get_active_sites("P12345", "markdown")
    assert "Active and binding sites: P12345 (3 feature(s))" in out
    assert "### Active site (1)" in out
    assert "### Binding site (1)" in out
    assert "### Metal binding (1)" in out
    assert "Proton acceptor" in out
    assert "ligand: ATP" in out
    assert "ligand: Zn(2+)" in out
    # Out-of-bucket feature must not leak through
    assert "Protein kinase" not in out
    assert "Phosphoserine" not in out  # PTM bucket
    # Provenance footer present
    assert "_Source: UniProt release 2026_01" in out


async def test_active_sites_empty_set_carries_honest_advisory() -> None:
    """An entry with no active-site features must produce a non-empty
    response with the empty-set advisory — not an empty body."""
    empty_entry = {"primaryAccession": "P00000", "features": []}
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P00000").mock(
            return_value=httpx.Response(
                200, json=empty_entry, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_get_active_sites("P00000", "markdown")
    assert "0 feature(s)" in out
    assert "non-druggability" in out  # honest advisory text
    assert "allosteric" in out  # honest advisory text


async def test_active_sites_json_envelope() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        _mock_entry(router)
        out = await uniprot_get_active_sites("P12345", "json")
    payload = json.loads(out)
    assert "data" in payload and "provenance" in payload
    feats = payload["data"]["features"]
    assert len(feats) == 3
    assert {f["type"] for f in feats} == {"Active site", "Binding site", "Metal binding"}


async def test_active_sites_rejects_bad_accession() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_get_active_sites("not-an-accession", "markdown")
    assert "Input error" in out
    assert not router.calls  # no upstream call on validation failure


async def test_active_sites_rejects_bad_format() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_get_active_sites("P12345", "yaml")
    assert "Input error" in out
    assert not router.calls


# ---------------------------------------------------------------------------
# uniprot_get_processing_features
# ---------------------------------------------------------------------------


async def test_processing_features_renders_signal_and_chain() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        _mock_entry(router)
        out = await uniprot_get_processing_features("P12345", "markdown")
    assert "Processing and maturation: P12345 (2 feature(s))" in out
    assert "### Chain (1)" in out
    assert "### Signal peptide (1)" in out
    assert "Mature protein" in out
    # Range rendering: signal peptide is 1-22, chain is 23-393
    assert "1-22" in out
    assert "23-393" in out
    # No bucket leakage
    assert "Active site" not in out
    assert "Phosphoserine" not in out


async def test_processing_features_empty_set_advisory_mentions_chain() -> None:
    empty_entry = {"primaryAccession": "P00000", "features": []}
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P00000").mock(
            return_value=httpx.Response(
                200, json=empty_entry, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_get_processing_features("P00000", "markdown")
    assert "mature protein is likely the full sequence" in out


async def test_processing_features_json_envelope() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        _mock_entry(router)
        out = await uniprot_get_processing_features("P12345", "json")
    payload = json.loads(out)
    types = {f["type"] for f in payload["data"]["features"]}
    assert types == {"Signal peptide", "Chain"}


# ---------------------------------------------------------------------------
# uniprot_get_ptms
# ---------------------------------------------------------------------------


async def test_ptms_renders_modified_residue_and_disulfide() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        _mock_entry(router)
        out = await uniprot_get_ptms("P12345", "markdown")
    assert "Post-translational modifications: P12345 (2 feature(s))" in out
    assert "### Modified residue (1)" in out
    assert "### Disulfide bond (1)" in out
    assert "Phosphoserine" in out
    # Disulfide spans two cysteines
    assert "47-201" in out
    # No bucket leakage
    assert "Active site" not in out
    assert "Signal peptide" not in out


async def test_ptms_empty_set_advisory_points_at_phosphositeplus() -> None:
    empty_entry = {"primaryAccession": "P00000", "features": []}
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P00000").mock(
            return_value=httpx.Response(
                200, json=empty_entry, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_get_ptms("P00000", "markdown")
    assert "PhosphoSitePlus" in out
    assert "GlyConnect" in out


async def test_ptms_json_envelope_carries_provenance() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        _mock_entry(router)
        out = await uniprot_get_ptms("P12345", "json")
    payload = json.loads(out)
    assert payload["provenance"]["release"] == "2026_01"
    assert payload["provenance"]["url"].endswith("/uniprotkb/P12345")


# ---------------------------------------------------------------------------
# Pure-formatter coverage (no network) — for exhaustive feature-type cases
# ---------------------------------------------------------------------------


def test_fmt_active_sites_handles_missing_location_gracefully() -> None:
    """A feature with a malformed location must not crash the formatter
    and must render with ``?`` placeholders."""
    feats = [{"type": "Active site"}]
    out = fmt_active_sites(feats, "P12345", "markdown")
    assert "?" in out  # placeholder rendering


def test_fmt_processing_features_renders_initiator_methionine_correctly() -> None:
    """Initiator methionine is always at residue 1 — single-residue
    features must render as a single number, not 1-1."""
    feats = [
        {
            "type": "Initiator methionine",
            "description": "Removed",
            "location": {"start": {"value": 1}, "end": {"value": 1}},
        }
    ]
    out = fmt_processing_features(feats, "P12345", "markdown")
    assert "**1**" in out  # single-residue rendering, not "1-1"
    assert "Removed" in out


def test_fmt_ptms_renders_lipidation_with_ligand() -> None:
    feats = [
        {
            "type": "Lipidation",
            "description": "GPI-anchor amidated alanine",
            "location": {"start": {"value": 100}, "end": {"value": 100}},
        }
    ]
    out = fmt_ptms(feats, "P12345", "markdown")
    assert "GPI-anchor" in out
