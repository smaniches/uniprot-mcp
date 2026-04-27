# Competitive landscape — bio-MCP servers (April 2026)

This page records what `uniprot-mcp` does that other Model Context
Protocol servers in the biomedical space do not, *as observed on
2026-04-26*. The bio-MCP ecosystem is moving fast; the table below
will be updated when changes are detected. **If you are the author of
one of these servers and an entry is wrong or out of date, please
file an issue and I will correct it.**

The point of this page is not to disparage any other server — most
are excellent at what they do, with broader scope or larger user
bases than `uniprot-mcp`. The point is to be specific about the
*intersection* of features the regulated-bio-pharma niche cares
about, so an adopter can pick the right tool for their workflow.

## Survey

| Server | Domain | Tools | License | Last push (2026-04-26) | Per-response SHA-256 | Verify primitive | Release pinning | SLSA / Sigstore / SBOM | `.well-known/mcp.json` |
|---|---|---|---|---|---|---|---|---|---|
| **smaniches/uniprot-mcp** (this) | UniProt + AlphaFold + ClinVar | **41** | Apache-2.0 | 2026-04-26 | **Yes** | **Yes** (`uniprot_provenance_verify`) | **Yes** (`--pin-release`) | **Yes** (release.yml ships SLSA + Sigstore + CycloneDX) | **Yes** |
| genomoncology/biomcp | meta-router (gene/variant/trial/drug/protein/disease/...) | ~30+ over 40+ upstreams | MIT | 2026-04-26 | No (installer SHA-256 only) | No | No | No | No |
| Augmented-Nature/UniProt-MCP-Server | UniProt | 26 | Custom (NOASSERTION) | 2025-12-21 | No | No | No | No | No |
| TakumiY235/uniprot-mcp-server | UniProt | ~5 | none | 2025-03-11 | No | No | No | No | No |
| BioContext/UniProt-MCP | UniProt | small | — | — | No | No | No | No | No |
| QuentinCody/uniprot-mcp-server | UniProt | small | — | — | No | No | No | No | No |
| Augmented-Nature/AlphaFold-MCP-Server | AlphaFold DB | 22 | MIT | 2025-12-21 | No | No | No | No | No |
| longevity-genie/biothings-mcp | mygene/myvariant/mychem | ~15 | MIT | 2025-11-03 | No | No | No | No | No |
| longevity-genie/gget-mcp | gget wrapper (BLAST/AlphaFold/Enrichr) | ~15 | MIT | 2026 | No | No | No | No | No |
| cyanheads/pubmed-mcp-server | NCBI E-utilities | 9 | Apache-2.0 | 2026-04-25 | No | No | No | No | No |
| openags/paper-search-mcp | arXiv/PubMed/bioRxiv | ~10 | MIT | 2026-04-21 | No | No | No | No | No |
| JamesANZ/medical-mcp | FDA/WHO/PubMed/RxNorm | ~12 | MIT | 2026-02-18 | No | No | No | No | No |
| Cicatriiz/healthcare-mcp | FDA/PubMed/medRxiv/ICD-10 | ~15 | MIT | 2025-08-16 | No | No | No | No | No |
| Proprius-Labs/pocketscout-mcp | UniProt+PDB+AlphaFold+ChEMBL+PubMed druggability | small | MIT | 2026-03-13 | No | No | No | No | No |
| donbr/lifesciences-research | OpenTargets/ChEMBL/UniProt agent wrappers | small | MIT | 2026-02-26 | No | No | No | No | No |

ClinVar-specific MCP and a ChEMBL-only MCP were not found as standalone servers — only as facets of meta-routers.

## What `uniprot-mcp` does that no surveyed bio-MCP does

1. **Per-response SHA-256 + canonicalised `Provenance` footer** on every tool result (release tag, retrieval timestamp, resolved URL, body digest). No other bio-MCP scanned attaches a body digest. BioMCP attaches an installer SHA-256 only.
2. **`uniprot_provenance_verify` re-fetch primitive** with five enumerated verdicts (`verified`, `release_drift`, `hash_drift`, `release_and_hash_drift`, `url_unreachable`) and per-verdict advice. GitHub code search across repos finds zero other implementations of `provenance_verify` / `hash_drift` / `release_drift` semantics.
3. **`UNIPROT_PIN_RELEASE` / `--pin-release=YYYY_MM` release pinning** that raises on drift inside the running server. Not present in any competitor README.
4. **`uniprot_target_dossier` nine-section composition** (identity / function / chemistry / structure / drug-target / disease / variants / functional annotations / cross-refs) in one call.
5. **`uniprot_lookup_variant` (HGVS) + `uniprot_features_at_position` + `uniprot_get_alphafold_confidence` (pLDDT bands) + `uniprot_resolve_clinvar`**, all chained with the same provenance envelope.
6. **`UNIPROT_MCP_CACHE_DIR` offline replay** (`uniprot_replay_from_cache`) for air-gapped re-runs.
7. **SLSA build provenance + Sigstore keyless signatures + CycloneDX SBOM** on every release artefact. PyPI Trusted Publishing (OIDC) — no long-lived API tokens. Not present in any competitor scanned.
8. **Pre-registered benchmark with SHA-256 commitments on `main`** (`tests/benchmark/expected.hashes.jsonl`) — reviewer cannot rewrite "correct" answers post-hoc. 30 prompts; v1.1.0 measured run at 30/30.

## Honest weaknesses vs alternatives

- **Scope**: BioMCP is bigger surface area (13 entities, 40+ upstreams). `uniprot-mcp` is single-database (UniProt) plus two cross-origin enrichments (AlphaFold DB, NCBI eutils for ClinVar).
- **Tool overlap on basics**: search / get-entry / sequence / GO / cross-refs are commodity; ~25 of the 41 tools are commodity wrappers and ~16 tools are the differentiated layer (provenance, verify, dossier, position-aware features, biomedical features, cache).
- **Distribution presence**: BioMCP is in the Anthropic Connectors Directory; Augmented-Nature is on Smithery. As of 2026-04-26 `uniprot-mcp` is on PyPI but not yet listed in either directory.
- **Adoption**: BioMCP has 497 GitHub stars; `uniprot-mcp` has 1. The Zenodo DOI argument is artefact merit, not adoption.

## Adjacencies the same author could pursue

(documented for future planning, not commitments)

1. **`clinvar-mcp`** — same provenance/verify discipline, ClinVar release ID + per-record digest. Currently only available as a sub-route inside biothings-mcp / BioMCP.
2. **`pdb-mcp`** — direct RCSB with mmCIF / structure-factor digest. Currently only available as part of BioMCP and Augmented-Nature.
3. **`ensembl-mcp`** — gget wraps it, but no dedicated server.
4. **`reactome-mcp`** / **`kegg-mcp`** — pathway resources, no dedicated server.

## Method

The survey was performed via:

- GitHub code search: `bio mcp`, `uniprot mcp`, `bioinformatics mcp`, `provenance_verify`, `hash_drift`, `release_drift`.
- MCP Registry (registry.modelcontextprotocol.io) browse.
- Smithery (smithery.ai) bio category browse.
- Anthropic Connectors Directory.
- PyPI search for `*-mcp` packages.

Each candidate's README was read for: per-response digest behaviour, verify-style primitives, release-pinning semantics, supply-chain attestations. Where the README was ambiguous, the source was inspected.

If you find a server I missed, **please file an issue**. I will update this page and adjust the README's claim accordingly.
