"""Contract test for the atlas comprehensive-index reproducibility manifest.

The manifest at ``examples/atlas/manifest.json`` records the SHA-256
and row count of every committed TSV the comprehensive index ships.
A reviewer (or an automated reproducibility checker) trusts those
commitments to detect post-hoc edits to the data files.

In v1.1.2 the manifest's commitments had drifted from the actual
on-disk TSV bytes — the index files had been edited after the
manifest was generated, and there was no test forcing a re-seal.
This test closes that gap. It must fail loudly the next time anyone
edits a committed TSV without refreshing the manifest in the same
commit.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ATLAS_DIR = REPO_ROOT / "examples" / "atlas"
MANIFEST = ATLAS_DIR / "manifest.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _row_count_excl_header(path: Path) -> int:
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for _ in fh) - 1


@pytest.fixture(scope="module")
def manifest() -> dict:
    if not MANIFEST.exists():
        pytest.skip(f"{MANIFEST} absent — manifest not yet built.")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_lists_at_least_two_files(manifest: dict) -> None:
    """The comprehensive index ships at least the two committed TSVs.
    Pinning the count guards against a future manifest edit silently
    dropping a file from coverage."""
    files = manifest.get("files")
    assert isinstance(files, list), "manifest.files must be a list"
    assert len(files) >= 2, f"manifest.files has only {len(files)} entries; expected >= 2"


def test_every_manifest_file_exists(manifest: dict) -> None:
    """Every path in manifest.files must exist relative to the repo root."""
    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), f"manifest.files entry missing on disk: {entry['path']}"


def test_every_manifest_sha256_matches_file(manifest: dict) -> None:
    """Recorded SHA-256 must equal the SHA-256 of the file on disk.

    The whole point of the manifest is post-hoc auditability; a stale
    hash defeats that purpose. This test must fail any time someone
    edits a committed TSV without refreshing the manifest. Re-seal via
    examples/atlas/build_comprehensive_index.py (or recompute manually
    and update manifest.json in the same commit).
    """
    failures: list[str] = []
    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        actual = _sha256(path)
        recorded = entry.get("sha256")
        if actual != recorded:
            failures.append(f"{entry['path']}: manifest says {recorded!r}, on-disk is {actual!r}")
    assert not failures, "Atlas manifest SHA-256 commitments are stale:\n  " + "\n  ".join(failures)


def test_every_manifest_row_count_matches_file(manifest: dict) -> None:
    """Row count (excluding the TSV header line) must equal the
    on-disk count. If a future edit reduces or expands the index, the
    manifest must be refreshed in the same commit."""
    failures: list[str] = []
    for entry in manifest["files"]:
        if "rows_excl_header" not in entry:
            continue
        path = REPO_ROOT / entry["path"]
        actual = _row_count_excl_header(path)
        recorded = entry["rows_excl_header"]
        if actual != recorded:
            failures.append(f"{entry['path']}: manifest says {recorded} rows, on-disk is {actual}")
    assert not failures, "Atlas manifest row counts are stale:\n  " + "\n  ".join(failures)


def test_every_manifest_byte_count_matches_file(manifest: dict) -> None:
    """Byte size, when recorded, must equal the on-disk size."""
    failures: list[str] = []
    for entry in manifest["files"]:
        if "bytes" not in entry:
            continue
        path = REPO_ROOT / entry["path"]
        actual = os.path.getsize(path)
        recorded = entry["bytes"]
        if actual != recorded:
            failures.append(f"{entry['path']}: manifest says {recorded} bytes, on-disk is {actual}")
    assert not failures, "Atlas manifest byte counts are stale:\n  " + "\n  ".join(failures)


def test_manifest_tool_sha256_matches_build_script(manifest: dict) -> None:
    """The tool.sha256 field is the SHA-256 of the build script that
    produced the TSVs. If the build script changes without refreshing
    the manifest, reviewers can't trust the regeneration story."""
    tool = manifest.get("tool") or {}
    script_rel = tool.get("path")
    recorded = tool.get("sha256")
    if not script_rel or not recorded:
        pytest.skip("manifest.tool.path or manifest.tool.sha256 missing; skipping check.")
    script_path = REPO_ROOT / script_rel
    if not script_path.exists():
        pytest.skip(f"build script {script_rel!r} absent on disk.")
    actual = _sha256(script_path)
    assert actual == recorded, (
        f"manifest.tool.sha256 ({recorded!r}) does not match the on-disk "
        f"{script_rel} ({actual!r}). Re-seal the manifest in the same commit "
        f"that edits the build script."
    )
