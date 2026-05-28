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


@pytest.hookimpl(trylast=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Lift ``pytest-socket``'s block per-test for integration tests.

    The project's offline default in ``pyproject.toml`` is a strict
    ``--disable-socket --allow-hosts=127.0.0.1,::1`` (so unit /
    property / client / contract tests cannot accidentally hit the
    network). Integration tests *must* hit the network — that is the
    entire point of running them.

    Two independent restrictions are in play and *both* must be lifted:
    ``--disable-socket`` blocks socket *creation*, while ``--allow-hosts``
    installs a session-global guard on ``socket.socket.connect`` that
    rejects any host outside the allow-list. ``enable_socket()`` only
    restores creation, so on its own a connection to ``rest.uniprot.org``
    still raises ``SocketConnectBlockedError``. ``_remove_restrictions()``
    restores both, so integration tests reach the live API regardless of
    how pytest is invoked (``nox -s integration``, a bare
    ``pytest --integration``, or CI's ``--override-ini``). pytest-socket
    reapplies its block before every test, so this must run per-item,
    *after* its own ``pytest_runtest_setup`` hook. We restrict it to
    items marked ``integration`` so the offline suites still respect the
    block.
    """
    if "integration" not in item.keywords:
        return
    try:
        import pytest_socket  # type: ignore[import-untyped]
    except ImportError:  # pragma: no cover - pytest-socket always installed in test extras
        return
    # Prefer the helper that also restores socket.socket.connect; fall
    # back to enable_socket() on any pytest-socket build that lacks it.
    remove = getattr(pytest_socket, "_remove_restrictions", None)
    if callable(remove):
        remove()
    else:  # pragma: no cover - exercised only on pytest-socket without the helper
        pytest_socket.enable_socket()


@pytest.fixture(autouse=True)
async def _reset_server_client_singleton():
    """Ensure the module-level UniProtClient singleton doesn't leak
    between tests. A connected httpx.AsyncClient captured before a
    `respx.mock` context starts will bypass the mock, producing flaky
    test-order dependencies."""
    yield
    try:
        from uniprot_mcp import server as _srv
    except ImportError:  # pragma: no cover - pre-install
        return
    if _srv._uniprot is not None:
        await _srv._uniprot.close()
        _srv._uniprot = None


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
