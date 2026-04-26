# Atlas — G6PD (Glucose-6-phosphate dehydrogenase)

**UniProt:** [P11413](https://www.uniprot.org/uniprotkb/P11413).
**Gene:** G6PD · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0010222 (G6PD deficiency); also linked to MONDO:0019146 (favism).
**OMIM:** 305900 (gene), 300908 (deficiency).
**Disease class:** X-linked enzymopathy; pharmacogenomic precaution flag (oxidative-drug avoidance).

## Question

For a patient with G6PD deficiency planning antimalarial or sulfonamide therapy, which variant class do they have (Class I/II severe, Class III mild, Class IV near-normal) and what's the structural rationale?

## Tool sequence

1. `uniprot_get_entry("P11413")` — function (rate-limiting enzyme of the pentose phosphate pathway; NADPH production protects erythrocytes from oxidative damage), 515 aa.
2. `uniprot_features_at_position("P11413", <pos>)` — variant context.
3. `uniprot_get_active_sites("P11413")` — substrate-binding (G6P), structural NADP+ site, catalytic NADP+ site.
4. `uniprot_resolve_pdb("P11413")` — many structures, mostly tetramer; substrate/cofactor complexes.
5. `uniprot_resolve_clinvar("P11413", size=20)` — hundreds of variants stratified across WHO classes I–IV.
6. `uniprot_get_disease_associations("P11413")` — G6PD deficiency, favism.

## Therapeutic axis (clinical management)

**Avoidance, not treatment:** oxidative drugs to avoid in G6PD-deficient patients include primaquine (antimalarial), tafenoquine, dapsone, sulfasalazine, sulfonamides (sulfamethoxazole), nitrofurantoin, and rasburicase. The pharmacogenomic decision is "is this patient G6PD-deficient" → "avoid these drugs" rather than "give a drug to fix the protein."

**Tafenoquine** specifically: requires *quantitative* G6PD testing pre-prescription due to severe hemolysis risk in deficient patients. The atlas entry serves as an interpretation key for the variant the lab reports.

**Gene therapy:** preclinical only; not a current clinical option.

## Cross-references

PDB: many tetramer structures with substrate/cofactor; AlphaFold `AF-P11413-F1`; ClinVar: hundreds of variants — the atlas is a useful trigger for the *class-stratification* lookup that downstream pharmacogenomics tools handle.

## Adjacent ontologies

MONDO:0010222 (G6PD deficiency); HPO:HP:0001923 (anemic crisis), HP:0001878 (hemolytic anemia); Orphanet:ORPHA:362; PharmGKB.

## Why G6PD

Demonstrates the *pharmacogenomics-precaution* axis of the tool — not a treatment target, but an actionable enzyme whose variants drive drug-avoidance decisions. The class stratification is a downstream-tool concern; `uniprot-mcp` surfaces the variant + structural context, which is the substrate.
