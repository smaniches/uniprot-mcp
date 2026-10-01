from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_release_please_surfaces_security_commits() -> None:
    config = json.loads((ROOT / "release-please-config.json").read_text(encoding="utf-8"))
    sections = config["changelog-sections"]
    assert {
        "type": "security",
        "section": "Security",
        "hidden": False,
    } in sections
