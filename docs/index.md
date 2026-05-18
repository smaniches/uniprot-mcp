# uniprot-mcp

> A reference-quality **Model Context Protocol** server for the
> [UniProt](https://www.uniprot.org) protein knowledgebase.
> **41 tools.** Every successful response carries a verifiable
> `Provenance` record (release · timestamp · URL · canonical SHA-256)
> that the agent (or a third party, a year later) can re-check with
> `uniprot_provenance_verify`.

## What it is

`uniprot-mcp` exposes UniProt's REST surface — and a curated set of
clinical and structural-biology compositions — as **typed, agent-safe
MCP tools**. Two design choices set it apart:

1. **Provenance on every response.** Markdown footer, JSON envelope,
   PIR-style FASTA header — pick your format, the same record is
   embedded. The `uniprot_provenance_verify` tool re-fetches the URL
   and compares the recorded release tag and canonical response
   SHA-256 against today's UniProt; you get one of five distinct
   verdicts (`verified` / `release_drift` / `hash_drift` /
   `release_and_hash_drift` / `url_unreachable`) with advice strings.

2. **Pre-registered, third-party-reproducible benchmark.** 30 prompts
   (Tier A/B/C × 10) sealed via SHA-256 commitments on `main`. A
   reviewer runs `python tests/benchmark/verify_answers.py` to
   re-derive every answer from the live UniProt REST API in two
   commands.

Together these mean a regulated user can take any prior `uniprot-mcp`
answer and prove — **without contacting the author** — that UniProt
still returns the same bytes.

## Tool surface (41)

| Family | Tools | Question it answers |
|---|---|---|
| **Core UniProtKB** | 10 | "what does UniProt say about this protein?" |
| **Controlled vocabularies** | 4 | "what's the canonical KW / SL identifier for X?" |
| **Sequence archives & clusters** | 4 | "what's in this UniRef cluster / UniParc record?" |
| **Proteomes & literature** | 4 | "what is the human reference proteome / who cites this entry?" |
| **Structured cross-DB resolvers** | 4 | "what PDB / AlphaFold / InterPro / ChEMBL records exist?" |
| **Biomedical features** | 7 | "what's at residue 175 / is R175H known / what diseases / what's the chemistry / where are the active sites / how is it processed / what PTMs?" |
| **Cross-origin enrichment** | 3 | "AlphaFold pLDDT / ClinVar significance / publications" |
| **Composition + provenance** | 5 | "give me a full target dossier / verify a recorded provenance / replay from cache / orthology / evidence-quality summary" |

[Full list →](tools.md)

## When to use it

- You're building an LLM agent that needs **citable** UniProt data — not just text the model paraphrases.
- You're writing a regulatory or clinical-research workflow that requires **per-query auditability**.
- You want **reproducibility** across releases — pin via `--pin-release=YYYY_MM` and the client refuses any drift.
- You want to **stop writing UniProt URL strings by hand** and let a typed surface handle accession validation, retry, error envelopes, and rate-limit politeness.

## Quickstart

See the [quickstart guide](quickstart.md). One-liner:

```bash
pip install uniprot-mcp-server   # PyPI distribution; console script is `uniprot-mcp`
uniprot-mcp --self-test
```

## What this project explicitly is not

- **Not** an orchestrator across multiple bio data sources. That's the
  BUSL-1.1 layer in `topologica-bio`. `uniprot-mcp` stays a permissive
  Apache-2.0 gateway forever.
- **Not** a structure-prediction service. AlphaFold confidence is
  surfaced; structure files (CIF/PDB) are URLs the agent can fetch
  separately.
- **Not** a variant-effect predictor. ClinVar significance is
  surfaced; functional impact prediction belongs in dedicated tools
  like Ensembl VEP.
- **Not** a free-tier / freemium ladder. Every tool is and remains
  Apache-2.0.

## Status

| Layer | State |
|---|---|
| Tool surface | **41 tools** across 8 families |
| Tests | **744 offline + 42 live integration** |
| Static analysis | **mypy strict** + **ruff** + **bandit** + **pip-audit** clean |
| Provenance verification | **Live round-trip-tested against real UniProt** |
| Pre-registered benchmark | **30 SHA-256 commitments on `main`** |
| Mutation testing | Workflow shipped (`.github/workflows/mutation.yml`); measurement-first per-module baseline in [`docs/MUTATION_SCORES.md`](MUTATION_SCORES.md). ≥ 95 % kill rate is the v1.2.0 target, not the current state. |
| 3 × 3 CI matrix on `main` | **Green** (Ubuntu / Windows / macOS × Python 3.11 / 3.12 / 3.13) |

[Read the release runbook →](RELEASE.md)

## Citation

```
@software{maniches2026uniprotmcp,
  author = {Maniches, Santiago},
  title = {uniprot-mcp: Reference Model Context Protocol server for the UniProt knowledgebase},
  year = {2026},
  url = {https://github.com/smaniches/uniprot-mcp},
  orcid = {0009-0005-6480-1987}
}
```

Always also cite the UniProt Consortium:

> The UniProt Consortium. *UniProt: the Universal Protein Knowledgebase
> in 2025.* Nucleic Acids Research (2025).
> [doi:10.1093/nar/gkae1010](https://doi.org/10.1093/nar/gkae1010)
