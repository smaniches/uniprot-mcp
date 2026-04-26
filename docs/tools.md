# Tools reference

`uniprot-mcp` ships **38 tools** across eight families. All
read-only (`readOnlyHint: true`). All but `uniprot_replay_from_cache`
interact with at least one upstream service (`openWorldHint: true`).

## Core UniProtKB (10)

| Tool | Purpose |
|---|---|
| `uniprot_get_entry` | Fetch full entry by accession. |
| `uniprot_search` | UniProt query language; filter by gene / organism / reviewed. |
| `uniprot_get_sequence` | FASTA with PIR-style provenance comment block. |
| `uniprot_get_features` | Domains / sites / PTMs / signal peptides. |
| `uniprot_get_variants` | Natural variants and disease mutations. |
| `uniprot_get_go_terms` | GO annotations grouped by aspect (F / P / C). |
| `uniprot_get_cross_refs` | Raw cross-references (PDB / Pfam / Ensembl / Reactome / KEGG / STRING / …). |
| `uniprot_id_mapping` | Map IDs between databases. |
| `uniprot_batch_entries` | Up to 100 entries in one call; invalid accessions filtered client-side. |
| `uniprot_taxonomy_search` | Search UniProt taxonomy by organism name. |

## Controlled vocabularies (4)

| Tool | Purpose |
|---|---|
| `uniprot_get_keyword` | Keyword by ID (e.g. `KW-0007` = Acetylation). |
| `uniprot_search_keywords` | Free-text keyword search. |
| `uniprot_get_subcellular_location` | Subcellular-location term by ID (e.g. `SL-0039` = Cell membrane). |
| `uniprot_search_subcellular_locations` | Free-text location search. |

## Sequence archives & clusters (4)

| Tool | Purpose |
|---|---|
| `uniprot_get_uniref` | UniRef cluster by ID (`UniRef50_P04637`, etc.). |
| `uniprot_search_uniref` | Cluster search with `identity_tier` filter. |
| `uniprot_get_uniparc` | Sequence-archive record by UPI (`UPI000002ED67`). |
| `uniprot_search_uniparc` | UniParc full-text search. |

## Proteomes & literature (4)

| Tool | Purpose |
|---|---|
| `uniprot_get_proteome` | Proteome by UP ID (`UP000005640` = human). Counts, BUSCO, components. |
| `uniprot_search_proteomes` | Filter by organism / type / completeness. |
| `uniprot_get_citation` | Citation record by ID (typically PubMed). |
| `uniprot_search_citations` | Citation index search. |

## Structured cross-DB resolvers (4)

These extract cross-references from a UniProt entry and return
**structured records** — typed lists / objects, not passthrough
strings. Gateway-only — no calls leave the UniProt origin.

| Tool | Purpose |
|---|---|
| `uniprot_resolve_pdb` | PDB structures: id + method + resolution + chain coverage. |
| `uniprot_resolve_alphafold` | AlphaFold model id + EBI viewer URL (model id only — for confidence call the dedicated tool below). |
| `uniprot_resolve_interpro` | InterPro signatures: id + entry name. |
| `uniprot_resolve_chembl` | ChEMBL drug-target id + EBI target-card URL. |

## Clinical bioinformatics (4)

| Tool | Purpose |
|---|---|
| `uniprot_compute_properties` | Derived sequence chemistry: MW / pI / GRAVY / aromaticity / charge / ε₂₈₀. Pure-Python on the FASTA — no external API. |
| `uniprot_features_at_position` | Every feature overlapping a residue position (1-indexed). Critical for variant-effect interpretation. |
| `uniprot_lookup_variant` | HGVS-shorthand match (`R175H`, `V600E`, `R248*`) against UniProt's natural-variant features. |
| `uniprot_get_disease_associations` | Structured disease records from DISEASE-type comments: name + MIM cross-ref + description. |

## Cross-origin enrichment (3)

These are the only tools that consult origins outside
`rest.uniprot.org`. Each is documented in
[PRIVACY.md](https://github.com/smaniches/uniprot-mcp/blob/main/PRIVACY.md)
and in [the threat model](THREAT_MODEL.md#t3b-cross-origin-allowlist-for-non-uniprot-endpoints).

| Tool | Origin | Purpose |
|---|---|---|
| `uniprot_get_alphafold_confidence` | alphafold.ebi.ac.uk | pLDDT mean + four-band distribution; lets the agent decide whether to trust the model. |
| `uniprot_resolve_clinvar` | eutils.ncbi.nlm.nih.gov | ClinVar significance + condition + review status by gene + optional HGVS shorthand. |
| `uniprot_get_publications` | rest.uniprot.org | Pure-Python over the entry's references — listed here because it complements the cross-origin enrichment. |

## Composition + provenance (5)

| Tool | Purpose |
|---|---|
| `uniprot_resolve_orthology` | Group orthology cross-references by source DB (KEGG / OMA / OrthoDB / eggNOG / 8 more). |
| `uniprot_get_evidence_summary` | Aggregate ECO codes (Evidence and Conclusion Ontology) across an entry. Distinguishes wet-lab confirmed from inferred-by-similarity from automatic. |
| `uniprot_target_dossier` | One-call comprehensive characterisation: nine sections in one structured report. |
| `uniprot_provenance_verify` | Re-fetch a previously recorded URL and compare release + canonical SHA-256. Five verdicts (`verified` / `release_drift` / `hash_drift` / `release_and_hash_drift` / `url_unreachable`). |
| `uniprot_replay_from_cache` | Read a cached UniProt response without hitting the upstream. Opt-in via `UNIPROT_MCP_CACHE_DIR`. |

## Cross-cutting input validation

Every tool that takes an identifier validates it **before** any HTTP
call. The regexes are defined once in
`src/uniprot_mcp/client.py` and shared:

| Identifier | Regex |
|---|---|
| UniProt accession | `\A(?:[OPQ][0-9][A-Z0-9]{3}[0-9]\|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})\Z` |
| Keyword | `\AKW-[0-9]{4}\Z` |
| Subcellular location | `\ASL-[0-9]{4}\Z` |
| UniRef cluster | `\AUniRef(?:50\|90\|100)_(<acc>\|UPI<10 hex>)\Z` |
| UniParc UPI | `\AUPI[A-F0-9]{10}\Z` |
| Proteome UP | `\AUP[0-9]{9,11}\Z` |
| Citation | `\A[0-9]{1,12}\Z` |
| HGVS shorthand | `\A[A-Z][1-9][0-9]{0,4}[A-Z*]\Z` |

Length caps are also applied; see `src/uniprot_mcp/server.py` for the
exact constants.

## Output formats

Every tool accepts `response_format="markdown"` (default) or
`response_format="json"`.

- **Markdown** carries a trailing provenance footer (`---` separator
  + `_Source:_` + `_Query:_` + `_SHA-256:_`).
- **JSON** wraps the data in a `{"data": ..., "provenance": ...}`
  envelope.
- **FASTA** (sequence tool only) prepends a PIR-style `;`-prefix
  comment block before the first `>` record — parser-safe for BLAST+,
  biopython, emboss.
