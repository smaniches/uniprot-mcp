"""Every file that names the project version must agree with
``pyproject.toml`` exactly. Delegated to ``scripts/check_versions.py``
(which is also wired as a ``pre-commit`` hook so drift is caught
before push, not after CI red)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_versions.py"


def test_version_strings_agree_across_all_sites() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "Version drift between pyproject.toml and one or more downstream "
        "files. Run `python scripts/check_versions.py --fix` to "
        f"resync.\n\nstdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
    )
