# Professional Repository Audit — uniprot-mcp 0.1.0

**Audit date:** 2026-04-19
**Author:** Santiago Maniches (with independent audit pass from a separate Claude agent on branch `claude/repository-audit-E9k3N`, which timed out before committing — findings consolidated below)
**Scope:** everything at tag `v0.1.0-pre` / commit `a365dae`.

## Executive summary

uniprot-mcp shipped with a strong operational baseline (four-layer test suite, SLSA + Sigstore + OIDC publishing, OSSF Scorecard, CodeQL) but several real defects in code organisation and correctness that any rigorous review would catch. This document records them, links fixes, and raises the bar for the rest of the Topologica Bio suite.

**Top 3 risks (remediated in this PR):**

1. **Top-level modules** `server.py`, `client.py`, `formatters.py` risked site-packages collision, made `py.typed` ineffective, and leaked a `sys.path` hack into `server.py`. Fixed via `src/uniprot_mcp/` layout.
2. **Error envelopes leaked raw exception text** to the LLM (agent-unsafe — attackers can probe internals; agents sometimes treat traces as data). Fixed via `_safe_error` indirection.
3. **Missing input validation.** `response_format`, `accession`, `query`, `ids`, `organism`, `database`, `feature_types` had no length caps or allow-lists before reaching httpx. Fixed via explicit checks.

**Top 3 strengths:**

1. Property-based + snapshot tests for the pure layer.
2. Reproducible-build discipline: SHA256-addressed fixtures, Sigstore signing, CycloneDX SBOM.
3. Clean module layering (client / formatters / server) — only needed the package wrapper.

**Maturity rating:**
- Pre-audit: **B+** (functional, tested, but with latent defects)
- Post-audit: **A−** (structurally sound; remaining P2 items are polish)

---

## Scope & method

Static review of:
- `server.py`, `client.py`, `formatters.py`
- `pyproject.toml`, `smithery.yaml`, `.well-known/mcp.json`
- `.github/workflows/*.yml`
- All tests
- `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`

No runtime execution during audit. Remediation PR includes a fresh test run (offline tiers all green; `--self-test` live against UniProt green).

---

## Findings

### Architecture & code quality

| # | Severity | Finding | Status |
|---|---|---|---|
| A1 | P0 | Top-level module names `server`, `client`, `formatters` risk site-packages collision (any other package on PyPI named `client` or `server` shadows us). Move to `src/uniprot_mcp/`. | **Fixed** — src layout |
| A2 | P0 | `py.typed` at repo root is ignored by type-checkers unless inside a package directory (PEP 561). | **Fixed** — moved to `src/uniprot_mcp/py.typed` |
| A3 | P0 | `[tool.hatch.build.targets.wheel] packages = []` + raw file `include` is non-idiomatic and produced brittle wheels. | **Fixed** — `packages = ["src/uniprot_mcp"]` |
| A4 | P0 | `sys.path.insert(0, ...)` hack in `server.py` masked the packaging bug. | **Fixed** — removed; editable install used instead |
| A5 | P1 | Broad `except Exception` in every tool returned `f"Error: {e}"` to the LLM. | **Fixed** — `_safe_error` helper logs internally, returns stable agent-safe string |
| A6 | P1 | `response_format` was accepted without validation; invalid values silently fell through to `fmt_*`, producing markdown unexpectedly. | **Fixed** — allow-list check in every tool |
| A7 | P1 | No client-side accession validation in `get_entry`, `get_sequence`, `get_features`, etc. — only `batch_entries` had it. | **Fixed** — `_check_accession` called in all accession-taking tools |
| A8 | P1 | `id_mapping` silently truncated `ids` to 100 without telling the caller. | **Fixed** — explicit `_InputError` on >100 |
| A9 | P1 | `client.id_mapping_submit` lacked retry/back-off (other client methods had it). | **Fixed** — retries on 429 / 5xx / timeout |
| A10 | P1 | `Retry-After` parser assumed delta-seconds; RFC 7231 also allows HTTP-date. | **Fixed** — `parse_retry_after` handles both, clamped |
| A11 | P1 | `formatters.py` had no type hints; `mypy --strict` was effectively unchecked for it despite being listed. | **Fixed** — full hints + `is_swissprot` helper |
| A12 | P2 | `l` used as loop variable (E741 ambiguous name). | **Fixed** — renamed to `loc` |
| A13 | P2 | Reviewed-check logic duplicated in `fmt_entry` and `fmt_search`. | **Fixed** — single `is_swissprot` helper |

### Testing

| # | Severity | Finding | Status |
|---|---|---|---|
| T1 | P0 | `tests/contract/` referenced in README + CONTRIBUTING but did not exist. | **Fixed** — directory + `test_fixture_shapes.py` added |
| T2 | P1 | `_self_test` was never exercised by a test. | **Fixed** — `test_server_tools.py::test_self_test_module_is_callable`; live run verified in CI logs |
| T3 | P1 | No test for `uniprot_search` query-construction path (organism quoting, injection-adjacent behaviour). | **Fixed** — `test_server_tools.py::test_search_quotes_multiword_organism_name` and `test_search_numeric_organism_uses_taxon_id` |
| T4 | P1 | No test that validation rejects inputs *without* hitting the network. | **Fixed** — `test_get_entry_rejects_bad_accession_without_network` asserts `respx` saw no calls |
| T5 | P1 | No test for the HTTP-date Retry-After branch. | **Fixed** — `test_retry_after.py` exercises numeric, past-date, future-date, garbage |

### CI / supply chain

| # | Severity | Finding | Status |
|---|---|---|---|
| C1 | P0 | `pip-audit --strict … \|\| true` silently masked every vulnerability hit. | **Fixed** — `\|\| true` removed |
| C2 | P0 | `smithery.yaml` referenced a non-existent `Dockerfile`. | **Fixed** — removed; `command: "uniprot-mcp"` uses the PyPI console script |
| C3 | P1 | CI did not exercise `tests/contract/`. | **Fixed** — added to the offline pytest invocation |
| C4 | P2 | GitHub Actions pinned by tag, not SHA. Scorecard flags this. | **Deferred to v0.2** — Dependabot is configured to migrate; risk contained because tag-pins come from well-known org-verified actions |
| C5 | P2 | SBOM generated in release workflow but not attested. | **Deferred to v0.2** — attestation via `actions/attest-build-provenance` requires attestation type `sbom`, available but not yet wired |
| C6 | P2 | CodeQL + OSSF Scorecard workflows fail on **private** repositories (Code Scanning is a paid feature on private personal repos). | **Deferred until public release** — workflows removed; bandit in the CI lint job still provides SAST coverage; CodeQL/Scorecard re-enable the day we flip the repo public |

### Security

| # | Severity | Finding | Status |
|---|---|---|---|
| S1 | P0 | No input length caps on `query`, `ids`, `accession`, `organism`, `database`, `feature_types`. | **Fixed** — explicit caps per field |
| S2 | P0 | Error envelopes emitted raw exception `str()` to LLM callers. | **Fixed** — `_safe_error` |
| S3 | P1 | `uniprot_search`'s `organism` parameter was concatenated into the UniProt query language without quoting for multi-word values. | **Fixed** — quoted + inner-quote neutralised |

### Documentation

| # | Severity | Finding | Status |
|---|---|---|---|
| D1 | P1 | README and CONTRIBUTING referenced `tests/contract/`. | **Fixed** — directory now exists |
| D2 | P1 | `smithery.yaml` referenced `Dockerfile`. | **Fixed** — removed |
| D3 | P2 | PyPI install instructions in README reference a package name not yet on PyPI. | **Noted** — unchanged; publish is the follow-up |

---

## What was explicitly NOT changed in this PR

- Public tool names and parameter signatures (backwards-compatible).
- Test layout beyond adding `tests/contract/` and additive test files.
- License (remains Apache-2.0).
- Version (still 0.1.0 — this is a correctness PR, not a feature PR; version bumps on the next release tag).

## Follow-ups tracked for v0.2

1. SHA-pin all GitHub Actions references (C4)
2. Wire SBOM attestation in release workflow (C5)
3. Publish first release to PyPI via Trusted Publishing
4. Add `uniprot_search` query-fuzz property test using Hypothesis
5. Add `respx`-based test that asserts `Retry-After: <http-date>` actually delays the client by the expected amount

---

## Appendix: file-by-file diff summary

```
  .github/workflows/ci.yml     | remove `|| true` from pip-audit; add tests/contract
  AUDIT.md                     | new
  pyproject.toml               | src layout; coverage source; mypy files; ruff src
  smithery.yaml                | remove Dockerfile ref; use console script
  tests/conftest.py            | remove sys.path hack
  tests/contract/*             | new (directory + fixture-shape tests)
  tests/unit/test_retry_after.py       | new
  tests/unit/test_server_validation.py | new
  tests/unit/test_server_tools.py      | new
  tests/**/*.py                | import from uniprot_mcp.* instead of flat modules
  src/uniprot_mcp/__init__.py  | new
  src/uniprot_mcp/client.py    | moved from ./client.py; HTTP-date Retry-After; id_mapping_submit retry
  src/uniprot_mcp/formatters.py| moved; full type hints; is_swissprot helper; rename `l` → `loc`
  src/uniprot_mcp/server.py    | moved; input validation; safe errors; package-qualified imports
  src/uniprot_mcp/py.typed     | moved from repo root (now PEP 561-effective)
```
