"""Contract: .pre-commit-config.yaml stays in lockstep with dev.lock.

``.pre-commit-config.yaml`` declares that the linter revs and the mypy
type-stub dependencies track ``constraints/dev.lock``, so a local
``pre-commit run`` enforces the same versions as the CI lint job.

Without this test that promise is unenforced, and the monthly
``dev-lock-maintenance.yml`` refresh is the likely thing to break it:
it advances the lock and commits only ``constraints/``, so a bumped
ruff / mypy / bandit would leave the hook revs behind and local and CI
linting would quietly disagree.

Mirrors tests/contract/test_version_consistency.py, which wraps
scripts/check_versions.py the same way.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "check_precommit_lockstep.py"


def test_precommit_config_matches_dev_lock() -> None:
    """Every pinned hook version equals the pin in constraints/dev.lock.

    On failure the script prints each drifted site and the exact fix
    command, so the assertion message is the actionable report.
    """
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, (
        "pre-commit hook versions have drifted from constraints/dev.lock.\n"
        f"{result.stdout}{result.stderr}"
    )
