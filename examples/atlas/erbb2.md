# Atlas — ERBB2 (HER2)

**UniProt:** [P04626](https://www.uniprot.org/uniprotkb/P04626).
**Gene:** ERBB2 · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0007254 (HER2-positive breast cancer subtype), MONDO:0006520 (gastric adenocarcinoma).
**OMIM:** 164870 (gene), 137215 (HBOC), 114500 (CRC, HER2 subset).
**Disease class:** receptor tyrosine kinase oncogene (amplification-driven + activating-mutation-driven).

## Question

For HER2-positive breast cancer, what are the actionable axes — amplification, exon-20 insertion mutations, and the canonical S310F / V842I mutations — with the rich antibody-drug-conjugate (ADC) and tyrosine-kinase-inhibitor landscape?

## Tool sequence

1. `uniprot_get_entry("P04626")` — function (RTK; no high-affinity ligand of its own; signals as heterodimer with EGFR/ERBB3/ERBB4).
2. `uniprot_features_at_position("P04626", <pos>)` — domain context for variants of interest.
3. `uniprot_resolve_clinvar("P04626", size=10)` — somatic + germline variants.
4. `uniprot_get_active_sites("P04626")` — ATP-binding kinase residues + dimerization interface.
5. `uniprot_resolve_pdb("P04626")` — kinase domain structures + ectodomain (TDM1/TDXd binding context).
6. `uniprot_resolve_chembl("P04626")` — trastuzumab, pertuzumab, ado-trastuzumab emtansine (T-DM1), trastuzumab deruxtecan (T-DXd), tucatinib, neratinib, lapatinib, margetuximab.

## Therapeutic axis

**Antibody therapies:** trastuzumab (humanised mAb against subdomain IV of the ectodomain; the seminal HER2 drug); pertuzumab (subdomain II — blocks dimerization); margetuximab (Fc-engineered for ADCC).

**ADCs:** trastuzumab emtansine (T-DM1, microtubule poison payload); trastuzumab deruxtecan (T-DXd, topoisomerase I inhibitor payload — bystander effect, active even in HER2-low). T-DXd is a paradigm-shifting ADC.

**TKIs:** tucatinib (HER2-selective, CNS-penetrant); neratinib (irreversible pan-HER, activity in HER2-mutant including exon-20); lapatinib (older, EGFR/HER2 dual).

**HER2-mutant (non-amplified):** neratinib + selpercatinib for select alleles; T-DXd shows activity here as well.

## Cross-references

| Resource | Notes |
|---|---|
| PDB | Kinase domain + ectodomain (with trastuzumab Fab, pertuzumab Fab). |
| ChEMBL | Rich; one of oncology's most-populated targets. |
| InterPro | EGF receptor / ErbB receptor signature. |

## Adjacent ontologies

MONDO:0007254 (HER2+ breast cancer), MONDO:0006520 (gastric adenocarcinoma), MONDO:0021682 (HER2-low breast cancer); EFO:0003869 (breast carcinoma); HPO:HP:0003002.

## Why ERBB2

Demonstrates the *amplification + mutation* dual axis (most HER2 disease is amplification, but mutations are increasingly actionable) and the rich antibody/ADC/TKI ecosystem — a useful test of the dossier breadth on a heavily-druggable target.
