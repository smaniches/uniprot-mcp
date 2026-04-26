# Atlas — CFTR

**UniProt:** [P13569](https://www.uniprot.org/uniprotkb/P13569)
**Gene symbol:** CFTR
**Protein:** Cystic fibrosis transmembrane conductance regulator
**Organism:** *Homo sapiens* (taxonomy ID 9606)
**Disease (MONDO):** [MONDO:0009061 — cystic fibrosis](https://monarchinitiative.org/disease/MONDO:0009061).
**OMIM:** [602421 (CFTR gene)](https://omim.org/entry/602421), 219700 (cystic fibrosis).
**Disease class:** rare-disease (single-gene); ABC-transporter ion channel.

## Question this atlas entry answers

A clinical genetics team needs to interpret a CFTR variant. The
canonical case is `F508del` (`p.Phe508del`) — the most common cystic
fibrosis-causing variant — and a structural assessment of the
nucleotide-binding domain 1 (NBD1) where it lies.

## Tool sequence

| # | Tool | Question |
|---|---|---|
| 1 | `uniprot_get_entry("P13569")` | Function (chloride channel), domains (NBD1, NBD2, R-domain). |
| 2 | `uniprot_features_at_position("P13569", 508)` | What is at residue 508? (Expected: Chain, NBD1 domain, Natural variant.) |
| 3 | `uniprot_lookup_variant("P13569", "F508del")` | UniProt's natural-variant catalogue includes F508del. |
| 4 | `uniprot_resolve_clinvar("P13569", change="F508del", size=5)` | ClinVar classification (Pathogenic, expert-reviewed). |
| 5 | `uniprot_get_alphafold_confidence("P13569")` | NBD1 pLDDT band; expect `very high` confidence over the structured ATP-binding fold. |
| 6 | `uniprot_resolve_pdb("P13569")` | PDB structures of NBD1 (multiple). |
| 7 | `uniprot_get_active_sites("P13569")` | ATP-binding sites in NBD1 + NBD2 (Walker A/B motifs). |
| 8 | `uniprot_get_disease_associations("P13569")` | Cystic fibrosis (MIM:219700), CBAVD (MIM:277180). |

## Expected response shape

- **Step 2**: residue 508 sits in NBD1 (~residues 433–586). Expected features: `Chain`, `Domain` (NBD1), and `Natural variant` (F508del).
- **Step 4**: at least one Pathogenic ClinVar entry for F508del with expert-panel review.
- **Step 5**: NBD1 region in `very high` pLDDT band.
- **Step 7**: Walker A motif residues (~458–465) and Walker B residues (~571) annotated as binding sites or active sites.

## Therapeutic axis (interpretation)

- **Modulators:** F508del is rescued by *correctors* (lumacaftor,
  tezacaftor, elexacaftor) that improve protein folding/trafficking,
  combined with *potentiators* (ivacaftor) that enhance gating of
  rescued protein at the cell surface.
- **Triple therapy** (elexacaftor/tezacaftor/ivacaftor, ETI) covers
  ~90% of CF patients including F508del homozygotes and
  heterozygotes.
- ChEMBL bridge: ivacaftor and the corrector class appear in
  ChEMBL with CFTR as the recorded target.

## Provenance fields (every response)

Same standard envelope: `source / release / release_date /
retrieved_at / url / response_sha256`.

## Cross-references in scope

| Resource | Returned via |
|---|---|
| PDB | NBD1 structures (multiple); `uniprot_resolve_pdb`. |
| AlphaFold DB | Full-length model `AF-P13569-F1`. |
| ChEMBL | `uniprot_resolve_chembl` — CFTR target with ivacaftor + corrector compounds. |
| InterPro | ABC transporter signature, MRP family signatures. |
| ClinVar | F508del + ~2000 other CFTR variants. |
| OMIM | 219700 (CF), 277180 (CBAVD), 277180 (idiopathic pancreatitis). |

## Adjacent ontologies

| Ontology | Identifier |
|---|---|
| MONDO | MONDO:0009061 (cystic fibrosis), MONDO:0009217 (CBAVD) |
| HPO | HP:0002721 (immunodeficiency), HP:0001738 (exocrine pancreatic insufficiency), HP:0006538 (recurrent bronchitis) |
| Orphanet | ORPHA:586 (cystic fibrosis) |

## Why CFTR

CFTR demonstrates the position-aware-feature workflow on a textbook
single-gene rare disease, exercises the ClinVar bridge for one of
medicine's most-cited variants, and shows the AlphaFold confidence
signal on a multi-domain protein with both well-folded (NBD1, NBD2)
and disordered (R-domain) regions.
