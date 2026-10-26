"""Verify that the built sdist is installable without incomplete checkout tests.

The full scientific contract/fixture suite remains in the version-pinned
GitHub checkout. Including those tests without their scripts and captures
makes the sdist misleading and non-self-contained.
"""

from __future__ import annotations

import tarfile
from pathlib import Path

import pytest
from hatchling.build import build_sdist

ROOT = Path(__file__).resolve().parents[2]


def test_sdist_contains_runtime_sources_but_no_checkout_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise the actual PEP 517 backend, not merely the TOML declaration."""
    # pytest's monkeypatch fixture restores cwd after the build.
    monkeypatch.chdir(ROOT)
    archive_name = build_sdist(str(tmp_path))
    archive = tmp_path / archive_name
    assert archive.is_file()

    with tarfile.open(archive, mode="r:gz") as tf:
        members = {
            member.name.split("/", 1)[1]
            for member in tf.getmembers()
            if member.isfile() and "/" in member.name
        }

    for required in (
        "pyproject.toml",
        "PKG-INFO",
        "README.md",
        "LICENSE",
        "src/uniprot_mcp/__init__.py",
        "src/uniprot_mcp/server.py",
    ):
        assert required in members, required

    included_tests = sorted(name for name in members if name.startswith("tests/"))
    assert not included_tests, included_tests[:10]
    assert not any(name.startswith("examples/captures/") for name in members)
