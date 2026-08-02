#!/usr/bin/env python3
""".pre-commit-config.yaml must stay in lockstep with constraints/dev.lock.

``.pre-commit-config.yaml`` states that the linter revs and the mypy
type-stub dependencies are kept aligned with ``constraints/dev.lock``,
so that a contributor's local ``pre-commit run`` enforces exactly the
versions the CI lint job pins. Nothing enforced that: the monthly
``dev-lock-maintenance.yml`` refresh advances the lock and stages only
``constraints/``, so a bumped ruff/mypy/bandit in the lock would
silently leave the hook revs behind and local and CI linting would
start disagreeing.

``constraints/dev.lock`` is canonical here (it is what CI executes).
This script is invoked by:

  * ``tests/contract/test_precommit_lockstep.py`` — so pytest fails the
    CI test matrix on drift, before merge, whatever introduced it; and
  * a ``pre-commit`` local hook — so drift is caught on commit; and
  * ``dev-lock-maintenance.yml`` with ``--fix`` — so the monthly refresh
    updates the hook revs in the same PR as the lock bump instead of
    quietly desynchronising them.

Usage:
    python scripts/check_precommit_lockstep.py         # check; exit 1 on drift
    python scripts/check_precommit_lockstep.py --fix   # rewrite the config to
                                                       # match dev.lock

Stdlib only (no PyYAML), matching scripts/check_versions.py, so it can
run as a ``pre-commit`` ``language: system`` hook with no env bootstrap.
Every site below must match exactly once; a config restructure that
moves a site makes this script fail loudly rather than silently pass.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / ".pre-commit-config.yaml"
LOCK = ROOT / "constraints" / "dev.lock"


@dataclass(frozen=True)
class Site:
    """One version literal in .pre-commit-config.yaml bound to a lock pin.

    ``package`` is the distribution name to read out of ``dev.lock``.
    ``pattern`` must contain exactly one capturing group: the bare
    version literal as it appears in the config. Any ``v`` tag prefix
    stays OUTSIDE the group, so rewriting the captured span preserves
    each upstream repo's own tag spelling (ruff and mypy tag
    ``v0.16.1``; bandit tags ``1.9.4``).
    """

    label: str
    package: str
    pattern: re.Pattern[str]


SITES: tuple[Site, ...] = (
    Site(
        label="ruff-pre-commit rev",
        package="ruff",
        pattern=re.compile(
            r"(?s)(?<=repo: https://github\.com/astral-sh/ruff-pre-commit\n)"
            r"\s*rev:\s*v(\S+)"
        ),
    ),
    Site(
        label="mirrors-mypy rev",
        package="mypy",
        pattern=re.compile(
            r"(?s)(?<=repo: https://github\.com/pre-commit/mirrors-mypy\n)"
            r"\s*rev:\s*v(\S+)"
        ),
    ),
    Site(
        label="bandit rev",
        package="bandit",
        pattern=re.compile(r"(?s)(?<=repo: https://github\.com/PyCQA/bandit\n)\s*rev:\s*(\S+)"),
    ),
    Site(
        label="mypy additional_dependencies httpx",
        package="httpx",
        pattern=re.compile(r'"httpx==(\S+?)"'),
    ),
    Site(
        label="mypy additional_dependencies mcp",
        package="mcp",
        pattern=re.compile(r'"mcp==(\S+?)"'),
    ),
)


def _lock_versions() -> dict[str, str]:
    """Map distribution name -> pinned version from constraints/dev.lock.

    uv emits ``name==version \\`` followed by indented ``--hash`` lines,
    so an anchored match on the start of a line is unambiguous: a hash
    continuation can never look like a pin.
    """
    text = LOCK.read_text(encoding="utf-8")
    return {
        m.group(1).lower(): m.group(2)
        for m in re.finditer(r"^([A-Za-z0-9._-]+)==(\S+?)(?:\s|$)", text, re.MULTILINE)
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite .pre-commit-config.yaml to match constraints/dev.lock",
    )
    args = parser.parse_args()

    versions = _lock_versions()
    text = CONFIG.read_text(encoding="utf-8")
    original = text
    drift: list[str] = []

    for site in SITES:
        expected = versions.get(site.package.lower())
        if expected is None:
            print(
                f"error: {site.package} is not pinned in {LOCK.relative_to(ROOT)}; "
                f"cannot verify {site.label}",
                file=sys.stderr,
            )
            return 1

        matches = list(site.pattern.finditer(text))
        if len(matches) != 1:
            print(
                f"error: expected exactly 1 match for {site.label} in "
                f"{CONFIG.relative_to(ROOT)}, found {len(matches)}. The config "
                f"layout changed — update SITES in {Path(__file__).name}.",
                file=sys.stderr,
            )
            return 1

        found = matches[0].group(1)
        if found == expected:
            continue

        drift.append(f"  {site.label}: config has {found!r}, dev.lock pins {expected!r}")
        if args.fix:
            start, end = matches[0].span(1)
            # Rewrite only the captured version span, so surrounding
            # YAML (indentation, quoting, comments) is byte-preserved.
            text = text[:start] + expected + text[end:]

    if not drift:
        print(f"{CONFIG.relative_to(ROOT)} is in lockstep with {LOCK.relative_to(ROOT)}")
        return 0

    if args.fix:
        if text != original:
            CONFIG.write_text(text, encoding="utf-8")
        print("Realigned .pre-commit-config.yaml with constraints/dev.lock:")
        print("\n".join(drift))
        return 0

    print(
        ".pre-commit-config.yaml has drifted from constraints/dev.lock.\n"
        "The config declares these are kept in lockstep so local `pre-commit "
        "run` matches the CI lint job.\n",
        file=sys.stderr,
    )
    print("\n".join(drift), file=sys.stderr)
    print(
        "\nRun: python scripts/check_precommit_lockstep.py --fix",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
