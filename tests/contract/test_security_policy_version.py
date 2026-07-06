"""SECURITY.md must declare the current ``pyproject.toml`` minor series as
supported.

Shipping a version whose own security policy does not cover it is exactly
the version-coherence drift the rest of this repo guards against (see
``test_version_consistency`` for the exact-version sites and
``test_changelog_has_current_version`` for the changelog heading). This
closes the same gap for the security policy's supported-versions table,
which names a minor series (``1.2.x``) rather than an exact version and so
cannot be folded into ``scripts/check_versions.py``'s exact-match sites.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _canonical_version() -> str:
    # tomllib (stdlib on Python 3.11+, our minimum) rather than regex, so a
    # stray ``version =`` in a tool config or dependency block can't match.
    with (REPO_ROOT / "pyproject.toml").open("rb") as f:
        return str(tomllib.load(f)["project"]["version"])


def test_security_policy_covers_current_minor_series() -> None:
    version = _canonical_version()
    major, minor, *_ = version.split(".")
    series = f"{major}.{minor}.x"
    security = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    # A supported row in the table looks like: ``| 1.2.x | :white_check_mark: |``.
    # Requiring the current series be present *and* checked allows the policy
    # to still support older series without weakening the invariant that the
    # shipped series is covered.
    pattern = re.compile(
        rf"^\|\s*{re.escape(series)}\s*\|\s*:white_check_mark:\s*\|",
        re.MULTILINE,
    )
    assert pattern.search(security), (
        f"SECURITY.md does not list the current minor series `{series}` as "
        f"supported (:white_check_mark:). pyproject version is {version}; "
        "update the Supported Versions table so the shipped series is covered."
    )
