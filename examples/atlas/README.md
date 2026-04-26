# Disease & target atlas

Curated worked examples spanning the major axes of biomedical research,
each demonstrating the `uniprot-mcp` tool surface end-to-end on a real
disease/protein pair. Every entry is one Markdown file, structured as:

1. **Anchor** — the canonical UniProt accession plus the MONDO disease
   identifier (when applicable).
2. **Tool sequence** — the exact MCP tool calls a Claude agent would
   issue, in order, with the questions they answer.
3. **Expected provenance** — fields that should appear on every
   response so a third party can audit the answer years later.
4. **Cross-references** — pointers to ClinVar, OMIM, AlphaFold, PDB,
   ChEMBL, and adjacent ontologies (MONDO, HPO, EFO) that complement
   what `uniprot-mcp` returns.

## Why an atlas

A single worked transcript (`examples/01..04.jsonl`) demonstrates the
tool on one workflow. An atlas demonstrates breadth — that the tool
behaves consistently across the major disease classes and target
families that biomedical researchers actually work on. Pinning the
expected behaviour per atlas entry guards against silent drift when
UniProt issues a release change.

## Disease classes covered

| Class | Atlas entries | Why |
|---|---|---|
| **Hereditary cancer syndromes** | TP53, BRCA1, BRCA2, MSH2 | Most-cited Mendelian cancer drivers; high-confidence variant annotations; multiple OMIM/MONDO links per entry. |
| **Single-gene rare disease** | HTT (Huntington), DMD (Duchenne), CFTR (cystic fibrosis), HBB (sickle cell), PAH (phenylketonuria) | Textbook rare-disease examples; stable annotations; demonstrate position-aware feature lookup. |
| **Neurodegenerative** | APP (Alzheimer), SNCA (Parkinson), MAPT (FTD/PSP) | Multiple disease links per entry; show MONDO axis for sporadic vs familial forms. |
| **Cardiovascular** | MYH7 (HCM), LMNA (laminopathies) | Show variant-effect interpretation in structural proteins. |
| **Metabolic / lysosomal** | GAA (Pompe), GBA (Gaucher) | Enzyme replacement therapy targets; demonstrate active-site queries. |
| **Infectious-disease targets** | TEM-1 beta-lactamase, MTB gyrA | Pathogen drug-target side; demonstrate `uniprot_get_active_sites` + `uniprot_get_processing_features` for drug discovery. |
| **Solid-tumour drug targets** | EGFR, KRAS, BRAF | The non-Mendelian cancer axis; show ChEMBL bridge + ClinVar somatic variant resolution. |

Total: 18 atlas entries planned; 10 are populated in this initial
release (v1.1.0). The remaining 8 land in v1.2.

## How to read an atlas entry

Each entry is structured around the question a researcher would ask
next. Take `tp53.md`:

> *Question: is `TP53 R175H` a clinically actionable variant? What's
> the structural confidence at residue 175? Which diseases are
> associated with TP53 in OMIM/MONDO?*

The atlas entry lists:

- The **MCP tool calls** in execution order.
- The **expected response shape** (without locking the exact text,
  which can drift with UniProt releases).
- The **provenance fields** that must appear on every response.
- **Cross-references** the tool surfaces (ClinVar, AlphaFold, PDB,
  ChEMBL) plus adjacent ontologies the agent layer can query.

The entry does not pin the exact variant count, disease list, or
sequence — those drift between UniProt releases by design. The
atlas pins the *shape* of the answer, not its content. The
`uniprot_provenance_verify` tool detects content drift between any
two captures.

## How to extend

Add a new file `examples/atlas/<gene>.md` following the template above.
Open a PR; `tests/contract/test_atlas_consistency.py` (planned for
v1.2.0) will assert that:

- Each file references a real UniProt accession that resolves
  `200 OK`.
- The tool sequence cites tools that exist on the live FastMCP
  instance.
- The MONDO/OMIM IDs are well-formed.

## Why MONDO

The [Mondo Disease Ontology](https://mondo.monarchinitiative.org/)
unifies disease nomenclature across DOID, OMIM, Orphanet, MeSH, NCIt,
and others. UniProt's DISEASE-type comments link to OMIM directly;
MONDO acts as the bridge to the broader disease-ontology landscape
that adjacent MCP servers (planned: `clinvar-mcp`, `pdb-mcp`,
`mondo-mcp`) will query. The atlas anchors each protein on both
its UniProt accession (the gateway-of-record for protein knowledge)
*and* its primary MONDO identifier (the gateway-of-record for the
disease side), so a downstream orchestrator can chain the two
without re-deriving mappings.

## Compliance & provenance

Every atlas entry's tool calls produce per-response provenance
records (UniProt release + retrieval timestamp + resolved URL +
canonical SHA-256). A regulated user can capture the full set of
provenance footers, archive them, and re-verify against the live
APIs years later via `uniprot_provenance_verify`. The atlas itself
is *exemplary*, not authoritative — it shows what the tool can do,
not what UniProt says today. The authoritative answer is whatever
the live API returns at query time, with provenance.

## Atlas index

The v1.1.0 atlas entries (25 to start; the disease universe is open and
the atlas grows over time). Cross-references vary per entry — MONDO
applies for human Mendelian disease but not for pathogen drug-targets;
PharmGKB / CPIC apply for pharmacogenomic genes; ARO / CARD apply for
antibiotic-resistance enzymes. Each entry surfaces the
context-appropriate ontologies.

### Hereditary cancer & DNA-repair

| File | Gene | UniProt | Primary cross-ref | Theme |
|---|---|---|---|---|
| [tp53.md](tp53.md) | TP53 | P04637 | MONDO:0007254 (Li-Fraumeni) | germline + somatic; canonical clinical-variant case |
| [brca1.md](brca1.md) | BRCA1 | P38398 | MONDO:0011535 (HBOC1) | dossier; PARPi synthetic lethality |
| [brca2.md](brca2.md) | BRCA2 | P51587 | MONDO:0011544 (HBOC2) | PARPi axis; long-protein AlphaFold |
| [mlh1.md](mlh1.md) | MLH1 | P40692 | MONDO:0007648 (Lynch 2) | MMR-deficiency → checkpoint inhibitors |

### Solid-tumour drivers

| File | Gene | UniProt | Primary cross-ref | Theme |
|---|---|---|---|---|
| [egfr.md](egfr.md) | EGFR | P00533 | MONDO:0005233 (NSCLC) | RTK; L858R / T790M; TKI generations |
| [kras.md](kras.md) | KRAS | P01116 | MONDO:0005192 (PDAC) | "undruggable" → covalent G12C inhibitors |
| [braf.md](braf.md) | BRAF | P15056 | MONDO:0005105 (melanoma) | V600E + MEK combination therapy |
| [erbb2.md](erbb2.md) | ERBB2/HER2 | P04626 | MONDO:0007254 | amplification + ADC ecosystem (T-DXd) |

### Single-gene rare disease

| File | Gene | UniProt | Primary cross-ref | Theme |
|---|---|---|---|---|
| [cftr.md](cftr.md) | CFTR | P13569 | MONDO:0009061 (cystic fibrosis) | F508del; ETI corrector/potentiator |
| [htt.md](htt.md) | HTT | P42858 | MONDO:0007739 (Huntington) | polyQ expansion; HTT-lowering ASOs |
| [dmd.md](dmd.md) | DMD | P11532 | MONDO:0010679 (DMD) | exon-skipping ASO matchmaking |
| [hbb.md](hbb.md) | HBB | P68871 | MONDO:0011382 (sickle cell) | E6V / E7V numbering; voxelotor + gene therapy |
| [smn1.md](smn1.md) | SMN1 | Q16637 | MONDO:0011127 (SMA1) | nusinersen + risdiplam + onasemnogene |
| [fbn1.md](fbn1.md) | FBN1 | P35555 | MONDO:0007947 (Marfan) | cbEGF Ca2+ coordination; losartan |
| [nf1.md](nf1.md) | NF1 | P21359 | MONDO:0018975 (NF1) | RasGAP loss → MEK inhibition (selumetinib) |

### Metabolic & lysosomal

| File | Gene | UniProt | Primary cross-ref | Theme |
|---|---|---|---|---|
| [pah.md](pah.md) | PAH | P00439 | MONDO:0009861 (PKU) | iron + BH4 cofactor; sapropterin responsiveness |
| [gba.md](gba.md) | GBA | P04062 | MONDO:0009207 (GD1) | Gaucher ERT/SRT; +PD risk modifier |

### Neurodegenerative

| File | Gene | UniProt | Primary cross-ref | Theme |
|---|---|---|---|---|
| [app.md](app.md) | APP | P05067 | MONDO:0004975 (Alzheimer) | secretase processing; Aβ-mAbs |
| [snca.md](snca.md) | SNCA | P37840 | MONDO:0008199 (PD1) | IDP → Lewy bodies; aggregation modulators |

### Cardiovascular & laminopathies

| File | Gene | UniProt | Primary cross-ref | Theme |
|---|---|---|---|---|
| [myh7.md](myh7.md) | MYH7 | P12883 | MONDO:0024533 (HCM1) | sarcomeric; mavacamten |
| [lmna.md](lmna.md) | LMNA | P02545 | MONDO:0008034 (HGPS) | nine-phenotype laminopathy; lonafarnib |

### Pharmacogenomics

| File | Gene | UniProt | Primary cross-ref | Theme |
|---|---|---|---|---|
| [cyp2d6.md](cyp2d6.md) | CYP2D6 | P10635 | PharmGKB / CPIC | 25% of clinical drugs; star-allele system |
| [vkorc1.md](vkorc1.md) | VKORC1 | Q9BQB6 | PharmGKB / CPIC | warfarin dosing (with CYP2C9) |
| [g6pd.md](g6pd.md) | G6PD | P11413 | PharmGKB | oxidative-drug avoidance; tafenoquine precaution |

### Infectious-disease drug-resistance

| File | Gene | UniProt | Primary cross-ref | Theme |
|---|---|---|---|---|
| [tem1.md](tem1.md) | *bla* (TEM-1) | P62593 | ARO:3000014 (CARD) | β-lactamase; covalent Ser-70 inhibitors |
