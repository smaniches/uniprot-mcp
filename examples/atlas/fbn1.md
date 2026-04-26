# Atlas — FBN1 (Fibrillin-1)

**UniProt:** [P35555](https://www.uniprot.org/uniprotkb/P35555).
**Gene:** FBN1 · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0007947 (Marfan syndrome), MONDO:0011625 (acromicric dysplasia), MONDO:0009098 (geleophysic dysplasia 2), MONDO:0011382 (stiff skin syndrome).
**OMIM:** 134797 (gene), 154700 (Marfan), 102370 (acromicric).
**Disease class:** connective-tissue disorder; modular extracellular protein with calcium-binding EGF + TGF-β–binding domains.

## Question

For a Marfan syndrome family with a missense in a calcium-binding EGF-like domain, what's the structural impact (Ca2+ coordination disrupted → reduced microfibril integrity), and what's the therapeutic axis (losartan / β-blockers for aortic root protection; pre-emptive surgery)?

## Tool sequence

1. `uniprot_get_entry("P35555")` — function (microfibril ECM scaffold), 2871 aa, ~47 cbEGF + TGFβ-binding domains.
2. `uniprot_features_at_position("P35555", <pos>)` — which domain; cbEGF domains have Ca2+ coordination annotations.
3. `uniprot_lookup_variant("P35555", "<HGVS>")` — Marfan-causing missense variants are heavily concentrated in calcium-binding sites of EGF-like domains.
4. `uniprot_resolve_clinvar("P35555", size=15)` — Pathogenic + VUS landscape.
5. `uniprot_get_active_sites("P35555")` — calcium-binding annotations on cbEGF domains.
6. `uniprot_get_processing_features("P35555")` — signal peptide; furin cleavage at the C-terminus releasing the mature monomer.

## Therapeutic axis

**Marfan syndrome — pharmacological:** β-blockers (atenolol) historically; **losartan** (angiotensin-receptor blocker) reduces TGF-β signalling and slows aortic root dilation in some trials — comparable to atenolol in COMPARE/Pediatric Heart Network meta-analyses. **Pre-emptive aortic root surgery** when diameter approaches threshold (typically ≥5.0 cm in adults).

**Geleophysic / acromicric dysplasias** (gain-of-function mutations in TGFβ-binding domain 5) have no specific therapy yet.

**Stiff skin syndrome** (mutations in TB4 domain): no specific therapy.

## Cross-references

PDB has individual cbEGF domain structures; AlphaFold model `AF-P35555-F1`; ClinVar has thousands of FBN1 variants; OMIM 154700 (Marfan), 102370 (acromicric), 614185 (geleophysic 2), 184900 (stiff skin).

## Adjacent ontologies

MONDO:0007947, MONDO:0011625, MONDO:0009098, MONDO:0011382; HPO:HP:0002616 (aortic root aneurysm), HP:0001654 (aortic regurgitation), HP:0000545 (myopia), HP:0001083 (ectopia lentis), HP:0001763 (pes planus); Orphanet:ORPHA:558 (Marfan).

## Why FBN1

Demonstrates the *modular ECM protein* case (47+ tandem domains, residue-level calcium coordination critical for function). Shows how the position-aware feature tool reveals which specific cbEGF domain is hit and whether a calcium-coordinating residue is altered — the structural rationale for the variant's pathogenicity.
