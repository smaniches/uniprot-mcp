# Contributing to uniprot-mcp

Thanks for your interest in contributing. This project aims to be a
reference-quality Model Context Protocol server for UniProt — clean,
tested, and reproducible. Please read this guide before opening a PR.

## Ground rules

1. **No unverified claims ship.** If behaviour is not covered by a test,
   it does not exist. New features require new tests.
2. **Offline tests must stay offline.** The unit, property, client, and
   contract layers must not hit the network. Network is blocked by
   `pytest-socket` in `conftest.py` — don't disable it.
3. **Integration tests are opt-in.** They hit the live UniProt API and
   run only with `pytest --integration`.
4. **Style is automated.** Ruff formats and lints; mypy type-checks.
   CI rejects changes that don't pass. Run `pre-commit run --all-files`
   before pushing.
5. **Conventional commits preferred** (`feat:`, `fix:`, `docs:`, …).
   Not required, but it makes changelog work easier.

## Development setup

```bash
git clone https://github.com/smaniches/uniprot-mcp.git
cd uniprot-mcp
python -m venv .venv
# Windows:   .venv\Scripts\activate
# Unix/macOS: source .venv/bin/activate
pip install -e ".[test,dev]"
pre-commit install
```

## Running tests

```bash
# Fast, offline — what CI runs on every push:
pytest tests/unit tests/property tests/client tests/contract -v

# With coverage:
pytest --cov --cov-report=term-missing

# Live UniProt API (opt-in):
pytest --integration tests/integration -v

# The MCP JSON-RPC handshake test (spawns the server as a subprocess):
pytest -m mcp_protocol --integration
```

## Recording new API fixtures

Fixtures in `tests/fixtures/` are canned UniProt responses used by the
unit and contract layers. If the UniProt schema changes or you need a
new shape, re-record:

```bash
python -m tests.fixtures.capture
```

This hits the live API, writes pretty-printed JSON with a `_meta` block
(timestamp, UniProt release, source URL), and updates the fixture index.
Review the diff carefully — shape changes are a signal, not a rubber
stamp.

## Opening a pull request

- Fork and branch from `main`
- Keep PRs focused — one concern per PR
- Include tests and a `CHANGELOG.md` entry under **[Unreleased]**
- Fill out the PR template
- CI must be green before review

## Reporting bugs / requesting features

Use GitHub Issues. For security issues, see [SECURITY.md](SECURITY.md).
