"""Contract test: docs/INCIDENT_LOG.md and docs/incidents/ must agree.

Enforces the policy in `docs/INCIDENT_POLICY.md` mechanically: every
postmortem file in `docs/incidents/` is referenced by the log, and
every entry in the log points at a real file. Drift between the two
is the most likely silent failure of the policy and is exactly what
this test catches.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INCIDENTS_DIR = REPO_ROOT / "docs" / "incidents"
LOG_PATH = REPO_ROOT / "docs" / "INCIDENT_LOG.md"

# Match `[postmortem](incidents/2026-04-30-foo.md)` style links in the log.
_LOG_LINK_RE = re.compile(r"\(incidents/([A-Za-z0-9._-]+\.md)\)")


def _log_referenced_files() -> set[str]:
    text = LOG_PATH.read_text(encoding="utf-8")
    return set(_LOG_LINK_RE.findall(text))


def _on_disk_postmortem_files() -> set[str]:
    if not INCIDENTS_DIR.exists():
        return set()
    return {p.name for p in INCIDENTS_DIR.iterdir() if p.is_file() and p.suffix == ".md"}


def test_incident_log_exists() -> None:
    assert LOG_PATH.exists(), f"missing {LOG_PATH}; required by INCIDENT_POLICY.md"


def test_every_log_entry_points_at_a_real_file() -> None:
    referenced = _log_referenced_files()
    on_disk = _on_disk_postmortem_files()
    dangling = referenced - on_disk
    assert not dangling, (
        f"INCIDENT_LOG.md references postmortem files that don't exist: {sorted(dangling)}"
    )


def test_every_postmortem_file_has_a_log_entry() -> None:
    referenced = _log_referenced_files()
    on_disk = _on_disk_postmortem_files()
    orphans = on_disk - referenced
    assert not orphans, (
        f"docs/incidents/ contains files not referenced from INCIDENT_LOG.md: {sorted(orphans)}"
    )


def test_postmortem_template_exists() -> None:
    template = REPO_ROOT / "docs" / "POSTMORTEM_TEMPLATE.md"
    assert template.exists(), "docs/POSTMORTEM_TEMPLATE.md is required by INCIDENT_POLICY.md"


def test_incident_policy_exists() -> None:
    policy = REPO_ROOT / "docs" / "INCIDENT_POLICY.md"
    assert policy.exists(), "docs/INCIDENT_POLICY.md is required for the policy contract"
