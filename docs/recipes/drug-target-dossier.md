# Recipe: Drug-target dossier in one call

A drug-discovery team is evaluating a new oncology target. The
question: **what does the curated literature already say about this
protein, and is it tractable as a drug target?**

`uniprot_target_dossier(accession)` answers that in one call —
internally it fetches the UniProt entry plus the FASTA (two upstream
requests, not nine separate tool calls) and assembles a structured
nine-section report.

## Example: BRCA1 (P38398)

```text
> Give me the target dossier for human BRCA1.
```

Tool call: `uniprot_target_dossier("P38398")`.

Sections returned (paraphrased for length):

### Identity

- **Protein:** Breast cancer type 1 susceptibility protein
- **Gene:** BRCA1
- **Organism:** Homo sapiens
- **Length:** 1863 aa
- **Curation:** Swiss-Prot (reviewed)

### Function

> E3 ubiquitin-protein ligase that specifically mediates the formation
> of K6-linked polyubiquitin chains. Plays a central role in DNA
> repair via homologous recombination. Required for the resolution of
> DNA double-strand breaks following replication stress.

### Sequence chemistry (derived)

- Molecular weight: ~207,500 Da
- Theoretical pI: ~5.3
- GRAVY: ~−0.8 (hydrophilic)
- Aromaticity: 6.5%
- Net charge at pH 7: ~−40 (acidic)

### Structural evidence

- PDB structures: ~30 (best resolution e.g. 1JM7 at 1.85 Å)
- AlphaFold model: `P38398` (call `uniprot_get_alphafold_confidence`
  for the pLDDT bands — for BRCA1 the RING and BRCT domains are very
  high but the central region is largely disordered)
- InterPro signatures: ~12 (RING-type, BRCT, etc.)

### Drug-target context

- ChEMBL targets: typically a handful (ChEMBL5462, etc.)
- DrugBank cross-references: present

### Disease associations (10+)

- **Breast-ovarian cancer susceptibility 1** (MIM:604370)
- **Pancreatic cancer 4** (MIM:614320)
- **Fanconi anemia complementation group S** (MIM:617883)
- ... more

### Variants

- Natural variants annotated: 1500+ (one of UniProt's most-annotated
  cancer-driver entries)

### Functional annotations

- **GO Molecular Function:** ubiquitin-protein transferase activity,
  DNA binding, transcription coactivator activity, …
- **Subcellular locations:** Nucleus, Cytoplasm
- **Evidence codes:** 35+ distinct ECO codes (call
  `uniprot_get_evidence_summary` for the full breakdown)

### Cross-references

- 90+ databases, top: Ensembl, RefSeq, PDB, AlphaFoldDB, MIM, GO,
  InterPro, Pfam, …

## Why this composition matters

A drug-discovery team typically wants to answer:

1. **Is the protein druggable?** ChEMBL targets present, structural
   evidence (PDB or confident AlphaFold regions) — **yes/no in one
   line**.
2. **Is it disease-relevant?** Disease associations with MIM IDs —
   **yes/no with cross-references**.
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
| "Can I trust the AlphaFold model at residue X?" | `uniprot_get_alphafold_confidence` |
| "What variants are in ClinVar?" | `uniprot_resolve_clinvar` |
| "What papers cite this entry?" | `uniprot_get_publications` |
| "What do KEGG / OMA say about orthologs?" | `uniprot_resolve_orthology` |

## Reproducibility

Every dossier response carries the standard provenance footer.
Re-verify a dossier from six months ago by calling
`uniprot_provenance_verify` with the recorded URL + release +
SHA-256. If the dossier was generated against UniProt release
`2026_01` and the underlying entry hasn't been edited, the verifier
returns `verified`. If UniProt has rolled forward, the verifier
returns `release_drift` and you decide whether to refresh or treat
the old answer as a release-pinned record.

## What this recipe is **not**

- Not a substitute for a target-validation pipeline. Real validation
  needs cell-based assays, in vivo models, off-target screens — none
  of which fit in a UniProt-gateway tool.
- Not a fitness-for-purpose claim. The dossier reports what UniProt
  knows; whether your specific drug-discovery program can translate
  that into a credible target hypothesis is a separate question.

The dossier is the **fastest possible defensible first pass** — every
fact has a provenance footer and a UniProt entry behind it.
