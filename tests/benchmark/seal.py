"""Seal expected answers via SHA-256 commitment.

Run after authors write `expected.jsonl` (one JSON object per line, each
with keys ``prompt_id``, ``answer``, ``rationale``). This script:

1. Reads ``expected.jsonl``.
2. For each line, canonicalises the JSON (sorted keys, no spaces).
3. Hashes the canonical JSON with SHA-256.
4. Writes the hashes to ``expected.hashes.jsonl`` as one line per prompt
   with keys ``prompt_id`` and ``sha256``.

The hashes file is committed to git NOW. The plaintext ``expected.jsonl``
is committed ONLY at scoring time, in the same commit as the run output.

Verification (third party):

    python tests/benchmark/verify.py expected.jsonl expected.hashes.jsonl

Exit code 0 iff every line's canonical hash matches the commitment.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys


def canonical(obj: object) -> bytes:
    """Stable byte form: sorted keys, compact separators, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def main() -> int:
    here = pathlib.Path(__file__).parent
    plaintext = here / "expected.jsonl"
    hashes = here / "expected.hashes.jsonl"
    if not plaintext.exists():
        print(f"ERROR: {plaintext} does not exist — author expected.jsonl first.", file=sys.stderr)
        return 1

    lines_out: list[str] = []
    for line in plaintext.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        required = {"prompt_id", "answer", "rationale"}
        missing = required - set(obj)
        if missing:
            print(f"ERROR: line missing keys {missing}: {line}", file=sys.stderr)
            return 1
        digest = hashlib.sha256(canonical(obj)).hexdigest()
        lines_out.append(
            json.dumps({"prompt_id": obj["prompt_id"], "sha256": digest}, sort_keys=True)
        )

    hashes.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines_out)} commitments to {hashes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
