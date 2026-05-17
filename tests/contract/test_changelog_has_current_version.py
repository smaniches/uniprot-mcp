"""CHANGELOG.md must carry a ``## [<version>]`` heading for the current
``pyproject.toml`` version before a release tag is pushed.

This catches the "silent version bump" failure mode that has bitten
this repo twice (v1.1.4 UA test pin desync, v1.1.5 provenance repair),
without depending on tag-time inspection — by the time CI fires on
the tag, ``release.yml`` is already running.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _canonical_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml: cannot find [project].version"
    return match.group(1)


def test_changelog_has_heading_for_current_version() -> None:
    version = _canonical_version()
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    pattern = re.compile(rf"^##\s+\[{re.escape(version)}\]", re.MULTILINE)
    assert pattern.search(changelog), (
        f"CHANGELOG.md is missing a `## [{version}]` heading. "
        "Add an entry before tagging the release."
    )
