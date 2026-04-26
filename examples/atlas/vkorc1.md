# Atlas — VKORC1

**UniProt:** [Q9BQB6](https://www.uniprot.org/uniprotkb/Q9BQB6).
**Gene:** VKORC1 · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** *not a disease gene per se*; pharmacogenomic locus + warfarin sensitivity / resistance phenotypes; rare MONDO:0009842 (vitamin K-dependent clotting factor deficiency).
**OMIM:** 608547 (gene), 122700 (warfarin resistance).
**Disease class:** warfarin pharmacogenomic determinant; the canonical PGx case studied jointly with CYP2C9.

## Question

For a patient starting warfarin, what's the VKORC1 promoter genotype (rs9923231 / -1639G>A), and how does it combine with the CYP2C9 genotype to predict the maintenance dose?

## Tool sequence

1. `uniprot_get_entry("Q9BQB6")` — function (vitamin K epoxide reductase complex subunit 1; reduces vitamin K epoxide back to active vitamin K hydroquinone for γ-carboxylation of clotting factors), 163 aa.
2. `uniprot_get_active_sites("Q9BQB6")` — catalytic cysteines (the redox-active CXXC motif).
3. `uniprot_features_at_position("Q9BQB6", <pos>)` — transmembrane segments + active-site cysteines.
4. `uniprot_lookup_variant("Q9BQB6", "<HGVS>")` — coding variants causing warfarin resistance (`Val66Met`, `Leu120Gln`, etc.).
5. `uniprot_resolve_clinvar("Q9BQB6", size=10)`.
6. `uniprot_resolve_pdb("Q9BQB6")` — structures including warfarin-bound complexes (recent cryo-EM).

## Therapeutic axis (clinical PGx)

**Warfarin dosing:** the FDA-approved dosing algorithms (warfarindosing.org and similar) require both **VKORC1 -1639G>A** (rs9923231) genotype and **CYP2C9 \*2/\*3** genotype to compute the predicted maintenance dose. The combination explains ~30–40% of warfarin-dose variability.

**Warfarin resistance** (rare): coding mutations in VKORC1 (e.g., V66M, L128R) cause partial-to-complete resistance — patients require very high doses or alternative anticoagulants.

**Vitamin K-dependent clotting factor deficiency type 2 (rare):** loss-of-function VKORC1 variants cause neonatal coagulopathy responsive to vitamin K supplementation.

**Direct oral anticoagulants (DOACs):** apixaban, rivaroxaban, dabigatran, edoxaban — bypass the VKORC1/vitamin K cycle entirely, with no PGx requirement. Increasingly preferred over warfarin for atrial fibrillation, VTE.

## Cross-references

PDB has the cryo-EM structure of VKORC1 with warfarin (recent breakthrough); AlphaFold `AF-Q9BQB6-F1`; ChEMBL has warfarin, phenprocoumon, acenocoumarol (target = VKORC1); ClinVar; PharmGKB / CPIC clinical guidelines.

## Adjacent ontologies

PharmGKB (gene-centric); CPIC level A guideline for warfarin dosing; HPO:HP:0011868 (intracerebral hemorrhage — over-anticoagulation outcome), HP:0001892 (abnormal bleeding).

## Why VKORC1

Demonstrates the *small-membrane-protein PGx* case and the integration with another gene (CYP2C9) for the clinical phenotype. The VKORC1+CYP2C9 dual-gene warfarin-dosing algorithm is the canonical example of multi-gene PGx clinical decision support — and the gateway tool surfaces the variant + structural context that the algorithm consumes.
