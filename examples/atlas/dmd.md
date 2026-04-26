# Atlas — DMD (Dystrophin)

**UniProt:** [P11532](https://www.uniprot.org/uniprotkb/P11532)
**Gene symbol:** DMD
**Protein:** Dystrophin
**Organism:** *Homo sapiens* (taxonomy ID 9606)
**Disease (MONDO):** [MONDO:0010679 — Duchenne muscular dystrophy](https://monarchinitiative.org/disease/MONDO:0010679); see also MONDO:0010311 (Becker muscular dystrophy).
**OMIM:** [300377 (DMD gene)](https://omim.org/entry/300377), 310200 (DMD), 300376 (BMD).
**Disease class:** X-linked muscular dystrophy; spectrin-family cytoskeletal protein.

## Question this atlas entry answers

A neuromuscular clinic interprets a DMD nonsense or frameshift
variant. They need: which exons are affected, whether the variant
is amenable to *exon-skipping* therapy (eteplirsen, golodirsen,
viltolarsen, casimersen), and the structural region containing
the variant residue.

## Tool sequence

| # | Tool | Question |
|---|---|---|
| 1 | `uniprot_get_entry("P11532")` | Function (cytoskeletal scaffold), 3685 aa length, four spectrin-repeat regions. |
| 2 | `uniprot_features_at_position("P11532", <pos>)` | What region is the variant in? |
| 3 | `uniprot_get_processing_features("P11532")` | Initiator methionine; chain boundaries. |
| 4 | `uniprot_get_alphafold_confidence("P11532")` | Overall pLDDT (long, mostly-confident spectrin-repeat regions; flexible linkers). |
| 5 | `uniprot_resolve_pdb("P11532")` | PDB structures (limited; spectrin-repeat segment structures only). |
| 6 | `uniprot_get_disease_associations("P11532")` | DMD, BMD, X-linked dilated cardiomyopathy 3B. |

## Expected response shape

- **Step 1**: the entry shows ~3685 aa, multiple spectrin-repeat domains, and the WW + EF-hand + ZZ-type zinc-finger C-terminal modules.
- **Step 4**: pLDDT is high over each spectrin repeat individually but lower at inter-repeat linkers — consistent with a long modular cytoskeletal protein.
- **Step 6**: at least three associated diseases (DMD, BMD, CMD3B).

## Therapeutic axis (interpretation)

- **Exon skipping** (eteplirsen → exon 51, golodirsen → exon 53,
  viltolarsen → exon 53, casimersen → exon 45) restores the
  reading frame for specific deletion patterns. The atlas entry
  for a particular variant should call out which exon-skipping
  drug applies (if any).
- **Gene therapy** (delandistrogene moxeparvovec) delivers
  micro-dystrophin via AAV — applicable across many genotypes.
- **Stop-codon read-through** (ataluren) for nonsense mutations.
- ChEMBL bridge: the small-molecule axis is dominated by
  read-through compounds; the antisense and gene-therapy axes
  live outside ChEMBL.

## Provenance fields

Standard envelope on every response.

## Cross-references in scope

| Resource | Returned via |
|---|---|
| PDB | Limited — spectrin-repeat fragment structures only. |
| AlphaFold DB | `AF-P11532-F1` (very long; multi-fragment in legacy AF). |
| OMIM | 310200, 300376, 302045. |
| ClinVar | DMD has thousands of curated variants; surfaced via `uniprot_resolve_clinvar`. |

## Adjacent ontologies

| Ontology | Identifier |
|---|---|
| MONDO | MONDO:0010679 (DMD), MONDO:0010311 (BMD), MONDO:0010500 (CMD3B) |
| HPO | HP:0003560 (muscular dystrophy), HP:0001288 (gait disturbance), HP:0002650 (scoliosis), many more |
| Orphanet | ORPHA:98896 (DMD), ORPHA:98895 (BMD) |

## Why DMD

DMD demonstrates the *very long protein* case (one of the longest
human proteins at 3685 aa) and the *exon-skipping therapeutic
matchmaking* workflow, where the atlas entry for a particular
variant connects directly to FDA-approved antisense
oligonucleotide therapies. The empty-set ChEMBL advisory is also
relevant here — most therapeutic options are nucleic-acid based
and live outside ChEMBL's small-molecule remit.
