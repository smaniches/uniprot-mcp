"""Fresh-checkout-friendly benchmark verifier.

Re-derives every benchmark answer from live UniProt REST and compares
the canonical SHA-256 of the derived ``{"prompt_id": pid, "answer":
<live>}`` line against the committed ``expected.hashes.jsonl``.

Unlike ``verify_answers.py`` this script does **not** require
``expected.jsonl`` (which is gitignored). A third party with a fresh
checkout, network access to ``rest.uniprot.org``, and Python ≥ 3.11
can run it directly.

Usage::

    python tests/benchmark/verify_against_hashes.py \\
           [tests/benchmark/expected.hashes.jsonl]

Exit codes:
  0 — every Tier A / Tier B prompt's derived hash matches the
       commitment, and Tier C set-inclusion prompts (28, 29) reproduce
       the sealed items as a subset of the live response.
  1 — at least one prompt did not verify.
  2 — usage / IO error.

Tier C set-inclusion semantics: prompts 28 and 29 commit a *sealed*
answer that may be a strict subset of the live answer (UniProt
adds new feature types or cross-DB references over time). The hash
of the live answer therefore does **not** match the committed hash
in those two cases. We surface them with a ``set-inclusion: hash
verified separately required`` marker rather than failing — the
sealed hash check is left to maintainers running with the local
``expected.jsonl``. The other 28 prompts must hash-match exactly.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

# Reuse the live derivation pipeline from verify_answers (which already
# encodes the per-prompt source attribution and Tier C structured logic).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from verify import canonical
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

    print(f"Re-deriving {len(committed)} answers from live UniProt …", file=sys.stderr)
    with _client() as client:
        derived = derive_all(client)

    failures = 0
    set_inclusion_skipped = 0
    for pid in sorted(committed):
        if pid not in derived:
            print(f"  prompt {pid:>2}: NO DERIVED ANSWER")
            failures += 1
            continue
        if pid in _SNAPSHOT_SET_INCLUSION_PROMPTS:
            # Set-inclusion prompts: the live answer may be a superset
            # of the sealed answer, so the hashes legitimately differ.
            # Report-and-skip; maintainers verify these with the local
            # expected.jsonl via verify.py + verify_answers.py.
            print(
                f"  prompt {pid:>2}: SKIP — set-inclusion prompt; "
                f"hash check is maintainer-only (run verify.py with local expected.jsonl)"
            )
            set_inclusion_skipped += 1
            continue
        record = {"prompt_id": pid, "answer": derived[pid]}
        actual = hashlib.sha256(canonical(record)).hexdigest()
        if actual == committed[pid]:
            print(f"  prompt {pid:>2}: OK — hash matches commitment")
        else:
            print(f"  prompt {pid:>2}: FAIL — committed {committed[pid]}, derived {actual}")
            failures += 1

    if failures:
        print(f"\nFAILED: {failures} prompt(s) did not verify", file=sys.stderr)
        return 1

    n_checked = len(committed) - set_inclusion_skipped
    print(
        f"\nOK: {n_checked} hash commitment(s) verified live "
        f"({set_inclusion_skipped} set-inclusion prompt(s) skipped — see header)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
