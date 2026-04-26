# Atlas — BRCA2

**UniProt:** [P51587](https://www.uniprot.org/uniprotkb/P51587).
**Gene:** BRCA2 · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0011544 (HBOC2), MONDO:0009100 (Fanconi anemia complementation group D1), MONDO:0014498 (familial pancreatic cancer 2).
**OMIM:** 600185 (gene), 612555 (HBOC2), 605724 (FANCD1).
**Disease class:** hereditary cancer + DNA-repair (homologous recombination).

## Question

For a BRCA2 truncating variant in HBOC, what's the structural context of the BRC repeats, the Tower domain, and the C-terminal RAD51-binding region — and which PARP inhibitors apply (the same axis as BRCA1 but distinct mechanism)?

## Tool sequence

1. `uniprot_get_entry("P51587")` — function (homologous recombination scaffold), ~3418 aa.
2. `uniprot_features_at_position("P51587", <pos>)` — BRC-repeat / OB-fold / Tower / TR2 region context.
3. `uniprot_lookup_variant("P51587", "<HGVS>")` — UniProt natural variants for known founder mutations (Ashkenazi 6174delT, etc.).
4. `uniprot_resolve_clinvar("P51587", size=10)` — Pathogenic / likely-pathogenic.
5. `uniprot_get_alphafold_confidence("P51587")` — bimodal distribution; long disordered linkers.
6. `uniprot_resolve_pdb("P51587")` — limited; mostly individual domain structures.
7. `uniprot_get_disease_associations("P51587")` — HBOC2, FANCD1, FPC2, medulloblastoma.

## Therapeutic axis

Same synthetic-lethality logic as BRCA1: PARP inhibitors (olaparib, niraparib, rucaparib, talazoparib) exploit the homologous-recombination defect in BRCA2-deficient tumours. **Tumour-agnostic indications** for advanced BRCA1/2-mutated solid tumours via olaparib; specific indications in ovarian, breast, prostate, pancreatic.

## Cross-references

| Resource | Notes |
|---|---|
| PDB | Individual domain structures; the full-length protein is too large. |
| AlphaFold DB | `AF-P51587-F1`. |
| ChEMBL | PARP inhibitors (against PARP1, the synthetic-lethal partner). |
| ClinVar | Many curated variants; founder mutations well-annotated. |

## Adjacent ontologies

MONDO:0011544, MONDO:0009100, MONDO:0014498; HPO:HP:0003002 (breast carcinoma), HP:0100615 (ovarian neoplasm), HP:0006725 (Fanconi anemia type features); Orphanet:ORPHA:84.

## Why BRCA2

Companion to BRCA1; demonstrates the same dossier workflow on the second hereditary breast/ovarian cancer gene; reinforces the synthetic-lethality / PARPi narrative; one of the longest human proteins (3418 aa) — exercises the long-protein AlphaFold case differently from titin or dystrophin.
