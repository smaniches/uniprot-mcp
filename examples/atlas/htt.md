# Atlas — HTT (Huntingtin)

**UniProt:** [P42858](https://www.uniprot.org/uniprotkb/P42858)
**Gene symbol:** HTT
**Protein:** Huntingtin
**Organism:** *Homo sapiens* (taxonomy ID 9606)
**Disease (MONDO):** [MONDO:0007739 — Huntington disease](https://monarchinitiative.org/disease/MONDO:0007739).
**OMIM:** [613004 (HTT gene)](https://omim.org/entry/613004), 143100 (HD).
**Disease class:** trinucleotide-repeat disorder; neurodegenerative; autosomal dominant.

## Question this atlas entry answers

A neurogenetics group needs to characterise huntingtin: the
polyglutamine (polyQ) tract that drives disease, the structural
disorder of the N-terminus, and the lack of a directly druggable
small-molecule target (the therapeutic axis is *lowering* HTT
expression — antisense oligonucleotides, RNAi).

## Tool sequence

| # | Tool | Question |
|---|---|---|
| 1 | `uniprot_get_entry("P42858")` | Function (huntingtin scaffold), length (~3142 aa), domain organisation. |
| 2 | `uniprot_features_at_position("P42858", 18)` | Polyglutamine repeat region (~residues 18–36 normal). |
| 3 | `uniprot_get_processing_features("P42858")` | Caspase cleavage sites that release the toxic N-terminal fragment. |
| 4 | `uniprot_get_alphafold_confidence("P42858")` | pLDDT distribution; large disordered regions expected. |
| 5 | `uniprot_resolve_pdb("P42858")` | PDB coverage of HEAT repeats; full-length is too large to crystallise. |
| 6 | `uniprot_get_disease_associations("P42858")` | Huntington disease (MIM:143100). |

## Expected response shape

- **Step 2**: features at the polyQ region include `Compositional bias` (polyQ), `Region` (HEAT repeat), and possibly `Repeat` annotations.
- **Step 3**: caspase-3 cleavage at residues ~513 and ~552 should be annotated as `Site` features in the entry.
- **Step 4**: bimodal pLDDT — HEAT repeat core in `confident`/`very high`, N-terminus and inter-repeat linkers in `low`/`very low`.
- **Step 5**: structures cover individual HEAT repeats and the N-HEAT/C-HEAT subdomains; full-length structures are limited to cryo-EM at moderate resolution.

## Therapeutic axis (interpretation)

- **HTT-lowering therapies** (antisense oligonucleotides like
  tominersen; RNAi like AMT-130) target the *RNA*, not the protein.
- **Splice-modulating** approaches alter HTT mRNA processing.
- **Small-molecule inhibition of HTT itself** is not a viable
  axis — too large, too disordered, no druggable pocket.
- ChEMBL bridge: HTT entries in ChEMBL primarily reference
  research compounds for HTT-aggregation imaging, not therapeutic
  small molecules.

## Provenance fields

Standard envelope on every response.

## Cross-references in scope

| Resource | Returned via |
|---|---|
| PDB | Multiple HEAT-repeat segment structures. |
| AlphaFold DB | `AF-P42858-F1` full-length model (with confidence bands). |
| InterPro | HEAT repeat signature; HTT family signature. |
| OMIM | 143100 (Huntington disease). |
| ClinVar | CAG-repeat sizing variants (the canonical "expansion"). |

## Adjacent ontologies

| Ontology | Identifier |
|---|---|
| MONDO | MONDO:0007739 (Huntington disease) |
| HPO | HP:0002073 (chorea), HP:0000726 (dementia), many more |
| Orphanet | ORPHA:399 (Huntington disease) |

## Why HTT

HTT exercises the "long, partially-disordered protein" case —
showing how the AlphaFold confidence-band tool surfaces the
boundary between structured (HEAT repeats) and disordered regions.
It also illustrates an honest empty-set ChEMBL response: not every
disease-associated protein is a small-molecule drug target, and
the tool's empty-set advisory directs users to the actual
therapeutic axis (HTT lowering).
