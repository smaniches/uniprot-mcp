# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [1.3.0](https://github.com/smaniches/uniprot-mcp/compare/v1.2.6...v1.3.0) (2026-07-13)


### Features

* **evidence:** grade ECO codes into a 0-100 evidence-confidence score ([#133](https://github.com/smaniches/uniprot-mcp/issues/133)) ([67b2b27](https://github.com/smaniches/uniprot-mcp/commit/67b2b27718284dc63221816363231ae6d1c26a73))
* **server:** add per-parameter descriptions and usage guidance to all tools ([#132](https://github.com/smaniches/uniprot-mcp/issues/132)) ([2dcc5ff](https://github.com/smaniches/uniprot-mcp/commit/2dcc5ffb406fda8ae7a62a53b66c51b19fab06dd))
* **server:** finish per-parameter descriptions on the four search tools ([#134](https://github.com/smaniches/uniprot-mcp/issues/134)) ([e29aa5b](https://github.com/smaniches/uniprot-mcp/commit/e29aa5b5af0a1aba9acc4337f8e830cd3d6d60dd))


### Bug Fixes

* list 1.3.x as a supported series in SECURITY.md ([#135](https://github.com/smaniches/uniprot-mcp/issues/135)) ([76ae133](https://github.com/smaniches/uniprot-mcp/commit/76ae1330053e1c874bdb48df9670dc3913ef38c7))
* **tests:** stop pinning live ID-mapping test to broken Gene_Name field ([#130](https://github.com/smaniches/uniprot-mcp/issues/130)) ([08fbf67](https://github.com/smaniches/uniprot-mcp/commit/08fbf67a290356077a860a79a8e88539de7e06c2))

## [1.2.6](https://github.com/smaniches/uniprot-mcp/compare/v1.2.5...v1.2.6) (2026-07-06)


### Bug Fixes

* correct SECURITY.md supported-versions table to 1.2.x ([#128](https://github.com/smaniches/uniprot-mcp/issues/128)) ([1dbac8e](https://github.com/smaniches/uniprot-mcp/commit/1dbac8eb540e922ff408abddaaafbbe8829461f3))

## [1.2.5](https://github.com/smaniches/uniprot-mcp/compare/v1.2.4...v1.2.5) (2026-06-29)


### CI/CD

* **release:** auto-publish server.json to the MCP Registry on release ([#122](https://github.com/smaniches/uniprot-mcp/issues/122)) ([108559c](https://github.com/smaniches/uniprot-mcp/commit/108559c790da529400899841da991217a1e1c092))

## [1.2.4](https://github.com/smaniches/uniprot-mcp/compare/v1.2.3...v1.2.4) (2026-06-29)


### CI/CD

* **integration:** ride out transient UniProt blips and make failures diagnosable ([#119](https://github.com/smaniches/uniprot-mcp/issues/119)) ([60eed32](https://github.com/smaniches/uniprot-mcp/commit/60eed3211c9967a3a0500b0e05a802ae31ec4383))

## [1.2.3](https://github.com/smaniches/uniprot-mcp/compare/v1.2.2...v1.2.3) (2026-06-23)


### Bug Fixes

* **release-verify:** compare Zenodo version without the v prefix ([#115](https://github.com/smaniches/uniprot-mcp/issues/115)) ([e381ddd](https://github.com/smaniches/uniprot-mcp/commit/e381ddd090e6a12710c94c56ccf7513f79082eda))


### CI/CD

* scope release-please token permissions to job level (Scorecard TokenPermissions) ([#117](https://github.com/smaniches/uniprot-mcp/issues/117)) ([6a9e569](https://github.com/smaniches/uniprot-mcp/commit/6a9e569f1344923f1b267db885f8979894586311))

## [1.2.2](https://github.com/smaniches/uniprot-mcp/compare/v1.2.1...v1.2.2) (2026-06-21)


### Documentation

* **citation:** add v1.2.1 Zenodo version DOI ([#94](https://github.com/smaniches/uniprot-mcp/issues/94)) ([4c5803a](https://github.com/smaniches/uniprot-mcp/commit/4c5803a60e8760544e23b0e352a123223d6bf187))


### CI/CD

* harden lock-refresh (upload pristine before exec) and correct lock security docs ([#112](https://github.com/smaniches/uniprot-mcp/issues/112)) ([5bcb045](https://github.com/smaniches/uniprot-mcp/commit/5bcb0455ed9e4b9bbe3424f6e6aac137e1a1a4bc))
* scope Dependabot to direct deps + add monthly dev-lock maintenance ([#107](https://github.com/smaniches/uniprot-mcp/issues/107)) ([c123ff1](https://github.com/smaniches/uniprot-mcp/commit/c123ff10bc33e587507c8f1e149cf3d265a5b266))
* stop Dependabot touching the uv lock; isolate lock-refresh write creds ([#110](https://github.com/smaniches/uniprot-mcp/issues/110)) ([4410422](https://github.com/smaniches/uniprot-mcp/commit/4410422356876f3a98696ce56584b49195bbb29f))

## [1.2.1](https://github.com/smaniches/uniprot-mcp/compare/v1.2.0...v1.2.1) (2026-06-17)


### Documentation

* **citation:** add v1.2.0 Zenodo version DOI and align release date ([#90](https://github.com/smaniches/uniprot-mcp/issues/90)) ([e5a5e3b](https://github.com/smaniches/uniprot-mcp/commit/e5a5e3b722decd272ccce0ec7315a5c8a3ddcfff))
* soften two overstated phrasings ([#92](https://github.com/smaniches/uniprot-mcp/issues/92)) ([e874dec](https://github.com/smaniches/uniprot-mcp/commit/e874dec4078c97161c8a2d45e7fa1c19279a5b5f))

## [1.2.0](https://github.com/smaniches/uniprot-mcp/compare/v1.1.10...v1.2.0) (2026-06-17)


### Features

* **server:** raise ToolError so failed tool calls set isError ([#88](https://github.com/smaniches/uniprot-mcp/issues/88)) ([e8bbf53](https://github.com/smaniches/uniprot-mcp/commit/e8bbf53835e846861b87670804da7556c7172487))


### Bug Fixes

* **client:** scope provenance per-request via ContextVar ([#86](https://github.com/smaniches/uniprot-mcp/issues/86)) ([2aaa112](https://github.com/smaniches/uniprot-mcp/commit/2aaa112d127bd5c7b7d8f2f4c8e37936d934851e))


### Documentation

* **atlas:** make atlas metadata version-agnostic and cite the concept DOI ([#87](https://github.com/smaniches/uniprot-mcp/issues/87)) ([507b730](https://github.com/smaniches/uniprot-mcp/commit/507b730afddcccd0f621e6acc409548bbb7a763b))
* **citation:** add v1.1.10 Zenodo version DOI ([#84](https://github.com/smaniches/uniprot-mcp/issues/84)) ([05b89c2](https://github.com/smaniches/uniprot-mcp/commit/05b89c294418346f84f6a746104139410e5490c2))

## [1.1.10](https://github.com/smaniches/uniprot-mcp/compare/v1.1.9...v1.1.10) (2026-06-16)


### Bug Fixes

* **cache:** unlink temp file on write failure to keep writes atomic ([#77](https://github.com/smaniches/uniprot-mcp/issues/77)) ([c21b554](https://github.com/smaniches/uniprot-mcp/commit/c21b554f764381db18737f8213b1680f8d774697))
* **client:** sanitize Retry-After, raise on terminal id-mapping jobs, handle AlphaFold 404 ([#80](https://github.com/smaniches/uniprot-mcp/issues/80)) ([5ceb94e](https://github.com/smaniches/uniprot-mcp/commit/5ceb94e771b0717d6154efb1394803845f227d7a))
* explicit utf-8 read in README receipts snippet (Windows-safe) ([#62](https://github.com/smaniches/uniprot-mcp/issues/62)) ([147a549](https://github.com/smaniches/uniprot-mcp/commit/147a54999f911bc775e9090335b0d07f4fa59597))
* **formatters:** GO aspect filter in JSON + unknown positions render as '?' ([#79](https://github.com/smaniches/uniprot-mcp/issues/79)) ([5a7ff11](https://github.com/smaniches/uniprot-mcp/commit/5a7ff110fadb7d40f6f776b9d2284c21eabc972a))
* **proteinchem:** correct swapped Trp/Tyr 280 nm extinction coefficients ([#73](https://github.com/smaniches/uniprot-mcp/issues/73)) ([a2f6fd7](https://github.com/smaniches/uniprot-mcp/commit/a2f6fd70fa3cabf1f6d123a0411093f35a4fc172))
* **proteinchem:** count residues per-character to avoid fabricating residues ([#78](https://github.com/smaniches/uniprot-mcp/issues/78)) ([ed74a38](https://github.com/smaniches/uniprot-mcp/commit/ed74a38b0299f8b6cb236f50a2024c6fc59faf0c))
* provenance integrity and cache documentation honesty ([#74](https://github.com/smaniches/uniprot-mcp/issues/74)) ([e0b8c0f](https://github.com/smaniches/uniprot-mcp/commit/e0b8c0f72c117b4a101d3be682bb94de98b0f16e))


### Documentation

* **replicate:** resolve latest published version dynamically; correct stale version examples ([#82](https://github.com/smaniches/uniprot-mcp/issues/82)) ([939844e](https://github.com/smaniches/uniprot-mcp/commit/939844e6948d6a58fcdf0139928b3bc910e7c950))
* verifiable-provenance receipts demo, front and center ([#61](https://github.com/smaniches/uniprot-mcp/issues/61)) ([ed77002](https://github.com/smaniches/uniprot-mcp/commit/ed77002c1873c5933ef6e1a41066fcc0f7c44260))


### CI/CD

* add docstring-coverage gate (interrogate) ([#71](https://github.com/smaniches/uniprot-mcp/issues/71)) ([d2eb81e](https://github.com/smaniches/uniprot-mcp/commit/d2eb81e41d442c0c8e24e3d32fe8c9fef561a30a))
* shard mutation testing + weekly schedule ([#68](https://github.com/smaniches/uniprot-mcp/issues/68)) ([fb93d8b](https://github.com/smaniches/uniprot-mcp/commit/fb93d8bc0bedd9d3bc4c147e583559faea2df2ce))

## [Unreleased]


## [1.1.9] - 2026-06-08

### Added
- **MCP Registry `server.json` (2025-12-11 schema).** The registry
  manifest now validates against
  `https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json`:
  the version is carried at the top level and in `packages[0].version`,
  the PyPI distribution is named via `identifier` /`registryType`, and
  the launch is `runtimeHint: "uvx"` (the registry auto-appends
  `--from <identifier>@<version>`).
- **`mcp-name` ownership marker.** `README.md` — the PyPI long
  description — carries the hidden
  `<!-- mcp-name: io.github.smaniches/uniprot-mcp -->` marker so the MCP
  Registry can verify ownership of the published wheel against the
  declared server name.
- **`uniprot-mcp-server` console-script alias.** `[project.scripts]` now
  exposes `uniprot-mcp-server` alongside the existing `uniprot-mcp`
  entry point (both target `uniprot_mcp.server:main`), so a registry
  launch that derives the executable from the PyPI distribution name
  resolves.
- **Contract-test and version-checker alignment for the new schema.**
  `tests/contract/test_manifest_consistency.py` reads the top-level
  `version` and the `packages[pypi].identifier`, and
  `scripts/check_versions.py` (with its `tests/contract/test_version_consistency.py`
  driver) matches the camelCase fields — both updated for the
  2025-12-11 shape.

### Changed
- **Test coverage restored to 100% line + branch and the gate set to
  enforce it.** Coverage had drifted from the v1.0.0 100% to 92.20%
  across the v1.1.x clinical/biomedical work. New assertion-bearing
  tests (`tests/unit/test_coverage_gaps_client_chem.py`,
  `test_coverage_gaps_formatters.py`, `test_coverage_gaps_server.py`)
  exercise every previously-uncovered arc, and `[tool.coverage.report]`
  `fail_under` is raised from 91 to 100. The new coverage tests bring the
  offline suite from 749 to **874 tests** (`pytest --collect-only`); the
  live integration suite is unchanged at 44. A small number of
  genuinely-unreachable arcs carry a justified `# pragma` for
  import-time / defensive fallbacks (two in `client.py`, one pre-existing
  in `server.py`), each annotated inline. No source behaviour changed.
- **`_self_test()` now counts tools via the public MCP API.** The
  self-test previously reached into FastMCP internals
  (`mcp._tool_manager._tools`) to enumerate registered tools. It now uses
  the public, async `mcp.list_tools()` (driven through the `asyncio.run`
  already present in the function), so the check no longer depends on a
  private attribute that can change between SDK releases. Behaviour is
  unchanged: the self-test returns 0 on a healthy server and 1 when an
  expected tool is missing. The two coverage tests that monkeypatched the
  former internals were updated to drive the public accessor.

### Fixed
- **`_extract_provenance` now reads the response's accept header
  directly, dropping a misleading None-guard and its coverage pragma.**
  The previous `if response.request is not None:` check implied the
  request could be `None`, but `httpx.Response.request` is a property
  that *raises* `RuntimeError` when unset and never returns `None`. The
  guard's False arc was therefore unreachable, and the surrounding
  `# pragma` excluded the reachable accept-header read from the coverage
  gate. Because the same function also builds the `url` field from
  `response.url` — which httpx derives from `response.request` — the
  request is guaranteed present whenever the function runs, so the accept
  header is now read directly with no guard and no pragma. Covered by the
  existing `test_extract_provenance_reads_request_accept_header`.
  Behaviour is unchanged. Resolves automated-review comments on PR
  #57/#58.
- **Added `tests/unit/test_coverage_gaps_formatters.py` to the
  `formatters` mutation-testing runner.** The formatter coverage tests
  added above were not in the formatters matrix entry of
  `.github/workflows/mutation.yml`, so formatter mutants they cover were
  not exercised during mutation analysis. The file is now included.
- **Added the `Documentation` project URL.** `[project.urls]` now points
  to the published docs site (`https://smaniches.github.io/uniprot-mcp/`),
  so PyPI surfaces a Documentation link.
- **Added the differentiating capabilities to the PyPI keywords.**
  `provenance`, `reproducibility`, `alphafold`, `clinvar`, and
  `drug-discovery` were already in `.zenodo.json` but absent from the
  `[project]` keywords, so PyPI search did not surface the package for
  those terms. They are now in both, keeping the two metadata files
  aligned.
- **Reconciled the live test count across `main`-facing docs.** The
  README test badge, `docs/index.md`, `REVIEWER.md`, `docs/CLAIMS.md`
  (C6), and the `docs/SECURITY-AUDIT.md` "on `main`" aside still read
  749 offline; the current `pytest --collect-only` figure is 874. The
  historical `[1.1.8]` changelog entry below is left at 749 — the count
  that release actually shipped.
- **Corrected the `proteinchem` module header.** The header listed
  "Monoisotopic residue masses", but the `_RESIDUE_MASS` table holds
  *average* residue masses (e.g. G = 57.0519 average vs 57.02146
  monoisotopic; `_WATER` = 18.01528 average), consistent with
  `molecular_weight()`'s "Average molecular weight" docstring. The header
  and the table comment now read "Average residue masses". No values
  changed — only their description.
- **Corrected the third-party benchmark verification overclaim.** The
  v1.1.3 entry below (and the docs/scripts it shipped) described
  `tests/benchmark/verify_against_hashes.py` as re-deriving each Tier A /
  Tier B answer and hash-matching it against the committed
  `expected.hashes.jsonl`. That comparison could never match: the
  committed digest is sealed over `{prompt_id, answer, rationale}` (see
  `seal.py`) while the tool hashed `{prompt_id, answer}` only, so it
  failed all 28 Tier A/B prompts by construction. The tool is now an
  informational live answer-reproducibility check (re-derives and prints
  every answer; exit 0, exit 1 only on drift between
  `expected.hashes.jsonl` and the derivation pipeline) and no longer
  claims a cryptographic match. `README.md`, `OVERVIEW.md`, `REVIEWER.md`,
  `docs/CLAIMS.md`, `tests/benchmark/README.md`, `tests/benchmark/AUDIT.md`,
  and both `scripts/replicate.*` were corrected to state that the full
  cryptographic check is the maintainer path (`verify.py` +
  `verify_answers.py` with the local `expected.jsonl`). The genuine 30/30
  maintainer-path result of 2026-04-26 is unaffected and retained. No
  package runtime behaviour changed.


## [1.1.8] - 2026-06-04

### Fixed
- **`uniprot_get_citation` no longer fails on citations with an empty
  `citationCrossReferences` list.** `fmt_citation` evaluated
  `citationCrossReferences[0]` as the eager default of a `.get()` call,
  raising `IndexError` whenever the list was present but empty — which
  the tool's error envelope then surfaced as a misleading "upstream
  request failed". The id now derives from the cross-reference only when
  the list is non-empty, matching the guard `fmt_citation_search`
  already used. Regression tests added in `tests/unit/test_formatters.py`.
- **Corrected the example identifier in the `uniprot_get_citation`
  docstring.** The previous example, `7649814`, is absent from UniProt's
  citations index (`GET /citations/7649814` returns HTTP 404), so the
  documented example resolved to the tool's error envelope. Replaced with
  `9840937`, a literature reference recorded on the p53 entry and verified
  to return HTTP 200.

### Changed
- **The live integration suite is now executable outside CI.** The offline
  test configuration pins `--disable-socket --allow-hosts=127.0.0.1,::1`;
  pytest-socket enforces the host allow-list with a session-global guard on
  `socket.socket.connect` that `enable_socket()` does not remove, so the
  suite previously succeeded only under the `--override-ini` invocation in
  `integration.yml`. The per-item `conftest` hook now executes `trylast`
  (after pytest-socket's own setup) and calls `_remove_restrictions()`, so
  `nox -s integration` and a direct `pytest --integration` reach the live
  API. Offline network isolation is unchanged — the guard is reinstated
  before every test and lifted only for items marked `integration`.
- **Documentation accuracy pass.** Replaced the self-applied
  "reference-quality" descriptor with factual phrasing across `README`,
  the docs site, `server.json`, `.well-known/mcp.json`, `ARCHITECTURE.md`,
  `CONTRIBUTING.md`, and `SUPPORT.md`; aligned the `docs/index.md` citation
  title with `CITATION.cff`. Reconciled the test counts in `README.md`,
  `OVERVIEW.md`, `REVIEWER.md`, `docs/index.md`, `docs/CLAIMS.md`, and
  `docs/SECURITY-AUDIT.md` to the current `pytest --collect-only` figures
  (749 offline + 44 live integration).


## [1.1.7] - 2026-05-24

Provenance-verification fix + repo hygiene. No changes to the MCP tool
surface or query behaviour.

### Fixed
- **Provenance replay now records and honours the `Accept` header**
  (#38). Verification requests that omitted or mismatched the header
  could produce content-type mismatches against the sealed response.
- **Scorecard: cleared two Pinned-Dependencies findings** in the
  release-verify workflow (#34).

### Changed
- `scripts/check_versions.py` refactored to use `tomllib` and safer
  `.get()` key access (#33).
- Documentation accuracy pass: fixed overclaims, synced stale test
  counts, softened version-control vernacular (#35).

## [1.1.6] - 2026-05-17

Release-chain durability + repo polish. **No production code-path
changes** to any module under `src/uniprot_mcp/`; the tool surface,
provenance contracts, error envelopes, and HTTP behaviour are
unchanged from v1.1.5.

### Added
- **`scripts/check_versions.py`** — single-source-of-truth version
  check. `pyproject.toml`'s `[project].version` is canonical; the
  script asserts every other file naming the version (`CITATION.cff`,
  `server.json` ×2, `.well-known/mcp.json`, the
  `tests/unit/test_client_mutation_killers.py` UA pin) agrees
  exactly, and supports `--fix` to propagate the canonical version
  on a bump.
- **`tests/contract/test_version_consistency.py`** — the contract
  test that runs the version-consistency script under pytest, so CI
  fails closed on drift.
- **`tests/contract/test_changelog_has_current_version.py`** —
  asserts `CHANGELOG.md` carries a `## [X.Y.Z]` heading for the
  current `pyproject.toml` version. Catches "silent version bump"
  before a tag push starts the release chain. Closes the class of
  regression that bit v1.1.4 (UA test pin desync) and v1.1.5
  (provenance repair).
- **`.github/workflows/release-verify.yml`** — fires on
  `release: [published]`; verifies, with retries, that every link in
  the release chain landed: PyPI publish, GitHub Release assets
  (sdist + wheel + sbom + sigstore), SLSA build-provenance via
  `gh attestation verify`, and a Zenodo version DOI under concept
  `10.5281/zenodo.20109942`. On failure opens a `release-drift`
  issue (same pattern as the nightly `integration.yml`).
- **`docs/RELEASE.md`** — end-to-end release runbook: the four-link
  chain, the manual-once Zenodo + PyPI Trusted-Publisher setup,
  per-symptom troubleshooting table, and the "never re-push a tag"
  rule.
- **`.github/CODEOWNERS`** — single `* @smaniches` line so future
  PRs auto-request the maintainer.
- **Pre-commit hook** wiring for `check_versions.py` (local hook,
  `language: system`, no extra config file).

### Changed
- **README test-count badge** refreshed from `742 offline + 42 live`
  to `744 offline + 42 live` to reflect the two new contract tests
  added in this release.
- **Historical planning docs archived under `docs/archive/`** for
  audit trail: `docs/PENDING_V1.md`, top-level
  `RELEASE_AUDIT_v1.1.3.md`, and `docs/MERGE_PLAN.md`. None of them
  describe current-state; the README + `CHANGELOG.md` + new
  `docs/RELEASE.md` are the live references. `mkdocs.yml` excludes
  `archive/*.md` from the published site; nav swaps the obsolete
  "Merge plan" entry for the new "Release runbook" entry.

### Dependencies
- `chore(deps): bump github/codeql-action from 4.35.4 to 4.35.5`
  (PR #31, merged).

### Supply chain
- Release artifacts include CycloneDX SBOM metadata, Sigstore
  signing, SLSA build provenance, and PyPI Trusted-Publishing
  provenance (unchanged from v1.1.5).
- `release-verify.yml` now provides automated proof that all four
  links of the release chain landed, instead of trusting the
  fire-and-forget exit codes.


## [1.1.5] - 2026-05-10

### Changed
- Published release artifacts for `uniprot-mcp-server` 1.1.5.

### Supply chain
- Release artifacts include CycloneDX SBOM metadata and Sigstore/PyPI provenance.
- PyPI provenance for 1.1.5 records publication from `refs/tags/v.1.1.5` at commit `a8013d41047d66ecfac20f36f300e2bbf0510fab`.
- The canonical release tag is `v1.1.5`; the dotted compatibility tag `v.1.1.5` is retained only to preserve end-to-end provenance verification for the PyPI attestation chain.

## [1.1.4] - 2026-05-08

### Fixed
- client.py: broaden importlib.metadata exception catch from
  PackageNotFoundError to Exception so a corrupt or ambiguous
  dist-info (e.g. two dist-info directories present simultaneously)
  does not emit a DeprecationWarning that ilterwarnings = error
  converts into a collection error across all 26 test modules.
- .gitattributes: add explicit *.tsv text eol=lf rule to prevent
  CRLF checkout of atlas TSV files on Windows, which caused
  	est_every_manifest_sha256_matches_file to fail on Windows CI.
## [1.1.3] - 2026-05-05

Trust-repair patch. Documentation, correctness, and atlas re-sealing
only — **no production code-path changes** beyond the User-Agent
version string. No tool surface change. No behaviour change for any
caller. The full per-item audit is at
[`docs/archive/RELEASE_AUDIT_v1.1.3.md`](docs/archive/RELEASE_AUDIT_v1.1.3.md).

### Fixed

- **README — retracted the offline-replay automatic-write overclaim.**
  The previous wording asserted that "every successful response is
  mirrored to disk" when `UNIPROT_MCP_CACHE_DIR` is set. In fact
  `ProvenanceCache.write` is never called from production code in
  v1.1.x; only `uniprot_replay_from_cache` (read primitive) and tests
  invoke it. Sections rewritten: the "What makes this different"
  comparison row for the local cache; the §Provenance & verification
  block describing offline replay; the Claude-Desktop config block
  for `UNIPROT_MCP_CACHE_DIR`; Example workflow #5 ("Air-gapped
  clinical workflow"). All four passages now describe the cache as a
  read primitive that requires an externally-populated directory and
  flag automatic write-through as a v1.2.0 roadmap item.
- **Atlas manifest re-sealed.** `examples/atlas/manifest.json`
  recorded SHA-256 commitments that did not match the on-disk TSV
  files: the manifest was generated at git `da33b17` and the
  comprehensive index files were edited later without a manifest
  refresh. New manifest carries the SHA-256s of the current on-disk
  content (`comprehensive_index.tsv`
  `36f7001999075c44ba6e0e570dc046bc5d85822dceffb9243fdd7f2342c64124`,
  `comprehensive_index_pathogens.tsv`
  `a44939e6ceb8bbd60047815c61c0b5f68ca6ccbf2f3a70c76e2bc76a0873aa55`),
  refreshed `bytes`, refreshed `generated_at_utc`, and updated
  `git_commit_at_generation` to the v1.1.3 parent commit. Row counts
  (7,250 + 4,340 = 11,590) and the `tool.sha256` of
  `build_comprehensive_index.py` are unchanged.
- **Four MONDO ontology ID conflicts in the curated atlas corrected.**
  Each entry's MONDO ID was verified against the canonical MONDO
  ontology via OLS4. Per-entry resolution:
  - `tp53.md` Li-Fraumeni syndrome: `mondo:0007254` →
    **`mondo:0018875`**.
  - `erbb2.md` HER2-positive breast carcinoma: `mondo:0007254` →
    **`mondo:0006244`** (canonical label "HER2-positive breast
    carcinoma" — name field also normalised).
  - `hbb.md` Sickle cell disease: kept at `mondo:0011382` (the
    canonical label IS "sickle cell disease"; HBB was the correct
    side of the original collision).
  - `fbn1.md` Stiff skin syndrome: `mondo:0011382` →
    **`mondo:0008492`**.
  - `gba.md`: `mondo:0008199` ("late-onset Parkinson disease" —
    not the GBA1-susceptibility scope the atlas was describing) →
    **`mondo:1040030`** ("GBA1-related Parkinson disease,
    susceptibility"); `name` field updated to match the canonical
    label.
  - `snca.md` autosomal dominant Parkinson disease 1:
    `mondo:0008199` → **`mondo:0008200`** (canonical PARK1
    autosomal-dominant entry); `name` field normalised.
  - `myh7.md` dilated cardiomyopathy 1S: `mondo:0011712` →
    **`mondo:0013262`**.
  - `lmna.md` dilated cardiomyopathy 1A: `mondo:0011712` →
    **`mondo:0007269`**.
- **`PRIVACY.md` short version corrected.** Replaced the false claim
  "It calls one external service: the public UniProt REST API" with
  the accurate enumeration of the three origins the server may
  consult (UniProt REST, AlphaFold-DB, NCBI eutils ClinVar). Added a
  paragraph to the Data flows section pointing at the third-parties
  table for the cross-origin tools (`uniprot_get_alphafold_confidence`,
  `uniprot_resolve_clinvar`).
- **"11,590 rows linked to MONDO/OMIM/PharmGKB/ARO" wording
  narrowed.** README and `OVERVIEW.md` previously implied that the
  full 11,590-row comprehensive index linked to all four ontologies.
  In fact only the 25-entry curated atlas (`examples/atlas/atlas.json`)
  carries MONDO / PharmGKB / ARO mappings; the comprehensive index
  carries only UniProt's own disease ID and OMIM cross-reference.
  Wording rewritten to make the two scopes explicit.
- **`scripts/replicate.sh` step 6 made fresh-checkout-reproducible.**
  The previous step 6 invoked `verify.py` and `verify_answers.py`
  against the gitignored `tests/benchmark/expected.jsonl`, so a
  third party with a fresh clone could not run it. The new step 6
  uses `tests/benchmark/verify_against_hashes.py`, which re-derives
  every Tier A / Tier B answer live and hash-compares against the
  *committed* `tests/benchmark/expected.hashes.jsonl`. Tier C
  set-inclusion prompts (28, 29) are surfaced and skipped — the live
  answer may be a superset of the seal, so the hash bytes
  legitimately differ; maintainers verify those with the local
  plaintext via `verify.py`. Equivalent change in
  `scripts/replicate.ps1`.
- **README test count refreshed.** "446 offline + 42 live" updated
  to **735 offline + 42 live** (real counts via
  `pytest --collect-only` on the v1.1.3 commit). The
  commit-hash-pinned references to `ed0c76e` and `0403c0e` were
  decoupled from a specific commit, since v1.1.3 itself ships a new
  HEAD; mutation-rate prose now points at `docs/MUTATION_SCORES.md`
  for the live numbers. Coverage prose softened to note that
  v1.1.1 / v1.1.2 / v1.1.3 are metadata-and-correctness releases
  that did not touch source-code paths, so the v1.1.0 91.85 %
  measurement remains the operative figure.

### Added

- **`tests/contract/test_atlas_manifest.py`** — new contract test.
  For every file listed in `examples/atlas/manifest.json`, the
  recorded SHA-256, byte size, and row count must equal the on-disk
  values. Also pins that `manifest.tool.sha256` matches the on-disk
  build script. Closes the gap that allowed the v1.1.2-and-earlier
  manifest to drift undetected.
- **`test_no_duplicate_disease_ontology_id_with_distinct_names`** in
  `tests/contract/test_atlas_consistency.py`. Groups every disease
  `@id` in the curated atlas by its set of normalised names; fails
  if any ID maps to more than one normalised name, unless the ID is
  listed in an optional `examples/atlas/aliases_whitelist.json`.
  Closes the C7/C8 gap exposed in the v1.1.2 audit.
- **`tests/benchmark/verify_against_hashes.py`** — new helper. Live
  re-derivation + canonical SHA-256 comparison against
  `expected.hashes.jsonl` only; does not require the gitignored
  plaintext seal. Powers the new fresh-checkout `scripts/replicate.sh`
  step 6.
- **`RELEASE_AUDIT_v1.1.3.md`** — the patch-level audit document
  cataloguing the eleven items above, validation results, MONDO
  resolution sources, manifest re-sealing detail, and the explicit
  list of items deferred to v1.2.0.

### Changed

- Lock-step version bump 1.1.2 → 1.1.3 across `pyproject.toml`,
  `.well-known/mcp.json`, `server.json`, `CITATION.cff`,
  `examples/atlas/atlas.json`, `OVERVIEW.md`,
  `docs/SECURITY-AUDIT.md`, the `User-Agent` string in
  `src/uniprot_mcp/client.py`, and the default `VERSION` in
  `scripts/replicate.{sh,ps1}`.
- `examples/atlas/atlas.json` `schema:dateModified` → `2026-05-05`.

### Not changed (deferred to v1.2.0)

- `ProvenanceCache` write-through in `client._req` (the U1
  retraction is documentation only — the feature is not
  implemented).
- `uniprot_provenance_verify` URL scope.
- `uniprot_batch_entries` truncation behaviour.
- `id_mapping_results` redirect-URL allowlisting.
- README first-screen restructure.
- `docs/REPRODUCIBILITY.md`.

No functional behaviour change for any caller; no new dependency.

## [1.1.2] - 2026-04-27

Metadata-only follow-up to v1.1.1. The v1.1.1 release shipped with
stale text in `.zenodo.json` and `CITATION.cff` that said
"ships 38 read-only tools" and labelled the new family as
"position-aware features (active sites, signal peptides, modified
residues, natural variants)". The canonical surface is **41 tools**
(per `server.json` and `.well-known/mcp.json`) and the family is
**biomedical features** (with sub-categories: position-aware feature
intersection, active and binding sites, processing and maturation,
post-translational modifications). Cutting v1.1.2 lets the GitHub→
Zenodo webhook mint a fresh version DOI whose record advertises an
accurate count and family name; the concept DOI
(`10.5281/zenodo.19817710`) automatically resolves to v1.1.2 going
forward, so the README badge needs no edit.

### Changed

- `.zenodo.json` description and `CITATION.cff` abstract synced with
  the canonical strings used in `server.json` /
  `.well-known/mcp.json`: "41 read-only tools" + "biomedical features
  (position-aware feature intersection, active and binding sites,
  processing and maturation, post-translational modifications)".
- Lock-step version bump 1.1.1 → 1.1.2 across `pyproject.toml`,
  `.well-known/mcp.json`, `server.json`, `CITATION.cff`,
  `examples/atlas/atlas.json`, `OVERVIEW.md`, `docs/SECURITY-AUDIT.md`,
  and the User-Agent string in `src/uniprot_mcp/client.py`.

No functional code changes; no behaviour change for clients.

## [1.1.1] - 2026-04-27

Lock-step version bump to mint a Zenodo DOI. Zenodo's GitHub
integration was switched on for `smaniches/uniprot-mcp` on
2026-04-27 (~07:07 ET), after v1.1.0 had already shipped on
2026-04-26. Zenodo only mints DOIs for releases created after the
toggle, so v1.1.0 cannot be retroactively assigned a DOI. This patch
is the smallest valid bump that fires the GitHub→Zenodo webhook on
the `Release` workflow.

### Changed

- Version 1.1.0 → 1.1.1 across `pyproject.toml`,
  `.well-known/mcp.json`, `server.json`, `CITATION.cff` (and
  `date-released: 2026-04-27`), `examples/atlas/atlas.json`,
  `OVERVIEW.md`, `docs/SECURITY-AUDIT.md`, and the User-Agent string
  in `src/uniprot_mcp/client.py`.
- `.zenodo.json` intentionally omits a `version` field — Zenodo
  populates that from the GitHub release tag.

No functional code changes; behaviour for clients is unchanged
(8 files, 11 insertions, 11 deletions — all version-string updates).

## [1.1.0] - 2026-04-25

Biomedical-features expansion. Three new filtered-feature tools target
the active research domains of the v1.x release line: enzyme drug
design, therapeutic-protein engineering, and pathogen-secretion-system
analysis. Tool surface 38 -> 41. The new tools project the same
`features` array a UniProt entry already carries — they are pure
filters with structured grouping and an honest empty-set advisory, not
new endpoints.

### Known issues

- **Coverage regression vs v1.0.0.** Measured branch+line coverage at
  v1.0.0 release was 100%. The v1.0.1 -> v1.1.0 work added
  ~2,000 lines of formatter + server code without per-commit
  coverage gating, dropping measured coverage to 91.85%. The CI gate
  is temporarily aligned at 91 to match the floor. Uplift back to 99
  is planned for v1.2.0; PRs that further reduce coverage are
  rejected by review until the uplift lands.
- **Deferred SSRF hardening on `id_mapping_results` redirectURL.**
  Threat-model entry T3 commits to an explicit allowlist
  (`url.startswith("https://rest.uniprot.org/")` or relative-path
  only) before following the upstream-supplied redirect. Currently
  relies on httpx's same-origin redirect policy. Risk is low
  (requires compromised UniProt response) but acknowledged.
- **CVE-2026-3219 in `pip` itself** is acknowledged in CI via
  `--ignore-vuln`. `pip` is a bootstrap toolchain component on the
  GitHub-hosted runner, not a runtime dependency of
  `uniprot-mcp-server` — the CVE is not exposed by `pip install
  uniprot-mcp-server`. Remove the ignore once pip ships a fix.

### Added

- **`uniprot_get_active_sites`** — returns the catalytic and
  ligand-binding residues from an entry: active sites, binding sites,
  sites, metal-binding residues, and DNA-binding regions. The honest
  empty-set advisory points out that absence of these features does
  not imply non-druggability — the entry may be sparsely curated, or
  the function may be allosteric. The set of upstream feature types is
  exposed as `formatters.ACTIVE_SITE_FEATURE_TYPES`, the single source
  of truth shared with the property tests.
- **`uniprot_get_processing_features`** — returns the maturation
  features that describe how a translated polypeptide is cleaved and
  targeted: signal peptide, propeptide, transit peptide, initiator
  methionine, chain, peptide. Critical for therapeutic-protein
  engineering (the mature chain after signal-peptide cleavage is
  what reaches the patient) and for understanding pathogen secretion
  systems (signal peptides drive Gram-negative type-II / type-V
  secretion). Type set: `PROCESSING_FEATURE_TYPES`.
- **`uniprot_get_ptms`** — returns the post-translational modification
  features: modified residues (phosphorylation / acetylation /
  methylation), glycosylation sites, lipidation sites (GPI anchors,
  prenylation, palmitoylation), disulfide bonds, and cross-links
  (isopeptide / SUMO / ubiquitin). Empty-set advisory points
  PhosphoSitePlus / GlyConnect for additional mass-spec evidence the
  UniProt curators may not yet have integrated. Type set:
  `PTM_FEATURE_TYPES`.

### Changed

- Manifest descriptions (`.well-known/mcp.json`, `server.json`) updated
  to reflect 41 tools and the renamed "biomedical features" family.
- Version bumped 1.0.1 -> 1.1.0 across all locked-in-step files
  (pyproject.toml, .well-known/mcp.json, server.json, CITATION.cff,
  client.py UA string, docs/SECURITY-AUDIT.md privacy note).
  `uniprot_mcp.__version__` reads via `importlib.metadata` so this
  bump propagates automatically once the wheel is rebuilt.

## [1.0.1] - 2026-04-25

First public release. Closes the AUDIT.md follow-up list, raises every
formatter to provenance-aware output, expands the tool surface from
10 to 38 across 8 families (search/lookup, structural, variants and
disease, position-aware features, composition dossier, orthology, local
cache and replay, and per-query provenance verification), ships a
pre-registered SHA-256-committed benchmark with a third-party-reproducible
verifier, ships `uniprot_provenance_verify` for per-query auditability,
and ships `--pin-release` for strict reproducibility.

**Distribution.** Published on PyPI as `uniprot-mcp-server`
(`pip install uniprot-mcp-server`); the installed console script and the
MCP server identity are both `uniprot-mcp`. The Python import path is
`uniprot_mcp`. `uniprot_mcp.__version__` is sourced from the installed
wheel's metadata via `importlib.metadata`, so it cannot drift from
`pyproject.toml`; a contract test asserts it matches the manifest.

### Added
- **Provenance verification (`uniprot_provenance_verify` tool).**
  17th tool. Re-fetches a previously recorded UniProt URL and
  compares the release tag and a SHA-256 of the canonical response
  body against the values from a prior provenance footer. Distinct
  verdicts: `verified` / `release_drift` / `hash_drift` /
  `release_and_hash_drift` / `url_unreachable`, each with an advice
  string pointing at the recommended remediation (FTP snapshot,
  upstream investigation, etc.). Markdown + JSON output.
- **Release pinning (`--pin-release=YYYY_MM` / `UNIPROT_PIN_RELEASE`).**
  Strict opt-in: when set, every successful upstream response is
  checked against the pinned release; mismatches raise
  `ReleaseMismatchError`, which the server surfaces as an
  agent-safe error envelope naming both the pinned and the observed
  release plus the env var to unset for opt-out. Pinning is
  assertion-only — UniProt's REST API does not honour a release
  selector query parameter, so the client refuses drift rather than
  silently masking it. Forwarded from the `uniprot-mcp` CLI flag
  to the env var so the lazy client picks it up at first use.
- **Canonical response hash on every successful request.** The
  `Provenance` TypedDict gains a `response_sha256` field — JSON
  responses are parsed and re-serialised with sorted keys before
  hashing, so within-release key reordering doesn't break
  verification, but real content drift does.
- **Provenance on every response.** New `Provenance` TypedDict and
  `client.last_provenance` property capture the UniProt release
  number, release date, retrieval timestamp, and resolved URL. All
  formatters surface it as a Markdown footer, JSON envelope
  (`{"data": ..., "provenance": ...}`), or PIR-style `;`-prefix
  FASTA header (parser-safe for BLAST+, biopython, emboss).
- **18 new tools** (Wave B/1 → B/7), tool surface 10 → 28:
  - **B/1** controlled vocabularies: `uniprot_get_keyword`,
    `uniprot_search_keywords`, `uniprot_get_subcellular_location`,
    `uniprot_search_subcellular_locations`.
  - **B/2** UniRef clusters: `uniprot_get_uniref`, `uniprot_search_uniref`.
  - **B/3** UniParc archive: `uniprot_get_uniparc`, `uniprot_search_uniparc`.
  - **B/4** Proteomes: `uniprot_get_proteome`, `uniprot_search_proteomes`.
  - **B/5** Citations: `uniprot_get_citation`, `uniprot_search_citations`.
  - **B/6** Evidence-code summary: `uniprot_get_evidence_summary` —
    aggregates ECO codes across an entry's features and comments and
    labels the common ones (experimental vs by-similarity vs automatic).
  - **B/7** Structured cross-DB resolvers (gateway-only — no cross-
    origin calls): `uniprot_resolve_pdb`, `uniprot_resolve_alphafold`,
    `uniprot_resolve_interpro`, `uniprot_resolve_chembl`.
- **`uniprot_provenance_verify`** tool — re-fetches a recorded URL and
  compares both the release header and the canonical SHA-256 of the
  response body, with five distinct verdicts (`verified`,
  `release_drift`, `hash_drift`, `release_and_hash_drift`,
  `url_unreachable`) and an advice string per verdict.
- **Threat model:** `docs/THREAT_MODEL.md` (12 STRIDE-shaped threats,
  receipt-anchored to code paths).
- **Anthropic Connectors Directory artifacts:** `SUPPORT.md` and
  `PRIVACY.md` at repo root.
- **MCP Registry manifest:** `server.json` (2025-09-29 schema).
- **Merge plan:** `docs/MERGE_PLAN.md` (5-phase plan from
  `hardening-v2` to public flip with rollback policy).
- **Pending-items punch list:** `docs/PENDING_V1.md` (binary
  done/not-done criteria for v1.0.1).
- **Drift-prevention contract tests:** `.well-known/mcp.json`,
  `server.json`, and `pyproject.toml` versions are now pinned in
  lock-step against the registered tool surface.
- **AUDIT follow-ups:** Hypothesis fuzz for `uniprot_search` query
  construction, measured `Retry-After` delay tests across HTTP-date
  / delta-seconds / missing-header / past-date cases.

### Changed
- **Project layout:** migrated flat `server.py`/`client.py`/`formatters.py`
  to `src/uniprot_mcp/` (eliminates site-packages collision risk, makes
  `py.typed` PEP 561-effective, removes `sys.path` hack). Console script
  now wires `uniprot-mcp = "uniprot_mcp.server:main"`.
- **CI:** every GitHub Action `uses:` reference is now SHA-pinned with
  the human-readable tag preserved as a trailing comment. Dependabot's
  `github-actions` ecosystem auto-bumps the pins weekly.
- **CI:** `actions/attest-sbom@v1` now attests the CycloneDX SBOM
  alongside the existing build-provenance attestation.
- `.well-known/mcp.json` description expanded to mention provenance;
  `toolDefaults` and `support` URL blocks added.
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

[Unreleased]: https://github.com/smaniches/uniprot-mcp/compare/v1.1.8...HEAD
[1.1.8]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.8
[1.1.7]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.7
[1.1.6]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.6
[1.1.5]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.5
[1.1.4]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.4
[1.1.3]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.3
[1.1.2]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.2
[1.1.1]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.1
[1.1.0]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.0
[1.0.1]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.0.1
[0.1.0]: https://github.com/smaniches/uniprot-mcp/releases/tag/v0.1.0
