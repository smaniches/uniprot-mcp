# Atlas — BRCA1

**UniProt:** [P38398](https://www.uniprot.org/uniprotkb/P38398)
**Gene symbol:** BRCA1
**Protein:** Breast cancer type 1 susceptibility protein
**Organism:** *Homo sapiens* (taxonomy ID 9606)
**Disease (MONDO):** [MONDO:0011535 — hereditary breast-ovarian cancer syndrome 1 (HBOC1)](https://monarchinitiative.org/disease/MONDO:0011535); see also MONDO:0011686 (Fanconi anemia complementation group S).
**OMIM:** [113705 (BRCA1 gene)](https://omim.org/entry/113705), 604370 (HBOC1).
**Disease class:** hereditary cancer syndrome.

## Question this atlas entry answers

A drug-discovery team needs a complete characterisation of human
BRCA1 as a candidate target. They need: identity, function,
structural evidence, drug-target context (ChEMBL bridge), disease
associations (with MIM cross-references), and an evidence-quality
assessment.

## Tool sequence

| # | Tool | Question |
|---|---|---|
| 1 | `uniprot_target_dossier("P38398")` | One-call comprehensive nine-section view: identity, function, chemistry, structure, drug-target, disease, variants, functional annotations, cross-refs. |
| 2 | `uniprot_resolve_pdb("P38398")` | PDB structures (~30 typical; best resolution at the BRCT domain). |
| 3 | `uniprot_resolve_chembl("P38398")` | ChEMBL target id; BRCA1's therapeutic axis is *synthetic lethality* with PARP inhibitors in BRCA1-deficient tumours. |
| 4 | `uniprot_get_evidence_summary("P38398")` | ECO-code distribution; distinguishes wet-lab from inferred-by-similarity from automatic. |
| 5 | `uniprot_get_active_sites("P38398")` | RING domain E3 ligase active site + zinc-coordinating residues. |
| 6 | `uniprot_get_alphafold_confidence("P38398")` | pLDDT band breakdown; the central ~1500-residue region is largely disordered → low confidence there. |
| 7 | `uniprot_resolve_clinvar("P38398", size=10)` | Pathogenic / likely-pathogenic variants in ClinVar by gene. |

## Expected response shape

- **Step 1**: dossier `chemistry.molecular_weight` ≈ 207,720 Da; `structure.pdb_count` > 0; `diseases` list ≥ 5 entries (HBOC1, pancreatic cancer 4, FANCS, more).
- **Step 5**: at least one Active site (RING domain E3) and metal-binding residues (zinc).
- **Step 6**: bimodal pLDDT distribution — RING + BRCT domains in `confident`+ bands; central region in `low`/`very low` bands.

## Drug-target signal (interpretation)

- **Druggable surfaces:** RING domain (E3 ligase activity) and BRCT
  domain (phosphopeptide binding) are well-resolved structurally
  and have small-molecule inhibitor literature.
- **Therapeutic axis:** synthetic lethality with PARP inhibitors
  (olaparib, talazoparib) in BRCA1-mutant tumours — the
  established clinical strategy.
- **Direct inhibition of BRCA1:** discouraged; the central
  disordered region resists co-crystallisation with small
  molecules, and BRCA1 itself is a tumour suppressor.

## Provenance fields (every response)

Same as TP53 — every tool call carries `source / release /
release_date / retrieved_at / url / response_sha256`.
`uniprot_provenance_verify` recovers the verdict for any prior
capture.

## Cross-references in scope

| Resource | Returned via |
|---|---|
| PDB | `uniprot_resolve_pdb` (typical: ~30 structures) |
| AlphaFold DB | `uniprot_resolve_alphafold` + `uniprot_get_alphafold_confidence` |
| ChEMBL | `uniprot_resolve_chembl` (target ID + EBI card URL) |
| InterPro | `uniprot_resolve_interpro` (BRCT, RING, BRCA1 family) |
| OMIM | `uniprot_get_disease_associations` (MIM:604370, MIM:614320, MIM:617883, etc.) |
| ClinVar | `uniprot_resolve_clinvar` |

## Adjacent ontologies

| Ontology | Identifier |
|---|---|
| MONDO | MONDO:0011535 (HBOC1), MONDO:0011686 (FANCS) |
| HPO | HP:0003002 (breast carcinoma), HP:0100615 (ovarian neoplasm), many more |
| EFO | EFO_0003869 (breast carcinoma) |

## Why BRCA1

BRCA1 has 8 UniProt-curated disease associations, 1500+ natural
variants, ~30 PDB structures concentrated on RING + BRCT domains, a
well-established therapeutic axis (PARPi synthetic lethality), and
deep literature. It is the natural second case after TP53 for
demonstrating the dossier composition.
