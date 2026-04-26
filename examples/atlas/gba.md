# Atlas — GBA (Beta-glucocerebrosidase)

**UniProt:** [P04062](https://www.uniprot.org/uniprotkb/P04062).
**Gene:** GBA1 · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0009207 (Gaucher disease type 1, non-neuronopathic), MONDO:0009208 (type 2, acute neuronopathic), MONDO:0009209 (type 3, chronic neuronopathic); also MONDO:0008199 risk modifier (Parkinson disease 1).
**OMIM:** 606463 (gene), 230800 (GD1), 230900 (GD2), 231000 (GD3).
**Disease class:** lysosomal storage disorder + Parkinson-disease genetic risk factor.

## Question

For a Gaucher disease family with the canonical N370S (`p.Asn409Ser` in modern numbering, `Asn370Ser` in legacy mature-chain numbering) variant, what's the active-site context, and what therapeutic axes apply (enzyme replacement, substrate reduction, chaperone, gene therapy)?

## Tool sequence

1. `uniprot_get_entry("P04062")` — function (lysosomal glucocerebrosidase, glucosylceramide hydrolysis), 536 aa.
2. `uniprot_get_processing_features("P04062")` — signal peptide (1–39); mature chain begins at residue 40 → causes the +39 numbering offset that confuses literature.
3. `uniprot_features_at_position("P04062", 409)` — N370S in mature-chain numbering = N409S in UniProt numbering.
4. `uniprot_lookup_variant("P04062", "N409S")`.
5. `uniprot_resolve_clinvar("P04062", size=15)`.
6. `uniprot_get_active_sites("P04062")` — catalytic Glu-274 (acid/base) and Glu-379 (nucleophile).
7. `uniprot_get_alphafold_confidence("P04062")` — high-confidence TIM-barrel.
8. `uniprot_resolve_pdb("P04062")` — many structures with substrate analogues + clinical chaperones.

## Therapeutic axis

**Enzyme replacement therapy (ERT):** imiglucerase (Cerezyme), velaglucerase alfa (VPRIV), taliglucerase alfa (Elelyso) — recombinant β-glucocerebrosidase, IV infusion every 2 weeks. Standard of care for type 1.

**Substrate reduction therapy (SRT):** miglustat (Zavesca), eliglustat (Cerdelga) — inhibits glucosylceramide synthase, reducing substrate input to the deficient enzyme. Oral.

**Pharmacological chaperone:** ambroxol (off-label, investigational); isofagomine analogues investigational.

**Parkinson disease angle:** GBA1 heterozygous loss-of-function variants are the strongest single-gene genetic risk factor for sporadic PD (~5× risk). GBA1-targeting therapies for PD are an active investigational area (LRRK2-targeted approaches converge on the same lysosomal pathway).

## Cross-references

PDB has many co-crystal structures; AlphaFold `AF-P04062-F1`; ChEMBL has imiglucerase, eliglustat, miglustat; ClinVar has hundreds of curated variants.

## Adjacent ontologies

MONDO:0009207–0009209 (GD1–3), MONDO:0008199 (PD1); HPO:HP:0001744 (splenomegaly), HP:0001433 (hepatomegaly), HP:0001939 (osseous lesion); Orphanet:ORPHA:355.

## Why GBA

Demonstrates the *signal-peptide numbering offset* trap (mature-chain numbering vs UniProt full-precursor numbering — a real source of literature confusion that the processing-features tool resolves). Also shows the *one gene, two diseases* axis (lysosomal storage + Parkinson risk) that the disease-association tool surfaces honestly.
