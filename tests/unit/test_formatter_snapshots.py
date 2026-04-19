"""Snapshot tests for formatters (syrupy).

Golden markdown outputs for canonical inputs. Any accidental change to
formatting — whitespace, ordering, phrasing — shows up as a diff in
the PR. Regenerate intentionally with:

    nox -s snapshot-update
    # or: pytest --snapshot-update
"""
from __future__ import annotations

from uniprot_mcp.formatters import (
    fmt_crossrefs,
    fmt_entry,
    fmt_features,
    fmt_go,
    fmt_search,
    fmt_variants,
)


def test_fmt_entry_snapshot(fixture_loader, snapshot) -> None:
    assert fmt_entry(fixture_loader("p04637_min"), "markdown") == snapshot


def test_fmt_search_snapshot(fixture_loader, snapshot) -> None:
    assert fmt_search(fixture_loader("brca1_search_min"), "markdown") == snapshot


def test_fmt_features_snapshot(fixture_loader, snapshot) -> None:
    entry = fixture_loader("p04637_min")
    assert fmt_features(entry["features"], "P04637", "markdown") == snapshot


def test_fmt_variants_snapshot(fixture_loader, snapshot) -> None:
    entry = fixture_loader("p04637_min")
    assert fmt_variants(entry["features"], "P04637", "markdown") == snapshot


def test_fmt_go_snapshot(fixture_loader, snapshot) -> None:
    entry = fixture_loader("p04637_min")
    assert fmt_go(entry["uniProtKBCrossReferences"], "P04637", None, "markdown") == snapshot


def test_fmt_crossrefs_snapshot(fixture_loader, snapshot) -> None:
    entry = fixture_loader("p04637_min")
    assert fmt_crossrefs(entry["uniProtKBCrossReferences"], "P04637", None, "markdown") == snapshot
