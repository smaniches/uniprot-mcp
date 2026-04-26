# Atlas — SNCA (alpha-Synuclein)

**UniProt:** [P37840](https://www.uniprot.org/uniprotkb/P37840).
**Gene:** SNCA · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0008199 (Parkinson disease 1, autosomal dominant), MONDO:0008245 (dementia with Lewy bodies), MONDO:0008298 (multiple system atrophy).
**OMIM:** 163890 (gene), 168600 (PD1), 127750 (DLB).
**Disease class:** neurodegenerative; intrinsically disordered protein → amyloid (Lewy bodies).

## Question

How does the small intrinsically disordered protein α-synuclein cause disease, and what residue-level annotations support fibril-targeted therapeutic design (anti-aggregation antibodies, immunotherapy)?

## Tool sequence

1. `uniprot_get_entry("P37840")` — 140 aa, three regions: amphipathic N-term (1–60), NAC core (61–95), acidic C-term (96–140).
2. `uniprot_features_at_position("P37840", 53)` — A53T (PARK1) familial mutation residue.
3. `uniprot_lookup_variant("P37840", "A53T")` — UniProt natural variant.
4. `uniprot_get_alphafold_confidence("P37840")` — predominantly low/very-low pLDDT (intrinsically disordered).
5. `uniprot_resolve_pdb("P37840")` — fibril cryo-EM structures (the recent revolution); micelle-bound NMR structures.
6. `uniprot_get_processing_features("P37840")` — initiator methionine.
7. `uniprot_get_ptms("P37840")` — phosphorylation at Ser-129 (the dominant Lewy-body PTM).

## Therapeutic axis

**Anti-aggregation antibodies (clinical):** prasinezumab (Roche/Prothena), cinpanemab (Biogen — discontinued), MEDI1341.

**Immunotherapy:** active vaccines (PD01A from AFFiRiS, etc.).

**Small molecules:** anle138b (oligomer-modulator) in clinical trials; many natural-product hits (curcumin, EGCG) in preclinical literature.

**Antisense:** ION464 (Ionis/Biogen) — SNCA-lowering oligonucleotide.

**LRRK2 inhibitors** (BIIB122/DNL151, BIIB094) target downstream/upstream pathways but not SNCA directly.

## Cross-references

PDB has the fibril cryo-EM structures (revolutionary post-2018); ChEMBL has anle138b and aggregation modulators; ClinVar has familial PD variants (A53T, A30P, E46K, H50Q, G51D).

## Adjacent ontologies

MONDO:0008199 (PD1), MONDO:0008245 (DLB), MONDO:0008298 (MSA); HPO:HP:0001300 (parkinsonism), HP:0002354 (memory impairment); Orphanet:ORPHA:411602.

## Why SNCA

The intrinsically disordered protein → amyloid case. Demonstrates that AlphaFold's confidence bands correctly flag IDPs (low pLDDT throughout) — the tool surfaces the structural reality rather than overclaiming a single fold. Therapeutic axis is dominated by aggregation-modulators, not active-site inhibitors.
