"""Verify that expected.jsonl matches the published commitments.

Usage:
    python tests/benchmark/verify.py expected.jsonl expected.hashes.jsonl

Exit code 0 iff every line's canonical SHA-256 matches the corresponding
commitment in the hashes file. Any mismatch is fatal.

Third parties reading a published benchmark run should run this to confirm
the expected-answer file was not edited after commitment time.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    plaintext_path = pathlib.Path(argv[1])
    hashes_path = pathlib.Path(argv[2])

    plaintext_lines = [
        ln for ln in plaintext_path.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    hashes_lines = [ln for ln in hashes_path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    if len(plaintext_lines) != len(hashes_lines):
        print(
            f"ERROR: line-count mismatch — plaintext has {len(plaintext_lines)}, "
            f"commitments has {len(hashes_lines)}",
            file=sys.stderr,
        )
        return 1

    hashes_by_id = {json.loads(ln)["prompt_id"]: json.loads(ln)["sha256"] for ln in hashes_lines}

    mismatches = 0
    for ln in plaintext_lines:
        obj = json.loads(ln)
        pid = obj["prompt_id"]
        actual = hashlib.sha256(canonical(obj)).hexdigest()
        committed = hashes_by_id.get(pid)
        if committed is None:
            print(f"ERROR: prompt {pid} not in commitment file", file=sys.stderr)
            mismatches += 1
            continue
        if actual != committed:
            print(
                f"MISMATCH prompt {pid}: committed {committed}, actual {actual}",
                file=sys.stderr,
            )
            mismatches += 1

    if mismatches:
        print(f"FAILED: {mismatches} commitment mismatch(es)", file=sys.stderr)
        return 1
    print(f"OK: {len(plaintext_lines)} commitments verified")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
