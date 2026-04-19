"""Fixture content-addressing guard.

Every canonical fixture hashed in the repo must match the manifest.
Changes are intentional only — regenerate with:

    python -m tests.fixtures.verify --update
"""

from __future__ import annotations

from tests.fixtures.verify import verify


def test_fixture_manifest_matches() -> None:
    assert verify(update=False) == 0, "fixture drift; see stderr"
