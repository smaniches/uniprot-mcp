"""Published transitive security floors that downstream installers must see."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIN_PYJWT_FLOOR = (2, 15, 0)


def _normalized_name(requirement: str) -> str:
    token = re.match(r"([A-Za-z0-9._-]+)", requirement)
    assert token, f"unparseable requirement string: {requirement!r}"
    return re.sub(r"[-_.]+", "-", token.group(1)).lower()


def test_pyjwt_floor_not_below_security_baseline() -> None:
    with (ROOT / "pyproject.toml").open("rb") as f:
        dependencies = tomllib.load(f)["project"]["dependencies"]

    matches = [d for d in dependencies if _normalized_name(d) == "pyjwt"]
    assert len(matches) == 1, f"expected one direct PyJWT security floor, found {matches}"

    bound = re.search(r">=\s*([0-9]+(?:\.[0-9]+)*)", matches[0])
    assert bound, f"PyJWT requirement has no lower bound: {matches[0]!r}"
    floor = tuple(int(part) for part in bound.group(1).split("."))
    width = max(len(floor), len(MIN_PYJWT_FLOOR))
    assert floor + (0,) * (width - len(floor)) >= MIN_PYJWT_FLOOR + (0,) * (
        width - len(MIN_PYJWT_FLOOR)
    )
