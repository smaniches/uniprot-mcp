# Research examples: captured evidence versus unexecuted recipes

This directory deliberately separates **one byte-bound, recorded source capture**
from **three proposed research workflows**. Do not interpret a suggested tool call
as a completed query, a source observation, or a validated biological conclusion.

## Source-backed recorded example

- [01 — TP53 R175H](01_clinical_variant_interpretation.jsonl) is a dated
  **live capture from 2026-10-15**. It contains real tool outputs and their
  source footers. The underlying compressed upstream response bodies and
  hashes are preserved in
  [captures/2026-10-15_tp53_r175h/](captures/2026-10-15_tp53_r175h/README.md).
- `tests/contract/test_tp53_capture_binding.py` independently recomputes
  those hashes and checks that the transcript matches its captured tool
  outputs. This tests source binding, **not clinical validity**.
- Its ClinVar classification remains a **source-reported germline assertion**.
  A patient's somatic findings, therapeutic implications, and clinical
  actionability require separate assessment. Model-level AlphaFold pLDDT
  does not establish confidence at an individual residue.

## Unexecuted workflow recipes (not transcripts)

The other files intentionally have no recorded tool-result messages, model
syntheses of alleged results, source-response timestamps, or SHA-256 receipts.
Their `suggested_call` records show **which tools to invoke next**, not
calls that have already run.

| File | Question to investigate | Suggested tools |
|---|---|---|
| [02 — BRCA1 target dossier](02_drug_target_dossier.jsonl) | What evidence is available for BRCA1 characterization? | `uniprot_target_dossier`, `uniprot_resolve_pdb`, `uniprot_resolve_chembl`, `uniprot_get_evidence_summary` |
| [03 — source drift check](03_provenance_verify_after_a_year.jsonl) | Has a recorded UniProt response changed? | `uniprot_provenance_verify`; replace the explicitly marked placeholders with **real** recorded provenance |
| [04 — TEM-1 research plan](04_pathogen_drug_discovery.jsonl) | Which retrieved annotations are relevant to TEM-1? | `uniprot_search`, `uniprot_get_active_sites`, `uniprot_get_processing_features`, `uniprot_get_ptms`, `uniprot_resolve_pdb` |

Each JSONL file is one JSON object per line. The recorded capture uses
`user`, `assistant`, and `tool` roles. A **recipe** uses `user`,
`assistant`, and `suggested_call`. The last role is an instruction
template, not an MCP transcript event or proof of execution.

To use a recipe, run its suggested calls in an installed MCP client
against current source APIs. Preserve the returned source URL, release,
retrieval time and upstream bytes. Only then write a source-attributed
analysis that distinguishes source assertions, software-derived
calculations, uncertainty and unvalidated hypotheses.

A successful source retrieval, a reproducible SHA-256, and an expert
scientific validation are **different evidence levels**. This directory
does not claim clinical, regulatory, or prospective experimental
validation.

## Reproduction and drift

To verify the *historical* TP53 response, run
`pytest tests/contract/test_tp53_capture_binding.py -q` from the
repository checkout. Its frozen bytes allow offline hash reproduction.

To check whether UniProt still serves the *same* record, use
`uniprot_provenance_verify` with genuine source metadata. The current
UniProt release can differ. `--pin-release` is an assertion that
rejects release mismatch; it does not retrieve a historical release.
For exact historical records, retain original bytes or use an
appropriate upstream snapshot.
