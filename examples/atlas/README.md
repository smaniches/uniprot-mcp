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

The 10 v1.1.0 atlas entries:

| File | Gene | UniProt | MONDO | Disease class |
|---|---|---|---|---|
| [tp53.md](tp53.md) | TP53 | P04637 | MONDO:0007254 (Li-Fraumeni syndrome) | hereditary cancer |
| [brca1.md](brca1.md) | BRCA1 | P38398 | MONDO:0011535 (HBOC1) | hereditary cancer |
| [cftr.md](cftr.md) | CFTR | P13569 | MONDO:0009061 (cystic fibrosis) | rare disease |
| [htt.md](htt.md) | HTT | P42858 | MONDO:0007739 (Huntington disease) | rare disease |
| [dmd.md](dmd.md) | DMD | P11532 | MONDO:0010679 (Duchenne muscular dystrophy) | rare disease |
| [hbb.md](hbb.md) | HBB | P68871 | MONDO:0011382 (sickle cell disease) | rare disease |
| [pah.md](pah.md) | PAH | P00439 | MONDO:0009861 (phenylketonuria) | metabolic |
| [app.md](app.md) | APP | P05067 | MONDO:0004975 (Alzheimer disease) | neurodegenerative |
| [egfr.md](egfr.md) | EGFR | P00533 | MONDO:0005233 (NSCLC) | solid-tumour target |
| [tem1.md](tem1.md) | TEM-1 | P62593 | n/a (pathogen target) | infectious-disease target |
