"""The public worked example must be bound to preserved source bytes.

Illustrative, simulated, or hypothetical source-result transcripts are not
accepted as published scientific evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"
CAPTURE = EXAMPLES / "captures/2026-10-15_tp53_r175h"
LIVE = EXAMPLES / "01_clinical_variant_interpretation.jsonl"
LEGACY_DIGEST = "0040d79bb39e2f7386d55f81071e87858ec2e5c2cd9552e93c3633897f78345e"
CAPTURED_DIGEST = "112540dcb662c3ce2feba05272ce0e946ce76089a5bcf8346eb55141892f7fcf"


def test_only_source_bound_example_is_published() -> None:
    assert sorted(p.name for p in EXAMPLES.glob("*.jsonl")) == [LIVE.name]
    assert (CAPTURE / "capture_manifest.json").is_file()
    assert (CAPTURE / "tool_outputs.json").is_file()
    assert any((CAPTURE / "upstream").glob("*.body.gz"))

    messages = [
        json.loads(line) for line in LIVE.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert any(m.get("role") == "tool" for m in messages)
    assert any("tool_call" in m for m in messages)
    # The separate test_tp53_capture_binding.py binds digest/footer fields
    # to source bodies; it compares transcript text to saved tool text but
    # does not independently replay the parser over captured responses.


def test_public_readmes_do_not_present_unverified_receipts() -> None:
    root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    examples_readme = (EXAMPLES / "README.md").read_text(encoding="utf-8")

    assert LEGACY_DIGEST not in root_readme
    assert CAPTURED_DIGEST in root_readme
    assert "three unexecuted workflow recipes" not in root_readme
    assert "01..04.jsonl" not in root_readme
    assert "the only published example transcript" in examples_readme.lower()
    assert "illustrative transcripts were withdrawn" in examples_readme


def test_unverifiable_april_receipt_is_withdrawn_everywhere() -> None:
    sources = [
        ROOT / "README.md",
        ROOT / "docs/provenance-guide.md",
        ROOT / "tests/benchmark/AUDIT.md",
        ROOT / "tests/benchmark/run-2026-04-25-roundtrip/transcript.md",
    ]
    for path in sources:
        assert path.is_file(), path
        assert LEGACY_DIGEST not in path.read_text(encoding="utf-8"), path

    withdrawn = sources[-1].read_text(encoding="utf-8").lower()
    assert "withdrawn as verification evidence" in withdrawn
    assert "upstream response bodies" in withdrawn
    assert not (ROOT / "tests/benchmark/demo_roundtrip.py").exists()
