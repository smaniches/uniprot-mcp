# Atlas — HBB (Hemoglobin beta)

**UniProt:** [P68871](https://www.uniprot.org/uniprotkb/P68871)
**Gene symbol:** HBB
**Protein:** Hemoglobin subunit beta
**Organism:** *Homo sapiens* (taxonomy ID 9606)
**Disease (MONDO):** [MONDO:0011382 — sickle cell disease](https://monarchinitiative.org/disease/MONDO:0011382); see also MONDO:0007928 (beta-thalassemia).
**OMIM:** [141900 (HBB gene)](https://omim.org/entry/141900), 603903 (sickle cell anemia).
**Disease class:** rare-disease hemoglobinopathy; one of the most-studied human variants.

## Question this atlas entry answers

A clinical-genetics team interprets the canonical sickle-cell
variant `HBB E6V` (`p.Glu7Val` in modern numbering, `Glu6Val` in
the historical mature-chain numbering). They need: the residue's
structural context, ClinVar classification, AlphaFold confidence,
and the therapeutic landscape (transfusion, hydroxyurea,
voxelotor, gene therapy).

## Tool sequence

| # | Tool | Question |
|---|---|---|
| 1 | `uniprot_get_entry("P68871")` | Function (oxygen transport in erythrocytes); 147 aa length; processing (initiator methionine cleaved). |
| 2 | `uniprot_get_processing_features("P68871")` | Initiator methionine + Chain boundaries. Disambiguates the E6V vs E7V numbering. |
| 3 | `uniprot_features_at_position("P68871", 7)` | Residue 7 in UniProt numbering (= position 6 in mature chain). |
| 4 | `uniprot_lookup_variant("P68871", "E7V")` | UniProt natural variant for the sickle-cell mutation. |
| 5 | `uniprot_resolve_clinvar("P68871", change="E7V", size=5)` | ClinVar classification (Pathogenic; expert-reviewed). |
| 6 | `uniprot_get_ptms("P68871")` | Heme-binding ligand site at His-93. |
| 7 | `uniprot_get_alphafold_confidence("P68871")` | High pLDDT across the well-folded globin fold. |
| 8 | `uniprot_resolve_pdb("P68871")` | Many PDB structures (one of the most-resolved human proteins). |

## Expected response shape

- **Step 2**: `Initiator methionine` at position 1 (Removed); `Chain` from 2 to 147 ("Hemoglobin subunit beta"). The mature-chain renumbering offsets historical literature by 1.
- **Step 3**: residue 7 carries `Natural variant` annotations including the E→V sickle-cell mutation.
- **Step 5**: Pathogenic, reviewed by expert panel, condition includes sickle cell anemia + sickle-beta-thalassemia.
- **Step 6**: PTMs include `Modified residue` annotations and the `Site` annotation for heme binding.
- **Step 7**: pLDDT predominantly in `very high` band (small, well-folded globin fold).

## Therapeutic axis (interpretation)

- **Disease-modifying small molecules:** hydroxyurea (induces
  fetal hemoglobin); voxelotor (HbS polymerisation inhibitor);
  crizanlizumab (P-selectin antibody) for vaso-occlusive crisis.
- **Curative:** allogeneic stem-cell transplant; *ex vivo* gene
  therapy (exa-cel via CRISPR-Cas9 BCL11A disruption restoring
  fetal hemoglobin; lovotibeglogene autotemcel via lentiviral HbA
  delivery).
- ChEMBL bridge: small-molecule chaperones (voxelotor analogues),
  PDE9 inhibitors, BCL11A modulators.

## Provenance fields

Standard envelope on every response.

## Cross-references in scope

| Resource | Returned via |
|---|---|
| PDB | One of the most-resolved entries; thousands of structures of HbS, HbA, HbF tetramers. |
| AlphaFold DB | `AF-P68871-F1`. |
| ChEMBL | Voxelotor, hydroxyurea analogues, BCL11A modulators (indirect). |
| ClinVar | Hundreds of annotated variants spanning the entire gene. |
| OMIM | 603903 (sickle cell), 613985 (Heinz body anemia), 615159 (methemoglobinemia beta type), many more. |

## Adjacent ontologies

| Ontology | Identifier |
|---|---|
| MONDO | MONDO:0011382 (sickle cell disease), MONDO:0007928 (beta-thalassemia) |
| HPO | HP:0001923 (vaso-occlusive crisis), HP:0001877 (anemic crisis), HP:0001903 (hemolytic anemia) |
| Orphanet | ORPHA:232 (sickle cell anemia), ORPHA:848 (beta-thalassemia) |

## Why HBB

HBB demonstrates the *processing-features matters* workflow
(initiator methionine cleavage means UniProt residue 7 = literature
residue 6), the small-well-folded-protein AlphaFold case (uniformly
high pLDDT), and the rich ChEMBL bridge for a curable hemoglobinopathy.
