# Atlas — MYH7 (β-myosin heavy chain)

**UniProt:** [P12883](https://www.uniprot.org/uniprotkb/P12883).
**Gene:** MYH7 · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0024533 (hypertrophic cardiomyopathy 1), MONDO:0011712 (dilated cardiomyopathy 1S), MONDO:0011688 (Laing distal myopathy), MONDO:0008052 (Liang-Wang syndrome).
**OMIM:** 160760 (gene), 192600 (HCM), 613426 (DCM1S), 160500 (Laing).
**Disease class:** sarcomeric cardiomyopathy + skeletal myopathy.

## Question

For a hypertrophic cardiomyopathy family with a MYH7 missense in the motor head, what's the structural region (motor head 1–778, light-chain binding 779–838, S2/coiled-coil 839–1935, LMM tail 1936–1935), and what's the therapeutic axis (mavacamten — the cardiac myosin inhibitor)?

## Tool sequence

1. `uniprot_get_entry("P12883")` — function (sarcomeric β-myosin), 1935 aa.
2. `uniprot_features_at_position("P12883", <pos>)` — motor head domain (1–778), converter region (709–778), neck (779–842).
3. `uniprot_lookup_variant("P12883", "<HGVS>")`.
4. `uniprot_resolve_clinvar("P12883", size=15)`.
5. `uniprot_get_active_sites("P12883")` — ATP-binding P-loop (~178–185), actin-binding loop, converter-region key residues.
6. `uniprot_resolve_pdb("P12883")` — motor-head structures with various nucleotide/inhibitor states.
7. `uniprot_get_alphafold_confidence("P12883")` — high pLDDT motor head + coiled-coil tail.

## Therapeutic axis

**Mavacamten** (Camzyos, Bristol Myers Squibb): cardiac myosin inhibitor; FDA-approved 2022 for symptomatic obstructive HCM. Reduces hypercontractility by stabilising the auto-inhibited interacting-heads-motif state. **Aficamten** (Cytokinetics): next-generation cardiac myosin inhibitor in late-stage trials.

**Conventional management:** β-blockers, non-dihydropyridine calcium-channel blockers, disopyramide; septal myectomy or alcohol septal ablation for refractory obstructive HCM.

**DCM-1S** (dilated phenotype): standard heart-failure management; no MYH7-specific therapy yet.

**Laing distal myopathy** (skeletal, MYH7 LMM tail mutations): no specific therapy; supportive care.

## Cross-references

PDB has many motor-head structures with substrate analogues and inhibitors (mavacamten co-crystals); AlphaFold `AF-P12883-F1`; ChEMBL has mavacamten and aficamten as MYH7-targeted small molecules; ClinVar has thousands of curated variants.

## Adjacent ontologies

MONDO:0024533 (HCM1), MONDO:0011712 (DCM1S), MONDO:0011688 (Laing); HPO:HP:0001639 (HCM), HP:0001644 (DCM), HP:0003560 (skeletal muscle weakness); Orphanet:ORPHA:217569 (HCM).

## Why MYH7

Demonstrates that the same gene drives *cardiac* (HCM, DCM) and *skeletal* (Laing distal myopathy) disease, depending on which structural region is hit. The motor head versus coiled-coil-tail divide is essential for variant interpretation, and the position-aware feature tool surfaces it directly. Mavacamten's first-in-class approval showed that "structural / sarcomeric" diseases can have small-molecule therapies.
