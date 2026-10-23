# UniProt source index (historical snapshot)

This directory retains **source-derived, date-stamped research indexes**. It is not a clinical disease atlas, an ontology reconciliation service, or a drug-treatment reference.

The 25 hand-authored disease/drug example pages and their JSON-LD curated atlas were **removed from the active repository** because treatment status, gene–disease interpretation and suggested mechanisms require independent ongoing scientific review. The examples are not loaded by the MCP runtime. Their historical contents remain available in Git history and immutable archive releases, but are no longer presented as maintained source data.

## Retained datasets

| File | Snapshot scope | Rows |
|---|---|---:|
| [`comprehensive_index.tsv`](comprehensive_index.tsv) | UniProt reviewed human entries with DISEASE comments, source identifiers and metadata | 7,250 |
| [`comprehensive_index_pathogens.tsv`](comprehensive_index_pathogens.tsv) | Selected reviewed pathogen proteins, source identifiers and metadata | 4,340 |
| [`manifest.json`](manifest.json) | File digests, sizes, row counts, extraction script, provenance | — |

These figures describe **the recorded 2026-04-26 snapshot**, not UniProt's current totals or an independently validated clinical truth set. The two files have different grains: rows of human disease–protein associations versus pathogen protein records. They must not be interpreted as a single clinical disease dataset.

For new scientific claims, use the current MCP retrieval tools and verify each source's confidence, review status, date and disease mapping. The local index does **not** assert MONDO equivalence or drug efficacy.

See [METHODOLOGY.md](METHODOLOGY.md) for reproducibility and limits.
