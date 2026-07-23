"""The published ``mcp`` dependency floor must not regress below the fixed
version that remediates CVE-2026-59950.

``constraints/dev.lock`` pins ``mcp==1.28.1`` and CI resolves against that lock,
so CI is protected. But the lock is a dev/CI-only artefact: it is not shipped in
the wheel and is not applied to a downstream ``pip install``. What downstream
installs actually see is the ``[project].dependencies`` floor, which becomes the
wheel's ``Requires-Dist``. If that floor is ever lowered below 1.28.1, a
downstream environment could resolve an ``mcp`` in the vulnerable ``[1.2,
1.28.0]`` range even while CI stays green. This contract pins the invariant that
`test_security_policy_version` pins for the supported-versions table: the
declared floor is at least the security baseline.

The assertion is on the *lower bound only*, so a future legitimate floor
increase (e.g. ``mcp>=1.29.0``) still passes; it does not require 1.28.1 itself
to remain installable.

Stdlib only (``tomllib``/``re``/``pathlib``), matching the repo's other
metadata-coherence contracts; we deliberately do not import ``packaging`` (an
undeclared, transitive test dependency).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# The minimum ``mcp`` version carrying the CVE-2026-59950 fix (the deprecated
# WebSocket server transport lacked Host/Origin validation). The published floor
# must be at least this; raising it further is welcome.
MIN_MCP_FLOOR = (1, 28, 1)


def _normalized_name(requirement: str) -> str:
    """Return the PEP 503-normalized distribution name of a requirement string.

    Only the leading name token is inspected, so extras/specifiers/markers
    (``mcp[cli]>=1.28.1``, ``mcp >= 1.28.1``) resolve to ``mcp`` and a sibling
    like ``mcp-foo`` does not.
    """
    token = re.match(r"([A-Za-z0-9._-]+)", requirement)
    assert token, f"unparseable requirement string: {requirement!r}"
    return re.sub(r"[-_.]+", "-", token.group(1)).lower()


def _mcp_requirement() -> str:
    """Return the single direct ``mcp`` requirement from pyproject dependencies."""
    with (REPO_ROOT / "pyproject.toml").open("rb") as f:
        dependencies = tomllib.load(f)["project"]["dependencies"]
    mcp_requirements = [d for d in dependencies if _normalized_name(d) == "mcp"]
    assert len(mcp_requirements) == 1, (
        "expected exactly one direct 'mcp' requirement in [project.dependencies], "
        f"found {len(mcp_requirements)}: {mcp_requirements}"
    )
    return mcp_requirements[0]


def test_mcp_floor_not_below_security_baseline() -> None:
    requirement = _mcp_requirement()
    lower_bound = re.search(r">=\s*([0-9]+(?:\.[0-9]+)*)", requirement)
    assert lower_bound, (
        f"the 'mcp' requirement {requirement!r} declares no '>=' lower bound; "
        "a missing floor could resolve a version vulnerable to CVE-2026-59950. "
        "Declare at least 'mcp>=1.28.1'."
    )
    floor = tuple(int(part) for part in lower_bound.group(1).split("."))
    # Zero-pad both to compare release tuples of differing length, e.g. a floor
    # of (1, 28) must still be judged below the baseline (1, 28, 1).
    width = max(len(floor), len(MIN_MCP_FLOOR))
    floor_padded = floor + (0,) * (width - len(floor))
    baseline_padded = MIN_MCP_FLOOR + (0,) * (width - len(MIN_MCP_FLOOR))
    assert floor_padded >= baseline_padded, (
        f"the published 'mcp' floor {'.'.join(map(str, floor))} is below the "
        "security baseline 1.28.1 (CVE-2026-59950). Do not lower it: the wheel's "
        "Requires-Dist is the only floor a downstream 'pip install' sees."
    )
