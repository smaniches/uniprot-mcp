"""Verify recorded fixtures match their content-addressed manifest.

Fixtures are the ground truth for offline formatter tests. If one drifts
without a manifest update, tests should loudly fail — not silently pass
with subtly wrong data.

Usage:
    python -m tests.fixtures.verify           # check
    python -m tests.fixtures.verify --update  # regenerate MANIFEST.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent
MANIFEST = FIXTURE_DIR / "MANIFEST.json"


def _canonical_sha(path: Path) -> str:
    """SHA256 over a canonical JSON serialisation (ignoring _meta)."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    data.pop("_meta", None)
    blob = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _load_manifest() -> dict:
    if MANIFEST.exists():
        with MANIFEST.open(encoding="utf-8") as f:
            return json.load(f)
    return {"_schema_version": 1, "fixtures": {}}


def _write_manifest(manifest: dict) -> None:
    with MANIFEST.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")


def verify(update: bool = False) -> int:
    manifest = _load_manifest()
    recorded = manifest.get("fixtures", {})
    current = {
        p.name: _canonical_sha(p)
        for p in sorted(FIXTURE_DIR.glob("*.json"))
        if p.name != "MANIFEST.json"
    }

    if update:
        manifest["fixtures"] = current
        _write_manifest(manifest)
        print(f"wrote {MANIFEST.relative_to(FIXTURE_DIR.parent.parent)}")
        for name, sha in current.items():
            print(f"  {name}  {sha[:16]}…")
        return 0

    drift = [n for n, sha in current.items() if recorded.get(n) != sha]
    missing = [n for n in recorded if n not in current]
    if drift or missing:
        for n in drift:
            print(
                f"drift: {n}\n  expected {recorded.get(n, '?')[:16]}…\n  got      {current[n][:16]}…",
                file=sys.stderr,
            )
        for n in missing:
            print(f"missing: {n}", file=sys.stderr)
        return 1
    print(f"ok ({len(current)} fixtures match manifest)")
    return 0


if __name__ == "__main__":
    raise SystemExit(verify(update="--update" in sys.argv[1:]))
