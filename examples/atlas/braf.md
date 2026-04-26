# Atlas — BRAF

**UniProt:** [P15056](https://www.uniprot.org/uniprotkb/P15056).
**Gene:** BRAF · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0005105 (melanoma), MONDO:0005077 (CRC), MONDO:0008753 (cardiofaciocutaneous syndrome 1).
**OMIM:** 164757 (gene), 155600 (melanoma), 115150 (CFC1).
**Disease class:** somatic-driver oncogene (MAPK pathway kinase) + germline RASopathy.

## Question

`BRAF V600E` — the canonical oncogenic activation. What kinase-domain residues, what therapeutic axis (vemurafenib/dabrafenib/encorafenib + MEK inhibitor combination)?

## Tool sequence

1. `uniprot_get_entry("P15056")` — function (RAF kinase), 766 aa, kinase domain residues 457–717.
2. `uniprot_features_at_position("P15056", 600)` — activation loop; V600E is the dominant cutaneous melanoma mutation.
3. `uniprot_lookup_variant("P15056", "V600E")`.
4. `uniprot_resolve_clinvar("P15056", change="V600E", size=5)` — Pathogenic somatic.
5. `uniprot_get_active_sites("P15056")` — ATP-binding K483, catalytic D576, DFG-motif D594.
6. `uniprot_resolve_pdb("P15056")` — many V600E and wild-type kinase domain structures with various inhibitors.
7. `uniprot_resolve_chembl("P15056")` — vemurafenib, dabrafenib, encorafenib + next-gen.

## Therapeutic axis

V600E confers constitutive MAPK pathway activation. Type-I RAF inhibitors (vemurafenib, dabrafenib, encorafenib) bind the active conformation of BRAF V600E. **Combination with a MEK inhibitor** (trametinib, cobimetinib, binimetinib) prevents paradoxical MAPK activation in RAF-WT cells and improves efficacy. Type-II pan-RAF inhibitors (LY3009120, naporafenib) and "paradox breakers" (PLX8394) target resistant settings. In **CRC**, anti-EGFR addition is required because RAS-pathway feedback differs from melanoma.

## Cross-references

PDB-rich; AlphaFold model `AF-P15056-F1`; ChEMBL one of the best-populated kinase targets; ClinVar for V600E plus the rarer V600K, V600R, V600M alleles.

## Adjacent ontologies

MONDO:0005105 (melanoma), MONDO:0005077 (CRC), MONDO:0008753 (CFC1); EFO:0000756 (melanoma); HPO:HP:0002861 (melanoma), HP:0001627 (cardiofaciocutaneous syndrome features for germline).

## Why BRAF

Canonical kinase-V600E case; demonstrates the same position-aware workflow on a kinase domain rather than a small GTPase. Combination-therapy reasoning is downstream of `uniprot-mcp` but the gateway surfaces the substrate (target identity + variant + structures + ChEMBL bridge).
