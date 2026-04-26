# Atlas — NF1 (Neurofibromin)

**UniProt:** [P21359](https://www.uniprot.org/uniprotkb/P21359).
**Gene:** NF1 · **Organism:** *Homo sapiens* (9606).
**Disease (MONDO):** MONDO:0018975 (neurofibromatosis type 1).
**OMIM:** 613113 (gene), 162200 (NF1).
**Disease class:** rare-disease tumour predisposition; RAS-pathway negative regulator (RasGAP).

## Question

For a NF1 family with a truncating variant, what's the structural region (CSRD, GRD, SecPH, Sec14, PH, CTD), and what's the therapeutic axis for plexiform neurofibromas (selumetinib MEK inhibition)?

## Tool sequence

1. `uniprot_get_entry("P21359")` — function (Ras-GTPase activating protein), 2839 aa.
2. `uniprot_features_at_position("P21359", <pos>)` — GRD (GAP-related domain, ~1209–1531), Sec14 (~1545–1816).
3. `uniprot_lookup_variant("P21359", "<HGVS>")`.
4. `uniprot_resolve_clinvar("P21359", size=20)`.
5. `uniprot_get_active_sites("P21359")` — arginine finger in the GRD (R1276 catalytic).
6. `uniprot_resolve_pdb("P21359")` — GRD structure with HRAS; Sec14-PH structure.
7. `uniprot_get_disease_associations("P21359")` — NF1, Watson syndrome, NF–Noonan overlap.

## Therapeutic axis

**Plexiform neurofibromas in NF1:** **selumetinib** (Koselugo, AstraZeneca) — MEK1/2 inhibitor; FDA-approved 2020 for inoperable plexiform neurofibromas in pediatric NF1. Mechanism: NF1 loss → constitutive RAS activation → MAPK pathway hyperactivity → MEK inhibition restores balance.

**Cutaneous neurofibromas:** topical / surgical management.

**Malignant peripheral nerve sheath tumours (MPNST):** chemotherapy + emerging investigational targeted therapies (PRC2 inhibitors, others).

**NF1-mutant cancers (sporadic):** MEK inhibition is the primary actionable axis; investigational SHP2 + SOS1 inhibitors target upstream of RAS.

## Cross-references

PDB has GRD-RAS complex structures (mechanism of GAP catalysis); AlphaFold `AF-P21359-F1`; ChEMBL has selumetinib (against MEK1/MEK2, not NF1 itself); ClinVar has thousands of NF1 variants.

## Adjacent ontologies

MONDO:0018975 (NF1); HPO:HP:0000957 (café-au-lait macule), HP:0001065 (striae distensae), HP:0009732 (plexiform neurofibroma), HP:0009726 (neurofibroma); Orphanet:ORPHA:636.

## Why NF1

Demonstrates the *tumour-suppressor whose downstream pathway is druggable* case. NF1 itself is not a small-molecule target, but the MEK inhibition that restores RAS-pathway balance is — and selumetinib's approval was a landmark for NF1 management. Same logic applies to MLH1 (MMR-deficient → checkpoint-inhibitor responsiveness): the gateway surfaces the substrate; the orchestrator handles the matchmaking.
