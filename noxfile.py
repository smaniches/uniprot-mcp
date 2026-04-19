"""One-command entrypoint for lint, type-check, and test tiers.

Run a session:
    nox -s lint
    nox -s typecheck
    nox -s test
    nox -s integration
    nox -s snapshot-update

Install: ``pip install nox`` (or ``pipx install nox``).
"""
from __future__ import annotations

import nox

nox.options.sessions = ["lint", "typecheck", "test"]
nox.options.reuse_existing_virtualenvs = True

PYTHON_VERSIONS = ["3.11", "3.12", "3.13"]
SRC = ["client.py", "server.py", "formatters.py"]


@nox.session(python=False)
def lint(session: nox.Session) -> None:
    session.run("ruff", "check", ".", external=True)
    session.run("ruff", "format", "--check", ".", external=True)


@nox.session(python=False)
def typecheck(session: nox.Session) -> None:
    session.run("mypy", *SRC, external=True)


@nox.session(python=PYTHON_VERSIONS)
def test(session: nox.Session) -> None:
    """Offline tiers only: unit + property + client. CI-equivalent."""
    session.install("-e", ".[test]")
    session.run(
        "pytest",
        "tests/unit",
        "tests/property",
        "tests/client",
        "-v",
        "--cov",
        "--cov-report=term-missing",
    )


@nox.session(python="3.12")
def integration(session: nox.Session) -> None:
    """Live UniProt API — hits the network."""
    session.install("-e", ".[test]")
    session.run("pytest", "--integration", "tests/integration", "-v")


@nox.session(python="3.12", name="snapshot-update")
def snapshot_update(session: nox.Session) -> None:
    """Regenerate syrupy snapshots."""
    session.install("-e", ".[test]")
    session.run("pytest", "tests", "--snapshot-update")


@nox.session(python="3.12")
def security(session: nox.Session) -> None:
    session.install("bandit", "pip-audit")
    session.run("bandit", "-r", *SRC)
    session.run("pip-audit", "--strict")
