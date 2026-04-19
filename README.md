# uniprot-mcp

[![CI](https://github.com/smaniches/uniprot-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/smaniches/uniprot-mcp/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP compatible](https://img.shields.io/badge/MCP-compatible-6e56cf.svg)](https://modelcontextprotocol.io/)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0005--6480--1987-A6CE39?logo=orcid&logoColor=white)](https://orcid.org/0009-0005-6480-1987)

A **Model Context Protocol** server that gives LLM agents (Claude, and any
other MCP-compatible client) first-class, typed access to the
[UniProt](https://www.uniprot.org) protein knowledgebase — 250M+ entries
covering sequences, functions, domains, variants, cross-references, and
taxonomy.

Designed as a reference-quality MCP: strict input validation, mocked
offline tests, opt-in live-API integration tests, type-checked sources,
and machine-verifiable MCP protocol conformance.

> Author: **Santiago Maniches** · ORCID [0009-0005-6480-1987](https://orcid.org/0009-0005-6480-1987) · TOPOLOGICA LLC

---

## Tools (10)

| Tool | Purpose |
| --- | --- |
| `uniprot_get_entry` | Fetch a full UniProt entry by accession (e.g. `P04637` for p53). Returns function, gene, organism, disease associations, cross-references. |
| `uniprot_search` | Query UniProtKB with the full UniProt query syntax; filter for Swiss-Prot and/or organism. |
| `uniprot_get_sequence` | Protein sequence in FASTA format. |
| `uniprot_get_features` | Domains, binding sites, PTMs, signal peptides — optional type filter. |
| `uniprot_get_variants` | Natural variants and disease mutations. |
| `uniprot_get_go_terms` | GO annotations grouped by aspect (F / P / C). |
| `uniprot_get_cross_refs` | Cross-references to PDB, Pfam, ENSEMBL, Reactome, KEGG, STRING, … |
| `uniprot_id_mapping` | Map IDs between databases (Gene_Name → UniProtKB, PDB → UniProtKB, …). |
| `uniprot_batch_entries` | Fetch up to 100 entries in one call; invalid accessions filtered client-side. |
| `uniprot_taxonomy_search` | Search UniProt taxonomy by organism name. |

All tools are read-only (`readOnlyHint: true`) and interact with an
external system (`openWorldHint: true`). No UniProt API key is required.

---

## Install

```bash
pip install uniprot-mcp        # once published
# or, for a pinned, isolated install:
uvx uniprot-mcp
```

Until the PyPI release, install from source:

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
      "command": "python",
      "args": ["-m", "server"],
      "cwd": "/absolute/path/to/uniprot-mcp"
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add uniprot -- python /absolute/path/to/uniprot-mcp/server.py
```

---

## Example workflows

**1. Characterise a drug target.**

```text
> What does UniProt say about BRCA1, and which PDB structures are available?
→ uniprot_get_entry("P38398")
→ uniprot_get_cross_refs("P38398", database="PDB")
```

**2. Variant landscape for p53.**

```text
> List the top disease-associated variants of TP53.
→ uniprot_get_variants("P04637")
```

**3. Cross-database enrichment for a gene list.**

```text
> Map BRCA1, TP53, EGFR to UniProt, then pull GO molecular function.
→ uniprot_id_mapping("BRCA1,TP53,EGFR", "Gene_Name", "UniProtKB")
→ uniprot_get_go_terms("P38398", aspect="F")
```

---

## Development

```bash
pip install -e ".[test,dev]"
pre-commit install

# Fast, offline (what CI runs on every push):
pytest tests/unit tests/property tests/client tests/contract -v

# Live UniProt (opt-in, nightly in CI):
pytest --integration tests/integration -v

# Lint / type-check:
ruff check . && ruff format --check .
mypy client.py server.py formatters.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

---

## Design principles

- **No unverified claim ships.** Each tool has unit, property, and
  integration tests. Live API responses are recorded in
  `tests/fixtures/` with a `_meta` block carrying timestamp and UniProt
  release.
- **Offline tests are hermetic.** `pytest-socket` blocks real network
  everywhere except `tests/integration/`.
- **Property-based invariants.** Hypothesis checks that `ACCESSION_RE`
  and `batch_entries` obey their specification on arbitrary input, not
  just cherry-picked examples.
- **MCP conformance is machine-verified.** `tests/integration/test_mcp_protocol.py`
  spawns the server as a subprocess, speaks JSON-RPC 2.0, and validates
  every tool schema.

---

## Citation

If this software contributes to a publication, please cite via the
[`CITATION.cff`](CITATION.cff) metadata (GitHub renders a "Cite this
repository" button).

Always also cite the UniProt Consortium:

> The UniProt Consortium. *UniProt: the Universal Protein Knowledgebase
> in 2025.* Nucleic Acids Research (2025).
> [doi:10.1093/nar/gkae1010](https://doi.org/10.1093/nar/gkae1010)

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

Copyright © 2026 Santiago Maniches. TOPOLOGICA LLC.
