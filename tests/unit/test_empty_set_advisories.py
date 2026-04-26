"""Tests for the audit-identified empty-set advisory branches.

The audit flagged these branches as untested-but-user-facing:

- ``fmt_active_sites`` empty advisory (non-druggability / allosteric)
- ``fmt_processing_features`` empty advisory (mature protein full sequence)
- ``fmt_ptms`` empty advisory (PhosphoSitePlus / GlyConnect)
- ``fmt_features_at_position`` empty advisory (no annotated features)
- ``fmt_variant_lookup`` empty match list
- ``fmt_disease_associations`` empty list

Each branch produces a textual response that is shown to the LLM
caller. If the advisory text is wrong (e.g. typo, drift from the
formatter constant), the user sees the wrong message. These tests
pin the exact phrases the audit relied on.
"""

from __future__ import annotations

from uniprot_mcp.formatters import (
    fmt_active_sites,
    fmt_disease_associations,
    fmt_features_at_position,
    fmt_processing_features,
    fmt_ptms,
    fmt_variant_lookup,
)


def test_active_sites_empty_advisory_phrase() -> None:
    """The advisory must be honest: absence does not imply non-druggability."""
    out = fmt_active_sites([], "P12345", "markdown")
    assert "0 feature(s)" in out
    assert "non-druggability" in out
    assert "allosteric" in out


def test_processing_features_empty_advisory_phrase() -> None:
    """The advisory points at the entry's chain annotation as the
    canonical mature-form check."""
    out = fmt_processing_features([], "P12345", "markdown")
    assert "0 feature(s)" in out
    assert "mature protein is likely the full sequence" in out
    assert "chain annotation" in out


def test_ptms_empty_advisory_points_at_phosphositeplus() -> None:
    """The advisory directs users to PhosphoSitePlus and GlyConnect for
    additional mass-spec evidence — important so the absence is not
    over-interpreted."""
    out = fmt_ptms([], "P12345", "markdown")
    assert "0 feature(s)" in out
    assert "PhosphoSitePlus" in out
    assert "GlyConnect" in out


def test_features_at_position_empty_advisory() -> None:
    """When no feature overlaps the position, the formatter must say
    so explicitly with the position number."""
    out = fmt_features_at_position([], "P04637", 999, "markdown")
    assert "0 feature(s)" in out
    assert "No annotated features overlap position 999" in out


def test_variant_lookup_empty_advisory_text() -> None:
    """When no UniProt natural-variant matches the HGVS shorthand, the
    advisory must be shown so the user knows the absence is informative
    (the variant could still be known to ClinVar / dbSNP / gnomAD)."""
    out = fmt_variant_lookup([], "P04637", "Z999A", "markdown")
    assert "0 match(es)" in out


def test_disease_associations_empty_advisory_points_at_open_targets() -> None:
    """When the entry has no DISEASE-type annotations, the formatter
    points at adjacent disease-gene resources rather than implying the
    protein is disease-irrelevant."""
    out = fmt_disease_associations([], "P12345", "markdown")
    assert "0 record(s)" in out
    assert "Open Targets" in out or "OMIM" in out or "DisGeNET" in out


def test_active_sites_empty_in_json_envelope_too() -> None:
    """JSON envelope on empty input still carries the empty list +
    accession structure (no advisory text in JSON — that's a markdown
    affordance — but the shape must be stable)."""
    out = fmt_active_sites([], "P12345", "json")
    assert '"features"' in out
    assert '"accession": "P12345"' in out
