#!/usr/bin/env python3
"""Single-source-of-truth version check across every file that names
the project version.

``pyproject.toml`` ``[project].version`` is canonical. Every other
file must agree, exactly. This script is invoked by the
``tests/contract/test_version_consistency.py`` contract test (so
``pytest`` catches drift in CI) and by a ``pre-commit`` local hook
(so drift is caught on commit before it can reach a remote).

Usage:
    python scripts/check_versions.py            # check; exit 1 on drift
    python scripts/check_versions.py --fix      # rewrite each file to
                                                # the canonical version
                                                # from pyproject.toml

The script is intentionally stdlib-only (no toml or yaml deps) so it
can be a pre-commit ``language: system`` hook without a Python env
bootstrap.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Site:
    """One occurrence of the version string in a file.

    ``label`` is for human-readable diff output. ``pattern`` matches
    a single capturing group: the version literal currently present
    at the site. ``rewrite`` produces the line/block that should
    replace the match when ``--fix`` is invoked.
    """

    path: Path
    label: str
    pattern: re.Pattern[str]
    rewrite: Callable[[str], str]


def _read_canonical_version() -> str:
    """Read ``[project].version`` from ``pyproject.toml`` by regex.

    Stdlib's ``tomllib`` would be cleaner but only exists on 3.11+
    and we want this script to run unchanged under pre-commit's
    isolated env. A single regex over a short, stable file is fine.
    """
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("pyproject.toml: cannot find [project].version")
    return match.group(1)


def _sites() -> list[Site]:
    return [
        Site(
            path=ROOT / "CITATION.cff",
            label="CITATION.cff (version:)",
            pattern=re.compile(r"^version:\s*(\S+)\s*$", re.MULTILINE),
            rewrite=lambda v: f"version: {v}",
        ),
        Site(
            path=ROOT / "server.json",
            label="server.json (version_detail.version)",
            pattern=re.compile(r'"version":\s*"([^"]+)",\s*\n\s*"release_date"'),
            rewrite=lambda v: f'"version": "{v}",\n    "release_date"',
        ),
        Site(
            path=ROOT / "server.json",
            label="server.json (packages[0].version)",
            # The packages block has its own "version": "..." line; we
            # match the second occurrence by anchoring on the
            # surrounding "name": "uniprot-mcp-server" key.
            pattern=re.compile(r'"name":\s*"uniprot-mcp-server",\s*\n\s*"version":\s*"([^"]+)"'),
            rewrite=lambda v: f'"name": "uniprot-mcp-server",\n      "version": "{v}"',
        ),
        Site(
            path=ROOT / ".well-known" / "mcp.json",
            label=".well-known/mcp.json (version)",
            pattern=re.compile(r'"version":\s*"([^"]+)"'),
            rewrite=lambda v: f'"version": "{v}"',
        ),
        Site(
            path=ROOT / "tests" / "unit" / "test_client_mutation_killers.py",
            label="tests/unit/test_client_mutation_killers.py (UA pin)",
            # Match any PEP 440 version segment (digits + `.post`, `.dev`,
            # `rc`, `a`, `b`, etc.) — `[^ ]+` is wider than the canonical
            # release pattern so post-releases and pre-releases don't
            # silently bypass the check.
            pattern=re.compile(
                r'"uniprot-mcp/([^ ]+) \(\+https://github\.com/smaniches/uniprot-mcp\)"'
            ),
            rewrite=lambda v: f'"uniprot-mcp/{v} (+https://github.com/smaniches/uniprot-mcp)"',
        ),
    ]


def _check_site(site: Site, canonical: str) -> str | None:
    """Return None on match; return a human-readable mismatch line
    on drift; raise on a missing pattern (treated as a hard failure
    because the script's pattern itself has rotted)."""
    text = site.path.read_text(encoding="utf-8")
    match = site.pattern.search(text)
    if not match:
        return f"{site.label}: pattern not found in {site.path}"
    observed = match.group(1)
    if observed == canonical:
        return None
    return f"{site.label}: {observed!r} != canonical {canonical!r}"


def _fix_site(site: Site, canonical: str) -> bool:
    """Rewrite the site to the canonical version. Returns True if a
    change was written, False if already in sync."""
    text = site.path.read_text(encoding="utf-8")
    match = site.pattern.search(text)
    if not match:
        raise SystemExit(f"{site.label}: pattern not found; refusing to --fix")
    if match.group(1) == canonical:
        return False
    new_block = site.rewrite(canonical)
    new_text = text[: match.start()] + new_block + text[match.end() :]
    site.path.write_text(new_text, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Rewrite every site to match pyproject.toml. Use after bumping the canonical version.",
    )
    args = parser.parse_args(argv)
    canonical = _read_canonical_version()
    sites = _sites()

    if args.fix:
        changed = []
        for site in sites:
            if _fix_site(site, canonical):
                changed.append(site.label)
        if changed:
            print(f"check_versions: rewrote {len(changed)} site(s) to {canonical}:")
            for label in changed:
                print(f"  - {label}")
        else:
            print(f"check_versions: all sites already at {canonical}")
        return 0

    mismatches = [m for m in (_check_site(s, canonical) for s in sites) if m]
    if mismatches:
        print(f"check_versions: drift from canonical pyproject version {canonical!r}:")
        for line in mismatches:
            print(f"  - {line}")
        print("\nRun `python scripts/check_versions.py --fix` to propagate the canonical version.")
        return 1
    print(f"check_versions: {len(sites)} sites all at {canonical}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
