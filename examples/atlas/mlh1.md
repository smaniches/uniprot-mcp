# Atlas — MLH1

**UniProt:** [P40692](https://www.uniprot.org/uniprotkb/P40692).
**Gene:** MLH1 · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0007648 (Lynch syndrome 2), MONDO:0009116 (Muir-Torre syndrome), MONDO:0007637 (mismatch repair cancer syndrome 1, biallelic).
**OMIM:** 120436 (gene), 609310 (Lynch syndrome 2), 158320 (Muir-Torre).
**Disease class:** mismatch-repair (MMR) hereditary cancer; Lynch syndrome canonical.

## Question

For a Lynch-syndrome family with a MLH1 frameshift, what's the protein-domain context (ATPase + dimerisation), and what's the immunotherapy implication (MMR-deficient → microsatellite-instability-high → checkpoint-inhibitor responsiveness)?

## Tool sequence

1. `uniprot_get_entry("P40692")` — function (MutL homolog; MMR), 756 aa.
2. `uniprot_features_at_position("P40692", <pos>)` — N-terminal ATPase domain (1–340), C-terminal interaction domain.
3. `uniprot_lookup_variant("P40692", "<HGVS>")` — UniProt-curated mutations.
4. `uniprot_resolve_clinvar("P40692", size=15)` — many Pathogenic / likely-Pathogenic Lynch alleles.
5. `uniprot_get_active_sites("P40692")` — ATP-binding GHL motif; Mg2+ coordination.
6. `uniprot_resolve_pdb("P40692")` — N-terminal ATPase domain structures; C-terminal MutLα heterodimer with PMS2.
7. `uniprot_get_disease_associations("P40692")` — Lynch 2, Muir-Torre, MMRCS1.

## Therapeutic axis

**Direct therapy for MLH1 deficiency:** none — this is a tumour suppressor, not a drug target. **Indirect:** MMR-deficient tumours have very high mutational burden + microsatellite instability (MSI-H) → exceptional response to **PD-1 / PD-L1 inhibitors** (pembrolizumab, dostarlimab, nivolumab). Tumour-agnostic FDA approvals for dMMR/MSI-H solid tumours via pembrolizumab (KEYNOTE-158 / KEYNOTE-177).

## Cross-references

| Resource | Notes |
|---|---|
| PDB | ATPase domain + heterodimer with PMS2. |
| AlphaFold DB | `AF-P40692-F1`. |
| ChEMBL | Indirect: checkpoint inhibitors target PD-1 / PD-L1 (PDCD1 / CD274), not MLH1 itself. |
| ClinVar | Hundreds of curated Lynch alleles; founder mutations + variants of uncertain significance. |

## Adjacent ontologies

MONDO:0007648 (Lynch 2), MONDO:0009116 (Muir-Torre), MONDO:0007637 (MMRCS1, CMMRD); HPO:HP:0006716 (hereditary nonpolyposis colorectal cancer), HP:0003003 (colon cancer); Orphanet:ORPHA:144 (Lynch).

## Why MLH1

The MMR-deficiency → immunotherapy-responsiveness axis is a paradigm-defining example of how variant-level genetic analysis drives a totally non-obvious therapeutic decision. Demonstrates the dossier on a tumour-suppressor gene where the "drug target" is not the gene itself but the immune system response.
