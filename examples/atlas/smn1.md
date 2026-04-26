# Atlas — SMN1 (Survival of motor neuron 1)

**UniProt:** [Q16637](https://www.uniprot.org/uniprotkb/Q16637).
**Gene:** SMN1 · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0011127 (spinal muscular atrophy type 1, Werdnig-Hoffmann), MONDO:0011131 (SMA type 2), MONDO:0011132 (SMA type 3, Kugelberg-Welander), MONDO:0011130 (SMA type 4, adult-onset).
**OMIM:** 600354 (gene), 253300 (SMA1), 253550 (SMA2), 253400 (SMA3), 271150 (SMA4).
**Disease class:** rare-disease motor-neuron disorder; one of the most-cited gene-therapy success stories.

## Question

For a SMA newborn-screen positive, the SMN1 deletion is canonical. What does the SMN copy number (SMN1 + SMN2) predict about phenotype severity, and what's the therapeutic axis (nusinersen, risdiplam, onasemnogene abeparvovec)?

## Tool sequence

1. `uniprot_get_entry("Q16637")` — function (snRNP assembly + axonal transport), 294 aa.
2. `uniprot_features_at_position("Q16637", <pos>)` — Tudor domain (90–158), YG-box (260–293).
3. `uniprot_lookup_variant("Q16637", "<HGVS>")` — point variants (rare; most SMA is the canonical exon 7/8 deletion).
4. `uniprot_resolve_clinvar("Q16637", size=10)` — Pathogenic point mutations.
5. `uniprot_resolve_pdb("Q16637")` — Tudor domain structures.
6. `uniprot_get_disease_associations("Q16637")` — SMA1–4.

## Therapeutic axis

**Three FDA-approved disease-modifying therapies — a paradigm shift in rare disease:**

- **Nusinersen** (Spinraza, Biogen/Ionis): antisense oligonucleotide that promotes SMN2 exon-7 inclusion, increasing functional SMN protein. Intrathecal administration every 4 months.
- **Risdiplam** (Evrysdi, PTC/Roche/SMA Foundation): small-molecule SMN2-splicing modifier, oral daily. Same mechanism as nusinersen but oral.
- **Onasemnogene abeparvovec** (Zolgensma, Novartis/AveXis): AAV9-delivered SMN1 cDNA gene therapy. One-time IV administration in patients <2 years; ~$2.1M list price. The first multimillion-dollar gene therapy.

**SMN2 copy number** is the biomarker: more SMN2 copies → milder phenotype. Most SMA1 patients have 2 SMN2 copies; SMA3 patients often have 3–4 copies.

## Cross-references

PDB has Tudor-domain structures; AlphaFold model `AF-Q16637-F1`; ChEMBL has risdiplam (SMN2 splice modifier — the target is technically the spliceosome, not SMN1 itself); ClinVar has the rare point mutations (most disease is SMN1 deletion).

## Adjacent ontologies

MONDO:0011127–MONDO:0011132 (SMA1–4); HPO:HP:0003323 (proximal muscle weakness), HP:0008936 (axial muscle weakness), HP:0001324 (muscle weakness); Orphanet:ORPHA:83330 (SMA).

## Why SMN1

The rare-disease gene-therapy success story — three completely different therapeutic modalities (ASO, splice modifier, AAV gene therapy) all approved for the same disease within five years (2016–2019). Demonstrates that the gateway tool's job is to surface the substrate — the rest of the therapeutic-matchmaking is a downstream-tool / orchestrator concern.
