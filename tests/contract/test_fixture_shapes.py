"""Contract tests — verify recorded fixtures match the shape our code expects.

These are NOT integration tests (no network). They guard against silent
drift between (a) the shape of UniProt responses we recorded and (b) the
shape our formatters rely on. If UniProt changes its schema, the
nightly integration suite re-captures; any field our code reads but the
new capture doesn't expose will fail a contract test here.

Keep the schema explicit and minimal — only fields the code actually
reads. Over-specification creates false failures.
"""

from __future__ import annotations

from typing import Any


def _has_path(obj: Any, path: list[str]) -> bool:
    cur: Any = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return False
        cur = cur[key]
    return True


def test_entry_fixture_has_required_fields(fixture_loader) -> None:
    entry = fixture_loader("p04637_min")
    required_paths: list[list[str]] = [
        ["primaryAccession"],
        ["entryType"],
        ["proteinDescription", "recommendedName", "fullName", "value"],
        ["genes"],
        ["organism", "scientificName"],
        ["sequence", "length"],
        ["comments"],
        ["features"],
        ["uniProtKBCrossReferences"],
    ]
    missing = [p for p in required_paths if not _has_path(entry, p)]
    assert not missing, f"fixture missing fields formatters read: {missing}"


def test_entry_feature_items_have_type_and_location(fixture_loader) -> None:
    entry = fixture_loader("p04637_min")
    for f in entry["features"]:
        assert "type" in f, f"feature without type: {f}"
        assert "location" in f, f"feature without location: {f}"


def test_entry_crossrefs_have_database_and_id(fixture_loader) -> None:
    entry = fixture_loader("p04637_min")
    for x in entry["uniProtKBCrossReferences"]:
        assert "database" in x
        assert "id" in x


def test_search_fixture_has_results_list(fixture_loader) -> None:
    data = fixture_loader("brca1_search_min")
    assert "results" in data
    assert isinstance(data["results"], list)
    assert data["results"], "search fixture must have at least one result"
