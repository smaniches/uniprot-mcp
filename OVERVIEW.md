# `uniprot-mcp` — five-minute overview

This page is for time-constrained reviewers. Everything below is
auditable: each claim links to the file or workflow that proves it.
No claim is made that cannot be verified by reading code or running
a script.

## What this project is

A **Model Context Protocol** server that exposes the UniProt protein
knowledgebase to LLM agents (Claude, and any other MCP client) with
**per-query provenance verification**. Apache-2.0. Published on PyPI
as [`uniprot-mcp-server` v1.1.8](https://pypi.org/project/uniprot-mcp-server/1.1.8/).
Source: [github.com/smaniches/uniprot-mcp](https://github.com/smaniches/uniprot-mcp).

## What is concrete and verifiable

| Claim | Where to check |
|---|---|
| 41 tools across 8 families. | `src/uniprot_mcp/server.py` (each `@mcp.tool` decorator); `.well-known/mcp.json` lists them; contract test `tests/contract/test_manifest_consistency.py` enforces equality between code and manifest. |
| Per-response provenance with SHA-256. | `src/uniprot_mcp/client.py` `_extract_provenance` + `canonical_response_hash`; sample footer at `tests/benchmark/run-2026-04-25-roundtrip/transcript.md`. |
| A `uniprot_provenance_verify` tool with five enumerated verdicts. | `src/uniprot_mcp/server.py` (the tool registration); unit tests in `tests/unit/test_provenance_verify.py`. |
| 874 offline + 44 live integration tests (real counts via `pytest --collect-only`). | `pytest --collect-only --ignore=tests/integration -q` for the offline 874; `pytest --collect-only tests/integration -q` for the 44. |
| 30/30 sealed-prompt benchmark verified against live UniProt 2026-04-26 (maintainer cryptographic path: `verify.py` + `verify_answers.py` with the local `expected.jsonl`). | `tests/benchmark/run-2026-04-26-v1.1.0/` (transcript) + the cryptographic seals at `tests/benchmark/expected.hashes.jsonl`. Third-party reproducibility tool (re-derives + prints answers live; does not recompute the seal): `tests/benchmark/verify_against_hashes.py`. |
| The PyPI wheel was built from this exact repo. | SLSA build provenance attestation on every [GitHub Release](https://github.com/smaniches/uniprot-mcp/releases) (v1.1.8 = latest); `gh attestation verify` confirms. End-to-end script: `scripts/replicate.sh`. |
| **11,590 disease + pathogen rows** in the comprehensive index, sourced verbatim from UniProt. | `examples/atlas/comprehensive_index.tsv` (7,250 human disease rows from 5,296 entries, UniProt disease ID + OMIM cross-references where present) + `examples/atlas/comprehensive_index_pathogens.tsv` (4,340 entries across 16 pathogens). Reproducibility manifest at `examples/atlas/manifest.json` re-sealed in v1.1.3 with SHA-256 of every committed file + the script's git commit; contract test `tests/contract/test_atlas_manifest.py` fails any future drift. **Note:** MONDO / PharmGKB / ARO cross-ontology mappings live only in the 25-entry curated atlas (`examples/atlas/atlas.json`), not in the 11,590-row index. |
| Coverage gate enforced at 100% line + branch. | `pyproject.toml` `[tool.coverage.report]` block sets `fail_under = 100`; the suite measures 100.00% line + branch across all six source files (three branches carry justified `# pragma: no cover` for genuinely-unreachable import-time / defensive fallbacks). Reproduce: `pytest tests/unit tests/property tests/client tests/contract --cov=uniprot_mcp --cov-branch --cov-report=term-missing`. |
| Mutation testing infrastructure ships; per-module raw kill rates measured for `cache` 82 % (≈100 % behavioural, the 5 survivors are docstring), `proteinchem` 92 % (228/249), `client` 70 % (259/370 after the two-phase sync + async killer uplift); `formatters` and `server` partial pending bisection. | `.github/workflows/mutation.yml` (matrix per src/ file); `docs/MUTATION_SCORES.md` carries the full per-module table + survivor breakdown + v1.2.0 uplift action items. The ≥ 95 % gate is the v1.2.0 target, not the current state. |

## What is honest about this project

| Limitation | Disclosure |
|---|---|
| Coverage dipped from the v1.0.0 100% across the v1.1.x clinical/biomedical work (down to 92.20% on `main`); it is now restored to 100% line + branch with the gate enforcing it. | `pyproject.toml` `[tool.coverage.report]` (`fail_under = 100`) + the coverage-gap test files under `tests/unit/`. |
| Mutation testing gate is 0.0 today, not 95%. Per-module raw rates as of `0403c0e` are `cache` 82 %, `proteinchem` 92 %, `client` 70 %; `formatters` + `server` partial. | `docs/MUTATION_SCORES.md` carries the full table + the v1.2.0 path to ≥ 95 %. |
| The atlas is a research-demonstration corpus, not an authoritative ontology. Some MONDO IDs are approximate matches. | `examples/atlas/METHODOLOGY.md` enumerates what is machine-verified vs community-reviewable; invites issue reports. |
| Mature-chain numbering offsets (HBB E6V vs E7V; GBA N370S vs N409S) are surfaced explicitly per atlas entry. | `examples/atlas/hbb.md`, `examples/atlas/gba.md`. |
| `uniprot-mcp` does not replace UniProt; it is a client of it. | `docs/COMPETITIVE_LANDSCAPE.md` honest survey of where this fits. |

## What makes this differ from other bio-MCPs

[`docs/COMPETITIVE_LANDSCAPE.md`](docs/COMPETITIVE_LANDSCAPE.md) is the
honest survey (14 servers reviewed on 2026-04-26). To my knowledge
no other bio-MCP server has all of:

1. Per-response SHA-256 of canonical response body
2. A `provenance_verify` primitive with five enumerated verdicts
3. `--pin-release=YYYY_MM` strict release pinning
4. Local cache + offline replay
5. Pre-registered SHA-256-committed benchmark on `main`
6. SLSA + Sigstore + CycloneDX SBOM on every release artefact

This is the auditable-and-reproducible niche that the rest of the
bio-MCP space currently does not fill. Other servers (BioMCP at 497
stars; Augmented-Nature on Smithery) have broader scope or more atomic
tools; this one is narrower but stronger on the provenance dimension.

## How to verify everything in one command

```bash
bash scripts/replicate.sh   # POSIX
# or
pwsh scripts/replicate.ps1  # Windows
```

The script:

1. Downloads `uniprot-mcp-server==1.1.8` from PyPI (override with the `VERSION` env var to pin any released version); SHA-256s it.
2. Cross-checks that hash against PyPI's API + the GitHub Release
   asset + the SLSA build-provenance subject digest. **All four must
   match.**
3. Runs `gh attestation verify` to confirm SLSA build provenance is
   cryptographically valid.
4. Installs in an isolated venv, runs `uniprot-mcp --self-test`
   (live UniProt fetch).
5. Re-derives all 30 benchmark prompts from live UniProt and prints
   them, confirming they are reproducible from the primary source (this
   step does not recompute the committed seal; the full cryptographic
   check is the maintainer path with the local `expected.jsonl`).

Exit code 0 ⇔ every step passed ⇔ the wheel you'd get from PyPI is
provably the one this repo built.

## Author

Santiago Maniches — ORCID
[0009-0005-6480-1987](https://orcid.org/0009-0005-6480-1987) —
TOPOLOGICA LLC.

## License + citation

Apache-2.0. If this software contributes to your work please cite
via [`CITATION.cff`](CITATION.cff). Always also cite the UniProt
Consortium ([doi:10.1093/nar/gkae1010](https://doi.org/10.1093/nar/gkae1010)).

## Roadmap (honest — not commitments)

The natural next pieces for the same author:

1. **`clinvar-mcp`** — same provenance/verify discipline, ClinVar
   release ID + per-record digest. Currently only as a sub-route
   inside meta-routers.
2. **`pdb-mcp`** — direct RCSB with mmCIF / structure-factor digest.
3. **Mutation testing measurement complete** across all six modules
   (per-test-file scoping replaces full-suite-per-mutant).
4. **Atlas expansion** — extend the curated 25 entries; the
   comprehensive index already covers 11,590 rows automatically,
   but additional hand-curated entries demonstrate specific
   research workflows.
