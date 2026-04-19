# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Project layout:** migrated flat `server.py`/`client.py`/`formatters.py`
  to `src/uniprot_mcp/` (eliminates site-packages collision risk, makes
  `py.typed` PEP 561-effective, removes `sys.path` hack). Console script
  now wires `uniprot-mcp = "uniprot_mcp.server:main"`.
- `smithery.yaml` now invokes the `uniprot-mcp` console script instead
  of a non-existent `Dockerfile`.
- CI: `pip-audit --strict` no longer silently masked with `|| true`.
- CI: `tests/contract/` added to the offline pytest invocation.

### Added
- **Input validation layer** in every tool: length caps on `query`,
  `ids`, `accession`, `organism`, `database`, `feature_types`;
  allow-list for `response_format`; accession-format pre-check before
  any HTTP call.
- **Agent-safe error envelopes** — raw exception text no longer leaks
  to LLM callers (logged server-side instead).
- **Retry on `id_mapping_submit`** (was previously a single-shot call).
- **HTTP-date `Retry-After` parsing** (RFC 7231) — previously only
  delta-seconds were honoured; HTTP-date headers fell back to
  exponential back-off.
- `tests/contract/` — fixture-shape contract tests (directory was
  previously referenced in docs but did not exist).
- Unit tests for `_check_accession`, `_check_format`, `_safe_error`,
  the HTTP-date Retry-After branch, multi-word organism quoting in
  `uniprot_search`, and the no-network-on-bad-input property.

### Fixed
- `formatters.py` now fully type-hinted; `is_swissprot` helper replaces
  duplicated logic; ambiguous `l` loop variable renamed.

### Security
- See `AUDIT.md` — this release closes P0/P1 findings from the
  post-ship professional audit.



## [0.1.0] - 2026-04-18

### Added
- Initial public release of `uniprot-mcp` — ten UniProt tools exposed over
  the Model Context Protocol via `FastMCP` stdio transport:
  `get_entry`, `search`, `get_sequence`, `get_features`, `get_variants`,
  `get_go_terms`, `get_cross_refs`, `id_mapping`, `batch_entries`,
  `taxonomy_search`.
- Strict UniProt accession regex (`ACCESSION_RE`) applied client-side in
  `batch_entries` so a single malformed token no longer fails an entire
  batch. Invalid tokens are returned in the `invalid` field and surfaced
  in the formatted server response.
- Four-layer test suite: unit, property-based (Hypothesis), client
  (respx-mocked httpx), integration (live UniProt, `--integration`).
- Packaging (`pyproject.toml`, Hatch backend), Apache-2.0 license,
  `NOTICE`, `CITATION.cff` (ORCID 0009-0005-6480-1987).
- GitHub Actions CI (matrix 3.11/3.12/3.13 × ubuntu/windows/macos),
  nightly live-API drift check, Dependabot, CodeQL.

### Fixed
- `batch_entries` no longer returns HTTP 400 when one malformed accession
  is mixed into an otherwise valid batch.

[Unreleased]: https://github.com/smaniches/uniprot-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/smaniches/uniprot-mcp/releases/tag/v0.1.0
