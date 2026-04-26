# uniprot-mcp

[![CI](https://github.com/smaniches/uniprot-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/smaniches/uniprot-mcp/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP compatible](https://img.shields.io/badge/MCP-compatible-6e56cf.svg)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-411_offline_%2B_35_live-success)](#testing)
[![Provenance: SHA-256 + verify](https://img.shields.io/badge/provenance-SHA--256_+_verify-blue)](#provenance--verification)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0005--6480--1987-A6CE39?logo=orcid&logoColor=white)](https://orcid.org/0009-0005-6480-1987)

A **Model Context Protocol** server for the
[UniProt](https://www.uniprot.org) protein knowledgebase with
**per-query provenance verification**. **41 tools** across 8
families. Apache-2.0. Every successful response carries a verifiable
`Provenance` record — UniProt release, retrieval timestamp, resolved
URL, and a SHA-256 of the canonical response body — that the agent
(or a third party, a year later) can re-check with a single tool
call: `uniprot_provenance_verify`.

The wedge: **per-response SHA-256 + verify primitive + release pinning
+ offline replay** is, to the best of my survey of public MCPs as of
2026-04-26, absent from every other bio-MCP server I could find
(BioMCP, Augmented-Nature/UniProt-MCP, biothings-mcp, gget-mcp, and
others). If you are a regulated-bio-pharma user who needs to prove,
years later, that a UniProt-derived claim still holds, this is the
mechanism. Comparison and citations: [docs/COMPETITIVE_LANDSCAPE.md](docs/COMPETITIVE_LANDSCAPE.md).

> Author: **Santiago Maniches** · ORCID [0009-0005-6480-1987](https://orcid.org/0009-0005-6480-1987) · TOPOLOGICA LLC

---

## What makes this different

| | uniprot-mcp | Vanilla LLM + WebFetch | A typical bio-MCP |
|---|---|---|---|
| Tool surface | **41 tools, 8 families** | none — caller writes URLs | usually 5–10 |
| Provenance on every response | release • date • URL • SHA-256 | none | sometimes URL only |
| Per-query auditability | `uniprot_provenance_verify` re-checks any prior response | not possible | not possible |
| Release pinning | `--pin-release=YYYY_MM` raises on drift | n/a | n/a |
| Pre-registered benchmark | 30 prompts, SHA-256 committed on `main` + reproducible verifier | n/a | n/a |
| Local provenance cache | offline replay via `UNIPROT_MCP_CACHE_DIR` | n/a | n/a |
| Clinical primitives | sequence chemistry / position-aware features / HGVS variant lookup / disease associations / AlphaFold pLDDT / ClinVar | none | none |
| Composition tool | `uniprot_target_dossier` — one call, nine sections | n/a | n/a |
| Input validation | regex + length cap before any HTTP call | none | partial |
| Error-channel safety | upstream exception text never echoed to LLM | n/a | partial |
| Cross-origin allowlist | enumerated, threat-modelled, privacy-listed | n/a | usually unaudited |
| Supply chain | SLSA build provenance + Sigstore + CycloneDX SBOM (post-flip) | n/a | rare |
| Test layers | unit + property + contract + client + integration + benchmark | n/a | usually unit only |
| Mutation testing | weekly + on-demand workflow; baseline measurement on v1.1.0; ≥ 95 % gate planned post-baseline | n/a | rare |

The **provenance + verify** chain is, in my 2026-04-26 survey, absent
from every other bio-MCP I could find. A regulated user can take any
prior `uniprot-mcp` answer and prove — without contacting the author
— that UniProt still returns the same bytes, or detect exactly how the
upstream has drifted. If you find a counter-example I missed, please
file an issue and I will update the comparison.

---

## Tools (41)

Eight endpoint families. All read-only (`readOnlyHint: true`). All
but `uniprot_replay_from_cache` interact with at least one upstream
service (`openWorldHint: true`). No UniProt API key required.

### Core UniProtKB (10)

| Tool | Purpose |
|---|---|
| `uniprot_get_entry` | Full UniProt entry (e.g. `P04637` for p53). Function, gene, organism, disease, cross-refs. |
| `uniprot_search` | UniProt query language — gene, organism, taxon ID, reviewed flag, free text. |
| `uniprot_get_sequence` | FASTA. PIR-style provenance comment block above the first record (BLAST+ / biopython compatible). |
| `uniprot_get_features` | Domains, binding sites, PTMs, signal peptides — optional type filter. |
| `uniprot_get_variants` | Natural variants and disease mutations. |
| `uniprot_get_go_terms` | GO annotations grouped by aspect (F / P / C). |
| `uniprot_get_cross_refs` | Raw cross-references to PDB, Pfam, Ensembl, Reactome, KEGG, STRING … |
| `uniprot_id_mapping` | Map IDs between databases (Gene_Name → UniProtKB, PDB → UniProtKB, …). |
| `uniprot_batch_entries` | Up to 100 entries in one call; invalid accessions filtered client-side. |
| `uniprot_taxonomy_search` | Search UniProt taxonomy by organism name. |

### Controlled vocabularies (4)

| Tool | Purpose |
|---|---|
| `uniprot_get_keyword` | Keyword by ID (e.g. `KW-0007` = Acetylation). Definition, synonyms, GO refs, hierarchy. |
| `uniprot_search_keywords` | Free-text keyword search. |
| `uniprot_get_subcellular_location` | Subcellular-location term by ID (e.g. `SL-0039` = Cell membrane). |
| `uniprot_search_subcellular_locations` | Free-text location search. |

### Sequence archives & clusters (4)

| Tool | Purpose |
|---|---|
| `uniprot_get_uniref` | UniRef cluster by ID (`UniRef50_P04637`, `UniRef90_P04637`, `UniRef100_P04637`). |
| `uniprot_search_uniref` | Cluster search with `identity_tier` filter (50 / 90 / 100). |
| `uniprot_get_uniparc` | Sequence-archive record by UPI (`UPI000002ED67`). |
| `uniprot_search_uniparc` | UniParc full-text search. |

### Proteomes & literature (4)

| Tool | Purpose |
|---|---|
| `uniprot_get_proteome` | Proteome by UP ID (`UP000005640` = human). Counts, BUSCO score, components. |
| `uniprot_search_proteomes` | Filter by organism / type / completeness. |
| `uniprot_get_citation` | Citation record by ID (typically a PubMed numeric ID). |
| `uniprot_search_citations` | Index search across UniProt citations. |

### Structured cross-DB resolvers (4)

Gateway-only — no calls leave the UniProt origin. These extract the
relevant cross-references from a UniProt entry and return *structured*
records (typed lists / objects, not passthrough strings).

| Tool | Purpose |
|---|---|
| `uniprot_resolve_pdb` | PDB structures: id + method + resolution + chain coverage. |
| `uniprot_resolve_alphafold` | AlphaFold model id + EBI viewer URL (model id only — for pLDDT call the dedicated tool below). |
| `uniprot_resolve_interpro` | InterPro signatures: id + entry name. |
| `uniprot_resolve_chembl` | ChEMBL drug-target id + EBI target-card URL. |

### Biomedical features (7)

Pure-Python compositions over the entry — no extra origin. The first
four answer per-residue and per-variant questions; the last three are
the v1.1.0 expansion targeting drug discovery, therapeutic-protein
engineering, and pathogen-secretion analysis: each is a filter over the
entry's `features` array, with a structured grouping by feature type
and an honest empty-set advisory.

| Tool | Purpose |
|---|---|
| `uniprot_compute_properties` | Derived sequence chemistry from the FASTA: MW / pI / GRAVY / aromaticity / charge / ε₂₈₀. |
| `uniprot_features_at_position` | Every feature overlapping a residue position. Critical for variant-effect interpretation. |
| `uniprot_lookup_variant` | HGVS-shorthand match (`R175H`, `V600E`, `R248*`) against UniProt's natural-variant features. |
| `uniprot_get_disease_associations` | Structured disease records from DISEASE-type comments: name + acronym + UniProt disease ID + OMIM cross-ref + description. |
| `uniprot_get_active_sites` | Catalytic and ligand-binding residues: active sites, binding sites, sites, metal binding, DNA binding. The residue-level chemistry of the protein. |
| `uniprot_get_processing_features` | Maturation features: signal peptide, propeptide, transit peptide, initiator methionine, chain, peptide. Essential for therapeutic-protein engineering and pathogen-secretion analysis. |
| `uniprot_get_ptms` | Post-translational modifications: modified residues (phospho/acetyl/methyl), glycosylation, lipidation (GPI/prenyl/palmitoyl), disulfide bonds, cross-links. |

### Cross-origin enrichment (3)

The only tools that consult origins outside `rest.uniprot.org`. Each is documented in [`PRIVACY.md`](PRIVACY.md) and in the [threat model](docs/THREAT_MODEL.md#t3b-cross-origin-allowlist-for-non-uniprot-endpoints).

| Tool | Origin | Purpose |
|---|---|---|
| `uniprot_get_alphafold_confidence` | `alphafold.ebi.ac.uk` | pLDDT mean + four-band distribution; lets the agent decide whether to trust the model. |
| `uniprot_resolve_clinvar` | `eutils.ncbi.nlm.nih.gov` | ClinVar significance + condition + review status by gene + optional HGVS shorthand. |
| `uniprot_get_publications` | `rest.uniprot.org` | Pure-Python over the entry's references — listed here because it complements the cross-origin enrichment. |

### Composition + provenance (5)

| Tool | Purpose |
|---|---|
| `uniprot_resolve_orthology` | Group orthology cross-references by source DB (KEGG / OMA / OrthoDB / eggNOG / 8 more). |
| `uniprot_get_evidence_summary` | Aggregate ECO codes (Evidence and Conclusion Ontology) across an entry. Distinguishes wet-lab confirmed from inferred-by-similarity from automatic. |
| `uniprot_target_dossier` | One-call comprehensive characterisation: nine sections — identity / function / chemistry / structure / drug-target / disease / variants / functional annotations / cross-refs. |
| `uniprot_provenance_verify` | Re-fetch a previously recorded URL and compare release tag + canonical response SHA-256. Five verdicts (`verified`, `release_drift`, `hash_drift`, `release_and_hash_drift`, `url_unreachable`) each with an advice string. |
| `uniprot_replay_from_cache` | Read a cached UniProt response without hitting the upstream. Opt-in via `UNIPROT_MCP_CACHE_DIR`. |

---

## Provenance & verification

Every successful tool response includes a footer like:

```
---
_Source: UniProt release 2026_01 (28-January-2026) • Retrieved 2026-04-25T17:09:00Z_
_Query: https://rest.uniprot.org/uniprotkb/P04637_
_SHA-256: 0040d79bb39e2f7386d55f81071e87858ec2e5c2cd9552e93c3633897f78345e_
```

A year later, an auditor can call `uniprot_provenance_verify` with
those exact fields:

```
> uniprot_provenance_verify(
    url="https://rest.uniprot.org/uniprotkb/P04637",
    release="2026_01",
    response_sha256="0040d79bb39e2f7386d55f81071e87858ec2e5c2cd9552e93c3633897f78345e"
  )

## Provenance Verification

**Status:** verified

**URL:** https://rest.uniprot.org/uniprotkb/P04637
- ✓ URL resolves (HTTP 200)
- ✓ Release: recorded '2026_01', current '2026_01'
- ✓ Response SHA-256: recorded 0040d79bb39e2f73…, current 0040d79bb39e2f73…

**Advice:** Both checks passed. The recorded provenance is reproducible against the live UniProt API.
```

If UniProt has moved on, the tool tells you exactly how:

| Verdict | Meaning | Advice |
|---|---|---|
| `verified` | Both release and hash match | The provenance is reproducible |
| `release_drift` | UniProt released a new version | Pin via the FTP snapshot if you need the historical answer |
| `hash_drift` | Same release, body changed | An in-release edit; investigate or re-fetch |
| `release_and_hash_drift` | Both moved on | Use a release-specific FTP snapshot |
| `url_unreachable` | Endpoint dropped or rate-limited | Retry or report to UniProt |

For strict reproducibility, opt into release pinning:

```bash
export UNIPROT_PIN_RELEASE=2026_01
uniprot-mcp
# every response is checked against the pinned release;
# any drift raises `ReleaseMismatchError`, which the server surfaces
# as an agent-actionable error envelope.
```

For offline replay (post-cache-population):

```bash
export UNIPROT_MCP_CACHE_DIR=~/.uniprot-mcp-cache
uniprot-mcp
# every successful response is mirrored to disk; later replay via
# uniprot_replay_from_cache(url) without touching the upstream.
```

A live end-to-end demonstration is committed at
[`tests/benchmark/run-2026-04-25-roundtrip/transcript.md`](tests/benchmark/run-2026-04-25-roundtrip/transcript.md)
— real values, real verdicts, no mocks.

---

## Pre-registered benchmark

`tests/benchmark/` ships a 30-prompt evaluation (Tier A / B / C × 10)
with **SHA-256-committed expected answers** on `main`. The plaintext
`expected.jsonl` is held local-only until a benchmark run is
published; the cryptographic commitments mean the author cannot
rewrite "correct" answers post-hoc.

A reviewer can re-derive every Tier A and B answer from primary-source
UniProt REST in two commands:

```bash
python tests/benchmark/verify_answers.py tests/benchmark/expected.jsonl
# OK: all 30 prompts verified against https://rest.uniprot.org

python tests/benchmark/verify.py tests/benchmark/expected.jsonl tests/benchmark/expected.hashes.jsonl
# OK: 30 commitments verified
```

See [`tests/benchmark/AUDIT.md`](tests/benchmark/AUDIT.md) for the
per-prompt source attribution and the formal independence statement
(`uniprot-mcp` was *not* used during answer authoring).

---

## Install

```bash
pip install uniprot-mcp-server   # PyPI distribution
# or, for a pinned, isolated install:
uvx --from uniprot-mcp-server uniprot-mcp
```

> **Why three different names?** This is the standard Python packaging pattern, exactly because PyPI's namespace is global and collisions force disambiguation:
>
> | Concept | Value | What it is |
> |---|---|---|
> | GitHub repository | `smaniches/uniprot-mcp` | source code + issue tracker |
> | PyPI distribution | `uniprot-mcp-server` | what you `pip install` (the bare `uniprot-mcp` name was already claimed on PyPI when this project published) |
> | Python module | `uniprot_mcp` | what you `import` (PEP-8 underscore form) |
> | Console script + MCP server identity | `uniprot-mcp` | what you run from the shell and what Claude Desktop sees |
>
> Cross-checks that prove the wheel you installed was built from this repo: each release ships a [Sigstore signature](https://www.sigstore.dev/), [SLSA build provenance](https://slsa.dev/), and a [CycloneDX SBOM](https://cyclonedx.org/), all attached to the [v1.1.0 GitHub Release](https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.0). Run `bash scripts/replicate.sh` (POSIX) or `pwsh scripts/replicate.ps1` (Windows) to verify the full chain end-to-end. Common precedents for the same one-thing-three-names pattern: `pillow`/`PIL`, `python-dateutil`/`dateutil`, `beautifulsoup4`/`bs4`, `python-Levenshtein`/`Levenshtein`.

From source:

```bash
git clone https://github.com/smaniches/uniprot-mcp.git
cd uniprot-mcp
pip install -e .
```

### Claude Desktop

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "uniprot": {
      "command": "uniprot-mcp"
    }
  }
}
```

For pinned, reproducibility-grade access:

```json
{
  "mcpServers": {
    "uniprot": {
      "command": "uniprot-mcp",
      "args": ["--pin-release=2026_01"]
    }
  }
}
```

For offline replay via the local provenance cache:

```json
{
  "mcpServers": {
    "uniprot": {
      "command": "uniprot-mcp",
      "env": {
        "UNIPROT_MCP_CACHE_DIR": "/absolute/path/to/cache"
      }
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add uniprot -- uniprot-mcp
```

### Self-test (live UniProt smoke check)

```bash
uniprot-mcp --self-test
# [tools] registered: 41/41
# [live] P04637 -> TP53 OK
# [PASS]
```

---

## Example workflows

**1. Clinical-variant interpretation packet for `TP53 R175H`.**

```
> What's at residue 175 of P04637? Is R175H a known variant? Pull
> the UniProt and ClinVar evidence and tell me how confident the
> AlphaFold model is at that residue.
→ uniprot_features_at_position("P04637", 175)
→ uniprot_lookup_variant("P04637", "R175H")
→ uniprot_resolve_clinvar("P04637", change="R175H")
→ uniprot_get_alphafold_confidence("P04637")
```

**2. Drug-target dossier in one call.**

```
> Give me a complete drug-target characterisation of human BRCA1.
→ uniprot_target_dossier("P38398")
   # nine sections, two upstream calls (entry + FASTA), one tool call.
```

**3. Sequence chemistry for buffer choice / expression-system selection.**

```
> What's the molecular weight, pI, and hydrophobicity of human insulin?
→ uniprot_compute_properties("P01308")
   # MW 11,981 Da, pI 4.93, ε₂₈₀ 24,980 M⁻¹·cm⁻¹ — pure Python on the FASTA.
```

**4. Provenance round-trip — proving an answer is reproducible.**

```
> [later, with the provenance footer from a prior session in hand]
> Verify the recorded provenance for P04637.
→ uniprot_provenance_verify(
    url="https://rest.uniprot.org/uniprotkb/P04637",
    release="2026_01",
    response_sha256="0040d79bb39e2f7386d55f81071e87858ec2e5c2cd9552e93c3633897f78345e"
  )
```

**5. Air-gapped clinical workflow with sealed cache.**

```bash
# Day 1, online: cache populates as queries run.
export UNIPROT_MCP_CACHE_DIR=~/sealed-cache
# … every uniprot-mcp tool call writes to ~/sealed-cache/<sha>.json
# Day N, offline: replay any prior answer.
> uniprot_replay_from_cache("https://rest.uniprot.org/uniprotkb/P04637")
```

---

## Testing

| Layer | Path | What |
|---|---|---|
| Unit | `tests/unit/` | Behaviour of every public function. |
| Property | `tests/property/` | Hypothesis-driven invariants on regexes + query construction. |
| Contract | `tests/contract/` | Manifest / pyproject / docs / incident-policy / benchmark drift prevention. |
| Client | `tests/client/` | Retry / back-off / id-mapping polling against `respx`-mocked HTTP. |
| Integration | `tests/integration/` | Live UniProt + AlphaFold; opt-in via `--integration`. |
| Benchmark | `tests/benchmark/` | 30 SHA-256-committed prompts + reproducible verifier. |

**402 offline + 31 live integration tests, all green.** Mypy (strict),
ruff (check + format), bandit (0 issues at any severity), pip-audit
(`--strict`, no known vulnerabilities) all clean. Mutation testing
(`mutmut`) gate ≥ 95 % kill, populated post-billing-reset.

```bash
# Fast, offline (CI on every push):
pytest tests/unit tests/property tests/client tests/contract -v

# Live UniProt (opt-in, nightly in CI):
pytest --integration tests/integration -v

# Lint / type-check / security / SCA:
ruff check . && ruff format --check . && mypy src/uniprot_mcp
bandit -r src/uniprot_mcp && pip-audit --strict
```

---

## Architecture & threat model

- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — twelve STRIDE-shaped
  threats, each receipt-anchored to a code path or commit SHA, plus
  the cross-origin allowlist policy (§T3b).
- [`docs/INCIDENT_POLICY.md`](docs/INCIDENT_POLICY.md) +
  [`docs/POSTMORTEM_TEMPLATE.md`](docs/POSTMORTEM_TEMPLATE.md) +
  [`docs/INCIDENT_LOG.md`](docs/INCIDENT_LOG.md) — every nightly
  integration breakage triggers a postmortem entry.
- [`AUDIT.md`](AUDIT.md) — pre-1.0.1 professional audit, P0/P1
  remediations recorded.
- [`docs/MERGE_PLAN.md`](docs/MERGE_PLAN.md) — five-phase merge → tag
  → flip operational plan with rollback policy.
- [`docs/PENDING_V1.md`](docs/PENDING_V1.md) — the binary punch list
  to v1.0.1.
- [`mkdocs.yml`](mkdocs.yml) — Material-themed docs site, deployable to
  `gh-pages` via [`.github/workflows/docs.yml`](.github/workflows/docs.yml).
  Build locally with `pip install -e ".[docs]" && mkdocs serve`.

---

## Citation

Cite via [`CITATION.cff`](CITATION.cff) (GitHub renders a "Cite this
repository" button). Always also cite the UniProt Consortium:

> The UniProt Consortium. *UniProt: the Universal Protein Knowledgebase
> in 2025.* Nucleic Acids Research (2025).
> [doi:10.1093/nar/gkae1010](https://doi.org/10.1093/nar/gkae1010)

---

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

This project is the **gateway** layer of the [Topologica
Bio](https://github.com/smaniches) MCP suite. Multi-source
orchestration and tamper-evident provenance ledgers live in the
companion `topologica-bio` repository under BUSL-1.1 (Change Date
2030-04-19, auto-reverts to Apache-2.0). `uniprot-mcp` itself is and
will remain permissively Apache-2.0.

Copyright © 2026 Santiago Maniches. TOPOLOGICA LLC.
