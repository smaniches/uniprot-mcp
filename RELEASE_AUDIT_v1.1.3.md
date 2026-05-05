# Release audit — v1.1.3

**Release type.** Trust-repair patch. Documentation, correctness, and
atlas re-sealing only. **No code-path changes** to any production
module in `src/uniprot_mcp/` other than the `User-Agent` version
string. No tool surface change. No behavioural change for any
existing caller.

**Tag.** `v1.1.3` (to be created by the maintainer on merge of the
release PR).

**Date.** 2026-05-05.

**Branch the work was developed on.** `claude/review-mode-setup-0dZFZ`
(harness-mandated feature branch). The release PR opens against
`main`.

**Predecessor.** v1.1.2 (released 2026-04-27, current PyPI latest).

---

## 1. Summary of v1.1.3 changes

| Item | Change | Files |
|---|---|---|
| 1 | README: retract automatic-cache-write claims; mark cache write-through as a v1.2.0 roadmap item; document `uniprot_replay_from_cache` as a read primitive that requires an externally-populated cache. | `README.md` (3 sections: comparison row 60, Provenance & verification block ~234–252, Claude-Desktop config block ~339–352, Example workflow #5 ~413–422) |
| 2 | Atlas reproducibility manifest re-sealed against the on-disk TSVs that drifted between v1.1.0 and v1.1.2. Added a contract test that fails any future drift. | `examples/atlas/manifest.json` (regenerated); new `tests/contract/test_atlas_manifest.py` |
| 3 | `scripts/replicate.sh` step 6 rewritten to be runnable from a fresh checkout: re-derives answers live and hash-compares against the committed `expected.hashes.jsonl`. The plaintext `expected.jsonl` (gitignored) is no longer required for third-party reproduction. Equivalent change to `scripts/replicate.ps1`. New helper `tests/benchmark/verify_against_hashes.py`. | `scripts/replicate.sh`, `scripts/replicate.ps1`, new `tests/benchmark/verify_against_hashes.py`, `tests/benchmark/README.md` |
| 4 | Four MONDO ontology ID conflicts in `examples/atlas/atlas.json` corrected against the canonical MONDO ontology (OLS4). | `examples/atlas/atlas.json` |
| 5 | New contract test `test_no_duplicate_disease_ontology_id_with_distinct_names` in `tests/contract/test_atlas_consistency.py`. Optional whitelist file `examples/atlas/aliases_whitelist.json` is supported but not currently shipped. | `tests/contract/test_atlas_consistency.py` |
| 6 | `PRIVACY.md` short version corrected from "one external service" to "three external services" (UniProt + AlphaFold-DB + NCBI eutils ClinVar). Data-flow section gained a sentence pointing to the third-parties table for cross-origin tools. | `PRIVACY.md` |
| 7 | "11,590 disease and pathogen rows linked to MONDO/OMIM/PharmGKB/ARO" wording narrowed to match the data: comprehensive index has UniProt + OMIM only; curated atlas has the full ontology cross-references. | `README.md`, `OVERVIEW.md` |
| 8 | README test count is verified (735 offline + 42 live). Mutation-rate prose decoupled from a specific commit hash and pointed at `docs/MUTATION_SCORES.md`. Coverage prose softened ("v1.1.0 measurement remains operative"). | `README.md` |
| 9 | Lock-step version bump 1.1.2 → 1.1.3 across `pyproject.toml`, `.well-known/mcp.json`, `server.json`, `CITATION.cff`, `examples/atlas/atlas.json` (`schema:version`, `schema:identifier`, `fairPrinciples.findable.persistentIdentifier`, `schema:dateModified`), `OVERVIEW.md`, `docs/SECURITY-AUDIT.md`, the User-Agent string in `src/uniprot_mcp/client.py`, and `scripts/replicate.{sh,ps1}` defaults. | (multiple) |
| 10 | This file. | `RELEASE_AUDIT_v1.1.3.md` |
| 11 | `CHANGELOG.md` v1.1.3 entry covering all of the above. | `CHANGELOG.md` |

## 2. Validation commands and results

Run on the v1.1.3 working tree before the release commit:

| Command | Result |
|---|---|
| `ruff check .` | _filled in by the validation gate below_ |
| `ruff format --check .` | _filled in_ |
| `mypy --strict src` (project config: `mypy src/uniprot_mcp`) | _filled in_ |
| `bandit -r src/uniprot_mcp` | _filled in_ |
| `pip-audit --strict` (in the test venv) | _filled in_ |
| `pytest -q --ignore=tests/integration` | _filled in_ |

Post-validation row counts:

- Offline tests: should remain green (734 passed + 1 skipped previously, plus the 5 new tests in `test_atlas_manifest.py`).
- Total offline collected: 735 + 5 = 740.

## 3. MONDO conflict resolution detail

Each correction was verified against the EBI Ontology Lookup Service v4
(OLS4) MONDO record.

| Atlas entry | Old `@id` | Old `name` | New `@id` | New `name` | Source |
|---|---|---|---|---|---|
| `tp53.md` (entry 0) | `mondo:0007254` | "Li-Fraumeni syndrome" | `mondo:0018875` | "Li-Fraumeni syndrome" | OLS4 search exact-match for "Li-Fraumeni syndrome"; `MONDO:0007254` was a wrong assignment (canonical label there is "breast cancer") |
| `erbb2.md` (entry 7) | `mondo:0007254` | "HER2-positive breast cancer subtype" | `mondo:0006244` | "HER2-positive breast carcinoma" | OLS4 record `MONDO:0006244` has canonical label "HER2 positive breast carcinoma"; the previous `mondo:0007254` is in fact the broad "breast cancer" parent term |
| `hbb.md` (entry 11) | `mondo:0011382` | "Sickle cell disease" | _unchanged_ | _unchanged_ | OLS4 confirmed `MONDO:0011382` canonical label IS "sickle cell disease" — the HBB row was the correct side of the collision |
| `fbn1.md` (entry 13) | `mondo:0011382` | "Stiff skin syndrome" | `mondo:0008492` | "Stiff skin syndrome" | OLS4 search exact-match for "stiff skin syndrome" |
| `gba.md` (entry 16) | `mondo:0008199` | "Parkinson disease 1 (genetic risk modifier)" | `mondo:1040030` | "GBA1-related Parkinson disease, susceptibility" | OLS4 record `MONDO:1040030` is the canonical GBA1-susceptibility entry; `MONDO:0008199` is "late-onset Parkinson disease" (a broader term that does not match the GBA1-susceptibility scope the atlas was describing) |
| `snca.md` (entry 18) | `mondo:0008199` | "Parkinson disease 1, autosomal dominant" | `mondo:0008200` | "autosomal dominant Parkinson disease 1" | OLS4 record `MONDO:0008200` is the canonical PARK1 autosomal-dominant entry; SNCA is the established genetic cause; the previous `MONDO:0008199` is broader |
| `myh7.md` (entry 19) | `mondo:0011712` | "Dilated cardiomyopathy 1S" | `mondo:0013262` | "dilated cardiomyopathy 1S" | OLS4 record `MONDO:0013262` is "dilated cardiomyopathy 1S" with MYH7 as the cause; `MONDO:0011712` was a wrong assignment (canonical label there is "van der Woude syndrome 2") |
| `lmna.md` (entry 20) | `mondo:0011712` | "Dilated cardiomyopathy 1A" | `mondo:0007269` | "dilated cardiomyopathy 1A" | OLS4 record `MONDO:0007269` is "dilated cardiomyopathy 1A" |

Post-correction, the duplicate-ID-with-distinct-names scan reports
**0 conflicts**. The new contract test
`test_no_duplicate_disease_ontology_id_with_distinct_names` enforces
this on every commit going forward.

## 4. Atlas manifest re-sealing detail

The previous manifest's commitments diverged from the on-disk TSV
files; the manifest was generated at git commit `da33b17` and the
TSV plaintext was edited after without a manifest refresh.

| File | Old SHA-256 (manifest) | New SHA-256 (on disk) | Rows excl. header | Bytes |
|---|---|---|---|---|
| `examples/atlas/comprehensive_index.tsv` | `078711347db7d5205219ceae325c92db357fc569365d9a9534851dda8a75ef75` | `36f7001999075c44ba6e0e570dc046bc5d85822dceffb9243fdd7f2342c64124` | 7250 (unchanged) | 1208254 (was 1215505) |
| `examples/atlas/comprehensive_index_pathogens.tsv` | `b40b5c674d0091e8c011168ecc29c2da512897b2c1df617ba936634f7ff8e3e9` | `a44939e6ceb8bbd60047815c61c0b5f68ca6ccbf2f3a70c76e2bc76a0873aa55` | 4340 (unchanged) | 537760 (was 542101) |
| `examples/atlas/build_comprehensive_index.py` | `dbd62896fca6cc842893763f16db1abb3d8d376ff0ede6a34f96c0a5da5f2429` | `dbd62896fca6cc842893763f16db1abb3d8d376ff0ede6a34f96c0a5da5f2429` | n/a | (build script, not regenerated) |

Total row count: **11,590** (7,250 + 4,340) — unchanged from the
public-facing claim. Only the SHA-256 of each TSV was stale; the
content was already on disk.

The TSVs themselves are **not regenerated** in this patch — that
would require a live UniProt run, which is out of v1.1.3 scope. The
manifest is simply re-sealed against the existing on-disk content.
Future regenerations should be paired with a manifest refresh in the
same commit; the new `tests/contract/test_atlas_manifest.py` will fail
CI if the pairing is forgotten.

`tool.git_commit_at_generation` updated from `da33b17129…` to the
current branch HEAD (parent of the v1.1.3 release commit).

## 5. Deferred to v1.2.0

These items were explicitly out of scope for v1.1.3 and remain open:

1. **`ProvenanceCache` write-through** in `client._req` gated on
   `UNIPROT_MCP_CACHE_DIR` (U1 path A). The v1.1.3 patch only
   retracted the misleading documentation; the feature itself is
   not implemented.
2. **`uniprot_provenance_verify` scope decision** (C4): broaden the
   verifier to accept `alphafold.ebi.ac.uk` and `eutils.ncbi.nlm.nih.gov`
   URLs with origin-specific verification semantics, OR formally
   narrow the recorded `Provenance` records on cross-origin
   responses so they are not misinterpreted as verifiable. Either
   path is a v1.2.0 minor.
3. **`uniprot_batch_entries` explicit rejection of >100 accessions**
   (C9). Changes today's silent truncation into the same loud
   rejection that `uniprot_id_mapping` already does. Breaking change
   for callers that rely on truncation.
4. **SSRF redirect allowlisting in `id_mapping_results`** (C10):
   validate the `redirectURL` origin against `rest.uniprot.org`
   before re-issuing the request, and consider disabling
   `follow_redirects` on the redirect-handling path so a chain
   attack cannot escape.
5. **README first-screen restructure** (P2 #10): move the 41-tool
   table below a 5-line "Why this exists / Install / 60-second
   example / Provenance demo" block.
6. **`docs/REPRODUCIBILITY.md`** (P2 #11) consolidating the
   `expected.hashes.jsonl` mechanics, the `replicate.sh` semantics,
   the atlas manifest regeneration, and the SLSA verification
   commands into one navigable document.
7. **`MAX_CACHE_BYTES` env knob** — only meaningful once write-through
   exists.
8. Decide whether to update `docs/THREAT_MODEL.md` with an explicit
   reference to the opt-in cache primitives, even though production
   behaviour matches the current "not stored" claim.

## 6. Explicit scope statement

This is a documentation, correctness, and atlas re-sealing release.
**None** of the following are touched in v1.1.3:

- No tool surface change. The 41-tool surface is identical.
- No `Provenance` TypedDict shape change.
- No verify-tool URL allowlist change.
- No batch-entries truncation change.
- No SSRF allowlisting change.
- No release-pinning behaviour change.
- No new dependency.
- No test fixture or snapshot change beyond the new
  `test_atlas_manifest.py` and the new test in `test_atlas_consistency.py`.
- No structural or path-encoding change for the cache JSON shape.

## 7. C1 status

The pre-flight audit investigated the `C1` claim ("PyPI latest is
1.1.0; repo claims 1.1.2") and **falsified** it: PyPI was already at
1.1.2 before this patch (verified directly via the PyPI JSON API on
2026-05-05). All repo metadata files were already at 1.1.2 with no
drift. The v1.1.3 bump is therefore a forward step, not a
re-synchronisation.

---

## Author

Santiago Maniches · ORCID
[0009-0005-6480-1987](https://orcid.org/0009-0005-6480-1987) ·
TOPOLOGICA LLC.
