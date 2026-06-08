"""Fresh-checkout live answer-reproducibility tool (informational).

Re-derives every benchmark answer from live UniProt REST and prints the
derived answer for each prompt. This lets a third party with only a
fresh checkout (no ``expected.jsonl``, which is gitignored) confirm that
every Tier A / Tier B answer is independently reproducible from the
primary source today.

What this tool does **not** do
------------------------------
It does not — and cannot — recompute the committed SHA-256 digests in
``expected.hashes.jsonl``. Those digests are sealed over the canonical
JSON of ``{"prompt_id", "answer", "rationale"}`` (see ``seal.py``). The
``rationale`` is deliberately withheld as part of the sealed
pre-registration, so the digest is not derivable from the live answer
alone. A live re-derivation therefore confirms **answer
reproducibility**, not a cryptographic match.

The full cryptographic check is the maintainer path, which requires the
local ``expected.jsonl``::

    python tests/benchmark/verify.py \\
        tests/benchmark/expected.jsonl tests/benchmark/expected.hashes.jsonl
    python tests/benchmark/verify_answers.py tests/benchmark/expected.jsonl

``verify.py`` confirms the plaintext seal matches the published
commitments; ``verify_answers.py`` confirms each sealed answer matches
the live primary source (exact for Tier A/B, set-inclusion for Tier C
28/29). See ``tests/benchmark/AUDIT.md`` for the protocol and the
verification log.

Usage::

    python tests/benchmark/verify_against_hashes.py \\
           [tests/benchmark/expected.hashes.jsonl]

The optional argument is read only to enumerate the committed prompt
IDs; its digests are not compared (see above).

Exit codes:
  0 — every committed prompt was re-derived from live UniProt and
       printed. This is an informational reproducibility tool, not a
       pass/fail gate; it does not assert a cryptographic match.
  2 — usage / IO error (hashes file missing).

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import json
import pathlib
import sys

# Reuse the live derivation pipeline from verify_answers (which already
# encodes the per-prompt source attribution and Tier C structured logic).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from verify_answers import _SNAPSHOT_SET_INCLUSION_PROMPTS, _client, derive_all

DEFAULT_HASHES = pathlib.Path(__file__).resolve().parent / "expected.hashes.jsonl"


def main(argv: list[str]) -> int:
    hashes_path = pathlib.Path(argv[1]) if len(argv) > 1 else DEFAULT_HASHES
    if not hashes_path.exists():
        print(f"ERROR: {hashes_path} does not exist", file=sys.stderr)
        return 2

    committed: dict[int, str] = {}
    for line in hashes_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        committed[int(obj["prompt_id"])] = obj["sha256"]

    print(f"Re-deriving {len(committed)} answers from live UniProt ...", file=sys.stderr)
    with _client() as client:
        derived = derive_all(client)

    missing = 0
    for pid in sorted(committed):
        if pid not in derived:
            print(f"  prompt {pid:>2}: NO DERIVED ANSWER")
            missing += 1
            continue
        tag = " (Tier C set-inclusion)" if pid in _SNAPSHOT_SET_INCLUSION_PROMPTS else ""
        print(f"  prompt {pid:>2}: {json.dumps(derived[pid], sort_keys=True)}{tag}")

    print(
        f"\nRe-derived {len(derived)} answer(s) live from https://rest.uniprot.org.",
        file=sys.stderr,
    )
    print(
        "These answers are independently reproducible from the primary source. "
        "The committed SHA-256 digests in expected.hashes.jsonl are sealed over "
        "{prompt_id, answer, rationale}; the rationale is deliberately withheld, "
        "so the digest cannot be recomputed from the answer alone. This tool "
        "confirms live answer-reproducibility, NOT a cryptographic match.",
        file=sys.stderr,
    )
    print(
        "Full cryptographic verification is the maintainer path: "
        "verify.py + verify_answers.py with the local expected.jsonl "
        "(see tests/benchmark/AUDIT.md).",
        file=sys.stderr,
    )
    if missing:
        # Invariant: every committed prompt_id must be produced by derive_all().
        # Each derivation helper calls raise_for_status()/raise RuntimeError on a
        # miss and derive_all() assigns out[1..30] unconditionally, so a partial
        # dict cannot reach here under normal operation (an upstream failure raises
        # before this loop). This guard therefore fails fast ONLY on drift between
        # expected.hashes.jsonl and the derivation pipeline. Printing the
        # reproducibility note and returning success while a committed prompt was
        # not re-derived would itself be an overclaim, so exit non-zero.
        print(
            f"FAILED: {missing} committed prompt(s) not re-derived — "
            "expected.hashes.jsonl and the live derivation pipeline have diverged; "
            "reproduction is incomplete.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
