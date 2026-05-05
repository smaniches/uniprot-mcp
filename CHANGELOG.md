# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.3] - 2026-05-05

Trust-repair patch. Documentation, correctness, and atlas re-sealing
only — **no production code-path changes** beyond the User-Agent
version string. No tool surface change. No behaviour change for any
caller. The full per-item audit is at
[`RELEASE_AUDIT_v1.1.3.md`](RELEASE_AUDIT_v1.1.3.md).

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

[Unreleased]: https://github.com/smaniches/uniprot-mcp/compare/v1.1.2...HEAD
[1.1.2]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.2
[1.1.1]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.1
[1.1.0]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.0
[1.0.1]: https://github.com/smaniches/uniprot-mcp/releases/tag/v1.0.1
[0.1.0]: https://github.com/smaniches/uniprot-mcp/releases/tag/v0.1.0
