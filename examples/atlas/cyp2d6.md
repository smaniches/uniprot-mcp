# Atlas — CYP2D6

**UniProt:** [P10635](https://www.uniprot.org/uniprotkb/P10635).
**Gene:** CYP2D6 · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** *not a disease gene*; pharmacogenomic locus controlling drug metabolism.
**OMIM:** 124030 (gene), 608902 (debrisoquine sensitivity).
**Disease class:** pharmacogenomic enzyme — drug-metabolism phenotype determinant (poor / intermediate / extensive / ultrarapid metabolizer classes).

## Question

For a patient prescribed codeine, tamoxifen, or atomoxetine, what's their CYP2D6 metabolizer phenotype based on star-allele genotype, and what's the dosing implication?

## Tool sequence

1. `uniprot_get_entry("P10635")` — function (cytochrome P450 2D6; ~25% of clinically used drugs), 497 aa.
2. `uniprot_features_at_position("P10635", <pos>)` — heme-binding region; substrate-recognition sites (SRS1–SRS6).
3. `uniprot_lookup_variant("P10635", "<HGVS>")` — known star-allele defining variants (`*4` rs3892097, `*10` rs1065852, etc.).
4. `uniprot_resolve_clinvar("P10635", size=15)`.
5. `uniprot_get_active_sites("P10635")` — heme iron coordination, oxygen-binding pocket.
6. `uniprot_resolve_pdb("P10635")` — apo + substrate-bound structures.
7. `uniprot_get_alphafold_confidence("P10635")` — high pLDDT across the P450 fold.

## Therapeutic axis (clinical PGx)

**Codeine:** prodrug bioactivated to morphine by CYP2D6. Poor metabolizers get inadequate analgesia; ultrarapid metabolizers risk respiratory depression / death (FDA black-box warning, especially in nursing infants of UM mothers).

**Tamoxifen:** prodrug bioactivated to endoxifen by CYP2D6 (and CYP3A4). PMs and IMs may have reduced antitumor activity in adjuvant breast-cancer therapy. CPIC guidelines exist.

**Tricyclic antidepressants (amitriptyline, nortriptyline):** CYP2D6 phenotype guides dose adjustment per CPIC.

**Atomoxetine:** CYP2D6 phenotype affects exposure (PMs have ~10× higher AUC); CPIC guidelines.

**Antipsychotics (risperidone, haloperidol, aripiprazole), opioids (tramadol, oxycodone):** various PGx considerations.

The **star-allele system** (CYP2D6\*1 wild type, \*2 normal, \*4 null, \*5 deletion, \*10 reduced, \*17 reduced, \*41 reduced; \*1xN duplication = ultrarapid) is canonical PGx vocabulary.

## Cross-references

PDB has multiple CYP2D6 structures including substrate complexes; AlphaFold `AF-P10635-F1`; ChEMBL has CYP2D6 as both a target (inhibitors: paroxetine, fluoxetine) and a metabolizer (annotated in many drug entries); ClinVar has the canonical PGx variants; **PharmGKB / CPIC** are the authoritative resources for clinical guideline tables.

## Adjacent ontologies

PharmGKB (gene-centric); CPIC (drug–gene clinical guideline level A/B/C); HPO:HP:0006759 (decreased drug response — generic).

## Why CYP2D6

The canonical pharmacogenomic enzyme — demonstrates that the gateway tool serves PGx workflows where the actionable axis is "given this variant + this drug, what's the dose adjustment?" rather than disease treatment. The PharmGKB / CPIC databases are the authoritative orchestrator-layer resources; `uniprot-mcp` surfaces the substrate (the variant + structural context).
