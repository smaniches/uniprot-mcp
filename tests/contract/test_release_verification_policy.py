"""Contract tests for release verification timing and responsibility."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
IMMEDIATE_WORKFLOW = ROOT / ".github" / "workflows" / "release-verify.yml"
ZENODO_WORKFLOW = ROOT / ".github" / "workflows" / "zenodo-verify.yml"


def test_zenodo_is_not_part_of_the_immediate_release_gate() -> None:
    """A short Zenodo propagation delay must not fail the immediate gate."""
    immediate = IMMEDIATE_WORKFLOW.read_text(encoding="utf-8")

    assert "zenodo.org" not in immediate.lower()
    assert "ZENODO_CONCEPT_RECID" not in immediate
    assert "PyPI, GitHub Release assets, SLSA provenance" in immediate


def test_zenodo_failure_is_reported_only_after_a_delayed_gate() -> None:
    """Scheduled verification must wait before creating a drift issue."""
    delayed = ZENODO_WORKFLOW.read_text(encoding="utf-8")

    assert "schedule:" in delayed
    match = re.search(r'MIN_RELEASE_AGE_HOURS: "([0-9]+)"', delayed)
    assert match is not None
    assert int(match.group(1)) >= 6

    age_gate = "if (!requestedTag && ageHours < minAgeHours)"
    issue_title = "Zenodo verification failed for ${tag}"
    assert age_gate in delayed
    assert issue_title in delayed
    assert delayed.index(age_gate) < delayed.index(issue_title)

    assert "actualVersion === expectedVersion" in delayed
    assert 'state_reason: "completed"' in delayed
    assert "Do not mint a" in delayed
