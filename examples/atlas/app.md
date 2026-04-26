# Atlas — APP (Amyloid precursor protein)

**UniProt:** [P05067](https://www.uniprot.org/uniprotkb/P05067)
**Gene symbol:** APP
**Protein:** Amyloid-beta precursor protein
**Organism:** *Homo sapiens* (taxonomy ID 9606)
**Disease (MONDO):** [MONDO:0004975 — Alzheimer disease](https://monarchinitiative.org/disease/MONDO:0004975); see also MONDO:0007088 (familial AD type 1).
**OMIM:** [104760 (APP gene)](https://omim.org/entry/104760), 104300 (Alzheimer disease).
**Disease class:** neurodegenerative; the textbook secreted-protein-precursor proteolytic-processing case.

## Question this atlas entry answers

A neurogenetics group analyses an APP variant in a familial AD
pedigree. They need: where in the protein the variant sits relative
to the secretase cleavage sites (β-secretase, α-secretase,
γ-secretase), and how that affects the Aβ40 / Aβ42 ratio.

## Tool sequence

| # | Tool | Question |
|---|---|---|
| 1 | `uniprot_get_entry("P05067")` | Function, 770 aa length (canonical isoform), domain organisation. |
| 2 | `uniprot_get_processing_features("P05067")` | The headline tool: signal peptide, secretase cleavage sites, the Aβ peptide chain (residues 672–711 / 672–713). |
| 3 | `uniprot_features_at_position("P05067", <variant_pos>)` | Which secretase cleavage region houses the variant? |
| 4 | `uniprot_lookup_variant("P05067", "<HGVS>")` | Familial AD variants in UniProt's catalogue. |
| 5 | `uniprot_resolve_clinvar("P05067", size=10)` | ClinVar classifications for APP variants. |
| 6 | `uniprot_get_disease_associations("P05067")` | AD type 1, cerebral amyloid angiopathy. |
| 7 | `uniprot_get_alphafold_confidence("P05067")` | pLDDT distribution; the soluble extracellular E1/E2 domains are well-folded, the Aβ region is small and partially disordered. |

## Expected response shape

- **Step 2**: the formatter must surface (at minimum) `Signal peptide`, `Chain`, and (if curated) `Site` annotations near the secretase cleavages. Aβ as a `Peptide` feature ~672–713.
- **Step 4**: known FAD variants like `V717I` (London), `K670N/M671L` (Swedish), `A673T` (Icelandic protective) appear.
- **Step 6**: at least Alzheimer disease, type 1 (familial), and cerebral amyloid angiopathy (Dutch type).

## Therapeutic axis (interpretation)

- **Aβ-targeting antibodies:** lecanemab, donanemab, aducanumab —
  approved or investigational anti-amyloid mAbs that bind soluble
  Aβ aggregates and amyloid plaques.
- **β-secretase (BACE1) inhibitors:** mostly halted clinical
  programs due to cognitive worsening; the mechanism is ruled out.
- **γ-secretase modulators:** investigational.
- **APP itself:** not a small-molecule drug target; the
  therapeutic axis is the Aβ peptide and its proteolytic origin.
- ChEMBL bridge: small-molecule modulators of BACE1 (target =
  BACE1 entry), γ-secretase complex; the APP entry's ChEMBL link
  is mostly indirect.

## Provenance fields

Standard envelope on every response.

## Cross-references in scope

| Resource | Returned via |
|---|---|
| PDB | Multiple structures of the E1/E2 extracellular domains, the Aβ peptide in various aggregation states. |
| AlphaFold DB | `AF-P05067-F1`. |
| ChEMBL | APP entry direct; the BACE1/γ-secretase entries are richer. |
| ClinVar | Familial AD variants; β-amyloid pathology variants. |
| OMIM | 104300 (AD), 605714 (CAA Dutch). |

## Adjacent ontologies

| Ontology | Identifier |
|---|---|
| MONDO | MONDO:0004975 (AD), MONDO:0007088 (FAD type 1), MONDO:0007098 (CAA Dutch) |
| HPO | HP:0002511 (Alzheimer disease), HP:0002145 (frontotemporal dementia overlap), HP:0001302 (pachygyria — for some FAD variants) |
| Orphanet | ORPHA:1020 (familial AD) |

## Why APP

APP exercises the `uniprot_get_processing_features` tool family on
a textbook proteolytic-processing protein. Demonstrates that the
position of a variant *relative to the secretase cleavage sites*
controls its disease mechanism — a query the position-aware
feature tools answer directly.
