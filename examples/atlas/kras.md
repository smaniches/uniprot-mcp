# Atlas — KRAS

**UniProt:** [P01116](https://www.uniprot.org/uniprotkb/P01116) — KRas isoform 4B canonical.
**Gene:** KRAS · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0005233 (NSCLC), MONDO:0005077 (colorectal cancer), MONDO:0005192 (pancreatic adenocarcinoma).
**OMIM:** 190070 (gene), 211980 (NSCLC), 114500 (CRC), 260350 (PDAC).
**Disease class:** somatic-driver oncogene (small GTPase).

## Question

How is `KRAS G12C` actionable, and what's the structural context at the GTP/GDP switch region (residues 32–40)?

## Tool sequence

1. `uniprot_get_entry("P01116")` — function (small GTPase, RAS family), 189 aa.
2. `uniprot_features_at_position("P01116", 12)` — Switch I region, P-loop, Natural variant (G12C / G12D / G12V).
3. `uniprot_lookup_variant("P01116", "G12C")` — surfaces oncogenic variant.
4. `uniprot_resolve_clinvar("P01116", change="G12C", size=5)` — somatic Pathogenic.
5. `uniprot_get_active_sites("P01116")` — GTP-binding residues, magnesium coordination.
6. `uniprot_resolve_pdb("P01116")` — many GDP/GTP-bound structures + sotorasib/adagrasib-bound G12C structures.
7. `uniprot_resolve_chembl("P01116")` — sotorasib, adagrasib, MRTX1133.

## Therapeutic axis

KRAS was "undruggable" until covalent G12C inhibitors (sotorasib/AMG-510, adagrasib/MRTX-849) showed clinical activity by trapping the protein in its inactive GDP-bound state via Cys-12. G12D-specific inhibitors (MRTX1133) and pan-KRAS allele inhibitors (RMC-6236, RMC-6291) are next-generation. SHP2 (PTPN11) and SOS1 inhibitors target upstream of KRAS.

## Cross-references

| Resource | Notes |
|---|---|
| PDB | Many GDP/GTP forms; sotorasib + adagrasib co-crystal structures. |
| AlphaFold DB | `AF-P01116-F1`. |
| ChEMBL | KRAS rapidly populated since 2020 G12C breakthrough. |
| ClinVar | G12-codon and Q61-codon somatic variants well-curated. |

## Adjacent ontologies

MONDO:0005233 (NSCLC), MONDO:0005077 (CRC), MONDO:0005192 (PDAC); EFO:0003060 (NSCLC); HPO:HP:0100526 (lung neoplasm).

## Why KRAS

The undruggable-target-redeemed story; demonstrates the position-aware feature tool on a small GTPase + the ChEMBL bridge for a recently-druggable oncogene.
