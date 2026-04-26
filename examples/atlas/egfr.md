# Atlas — EGFR

**UniProt:** [P00533](https://www.uniprot.org/uniprotkb/P00533)
**Gene symbol:** EGFR
**Protein:** Epidermal growth factor receptor
**Organism:** *Homo sapiens* (taxonomy ID 9606)
**Disease (MONDO):** [MONDO:0005233 — non-small cell lung carcinoma](https://monarchinitiative.org/disease/MONDO:0005233) (non-Mendelian; somatic-driver context).
**OMIM:** [131550 (EGFR gene)](https://omim.org/entry/131550), 211980 (NSCLC).
**Disease class:** solid-tumour driver; receptor tyrosine kinase; precision-oncology canonical target.

## Question this atlas entry answers

An oncology team analyses a tumour-sequencing report with `EGFR
L858R` (the canonical sensitising mutation) and `EGFR T790M` (the
canonical first-generation TKI resistance mutation). They need:
the kinase-domain context, ChEMBL coverage of EGFR inhibitors, and
which TKI generation each variant matches (gefitinib/erlotinib,
afatinib, osimertinib, amivantamab).

## Tool sequence

| # | Tool | Question |
|---|---|---|
| 1 | `uniprot_get_entry("P00533")` | Function (RTK), 1210 aa, ectodomain + transmembrane + kinase + C-tail. |
| 2 | `uniprot_features_at_position("P00533", 858)` | L858 in the activation loop of the kinase domain. |
| 3 | `uniprot_lookup_variant("P00533", "L858R")` | UniProt natural-variant annotation. |
| 4 | `uniprot_lookup_variant("P00533", "T790M")` | The gatekeeper resistance mutation. |
| 5 | `uniprot_resolve_clinvar("P00533", change="L858R", size=5)` | ClinVar somatic-cancer classification. |
| 6 | `uniprot_get_active_sites("P00533")` | ATP-binding residues in the kinase domain (Lys-745, the catalytic loop, the DFG motif). |
| 7 | `uniprot_resolve_chembl("P00533")` | EGFR is one of the richest ChEMBL targets — many TKIs. |
| 8 | `uniprot_resolve_pdb("P00533")` | Many kinase-domain structures with various inhibitors bound. |

## Expected response shape

- **Step 2**: residue 858 sits inside the kinase domain (~residues 712–979). Features: `Domain` (Protein kinase), `Active site`, `Binding site` (ATP), and `Natural variant` (L858R).
- **Step 5**: somatic Pathogenic / oncogenic variant in NSCLC; the canonical sensitising mutation.
- **Step 6**: classical kinase active-site residues — Lys-745 (β3-catalytic), Asp-855 (DFG), Glu-762 (αC-helix glutamate).
- **Step 7**: ChEMBL target with extensive inhibitor coverage including gefitinib, erlotinib, afatinib, osimertinib.

## Therapeutic axis (interpretation)

- **First-generation TKIs** (gefitinib, erlotinib): bind ATP site
  reversibly. Effective against L858R and exon-19 deletion;
  resistance via T790M emerges in ~50% of cases within 1–2 years.
- **Second-generation TKIs** (afatinib, dacomitinib): irreversible
  covalent inhibitors of EGFR + HER2. Activity against T790M is
  modest.
- **Third-generation TKIs** (osimertinib, lazertinib):
  T790M-active and CNS-penetrant. Now standard of care for
  EGFR-mutant NSCLC.
- **Fourth-generation / amplification handlers:** patritumab
  deruxtecan (HER3 ADC), amivantamab (EGFR/MET bispecific),
  exon-20-insertion-targeted agents (mobocertinib).
- ChEMBL bridge: EGFR is one of ChEMBL's most-populated targets.

## Provenance fields

Standard envelope on every response.

## Cross-references in scope

| Resource | Returned via |
|---|---|
| PDB | Many kinase-domain structures; ectodomain dimers; transmembrane structures. |
| AlphaFold DB | `AF-P00533-F1` (full-length, with confidence variation). |
| ChEMBL | Rich; the canonical RTK target. |
| ClinVar | Somatic-tumour annotations; most variants outside ClinVar's germline focus, but L858R and T790M are well-curated. |
| InterPro | Protein kinase domain, EGF-receptor signature, furin-like cysteine-rich region. |

## Adjacent ontologies

| Ontology | Identifier |
|---|---|
| MONDO | MONDO:0005233 (NSCLC), MONDO:0021642 (lung adenocarcinoma) |
| HPO | HP:0002088 (abnormal lung function), HP:0100526 (lung neoplasm) |
| EFO | EFO_0003060 (NSCLC) |

## Why EGFR

EGFR exercises the *somatic-driver / precision-oncology* axis of
the tool. It demonstrates that the same position-aware feature
workflow that handles germline variants (TP53 R175H, BRCA1) also
handles somatic variants in the same protein, with ClinVar's
oncogenic-variant annotations. The richness of ChEMBL coverage
makes it the natural showcase for the drug-target dossier on a
solid-tumour target.
