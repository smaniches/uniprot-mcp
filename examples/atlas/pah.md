# Atlas — PAH (Phenylalanine hydroxylase)

**UniProt:** [P00439](https://www.uniprot.org/uniprotkb/P00439)
**Gene symbol:** PAH
**Protein:** Phenylalanine-4-hydroxylase
**Organism:** *Homo sapiens* (taxonomy ID 9606)
**Disease (MONDO):** [MONDO:0009861 — phenylketonuria](https://monarchinitiative.org/disease/MONDO:0009861); see also MONDO:0017739 (mild hyperphenylalaninemia).
**OMIM:** [612349 (PAH gene)](https://omim.org/entry/612349), 261600 (PKU), 261630 (HPABH4A).
**Disease class:** rare-disease metabolic enzyme deficiency; aromatic-amino-acid hydroxylase family.

## Question this atlas entry answers

A metabolic-disease genetics team interprets a PAH variant in a
newborn-screening positive. They need: which structural domain is
affected (regulatory N-term, catalytic, tetramerisation),
co-factor / metal-binding sites (BH4, iron), and whether the
variant is *responsive* to BH4 supplementation (sapropterin /
Kuvan).

## Tool sequence

| # | Tool | Question |
|---|---|---|
| 1 | `uniprot_get_entry("P00439")` | Function (Phe → Tyr hydroxylation), 452 aa, three domains. |
| 2 | `uniprot_features_at_position("P00439", <pos>)` | Which domain houses the variant? |
| 3 | `uniprot_get_active_sites("P00439")` | Iron-binding residues (His-285, His-290, Glu-330) + BH4-binding region. |
| 4 | `uniprot_get_alphafold_confidence("P00439")` | High pLDDT across the catalytic domain. |
| 5 | `uniprot_resolve_pdb("P00439")` | Many PDB structures; tetrameric and monomeric forms. |
| 6 | `uniprot_resolve_clinvar("P00439", size=10)` | Variants by clinical significance. |
| 7 | `uniprot_get_disease_associations("P00439")` | PKU, HPA, HPABH4A. |

## Expected response shape

- **Step 3**: at least three Metal-binding annotations for iron (the active-site iron is co-ordinated by two histidines and a glutamate); BH4 binding site annotations.
- **Step 5**: structures include the catalytic domain alone, tetrameric assembly, and the regulatory ACT-domain in complex with phenylalanine.
- **Step 7**: at least PKU (MIM:261600) and one HPA-related entry.

## Therapeutic axis (interpretation)

- **Diet:** phenylalanine-restricted diet (cornerstone since 1950s).
- **BH4 supplementation:** sapropterin (Kuvan) for BH4-responsive
  variants — typically those that destabilise the dimer/tetramer
  but retain catalytic activity. Predicting BH4-responsiveness
  from a variant requires structural reasoning, which the
  position-aware feature tool supports.
- **Enzyme replacement:** pegvaliase (Palynziq) — pegylated
  phenylalanine ammonia lyase from *Anabaena*, an alternative
  Phe-degrading enzyme. Not a PAH-targeted therapy.
- **Gene therapy:** in clinical trial.
- ChEMBL bridge: sapropterin (BH4 cofactor analogue).

## Provenance fields

Standard envelope on every response.

## Cross-references in scope

| Resource | Returned via |
|---|---|
| PDB | Many structures; tetramer, monomer, ACT-domain–Phe complex. |
| AlphaFold DB | `AF-P00439-F1`. |
| ChEMBL | Sapropterin and analogues. |
| ClinVar | Hundreds of PAH variants with PKU/HPA classifications. |
| OMIM | 261600 (PKU), 261630 (HPABH4A), 264070 (HPA mild). |

## Adjacent ontologies

| Ontology | Identifier |
|---|---|
| MONDO | MONDO:0009861 (PKU), MONDO:0017739 (mild HPA) |
| HPO | HP:0002148 (hyperphenylalaninemia), HP:0001249 (intellectual disability), HP:0000718 (aggressive behavior), HP:0002375 (hypotonia) |
| Orphanet | ORPHA:716 (PKU) |

## Why PAH

PAH demonstrates the *enzyme drug-target* workflow: surface the
co-factor binding (BH4) and metal-binding (iron) residues via the
biomedical-features family of tools, then connect to therapeutic
matchmaking (BH4-responsive vs not). It also exercises the
mature-protein active-site annotations on a small, well-resolved
metabolic enzyme.
