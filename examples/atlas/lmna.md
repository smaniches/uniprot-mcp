# Atlas — LMNA (Lamin A/C)

**UniProt:** [P02545](https://www.uniprot.org/uniprotkb/P02545).
**Gene:** LMNA · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0011712 (dilated cardiomyopathy 1A), MONDO:0008977 (Emery-Dreifuss muscular dystrophy 2), MONDO:0008034 (Hutchinson-Gilford progeria syndrome), MONDO:0011055 (familial partial lipodystrophy 2, Dunnigan), MONDO:0009872 (Charcot-Marie-Tooth 2B1).
**OMIM:** 150330 (gene), 115200 (DCM1A), 181350 (EDMD2), 176670 (HGPS), 151660 (FPLD2).
**Disease class:** laminopathy spectrum — at least nine distinct phenotypes from one gene.

## Question

For a LMNA family with the canonical R453W mutation, which laminopathy phenotype is most likely (LMNA mutations are pleiotropic, with phenotype depending on residue position + mutation type), and what's the experimental therapeutic axis (HGPS → lonafarnib)?

## Tool sequence

1. `uniprot_get_entry("P02545")` — function (nuclear lamina structural component), 664 aa.
2. `uniprot_features_at_position("P02545", <pos>)` — head (1–32), coiled-coil (33–387), tail (388–664) with Ig-like fold (430–544).
3. `uniprot_lookup_variant("P02545", "<HGVS>")`.
4. `uniprot_resolve_clinvar("P02545", size=20)`.
5. `uniprot_get_processing_features("P02545")` — initiator methionine; the splice-isoform difference between Lamin A (full) and Lamin C (truncated at residue 566).
6. `uniprot_get_ptms("P02545")` — farnesylation at C-terminal CAAX motif (Cys-661, processed to mature lamin A).
7. `uniprot_get_disease_associations("P02545")` — DCM1A, EDMD2, HGPS, FPLD2, CMT2B1, restrictive dermopathy, mandibuloacral dysplasia.

## Therapeutic axis

**Hutchinson-Gilford Progeria Syndrome (HGPS — c.1824C>T → cryptic splice site → "progerin" with farnesylation that cannot be cleaved):**
- **Lonafarnib** (Zokinvy, Eiger): farnesyltransferase inhibitor; FDA-approved 2020 for HGPS. Prevents farnesylation of progerin. The first FDA-approved HGPS therapy.
- **Investigational:** rapamycin/everolimus (autophagy enhancers); MG132 / proteasome modulators.

**DCM1A:** heart-failure standard of care; ICD prophylaxis given high arrhythmic risk; investigational ARRY-371797 (p38 MAPK inhibitor).

**Other laminopathies:** mostly supportive management.

## Cross-references

PDB has Ig-like-fold tail-domain structures + N-terminal coiled-coil; AlphaFold `AF-P02545-F1`; ChEMBL has lonafarnib (against farnesyltransferase, not LMNA itself); ClinVar has thousands of curated alleles.

## Adjacent ontologies

MONDO:0011712, MONDO:0008977, MONDO:0008034, MONDO:0011055, MONDO:0009872; HPO:HP:0001644 (DCM), HP:0003560 (muscular dystrophy), HP:0008066 (atypical scarring), HP:0008064 (premature aging); Orphanet:ORPHA:740 (HGPS).

## Why LMNA

The paradigm laminopathy/pleiotropy case — one gene, at least nine distinct phenotypes, with the phenotype determined by residue position + mutation type. The position-aware feature tool is essential for variant interpretation here. Lonafarnib's HGPS approval is a triumph of mechanism-based rare-disease drug development.
