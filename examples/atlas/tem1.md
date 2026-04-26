# Atlas — TEM-1 β-lactamase

**UniProt:** [P62593](https://www.uniprot.org/uniprotkb/P62593)
**Gene symbol:** *bla* (TEM)
**Protein:** β-lactamase TEM
**Organism:** *Escherichia coli* (taxonomy ID 562)
**Disease (MONDO):** *not applicable* — this is a pathogen drug-resistance enzyme, not a host disease gene. Adjacent ontology: NCBIT taxon 562; DOID:0050486 (drug-resistant infection).
**Disease class:** infectious-disease drug-resistance target (not a Mendelian disease); class A serine β-lactamase.

## Question this atlas entry answers

A medicinal-chemistry team scopes a β-lactamase inhibitor program.
They need: the catalytic machinery (Ser-70 nucleophile + the
oxyanion hole + the general base), the Sec-system signal peptide
and mature-chain boundaries, and the structural evidence
(many-PDB-structures-of-the-canonical-enzyme story).

## Tool sequence

| # | Tool | Question |
|---|---|---|
| 1 | `uniprot_search("protein_name:\"Beta-lactamase TEM\" AND organism_id:562 AND reviewed:true", size=1)` | Confirm canonical accession (P62593). |
| 2 | `uniprot_get_entry("P62593")` | Function (β-lactam hydrolysis), 286 aa, periplasmic localisation. |
| 3 | `uniprot_get_active_sites("P62593")` | The headline tool: Ser-70 (nucleophile), Glu-166 (general base), Lys-234 (oxyanion stabilisation), Ser-130 (substrate binding). |
| 4 | `uniprot_get_processing_features("P62593")` | 23-aa Sec signal peptide; mature chain residues 24–286. |
| 5 | `uniprot_get_ptms("P62593")` | Empty advisory — bacterial Sec-secreted enzymes typically have no curated PTMs (the empty advisory points at PhosphoSitePlus / GlyConnect for completeness). |
| 6 | `uniprot_resolve_pdb("P62593")` | Many high-resolution structures; canonical 1BTL at 1.80 Å, 1JTG at 1.73 Å, etc. |
| 7 | `uniprot_resolve_chembl("P62593")` | β-lactamase inhibitors (clavulanate, sulbactam, tazobactam) and avibactam-class diazabicyclooctanes. |

## Expected response shape

- **Step 3**: at least four Active site / Binding site annotations clustered in the active-site cleft (Ser-70, Glu-166, Lys-234, Ser-130).
- **Step 4**: `Signal peptide` 1–23 + `Chain` 24–286.
- **Step 5**: `0 feature(s)` with the honest empty advisory pointing at PhosphoSitePlus / GlyConnect — bacterial periplasmic enzymes are typically PTM-free.
- **Step 6**: 30+ PDB structures; the best at 1.73 Å (1JTG).

## Therapeutic axis (interpretation)

- **β-lactamase inhibitors** — small molecules that occupy the
  active site and prevent β-lactam hydrolysis. Three "classical"
  inhibitors (clavulanate, sulbactam, tazobactam) form a covalent
  acyl-enzyme intermediate at Ser-70 that is more stable than the
  productive hydrolytic intermediate.
- **Newer-generation inhibitors:**
  diazabicyclooctanes (avibactam, relebactam, durlobactam) —
  reversible covalent binders;
  boronate-based (vaborbactam, taniborbactam) — transition-state
  mimics.
- **Class shift:** TEM-1 is a class A serine β-lactamase.
  Carbapenemases (KPC, NDM, OXA, IMP) and metallo-β-lactamases
  (NDM-1) require different inhibitor chemistries — but the
  active-site geometry tool surfaces those mechanism differences.
- ChEMBL bridge: β-lactamase is a richly-populated target with
  small-molecule, peptide, and natural-product inhibitors.

## Provenance fields

Standard envelope on every response.

## Cross-references in scope

| Resource | Returned via |
|---|---|
| PDB | Many high-resolution apo and inhibitor-bound structures. |
| AlphaFold DB | `AF-P62593-F1` (very high confidence over the entire fold). |
| ChEMBL | Rich; clavulanate, sulbactam, tazobactam, avibactam, vaborbactam, relebactam, more. |
| InterPro | Class A β-lactamase signature (PF00144 etc.). |

## Adjacent ontologies

| Ontology | Identifier |
|---|---|
| NCBI taxonomy | 562 (*E. coli*) |
| ARO (CARD) | ARO:3000014 (TEM-1) — the Antibiotic Resistance Ontology canonical entry |
| DOID | DOID:0050486 (drug-resistant infection) |

## Why TEM-1

TEM-1 is the canonical infectious-disease drug-target case. It
demonstrates that the same `uniprot_get_active_sites` /
`uniprot_get_processing_features` / `uniprot_get_ptms` workflow
that handles human enzymes (PAH) also handles pathogen enzymes —
the tool surface is organism-agnostic. The empty PTM advisory is
honest and informative for a bacterial periplasmic enzyme.
