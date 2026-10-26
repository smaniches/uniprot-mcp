# Recipe: Drug-target dossier in one call

A research team wants to retrieve what UniProt records about a protein.
These annotations alone cannot establish drug-target tractability.

`uniprot_target_dossier(accession)` answers that in one call —
internally it fetches the UniProt entry plus the FASTA (two upstream
requests, not nine separate tool calls) and assembles a structured
nine-section report.

## Request and result boundaries

Call `uniprot_target_dossier(accession)` using a verified UniProtKB
accession. Its nine views cover identity, function, derived sequence
chemistry, PDB/AlphaFold/InterPro links, ChEMBL/DrugBank references,
disease and variant annotations, GO evidence, and cross-references.

The tool does not run docking, evaluate biological efficacy, or
independently infer druggability. A missing PDB or ChEMBL cross-reference
on the UniProt entry does not establish that no such data exist
elsewhere. Current numerical values require a live source retrieval;
this repository does not maintain a separate drug-target atlas.

## Why this composition matters

A drug-discovery team typically wants to answer:

1. **Which target-related records exist?** ChEMBL/PDB cross-references
   guide research but cannot establish binding, druggability, or efficacy.
2. **Which disease annotations are present?** UniProt disease records
   and MIM links are context, not independent clinical validation.
3. **Is it well-characterised?** Cross-reference count + variant
   count + ECO-code diversity — **rough completeness signal**.
4. **What's the basic chemistry?** MW / pI / hydrophobicity for
   buffer selection, expression-system choice — **derived from the
   FASTA without an external tool**.

The dossier puts all four on one page. The agent can then decide
which deeper tool calls are warranted (e.g. `uniprot_get_variants`
for the full variant table, `uniprot_get_alphafold_confidence` for
the per-band pLDDT, `uniprot_get_evidence_summary` for the
quality-of-evidence picture).

## Pairing with other tools

| Question | Follow-up tool |
|---|---|
| "Show me the actual structures" | `uniprot_resolve_pdb` |
| "What model-wide pLDDT distribution is reported?" | `uniprot_get_alphafold_confidence` |
| "What variants are in ClinVar?" | `uniprot_resolve_clinvar` |
| "What papers cite this entry?" | `uniprot_get_publications` |
| "What do KEGG / OMA say about orthologs?" | `uniprot_resolve_orthology` |

## Reproducibility

The dossier may use **two** UniProtKB responses: the entry JSON and a
FASTA sequence for derived chemistry. The main footer binds the entry;
when chemistry succeeds, its section separately reports the FASTA URL
and SHA-256. Machine-readable output carries `chemistry_status` and,
when applicable, `chemistry_provenance`.

Use `uniprot_provenance_verify` for each UniProt REST input separately,
with the original Accept header. A digest match establishes source
integrity, not independent scientific validation of derived values.

## What this recipe is **not**

- Not a substitute for a target-validation pipeline. Real validation
  needs cell-based assays, in vivo models, off-target screens — none
  of which fit in a UniProt-gateway tool.
- Not a fitness-for-purpose claim. The dossier reports what UniProt
  knows; whether your specific drug-discovery program can translate
  that into a credible target hypothesis is a separate question.

The dossier is a **source-attributed research overview**, not a
validated druggability or clinical interpretation.
