"""Fail closed when illustrative workflows masquerade as source evidence.

Real tool-result transcripts must be backed by captured source bytes and
a dedicated binding test. Research recipes must never contain simulated
upstream responses, timestamps or purported source-response digests.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"
LIVE_CAPTURE = "01_clinical_variant_interpretation.jsonl"
RECIPES = {
    "02_drug_target_dossier.jsonl": (
        "uniprot_target_dossier",
        "uniprot_resolve_pdb",
        "uniprot_resolve_chembl",
        "uniprot_get_evidence_summary",
    ),
    "03_provenance_verify_after_a_year.jsonl": ("uniprot_provenance_verify",),
    "04_pathogen_drug_discovery.jsonl": (
        "uniprot_search",
        "uniprot_get_active_sites",
        "uniprot_get_processing_features",
        "uniprot_get_ptms",
        "uniprot_resolve_pdb",
    ),
}
HEX_DIGEST = re.compile(r"\b[0-9a-fA-F]{64}\b")


def _records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.mark.parametrize("filename,expected_calls", sorted(RECIPES.items()))
def test_research_recipes_have_no_unverified_results(
    filename: str, expected_calls: tuple[str, ...]
) -> None:
    path = EXAMPLES / filename
    raw = path.read_text(encoding="utf-8")
    records = _records(path)

    assert records[0]["role"] == "user"
    assert records[1]["role"] == "assistant"
    assert "NOT EXECUTED" in records[1]["content"]
    assert records[-1]["role"] == "assistant"
    assert set(record["role"] for record in records) == {
        "user",
        "assistant",
        "suggested_call",
    }
    assert not HEX_DIGEST.search(raw), "recipe contains a purported source digest"
    calls = [
        row["tool_call"]["name"]
        for row in records
        if row["role"] == "suggested_call"
    ]
    assert tuple(calls) == expected_calls
    assert all(
        isinstance(record["tool_call"]["arguments"], dict)
        for record in records
        if record["role"] == "suggested_call"
    )


def test_only_source_bound_live_capture_has_tool_results() -> None:
    paths = sorted(EXAMPLES.glob("*.jsonl"))
    assert {path.name for path in paths} == {LIVE_CAPTURE, *RECIPES}
    for path in paths:
        tool_results = [row for row in _records(path) if row["role"] == "tool"]
        if path.name == LIVE_CAPTURE:
            assert tool_results
            assert (
                EXAMPLES / "captures/2026-10-15_tp53_r175h/capture_manifest.json"
            ).exists()
        else:
            assert not tool_results, path.name

    # tests/contract/test_tp53_capture_binding.py independently binds
    # the one permitted live capture to its actual upstream response bytes.


def test_documentation_distinguishes_retrieval_from_illustration() -> None:
    examples_readme = (EXAMPLES / "README.md").read_text(encoding="utf-8")
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Unexecuted workflow recipes" in examples_readme
    assert "three unexecuted workflow recipes" in root_readme
    assert "A year later, an auditor can call" not in root_readme
    assert "# -> Status: verified  (release match" not in root_readme
    assert "2027_03" not in (EXAMPLES / "03_provenance_verify_after_a_year.jsonl").read_text(
        encoding="utf-8"
    )
