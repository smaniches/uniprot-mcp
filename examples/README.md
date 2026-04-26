# Worked-research transcripts

These are **realistic Claude Desktop conversations** demonstrating
`uniprot-mcp` in three research workflows. Each `.jsonl` file is a
sequence of message records (one per line) with the exact tool calls
the model would make and the structural shape of the responses.

The transcripts are **illustrative**, not regression-test artefacts:
the actual UniProt release shifts month-to-month, so values like
"83,526 proteins in the human proteome" or
"15 distinct feature types on TP53" drift over time. The
**provenance footers** in each response carry the SHA-256 digest at
capture time, so a third party can re-run any prompt and verify
that a current UniProt response would *or wouldn't* match the
recorded answer via `uniprot_provenance_verify`.

| File | Workflow | Tools exercised |
|---|---|---|
| `01_clinical_variant_interpretation.jsonl` | "Is `TP53 R175H` a clinically actionable variant?" | `uniprot_features_at_position`, `uniprot_lookup_variant`, `uniprot_resolve_clinvar`, `uniprot_get_alphafold_confidence`, `uniprot_get_disease_associations` |
| `02_drug_target_dossier.jsonl` | "Give me a complete characterisation of human BRCA1 as a drug target." | `uniprot_target_dossier`, `uniprot_resolve_pdb`, `uniprot_resolve_chembl`, `uniprot_get_evidence_summary` |
| `03_provenance_verify_after_a_year.jsonl` | "I have a research note from a year ago that cites a UniProt entry. Is the underlying answer still the same today?" | `uniprot_provenance_verify` |
| `04_pathogen_drug_discovery.jsonl` | "Scope a TEM-1 beta-lactamase inhibitor program: catalytic machinery, processing, PTMs, structures." | `uniprot_search`, `uniprot_get_active_sites`, `uniprot_get_processing_features`, `uniprot_get_ptms`, `uniprot_resolve_pdb` (v1.1.0 biomedical-features family) |

## How to read a transcript

Each line is a JSON object. The shape is one of:

| Type | Schema |
|---|---|
| User message | `{"role": "user", "content": "<prompt>"}` |
| Tool call by Claude | `{"role": "assistant", "tool_call": {"name": "<tool>", "arguments": {...}}}` |
| Tool result | `{"role": "tool", "name": "<tool>", "content": "<markdown body>"}` |
| Assistant final answer | `{"role": "assistant", "content": "<final text>"}` |

Real Claude Desktop transcripts include additional fields
(`message_id`, `created_at`, etc.) that are omitted here for
readability — the schema above captures the structurally-meaningful
parts.

## Reproducing

These transcripts capture deterministic tool calls but the live
UniProt and AlphaFold responses drift between releases. To reproduce
the *structure* (not the exact values), configure Claude Desktop with
the `uniprot-mcp` MCP server and paste the user prompts. Claude will
emit equivalent tool calls and produce a response with current values
and a current provenance footer.

To reproduce the *exact* values from a specific historical run,
run with `--pin-release=YYYY_MM` (matching the release tag in the
transcript's provenance footer) — and either accept the
`ReleaseMismatchError` if the live release has moved on, or fetch
the historical release from the UniProt FTP snapshot archive.
