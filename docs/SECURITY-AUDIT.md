# Security audit — `uniprot-mcp` v1.0.1 pre-flip

**Audit date:** 2026-04-25
**Auditor:** Santiago Maniches (with mechanical assistance from Claude Opus 4.7)
**Target:** branch `hardening-v2` head `46cf081`, 38 tools, 357 offline + 4 live integration tests (audit anchored at this commit; subsequent commits expand to 41 tools and 446 offline + 42 live tests as of commit `01ab7a8` — see CHANGELOG)
**License:** Apache-2.0

This is the formal security audit performed in the run-up to the
public flip. It complements [`docs/THREAT_MODEL.md`](THREAT_MODEL.md)
(architectural threats and mitigations) by running each defended
property through a mechanical check and recording the receipts.

---

## 1. Static-analysis matrix

| Check | Tool | Scope | Result |
|---|---|---|---|
| CVE in runtime deps | `pip-audit --strict` | `httpx`, `mcp` (resolved transitive set) | **No known vulnerabilities** |
| Source-level security smells | `bandit -r src/uniprot_mcp` (LOW-severity, all confidences) | 3,938 lines of code | **0 issues** at any severity |
| Type safety | `mypy --strict` (project config) | `src/uniprot_mcp/*.py` (6 source files) | **clean** |
| Lint correctness | `ruff check` | src + tests | **clean** |
| Format consistency | `ruff format --check` | src + tests | **clean** |

---

## 2. Manual code-review audit

### 2.1 Dangerous-pattern grep

| Pattern | Where searched | Hits |
|---|---|---|
| `http://` (cleartext URL) | `src/uniprot_mcp/` | **0** |
| `eval(` / `exec(` (raw, not `re.compile`) | `src/uniprot_mcp/` | **0** |
| `pickle` (serialization with code-execution risk) | `src/uniprot_mcp/` | **0** |
| `subprocess.` / `os.system` / `os.popen` | `src/uniprot_mcp/` | **0** |
| `shell=True` | `src/uniprot_mcp/` | **0** |
| `yaml.load(` (vs `yaml.safe_load`) | `src/uniprot_mcp/` | **0** |
| `open(` (file-system surface) | `src/uniprot_mcp/` | **0**[^1] |
| `__import__(` (dynamic import) | `src/uniprot_mcp/` | **0** |
| Bare `except:` | `src/uniprot_mcp/` | **0** |

[^1]: The `cache.py` module performs file I/O via `pathlib.Path.read_text`/`write_text` and `tempfile.NamedTemporaryFile`. Both are safer than raw `open()` but the pattern is acknowledged: cache writes only when the user opts in via `UNIPROT_MCP_CACHE_DIR`, and atomic-write via `os.replace` is enforced.

### 2.2 Network surface

| Origin | Where declared | Tools that consult it |
|---|---|---|
| `https://rest.uniprot.org` | `BASE_URL` constant in `src/uniprot_mcp/client.py:38` | All 32 UniProt-resident tools |
| `https://alphafold.ebi.ac.uk` | `ALPHAFOLD_API_BASE` constant in `src/uniprot_mcp/client.py:42` | `uniprot_get_alphafold_confidence` |
| `https://eutils.ncbi.nlm.nih.gov/entrez/eutils` | `NCBI_EUTILS_BASE` constant in `src/uniprot_mcp/client.py:43` | `uniprot_resolve_clinvar` |

Every origin is HTTPS. Adding a new origin requires modifying `client.py` *and* `THREAT_MODEL.md` *and* `PRIVACY.md` in the same commit, per the policy in [`docs/THREAT_MODEL.md` §T3b](THREAT_MODEL.md#t3b-cross-origin-allowlist-for-non-uniprot-endpoints).

### 2.3 Timeout coverage

Every `httpx.AsyncClient` instantiation in the codebase carries an explicit `httpx.Timeout(...)`:

| Location | Timeout |
|---|---|
| `src/uniprot_mcp/client.py:289` (the singleton `UniProtClient` shared by all UniProt-resident tools) | `httpx.Timeout(TIMEOUT)` where `TIMEOUT = 30.0` |
| `src/uniprot_mcp/client.py:499` (`get_clinvar_records` ephemeral client) | `httpx.Timeout(TIMEOUT)` |
| `src/uniprot_mcp/client.py:552` (`get_alphafold_summary` ephemeral client) | `httpx.Timeout(TIMEOUT)` |
| `src/uniprot_mcp/server.py:1619` (`provenance_verify` ephemeral client) | `httpx.Timeout(30.0)` |

There is no path where a network call escapes the 30-second timeout.

### 2.4 Retry budget

| Bound | Constant | Enforced in |
|---|---|---|
| Maximum retries per request | `MAX_RETRIES = 3` | `_req` and `id_mapping_submit` |
| Maximum server-dictated `Retry-After` wait | `MAX_RETRY_AFTER_SECONDS = 120.0` | `parse_retry_after` |
| `id_mapping_results` polling cap | 30 iterations × 1 s | hard-coded loop |

A client that hits 429 or 5xx forever still terminates: `MAX_RETRIES + 1` attempts, then `RuntimeError("Request failed after 4 attempts")` propagates and the tool's `_safe_error` envelope kicks in.

### 2.5 Input validation matrix

Every tool that accepts an identifier validates it before any HTTP call. The full coverage:

| Tool | Validator | Anchored regex |
|---|---|---|
| `uniprot_get_entry` / `_get_sequence` / `_get_features` / `_get_variants` / `_get_go_terms` / `_get_cross_refs` | `_check_accession` | `\A(?:[OPQ][0-9][A-Z0-9]{3}[0-9]\|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})\Z` |
| `uniprot_get_keyword` | `_check_keyword_id` | `\AKW-[0-9]{4}\Z` |
| `uniprot_get_subcellular_location` | `_check_subcellular_location_id` | `\ASL-[0-9]{4}\Z` |
| `uniprot_get_uniref` | `_check_uniref_id` | `\AUniRef(?:50\|90\|100)_…\Z` |
| `uniprot_get_uniparc` | `_check_uniparc_id` | `\AUPI[A-F0-9]{10}\Z` |
| `uniprot_get_proteome` | `_check_proteome_id` | `\AUP[0-9]{9,11}\Z` |
| `uniprot_get_citation` | `_check_citation_id` | `\A[0-9]{1,12}\Z` |
| `uniprot_features_at_position` (position) | `_check_position` | int ∈ [1, 100000] |
| `uniprot_lookup_variant` (change) | `_parse_variant_change` | `\A[A-Z][1-9][0-9]{0,4}[A-Z*]\Z` |
| `uniprot_resolve_clinvar` (change, optional) | `_parse_variant_change` | same |
| `uniprot_search` / etc. (free-text query) | `_check_len("query", value, MAX_QUERY_LEN=500)` | length cap; chars not constrained |
| `uniprot_search` (organism filter) | `_check_len("organism", value, MAX_ORGANISM_LEN=100)` + double-quote sanitise | length cap |
| `uniprot_provenance_verify` (URL) | `_check_len("url", value, MAX_PROVENANCE_URL_LEN=1000)` + `startswith("https://rest.uniprot.org/")` | scheme + host pinned |
| `uniprot_replay_from_cache` (URL) | `_check_len` | length cap; cache lookup is local-only |

Every regex uses `\A...\Z` anchors — no `re.MULTILINE` slip-pasts. Length caps are constants in `src/uniprot_mcp/server.py:99-128` so they show up at one location for review.

### 2.6 SSRF posture

Two controlled redirect surfaces:

1. **`id_mapping_results` redirect**: when UniProt returns `redirectURL` in the polling response, the URL is dispatched through the *same* `httpx.AsyncClient` whose `base_url` is hardcoded to `https://rest.uniprot.org`. httpx's redirect policy refuses cross-origin paths that are not absolute under that origin. (Tracked for v1.1: explicit allowlist check; current state is mitigated by httpx's same-origin enforcement.)
2. **Cross-origin allowlist**: the only other origins consulted are `alphafold.ebi.ac.uk` and `eutils.ncbi.nlm.nih.gov`, each declared by named constant and used in exactly one method (`get_alphafold_summary`, `get_clinvar_records`).

A compromise of either upstream origin would let an attacker return malicious metadata. The provenance subsystem records source URL + canonical SHA-256 so a poisoned answer is *detectable* via `uniprot_provenance_verify` — but not *prevented*. (Detection is the security claim; prevention requires upstream-side mitigations we cannot ship.)

### 2.7 Error-channel safety

`_safe_error` (`src/uniprot_mcp/server.py:135-160`) is the single chokepoint for tool error responses:

- `_InputError` (our own validation type) is forwarded verbatim — agent-actionable.
- `ReleaseMismatchError` (a controlled type from `client.py`) is rewritten into the standard format with the env-var name to unset; both pinned and observed release values are surfaced because they originate from our own state plus an upstream header (no raw stack-trace contents).
- Any other `Exception` produces the canonical message `"Error in <tool>: upstream request failed; see server logs for details."` — the actual exception is `logger.exception`-ed to stderr but never reaches the LLM.

Pinned by tests:

- `tests/unit/test_server_validation.py::test_safe_error_hides_internal_exception_text` — asserts `0xdeadbeef` and `sensitive` words never appear in the agent-visible error envelope.
- `tests/unit/test_pin_release.py::test_safe_error_formats_release_mismatch_distinctly` — asserts the release-mismatch path.

### 2.8 Provenance integrity

- Every successful request sets `client.last_provenance` immediately after `raise_for_status` succeeds. A failing request never overwrites a prior successful provenance — pinned by `tests/unit/test_provenance.py::test_client_last_provenance_unchanged_after_4xx`.
- `canonical_response_hash` parses JSON → re-serialises with `sort_keys=True` + compact separators → SHA-256 the canonical UTF-8 bytes. Within-release key-order changes do not break verification.
- `uniprot_provenance_verify` uses a fresh `httpx.AsyncClient` so the verifier itself is *not* subject to the singleton's pin-release config. A pinned-release client can still verify against a different release.

---

## 3. Cryptographic-commitment audit

| Property | Evidence |
|---|---|
| Pre-registered benchmark prompts (30) | `tests/benchmark/prompts.jsonl` on `main`; immutable from b1549f6 onward |
| Per-prompt expected-answer hashes (30, all unique) | `tests/benchmark/expected.hashes.jsonl` on `main` |
| Cryptographic round-trip | `python tests/benchmark/verify.py expected.jsonl expected.hashes.jsonl` → `OK: 30 commitments verified` |
| Live-REST third-party reproducibility | `python tests/benchmark/verify_answers.py expected.jsonl` → `OK: all 30 prompts verified against https://rest.uniprot.org` (re-verified 2026-04-25) |

The plaintext `expected.jsonl` is held local-only per `.gitignore`. Three tests pin this rule (`tests/contract/test_benchmark_integrity.py`).

---

## 4. Supply-chain audit

### 4.1 Dependencies

Production runtime: only `httpx >= 0.27` and `mcp >= 1.2`. Test extras: `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-socket`, `respx`, `hypothesis`, `syrupy`. Dev extras: `ruff`, `mypy`, `bandit`, `pip-audit`, `pre-commit`. Docs extras: `mkdocs`, `mkdocs-material`. All from PyPI-reputable maintainers.

Dependabot watches `pip` weekly (per `.github/dependabot.yml`).

### 4.2 GitHub Actions

Every `uses:` reference in every workflow file is **SHA-pinned** to the resolved commit, with the human-readable tag preserved as a trailing comment. Dependabot watches the `github-actions` ecosystem weekly to bump the pins safely (commit `843ace5`).

### 4.3 Release artefacts

`release.yml` (post-billing-reset) attaches:

- **SLSA build-provenance attestation** via `actions/attest-build-provenance@v1`.
- **CycloneDX SBOM** generated by `cyclonedx-py requirements`.
- **SBOM attestation** via `actions/attest-sbom@v1` — the SBOM itself is provenance-tied to the artefact.
- **Sigstore keyless signature** via `sigstore/gh-action-sigstore-python@v3.0.0`.
- **PyPI Trusted Publishing** — no long-lived API tokens.

Every release artefact is independently verifiable post-flip:

```bash
gh attestation verify dist/*.whl --repo smaniches/uniprot-mcp
gh attestation verify dist/*.whl --repo smaniches/uniprot-mcp --predicate-type https://cyclonedx.org/bom
python -m sigstore verify identity --cert-identity \
    'https://github.com/smaniches/uniprot-mcp/.github/workflows/release.yml@refs/tags/v1.0.1' dist/*.whl
```

---

## 5. Privacy posture

`uniprot-mcp` is a stateless gateway. No PII collected, no analytics SDK, no persistent session, no telemetry, no cookies. Three third parties:

| Third party | What it sees | Necessity |
|---|---|---|
| `rest.uniprot.org` | source IP, User-Agent (`uniprot-mcp/1.1.3`), request path/query | Required — this is what the server proxies |
| `alphafold.ebi.ac.uk` | source IP, User-Agent, the UniProt accession in the path | Optional — used only by `uniprot_get_alphafold_confidence` |
| `eutils.ncbi.nlm.nih.gov` | source IP, User-Agent, the gene symbol (and optional HGVS shorthand) in query | Optional — used only by `uniprot_resolve_clinvar` |

Full privacy notice: [`PRIVACY.md`](https://github.com/smaniches/uniprot-mcp/blob/main/PRIVACY.md).

---

## 6. Operational maturity

| Artefact | Purpose |
|---|---|
| [`docs/THREAT_MODEL.md`](THREAT_MODEL.md) | 12-threat STRIDE walk + cross-origin allowlist policy |
| [`docs/INCIDENT_POLICY.md`](INCIDENT_POLICY.md) | What triggers a postmortem; blameless discipline; sunset rule |
| [`docs/POSTMORTEM_TEMPLATE.md`](https://github.com/smaniches/uniprot-mcp/blob/main/docs/POSTMORTEM_TEMPLATE.md) | Header / timeline / root-cause / impact / detection / resolution / follow-up / lessons / 2030-compliance-officer view |
| [`docs/INCIDENT_LOG.md`](INCIDENT_LOG.md) | Append-only, currently empty (project pre-public) |
| `tests/contract/test_incident_policy.py` (5 tests) | Drift prevention — every log entry must point at a real file; every postmortem file must be referenced from the log |

---

## 7. Findings

**Zero P0/P1 findings.** Two P3 hardening items deferred (already tracked elsewhere):

| Severity | Finding | Tracking | Mitigation while open |
|---|---|---|---|
| P3 | Explicit `redirectURL` allowlist in `id_mapping_results` (currently relies on httpx's same-origin redirect default) | `THREAT_MODEL.md` §T3 — "Deferred hardening" | httpx's redirect policy already refuses cross-origin paths under a `base_url`-pinned client |
| P3 | NFKC Unicode normalisation on free-text inputs (`query`, `organism`) | `THREAT_MODEL.md` §T12 | All identifier validation uses ASCII subsets with `\A...\Z` anchors; impact limited to free-text query construction |

Both are documented for v1.1.

---

## 8. Conclusion

The static-analysis matrix is fully green. The manual review found no defects. The supply chain, cross-origin, validation, retry, and error-channel surfaces all carry their own automated tests pinning their behaviour. The release-artefact verification chain (SLSA + Sigstore + SBOM + Trusted Publishing) is wired and ready to fire on the v1.0.1 tag once GitHub Actions billing resets.

The defended posture matches the documented threat model.

— *Signed off by Santiago Maniches, ORCID 0009-0005-6480-1987, 2026-04-25.*
