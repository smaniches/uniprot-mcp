"""Reject accidental reintroduction of a retired curated research directory.

This test is intentionally the single negative-only reference to its old
path; no runtime code, examples, links or release metadata depend on it.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_retired_curated_directory_is_absent() -> None:
    assert not (ROOT / "examples" / "atlas").exists()


def test_live_mcp_implementation_independent_of_curated_examples() -> None:
    server = (ROOT / "src" / "uniprot_mcp" / "server.py").read_text(encoding="utf-8")
    assert 'examples/atlas' not in server
    assert 'def uniprot_search(' in server
