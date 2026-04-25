# uniprot-mcp

[![CI](https://github.com/smaniches/uniprot-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/smaniches/uniprot-mcp/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP compatible](https://img.shields.io/badge/MCP-compatible-6e56cf.svg)](https://modelcontextprotocol.io/)
[![287 tests](https://img.shields.io/badge/tests-287_offline_%2B_4_live-success)](#testing)
[![Provenance: SHA-256 + verify](https://img.shields.io/badge/provenance-SHA--256_+_verify-blue)](#provenance--verification)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0005--6480--1987-A6CE39?logo=orcid&logoColor=white)](https://orcid.org/0009-0005-6480-1987)

A reference-quality **Model Context Protocol** server for the
[UniProt](https://www.uniprot.org) protein knowledgebase. **28 tools.**
Every successful response carries a verifiable `Provenance` record —
UniProt release, retrieval timestamp, resolved URL, and a SHA-256 of
the canonical response body — that the agent (or a third party, a year
later) can re-check with a single tool call: `uniprot_provenance_verify`.

> Author: **Santiago Maniches** · ORCID [0009-0005-6480-1987](https://orcid.org/0009-0005-6480-1987) · TOPOLOGICA LLC

---

## What makes this different

| | uniprot-mcp | Vanilla LLM + WebFetch | A typical bio-MCP |
|---|---|---|---|
| Tool surface | **28 tools, 11 endpoint families** | none — caller writes URLs | usually 5–10 |
| Provenance on every response | release • date • URL • SHA-256 | none | sometimes URL only |
| Per-query auditability | `uniprot_provenance_verify` re-checks any prior response | not possible | not possible |
| Release pinning | `--pin-release=YYYY_MM` raises on drift | n/a | n/a |
| Pre-registered benchmark | 30 prompts, SHA-256 committed on `main` | n/a | n/a |
| Input validation | regex + length cap before any HTTP call | none | partial |
| Error-channel safety | upstream exception text never echoed to LLM | n/a | partial |
| Supply chain | SLSA build provenance + Sigstore + CycloneDX SBOM | n/a | rare |
| Test layers | unit + property + contract + client + integration | n/a | usually unit only |
| Mutation testing target | ≥ 95 % kill (gated, not aspirational) | n/a | rare |

The **provenance + verify** chain is the single feature nothing else
in the bio-MCP space currently has. A regulated user can take any
prior `uniprot-mcp` answer and prove — without contacting the author
— that UniProt still returns the same bytes, or detect exactly how the
upstream has drifted.

---

## Tools (28)

Eleven endpoint families. All read-only (`readOnlyHint: true`,
`openWorldHint: true`). No UniProt API key required.

### Core UniProtKB (10)

| Tool | Purpose |
|---|---|
| `uniprot_get_entry` | Full UniProt entry (e.g. `P04637` for p53). Function, gene, organism, disease, cross-refs. |
| `uniprot_search` | UniProt query language — gene, organism, taxon ID, reviewed flag, free text. |
| `uniprot_get_sequence` | FASTA. PIR-style provenance comment block above the first record (BLAST+ / biopython compatible). |
| `uniprot_get_features` | Domains, binding sites, PTMs, signal peptides — optional type filter. |
| `uniprot_get_variants` | Natural variants and disease mutations. |
| `uniprot_get_go_terms` | GO annotations grouped by aspect (F / P / C). |
| `uniprot_get_cross_refs` | Raw cross-references to PDB, Pfam, ENSEMBL, Reactome, KEGG, STRING … |
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
| `uniprot_resolve_alphafold` | AlphaFold model id + EBI viewer URL. |
| `uniprot_resolve_interpro` | InterPro signatures: id + entry name. |
| `uniprot_resolve_chembl` | ChEMBL drug-target id + EBI target-card URL. |

### Provenance & verification (2)

| Tool | Purpose |
|---|---|
| `uniprot_get_evidence_summary` | Aggregate ECO codes across an entry's annotations. Distinguishes wet-lab confirmed from inferred-by-similarity from automatic. |
| `uniprot_provenance_verify` | Re-fetch a recorded URL and compare release tag + canonical response SHA-256. Five verdicts: `verified`, `release_drift`, `hash_drift`, `release_and_hash_drift`, `url_unreachable`. |

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
pip install uniprot-mcp        # once published
# or, for a pinned, isolated install:
uvx uniprot-mcp
```

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

### Claude Code (CLI)

```bash
claude mcp add uniprot -- uniprot-mcp
```

### Self-test (live UniProt smoke check)

```bash
uniprot-mcp --self-test
# [tools] registered: 28/28
# [live] P04637 -> TP53 OK
# [PASS]
```

---

## Example workflows

**1. Drug target with structural + ChEMBL + AlphaFold context.**

```
> Resolve PDB structures, AlphaFold model, and ChEMBL drug-target records for human TP53 (P04637).
→ uniprot_resolve_pdb("P04637")
→ uniprot_resolve_alphafold("P04637")
→ uniprot_resolve_chembl("P04637")
```

**2. Variant landscape, evidence-quality-aware.**

```
> List p53 variants and tell me how many annotations are wet-lab confirmed vs inferred.
→ uniprot_get_variants("P04637")
→ uniprot_get_evidence_summary("P04637")
```

**3. Reference proteome characterisation.**

```
> Summarise the human reference proteome — protein count, BUSCO completeness, components.
→ uniprot_get_proteome("UP000005640")
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

---

## Testing

| Layer | Path | What |
|---|---|---|
| Unit | `tests/unit/` | Behaviour of every public function. |
| Property | `tests/property/` | Hypothesis-driven invariants on regexes + query construction. |
| Contract | `tests/contract/` | Manifest / pyproject / docs / incident-policy / benchmark drift prevention. |
| Client | `tests/client/` | Retry / back-off / id-mapping polling against `respx`-mocked HTTP. |
| Integration | `tests/integration/` | Live UniProt; opt-in via `--integration`. |
| Benchmark | `tests/benchmark/` | 30 SHA-256-committed prompts + reproducible verifier. |

**287 offline + 4 live integration tests, all green.** Mypy (strict),
ruff (check + format), bandit, pip-audit (`--strict`) all clean.
Mutation testing (mutmut) gate ≥ 95 % kill, populated post-billing-reset.

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
  threats, each receipt-anchored to a code path or commit SHA.
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
