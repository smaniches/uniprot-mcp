"""Shared pytest configuration, fixtures, and markers.

Key guarantees enforced here:
- Network is blocked for unit/property/client/contract tests. The real
  UniProt API is only ever hit from `tests/integration/` and only when
  `--integration` is passed.
- The ``uniprot_mcp`` package is imported via editable install
  (``pip install -e .``); no ``sys.path`` hacks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run tests that hit the live UniProt REST API",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--integration"):
        return
    skip_live = pytest.mark.skip(reason="live API test; pass --integration to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture
def fixture_loader():
    """Return a callable that loads a JSON fixture by stem."""

    def _load(stem: str) -> Any:
        path = FIXTURE_DIR / f"{stem}.json"
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        data.pop("_meta", None)
        return data

    return _load
