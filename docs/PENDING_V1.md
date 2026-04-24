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

- **2026-04-24** — §1.6 (Hypothesis fuzz for `uniprot_search` query construction) **and** §1.7 (measured-delay test for the client's `Retry-After` honour path) closed. Four property tests now assert organism-name quoting, numeric-taxid unquoted emission, no-unescaped-quote-in-clause, and `reviewed_only` idempotence. Four unit tests monkey-patch `asyncio.sleep` and verify the client sleeps for the exact duration `parse_retry_after` returns across HTTP-date, delta-seconds, missing-header, and past-date cases. 8 new tests, 154 total, zero regressions.
- **2026-04-24** — §1.1 (C4 SHA-pin all `uses:` references) **and** §1.2 (C5 wire SBOM attestation) closed in the same commit. Every Action is now pinned to its resolved commit SHA with the human-readable tag in a trailing comment; `actions/attest-sbom@v1` added to `release.yml` to attest the CycloneDX output alongside the existing build-provenance attestation. Dependabot's `github-actions` ecosystem (`.github/dependabot.yml:22-25`) will auto-bump the pins weekly.

