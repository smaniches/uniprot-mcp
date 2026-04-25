# Pending work — path to `uniprot-mcp` v1.0.1 public release

**Status date:** 2026-04-22
**Target flip window:** 2026-06-01 → 2026-06-07 (`topologica-bio/docs/LAUNCH_PLAN.md` Phase 4)
**GitHub Actions billing reset:** ~2026-05-01 (Phase 1 measurement cannot run before this)
**Release tag target:** `v1.0.1` (first public tag; `v0.1.0` stays the pre-flip private baseline)

This file is the authoritative punch list between the audit-remediated
state on `hardening-v2` (`020c2a8`) and the public-flip gate. Every
item is receipt-anchored and has a binary done/not-done criterion.

---

## Quality bar

`uniprot-mcp` is the reference implementation for the Topologica Bio
MCP family. It is not released until:

- all twelve items in §1 + §2 + §3 are green
- the mutation-kill score on every source module is ≥ 95 %
- the 3×3 CI matrix (Python 3.11 / 3.12 / 3.13 × Ubuntu / Windows / macOS) is green on `main`
- the live-integration suite has been green on at least two consecutive nightly runs
- every claim in `README.md` is anchored to either a code path, a test name, or a standard URL

No exceptions. No deferrals.

---

## §1 — Follow-ups explicitly deferred in AUDIT.md

Authoritative list: `AUDIT.md` lines 109–114 and the "Deferred" rows in
the per-area tables.

| # | Ref | Action | Unblocked? |
|---|---|---|---|
| 1.1 | AUDIT §C4 | SHA-pin every `uses:` in `.github/workflows/*.yml`; keep human-readable tag in trailing comment | ✅ today |
| 1.2 | AUDIT §C5 | Wire `actions/attest-build-provenance` with predicate type `sbom` for the CycloneDX output in `release.yml` | ✅ today |
| 1.3 | AUDIT §C6 | Restore `codeql.yml` workflow — enabled on flip day when repo is public | ⏳ flip day |
| 1.4 | AUDIT §C6 | Restore `scorecard.yml` workflow — enabled on flip day when repo is public | ⏳ flip day |
| 1.5 | AUDIT follow-up #3 | Configure PyPI Trusted Publisher in "pending-publisher" mode for `uniprot-mcp` under the `smaniches` account | ✅ today |
| 1.6 | AUDIT follow-up #4 | Hypothesis property-based fuzz test for `uniprot_search` query construction (organism quoting, reserved chars) | ✅ today |
| 1.7 | AUDIT follow-up #5 | `respx`-based test that asserts `Retry-After: <http-date>` actually delays the client by the expected interval (measure, don't just parse) | ✅ today |

---

## §2 — Launch-plan gates (billing-bound)

Cannot proceed until GitHub Actions billing resets. Authoritative
list: `topologica-bio/docs/LAUNCH_PLAN.md` gates 1–11.

| # | Gate | Action | Runs after billing reset |
|---|---|---|---|
| 2.1 | LP §1 | Add `mutation.yml` workflow; run `mutmut` on `src/uniprot_mcp/`; fail under 95 % kill | ⏳ May 1 |
| 2.2 | LP §2 | Populate `MUTATION_SCORES.md` with real per-module numbers and run metadata | ⏳ May 1 |
| 2.3 | LP §3 | Verify 3×3 matrix green across a full push on `main` | ⏳ May 1 |
| 2.4 | LP §4 | Add `docs.yml` workflow building the `mkdocs` site on every push to `main`; publish to `gh-pages` on tags | ⏳ May 1 |
| 2.5 | LP §5 | Nightly `integration.yml` green on two consecutive runs before flip | ⏳ May 2+ |
| 2.6 | LP §11 | Branch protection on `main`: required checks = {lint, tests[3.12/ubuntu], integration}, linear history, signed commits, no force-push | ⏳ pre-flip |
| 2.7 | — | gitleaks clean sweep against full history, including all branches | ⏳ pre-flip |
| 2.8 | — | `Dependabot` + `secret scanning` both enabled (already in `.github/dependabot.yml`; flip once repo is public) | ⏳ flip day |

---

## §3 — Raise-the-bar additions (not in original audit)

Scope gap between current state and "reference MCP that Wolfram
should look like a toy next to." Every item below is required for
v1.0.1 unless marked `optional`.

### 3a — Tool-surface completeness

| # | Action | Binary criterion |
|---|---|---|
| 3a.1 | Inventory the UniProt REST surface currently *not* exposed (UniRef, UniParc, proteomes, keywords, subcellular-locations, literature citations, suggestor, annotations-download, coordinates, taxonomy detail beyond search). Produce `docs/TOOL_SURFACE.md` with a table of "exposed / planned v1.0.1 / planned v1.1 / explicitly out-of-scope" decisions. | file exists on `main` |
| 3a.2 | First-class tools for cross-database resolution (not just passthrough strings): `uniprot_resolve_pdb`, `uniprot_resolve_alphafold`, `uniprot_resolve_interpro`, `uniprot_resolve_chembl`. Each returns a structured record, not a CSV line. | 4 tools registered, tested, snapshotted |
| 3a.3 | **UniProt release pinning** — every tool response carries the UniProt release number (e.g. `2026_02`) in a top-level `provenance` field. Tested by snapshot. | `fmt_*` emits `provenance.release`; ≥ 1 test per tool |

### 3b — Documentation

| # | Action | Binary criterion |
|---|---|---|
| 3b.1 | `mkdocs.yml` + `docs/` site with sections: Quickstart / Tool reference (auto-generated) / Recipes / Provenance / Threat model / Changelog. Deployed to `https://smaniches.github.io/uniprot-mcp/` on tag | site builds locally without warnings |
| 3b.2 | `examples/` directory with ≥ 3 worked Claude-Desktop sessions (JSON transcripts), each demonstrating a distinct research task. Required by Anthropic directory submission. | 3 `.jsonl` files, each under `examples/`, each referenced in README |
| 3b.3 | `asciinema` recording of the 90-second flagship demo, committed as `docs/media/demo.cast` + embedded in README | file present; README renders |
| 3b.4 | `docs/THREAT_MODEL.md` — STRIDE-style walk, matching the format of `topologica-bio/THREAT_MODEL.md`; all "deferred to v0.2" items either resolved or ticketed | file present; 0 open "deferred" rows |
| 3b.5 | Add `SUPPORT.md` and `PRIVACY.md` at repo root — both required by the Anthropic Connectors Directory submission | files present with real URLs, not placeholders |
| 3b.6 | `.well-known/mcp.json` — re-verify the tool list matches the 10 current + any added in §3a; update `auth: none` and contact fields | file present; `jq '.tools | length'` equals real tool count |

### 3c — Publishing surface

| # | Action | Binary criterion |
|---|---|---|
| 3c.1 | `server.json` at repo root, conforming to the MCP Registry 2026 manifest schema | validates against the official MCP Registry JSON schema |
| 3c.2 | `smithery.yaml` re-verified against the current CLI (`smithery validate`) — the AUDIT fixed the Dockerfile reference but we have not re-validated post-audit | `smithery validate` exits 0 |
| 3c.3 | Prepared submissions (drafts only, submitted on flip day): MCP Registry PR, Smithery listing, Anthropic directory form, Glama listing. Draft bodies live in `docs/launch/` | 4 draft files present |

### 3d — Evaluation

| # | Action | Binary criterion |
|---|---|---|
| 3d.1 | Pre-registered benchmark `tests/benchmark/` mirroring the `topologica-bio` pattern: 30 prompts (easy/medium/hard × 10), SHA-256 committed expected answers, `seal.py` + `verify.py`. Prompts authored using primary-source UniProt REST only; NOT using the uniprot-mcp server itself | `seal.py` passes; `expected.hashes.jsonl` on `main` |
| 3d.2 | Run the benchmark under two conditions (uniprot-mcp vs vanilla-Claude-with-WebFetch) and commit scored output to `tests/benchmark/run-<YYYYMMDD>/` | run directory on `main` before flip |

---

## §4 — Scope decisions required from the user

Items I cannot take unilaterally; flagged for explicit direction.

- **SD-1.** Tool surface for v1.0.1 — expand (include §3a.1 + §3a.2 new tools before flip) vs narrow (ship the current 10 + cross-DB bridges only, expand in v1.1). Recommendation: **expand**, because v1.0.1 is the reference and half a surface is a worse template than a complete one.
- **SD-2.** Release snapshot strategy — do we only *report* the UniProt release number in `provenance`, or do we also pin to a specific release by passing `?release=YYYY_MM` on every request when the client is configured with `--pin-release`? Recommendation: **report always, pin-on-demand** (keeps default latest-release behaviour fast; reproducibility opt-in).
- **SD-3.** Beta-cohort on `uniprot-mcp` — reuse the same 3-5 academic labs targeted for `topologica-bio`, or recruit a separate pool? Recommendation: **reuse**, with an explicit ask for one representative-per-lab to run the benchmark on their own machine.
- **SD-4.** License on any v1.0.1-new code — stay fully Apache-2.0, or dual-license new research-evaluation code BUSL-1.1-mirroring the monorepo? Recommendation: **stay Apache-2.0** — uniprot-mcp is the permissive gateway; BUSL belongs on the provenance/orchestrator tier only.

---

## §5 — Working order

1. **Today → May 1 (non-billing-blocked):** §1.1, §1.2, §1.5, §1.6, §1.7, §3a.3, §3b.1, §3b.2, §3b.4, §3b.5, §3b.6, §3c.1, §3c.2, §3d.1, and (pending SD-1) §3a.1 + §3a.2.
2. **May 1 → May 10 (Phase 1 measurement):** §2.1 – §2.5.
3. **May 10 → May 24 (Phase 2 beta):** §3d.2 run on at least two independent machines.
4. **May 24 → May 31 (Phase 3 pre-flip):** §2.6, §2.7, §1.3, §1.4 drafted in a branch, enabled at flip.
5. **June 1 → June 7 (the flip):** §3c.3 submissions go out; `v1.0.1` tag; `codeql.yml` + `scorecard.yml` enabled on first push to public `main`.

Any slippage on §1 or §3 pushes the entire window, not just the
missed item. If by 2026-05-25 any §3 item is still red, the default
is to slip the flip window by seven days, not to drop the item.

---

## §6 — Completed log

Reverse-chronological. Each entry names the item from §1–§3 and the
commit or artefact that closed it.

- **2026-04-25** — **§1.3 + §1.4 closed: CodeQL and Scorecard workflows restored, ready to activate at flip.** Both files ship now (committed to `hardening-v2`) so the actual visibility flip is purely a `gh repo edit --visibility public` action with **zero additional file edits required**. CodeQL: matrix on Python, security-extended + security-and-quality query packs, weekly Monday schedule + push + PR triggers. Scorecard: weekly schedule + on-branch-protection-change, publishes results to the public API + uploads SARIF to Code Scanning. Both Actions SHA-pinned to current commit (resolved via `gh api`); both will idle on the private repo (Code Scanning is paid on private personal accounts) and start producing results on the first push to `main` after the flip.
- **2026-04-25** — **README polish for the public flip.** Comprehensive rewrite. Tool count corrected from "(10)" to "(28)" with grouping into 6 endpoint families (core UniProtKB / controlled vocabularies / sequence archives & clusters / proteomes & literature / structured cross-DB resolvers / provenance & verification). New "What makes this different" comparison table vs vanilla LLM + WebFetch and vs typical bio-MCPs. New "Provenance & verification" section with the actual live values from `tests/benchmark/run-2026-04-25-roundtrip/transcript.md` and the five-verdict table. New "Pre-registered benchmark" section with the two-command third-party reproducibility recipe. New "Testing" section with all five test layers and the 287 offline + 4 live count. Updated install instructions (`pip install uniprot-mcp`, `uvx uniprot-mcp`); updated Claude-Desktop config to use the console script (no more `python -m server`); release-pinning configuration shown. Updated example workflows to feature the new resolvers (`uniprot_resolve_pdb`, etc.) and the provenance round-trip. License section now describes the gateway/orchestrator split with Topologica Bio. New "Architecture & threat model" section linking THREAT_MODEL, INCIDENT_POLICY, AUDIT, MERGE_PLAN, PENDING_V1.
- **2026-04-25** — **Wave B/3-7 closed: tool surface 17 → 28.** Eleven new tools across five families.
  - **B/3 UniParc** (2 tools): `uniprot_get_uniparc`, `uniprot_search_uniparc`. New `UNIPARC_ID_RE` (`UPI[A-F0-9]{10}`). UniParc is the non-redundant sequence archive — every protein sequence ever submitted to a public DB has exactly one UPI.
  - **B/4 Proteomes** (2 tools): `uniprot_get_proteome`, `uniprot_search_proteomes`. New `PROTEOME_ID_RE` (`UP\d{9,11}`). Surfaces protein/gene counts, BUSCO completeness score, annotation score, components (chromosome breakdown).
  - **B/5 Citations** (2 tools): `uniprot_get_citation`, `uniprot_search_citations`. New `CITATION_ID_RE` (PubMed numeric IDs). Returns title, authors, journal, year, cross-refs.
  - **B/6 Evidence summary** (1 tool): `uniprot_get_evidence_summary`. Walks every feature and comment in an entry, counts ECO (Evidence and Conclusion Ontology) codes, and labels the common ones with human-readable descriptions ("experimental evidence used in manual assertion" vs "match to InterPro signature used in automatic assertion"). Distinguishes wet-lab-confirmed from inferred-by-similarity — critical for any agent that cares about evidence quality.
  - **B/7 Structured cross-DB resolvers** (4 tools): `uniprot_resolve_pdb`, `uniprot_resolve_alphafold`, `uniprot_resolve_interpro`, `uniprot_resolve_chembl`. Extract the corresponding cross-references from a UniProt entry and return *structured* records (PDB: id + method + resolution + chains; AlphaFold: model id + EBI viewer URL; InterPro: signature id + name; ChEMBL: target id + EBI card URL). Gateway-only — no cross-origin calls. 23 new tests in `test_wave_b_3_to_7.py`. 287 total, mypy + ruff clean. **The "narrow MCP" gap is closed.**
- **2026-04-25** — **Live end-to-end provenance round-trip.** New integration suite `tests/integration/test_provenance_roundtrip_live.py` (4 tests, opt-in via `--integration`) exercises the full chain *upstream → Provenance → markdown / JSON surface → `uniprot_provenance_verify` re-fetch* against real UniProt. All 4 PASS. Companion demo `tests/benchmark/demo_roundtrip.py` writes a captured transcript at `tests/benchmark/run-2026-04-25-roundtrip/transcript.md` showing the actual observed values: live release `2026_01` (not `2026_02` as fixtures assumed; that's just hypothetical test data), live release-date format `28-January-2026` (UniProt returns human-readable, not ISO 8601 — the renderer doesn't care because it embeds the string verbatim), and a real `response_sha256` for P04637. Every verdict — `verified`, `hash_drift`, `release_drift`, `url_unreachable` — produced as predicted. **Every architectural claim about provenance is now grounded in observed behaviour, not just unit tests.** AUDIT.md verification log appended with this entry.
- **2026-04-25** — **Live-REST re-verification of every benchmark answer.** New script `tests/benchmark/verify_answers.py` programmatically re-derives every Tier A, B, and C answer from `https://rest.uniprot.org/...` using only documented public endpoints — no training-data shortcuts, no `uniprot-mcp` consultation, no canonical-list lookup tables. Run against the current local `expected.jsonl`: **30 / 30 prompts verify** (28 exact-match, 2 set-inclusion for prompts 28/29 per the snapshot-dependence policy). Cryptographic round-trip via `verify.py` also green: `OK: 30 commitments verified`. AUDIT.md updated with: (a) verifier script reference in the Method section, (b) new "Verification log" section recording the 2026-04-25 outcome with command + per-tier breakdown, (c) upgraded independence statement noting that the verifier is itself reviewable Python. **A third party can now reproduce the verification end-to-end with two commands.** That is what "no training-data shortcuts" looks like operationally.
- **2026-04-25** — **Provenance verification (Prompt 2 from `/effort max`) closed.** Two halves landed in one commit. (a) `--pin-release=YYYY_MM` opt-in: `UniProtClient` now accepts a `pin_release` constructor arg + reads `UNIPROT_PIN_RELEASE`; the `uniprot-mcp` CLI accepts `--pin-release=YYYY_MM` and forwards via env var. Strict assertion (UniProt REST has no release selector): mismatches raise `ReleaseMismatchError` which the server surfaces as an agent-safe error envelope naming pinned + observed releases + the env var to unset. (b) New 17th tool `uniprot_provenance_verify` re-fetches a recorded URL and compares both the release header and a SHA-256 of the canonical response body. Five verdicts: `verified`, `release_drift`, `hash_drift`, `release_and_hash_drift`, `url_unreachable`. Each carries an advice string pointing at the right remediation. Markdown + JSON output. (c) `Provenance` TypedDict gains a `response_sha256` field — JSON responses are parsed and re-serialised with sorted keys before hashing, so within-release key reordering doesn't break verification but content drift does. Markdown footer and PIR-style FASTA header now emit a `_SHA-256: <64 hex>_` / `;SHA-256:` line. 25 new tests (10 pin-release, 15 provenance-verify), 264 total, mypy + ruff clean. **A year from now, every uniprot-mcp answer is independently auditable in one tool call.** This is the wedge the regulated-bio-pharma 2030 test asks for.
- **2026-04-25** — **Benchmark sealed.** Highest-leverage move per the user's `/effort max` follow-up: every Tier-A and Tier-B factual answer was curl-verified against `https://rest.uniprot.org/...` at sealing time (no training-data shortcuts). 30 SHA-256 commitments now on `main` in `tests/benchmark/expected.hashes.jsonl`; plaintext `expected.jsonl` held local-only per `.gitignore`. `seal.py` round-trip green: `OK: 30 commitments verified`. Caught and recorded one defect during authoring (`SL-0086 = Cytoplasm`, not Cell membrane — fixed in the previous commit). New contract test `tests/contract/test_benchmark_integrity.py` (8 tests) pins prompts/hashes shape, ID-set agreement, hash uniqueness, and the `expected.jsonl` gitignore rule. AUDIT.md sealing checklist marked complete with execution date 2026-04-25 and per-prompt curl rationales. **A reviewer can now cryptographically prove the expected answers existed before any system was scored against them.** This is the artifact compliance officers cite. 239 / 239 tests, mypy + ruff clean.
- **2026-04-24** — Operational-maturity artifacts (Prompt 3 from the `/effort max` direction) closed: `docs/POSTMORTEM_TEMPLATE.md` (header / timeline / root-cause / impact / detection / resolution / follow-up / lessons-learned / 2030-compliance-officer view), `docs/INCIDENT_LOG.md` (severity scale S0-S3, open / closed sections, currently empty), `docs/INCIDENT_POLICY.md` (binary "what triggers a postmortem" rules, blameless discipline, sunset rule, fix-PR-with-postmortem requirement). Drift-prevention contract test `tests/contract/test_incident_policy.py` (5 tests) — every log entry must point at a real `docs/incidents/<...>.md` file; every postmortem file must be referenced from the log; orphans break CI.
- **2026-04-24** — Benchmark scaffold (Prompt 1 from the `/effort max` direction, partial — sealing in next commit) closed: `tests/benchmark/` directory created with `prompts.jsonl` (30 prompts frozen at v1, Tier A/B/C × 10, IDs contiguous 1-30, format-validated), `seal.py` + `verify.py` (Apache-2.0, ported from topologica-bio with adaptation), `run.py` + `score.py` skeleton stubs, `README.md` (commitment scheme, comparator definitions, scoring protocol, authorship statement), `AUDIT.md` (per-prompt source attribution, snapshot-dependence policy, formal independence statement). `.gitignore` updated to exclude the upcoming local-only `expected.jsonl`. **Caught and fixed** a documentation defect during authoring: the Wave B/1 docstrings claimed `SL-0086 = Cell membrane`, but primary-source REST verification confirmed `SL-0039 = Cell membrane` and `SL-0086 = Cytoplasm`. All references corrected (client, formatter, server docstrings, test fixture, AUDIT.md). Sealing of `expected.jsonl` + commit of `expected.hashes.jsonl` is the next-batch work.
- **2026-04-24** — Wave B/2 closed: **§3a.1 partial — UniRef cluster surface.** Tool count 14 → 16: `uniprot_get_uniref`, `uniprot_search_uniref`. Adds `UNIREF_ID_RE` accepting all three identity tiers (50 / 90 / 100 %) and either UniProt-accession or UniParc-UPI suffix; `_check_uniref_id` validator with 30-char length cap. `uniprot_search_uniref` accepts `identity_tier` ∈ {"50", "90", "100", ""}; the tier folds into UniProt query syntax as `identity:0.5/0.9/1.0`, asserted by 4 dedicated tests. `fmt_uniref` extracts the tier from `entryType` (preferred) or the cluster-id prefix (fallback) and surfaces representative member, member count, common taxon, last-updated date. 20 new tests, 226 total, mypy + ruff clean.
- **2026-04-24 — PIVOT.** User instruction: stop adding tools; promote Wave D (benchmark) and add two new sections — provenance verification (`--pin-release` + `provenance_verify` tool) and operational-maturity artifacts (postmortem template + incident log). The remaining Wave B groups (UniParc, proteomes, literature, utility, cross-DB resolvers) are **paused** until after the benchmark + verification surface land. Rationale (user's own framing): "would a regulated bio-pharma compliance officer who has never met me trust this artifact in 2030?" — pre-registered benchmark + verifiable provenance + incident log answer that question; more tools do not.
- **2026-04-24** — Wave B/1 closed: **§3a.1 partial — controlled-vocabulary surface.** Tool count 10 → 14: `uniprot_get_keyword`, `uniprot_search_keywords`, `uniprot_get_subcellular_location`, `uniprot_search_subcellular_locations`. Adds `KEYWORD_ID_RE` (`KW-NNNN`) and `SUBCELLULAR_LOCATION_ID_RE` (`SL-NNNN`) regexes to the client, plus `_check_keyword_id` / `_check_subcellular_location_id` validators in the server. Four new formatters (`fmt_keyword`, `fmt_keyword_search`, `fmt_subcellular_location`, `fmt_subcellular_location_search`) — all provenance-aware. Defensive shape handling for both nested-object (`{"keyword": {"id": ...}}`) and flat-string (`{"keyword": "KW-..."}`) UniProt response variants. 19 new tests in `test_keyword_subcellular.py` covering regex shape, validation rejection, happy-path Markdown + JSON, search truncation at 50, and minimal-shape graceful handling. CHANGELOG [Unreleased] populated. 206 / 206 tests, mypy + ruff clean.
- **2026-04-24** — Wave A docs batch closed: **§3b.4** `docs/THREAT_MODEL.md` (12-threat STRIDE-shaped walk specific to a UniProt gateway, format-matched to `topologica-bio/THREAT_MODEL.md`); **§3b.5** `SUPPORT.md` + `PRIVACY.md` at repo root (Anthropic Connectors Directory requirement; PRIVACY explicitly documents the stateless-no-telemetry posture); **§3b.6** `.well-known/mcp.json` re-verified against the live tool surface (10/10 match) and improved with provenance description, `toolDefaults` block, and `support` URLs; **§3c.1** `server.json` MCP Registry manifest at repo root (2025-09-29 schema, reverse-DNS name `io.github.smaniches/uniprot-mcp`); **§3c.2** `smithery.yaml` validated against the documented v1 schema (Smithery CLI v4.9.3 no longer ships a `validate` subcommand — pivoted to discovery; on-disk YAML structural check is the post-pivot equivalent); **bonus** `docs/MERGE_PLAN.md` (5-phase merge → tag → flip operational plan, with rollback). Drift-prevention contract test added: `tests/contract/test_manifest_consistency.py` (4 tests) pins the registered tool set against `.well-known/mcp.json`, version against `server.json`, version against `pyproject.toml`. 187 total tests, mypy + ruff clean.
- **2026-04-24** — §3a.3 (release-number + URL + timestamp provenance on every response) closed. `Provenance` TypedDict added to `client.py` with `_extract_provenance` helper reading `X-UniProt-Release` / `X-UniProt-Release-Date` headers; `UniProtClient.last_provenance` exposes the record after every successful request (stdio-serialized, non-reentrant — documented). Every formatter now accepts `provenance=` kwarg and emits either a trailing Markdown footer (`---` separator + `_Source: ..._` + `_Query: url_`), a JSON envelope (`{"data": ..., "provenance": ...}`), or a PIR-style `;`-prefix block (FASTA, parser-safe for BLAST+ / biopython / emboss). New `fmt_fasta` helper. Server tools wire `client.last_provenance` through to every formatter. 29 new tests in `test_provenance.py` covering extraction, client wiring, Markdown footer, JSON envelope, FASTA header, end-to-end tool surfacing. 183 total, zero regressions; mypy + ruff clean.
- **2026-04-24** — §1.6 (Hypothesis fuzz for `uniprot_search` query construction) **and** §1.7 (measured-delay test for the client's `Retry-After` honour path) closed. Four property tests now assert organism-name quoting, numeric-taxid unquoted emission, no-unescaped-quote-in-clause, and `reviewed_only` idempotence. Four unit tests monkey-patch `asyncio.sleep` and verify the client sleeps for the exact duration `parse_retry_after` returns across HTTP-date, delta-seconds, missing-header, and past-date cases. 8 new tests, 154 total, zero regressions.
- **2026-04-24** — §1.1 (C4 SHA-pin all `uses:` references) **and** §1.2 (C5 wire SBOM attestation) closed in the same commit. Every Action is now pinned to its resolved commit SHA with the human-readable tag in a trailing comment; `actions/attest-sbom@v1` added to `release.yml` to attest the CycloneDX output alongside the existing build-provenance attestation. Dependabot's `github-actions` ecosystem (`.github/dependabot.yml:22-25`) will auto-bump the pins weekly.

