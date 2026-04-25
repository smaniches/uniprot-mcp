"""Benchmark integrity contract — pinned shape of `prompts.jsonl` and
`expected.hashes.jsonl`.

The plaintext `expected.jsonl` is local-only by design (gitignored;
sealed via SHA-256 commitments published in `expected.hashes.jsonl`).
These tests therefore cannot re-run `verify.py` against `expected.jsonl`
in CI, but they pin the public-side invariants that any drift would
break:

1. `prompts.jsonl` has exactly 30 lines, IDs 1..30, tiers Tier-A x 10
   + Tier-B x 10 + Tier-C x 10.
2. `expected.hashes.jsonl` has exactly 30 lines with the same set of
   IDs and well-formed SHA-256 hex digests.
3. The two files agree on the prompt-ID set.

Together these prove the public commitment surface is well-formed.
The cryptographic check (`verify.py`) lives at scoring time — see
`tests/benchmark/AUDIT.md` for the protocol.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_PATH = REPO_ROOT / "tests" / "benchmark" / "prompts.jsonl"
HASHES_PATH = REPO_ROOT / "tests" / "benchmark" / "expected.hashes.jsonl"

_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")


def _load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_prompts_file_is_well_formed() -> None:
    prompts = _load_jsonl(PROMPTS_PATH)
    assert len(prompts) == 30, f"expected 30 prompts, got {len(prompts)}"
    ids = sorted(p["prompt_id"] for p in prompts)
    assert ids == list(range(1, 31)), f"prompt_ids must be contiguous 1-30, got {ids}"


def test_prompts_have_required_fields() -> None:
    required = {"prompt_id", "tier", "topic", "surface", "prompt"}
    for p in _load_jsonl(PROMPTS_PATH):
        missing = required - set(p)
        assert not missing, f"prompt {p.get('prompt_id')} missing fields: {missing}"


def test_prompts_tier_distribution_is_10_10_10() -> None:
    counts: dict[str, int] = {}
    for p in _load_jsonl(PROMPTS_PATH):
        counts[p["tier"]] = counts.get(p["tier"], 0) + 1
    assert counts == {"A": 10, "B": 10, "C": 10}, (
        f"tier distribution must be A=10 B=10 C=10, got {counts}"
    )


def test_prompts_have_no_empty_prompt_strings() -> None:
    for p in _load_jsonl(PROMPTS_PATH):
        assert isinstance(p["prompt"], str)
        assert p["prompt"].strip(), f"prompt {p['prompt_id']} has empty `prompt` field"


def test_hashes_file_exists_and_is_well_formed() -> None:
    if not HASHES_PATH.exists():
        pytest.skip(
            "expected.hashes.jsonl not yet sealed — pre-sealing scaffold state. "
            "After running tests/benchmark/seal.py and committing, this test "
            "becomes a hard assertion."
        )
    hashes = _load_jsonl(HASHES_PATH)
    assert len(hashes) == 30, f"expected 30 commitments, got {len(hashes)}"
    for h in hashes:
        assert "prompt_id" in h and "sha256" in h
        assert isinstance(h["prompt_id"], int)
        assert _SHA256_RE.match(str(h["sha256"])), (
            f"prompt {h['prompt_id']}: sha256 not a 64-char lowercase hex digest"
        )


def test_hashes_and_prompts_agree_on_ids() -> None:
    if not HASHES_PATH.exists():
        pytest.skip("expected.hashes.jsonl not yet sealed.")
    prompt_ids = {p["prompt_id"] for p in _load_jsonl(PROMPTS_PATH)}
    hash_ids = {h["prompt_id"] for h in _load_jsonl(HASHES_PATH)}
    missing_in_hashes = prompt_ids - hash_ids
    extra_in_hashes = hash_ids - prompt_ids
    assert not missing_in_hashes, f"hashes missing prompt IDs: {sorted(missing_in_hashes)}"
    assert not extra_in_hashes, f"hashes contain orphan prompt IDs: {sorted(extra_in_hashes)}"


def test_hashes_are_unique() -> None:
    """Two prompts hashing to the same value would mean the canonical
    answer payload is identical — almost certainly a copy-paste error
    in expected.jsonl. Belt-and-suspenders check."""
    if not HASHES_PATH.exists():
        pytest.skip("expected.hashes.jsonl not yet sealed.")
    hashes = _load_jsonl(HASHES_PATH)
    sha_values = [h["sha256"] for h in hashes]
    assert len(set(sha_values)) == len(sha_values), (
        "duplicate sha256 values in expected.hashes.jsonl — two prompts share an answer payload"
    )


def test_expected_jsonl_is_gitignored() -> None:
    """The plaintext expected answers must NEVER be committed before
    the scoring publication step — the commitment scheme requires it.
    Verify the gitignore rule is in place."""
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "tests/benchmark/expected.jsonl" in gitignore, (
        "tests/benchmark/expected.jsonl must be gitignored — see "
        "tests/benchmark/README.md commitment protocol"
    )
