"""Contract: constraints/mutation.lock satisfies constraints/mutation.in.

The ci.yml `lock` gate regenerates every other lock and asserts a clean
``git diff``, which is what keeps each input and its lock together.
``mutation.lock`` is excluded from that regeneration on purpose --
resolving it builds mutmut's and glob2's sdists, executing third-party
``setup.py`` code, which is not something to run on every pull request.

That exclusion means editing the ``mutmut==`` pin without running
``scripts/regenerate-mutation-lock.sh`` would otherwise pass every
check while the weekly mutation run silently kept using the old
version. This test closes that hole by comparing the two files
directly, resolving nothing.

Mirrors tests/contract/test_version_consistency.py and
tests/contract/test_precommit_lockstep.py, which wrap their scripts the
same way.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "check_mutation_lock_sync.py"


def test_mutation_lock_matches_its_input() -> None:
    """Every pin in mutation.in appears at the same version in the lock.

    On failure the script names each drifted pin and prints the exact
    regeneration command, so the assertion message is the fix.
    """
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, (
        "constraints/mutation.lock is out of sync with constraints/mutation.in.\n"
        f"{result.stdout}{result.stderr}"
    )
