# How the atlas was compiled — methodology, gates, and limits

This page exists to give the community everything it needs to audit
the atlas. The atlas is a **research-demonstration corpus**, not an
authoritative ontology. We pin the *shape* of the answer (which tools
to call, which provenance fields appear) rather than locking the
*content* (which UniProt drifts release-to-release). The honest
question for any reviewer is: *what is verified, what is
community-reviewable, and how is correctness enforced?*

## What is verified by automated gates

`tests/contract/test_atlas_consistency.py` runs on every push and
enforces twelve structural gates:

| # | Gate | What it catches |
|---|---|---|
| 1 | `atlas.json` parses as valid JSON | Hand-edits that break the file |
| 2 | Top-level JSON-LD shape (`@type`, `@context`, `schema:license`, `schema:version`, `entries[]`) | Manifest schema drift |
| 3 | Every entry has the required fields (`@id`, `atlasFile`, `name`, `gene`, `organism`, `diseaseClass`, `exemplifies`) | Missing-field defects |
| 4 | Every UniProt @id matches the official `ACCESSION_RE` from `uniprot_mcp.client` | Typos in accessions caught before any network call |
| 5 | Every entry's Markdown file (`atlasFile`) exists on disk | Dangling references |
| 6 | Every `diseaseClass` is in the eight-element allowlist | Accidental new classes — must be added intentionally |
| 7 | Every `organism.taxonId` matches the `ncbitaxon:NNN` pattern | Malformed organism IDs |
| 8 | Every disease `@id` is well-formed MONDO or DOID | Malformed disease identifiers |
| 9 | Every OMIM ID is exactly 6 digits | Wrong-length OMIM identifiers |
| 10 | Every ARO ID is well-formed (`aro:NNNNNNN`) | Malformed antibiotic-resistance ontology IDs |
| 11 | Atlas size never falls below the v1.1.0 baseline | Accidental deletions |
| 12 | **(opt-in via `--integration`)** Every UniProt accession resolves to HTTP 200 against the live UniProt REST API | **Fabricated accessions** — caught by the live API |

Gate 12 is the heart of the epistemic discipline. It is opt-in
(otherwise CI would always need network access to UniProt) but
**every release must run it before tag**. The v1.1.0 baseline run
on 2026-04-26 confirmed all 25 accessions resolve.

```
$ pytest tests/contract/test_atlas_consistency.py::test_every_uniprot_accession_resolves_live --integration -v
... PASSED  (17.13s elapsed; 25/25 accessions verified)
```

## What is community-reviewable (not yet machine-verified)

These are claims in the atlas that the gates above do NOT certify.
They are **community-reviewable** — please file an issue if any of
these are wrong:

- **MONDO IDs name the claimed disease.** The gates verify the format
  (`mondo:NNNNNNN`); they do not query the live MONDO API to check
  that, e.g., `mondo:0007254` actually names "Li-Fraumeni syndrome."
  Cross-check at https://monarchinitiative.org/.
- **OMIM IDs name the claimed gene/disease.** Same logic. Cross-check
  at https://omim.org/.
- **The therapeutic axis described in each entry.** This is curated
  prose summarising my interpretation of the published clinical
  literature. It can drift as new therapies are approved. It is
  intended to orient a researcher; it is not medical advice.
- **The "Exemplifies" tags.** Subjective characterisations of what
  each entry demonstrates about the tool surface.
- **Relative emphasis.** The 25 entries were selected to span eight
  disease classes; many other valid entries (BRCA2 already; many
  more) could have been chosen. The selection is illustrative, not
  comprehensive.

## How entries were selected

Each entry was chosen to demonstrate a distinct capability of the
tool surface against a canonical disease/protein pair. The selection
priorities, in order:

1. **Span the major axes of biomedical research.** Eight classes
   (hereditary cancer, solid-tumour drivers, single-gene rare disease,
   metabolic / lysosomal, neurodegenerative, cardiovascular /
   laminopathy, pharmacogenomic, infectious-disease drug-resistance).
2. **Pin canonical clinical examples** — entries the community
   recognises immediately. TP53 R175H. CFTR F508del. HBB E6V.
3. **Demonstrate breadth of UniProt's curation depth.** Long
   intrinsically-disordered proteins (HTT, SNCA), modular ECM proteins
   (FBN1), heavily-resolved enzymes (TEM-1), pleiotropic genes (LMNA's
   nine phenotypes), pharmacogenomic enzymes (CYP2D6).
4. **Include therapeutic-axis variety.** Small molecules (BRAF +
   vemurafenib), antibodies (HER2 + trastuzumab), ADCs (HER2 +
   T-DXd), gene therapy (SMN1 + onasemnogene), antisense
   oligonucleotides (DMD + eteplirsen), CRISPR therapy (HBB +
   exa-cel), enzyme replacement (GBA + imiglucerase).
5. **Demonstrate pathogen / infectious-disease coverage** — TEM-1
   shows that the tool surface is organism-agnostic.

The atlas does **not** attempt to cover every disease. It would be
dishonest to claim coverage of the disease universe in 25 entries.
It demonstrates how the tool *behaves* across a representative
sample so that an adopter can confidently apply it to entries we
did not pre-curate.

## How facts in each entry were sourced

Each entry contains:

- **UniProt accession** — verified by the live API gate (12).
- **Gene symbol** — taken from UniProt's canonical entry; community can verify by following the URL in the entry header.
- **MONDO IDs** — sourced from monarchinitiative.org browsing + cross-references in UniProt's DISEASE-type comments (which themselves cite OMIM, with MONDO mapping inferred via UniProt → OMIM → MONDO standard chain). Some MONDO IDs may be approximate matches; community correction welcome.
- **OMIM IDs** — from UniProt's CC DISEASE comments + cross-references.
- **Therapeutic axis prose** — composed from my interpretation of the public clinical-literature consensus. Each major drug name is independently verifiable on FDA.gov / EMA / clinicaltrials.gov. No proprietary data was used.
- **PDB / AlphaFold / ChEMBL pointers** — generic claims of "structures exist" / "ChEMBL coverage is rich"; the live tool produces the actual content per query.

## What the atlas does *not* do

To be explicit about scope:

- **Does not** make medical recommendations. Therapeutic-axis prose
  is research-context interpretation, not clinical advice.
- **Does not** claim to be exhaustive. 25 entries × 8 disease classes
  is a representative sample.
- **Does not** verify drug approvals against real-time regulatory
  databases. Approval status drifts; cross-check FDA.gov or EMA
  before citing.
- **Does not** lock UniProt content. Annotation can change between
  releases; the atlas pins the *shape*, not the content. The
  `uniprot_provenance_verify` tool handles content-drift detection.

## Versioning and reproducibility

- The atlas is versioned with the release line: each `uniprot-mcp-server`
  release ships an atlas pinned to the same version (e.g. atlas v1.1.2
  ships with `uniprot-mcp-server` v1.1.2). The atlas was authored at
  v1.1.0 (2026-04-26); v1.1.1 and v1.1.2 were metadata-only patches that
  did not modify atlas content.
- Every push to `main` runs the structural gates above.
- Every release-tag push (e.g., `v1.1.2`) must pass the live-UniProt
  gate before merge to main of the release-prep branch.
- Atlas changes between releases are recorded in `CHANGELOG.md`
  under the version's `### Atlas` section (introduced in v1.2.0).

## Invitation to the community

If any atlas entry contains a wrong identifier, a misleading
therapeutic-axis claim, or an out-of-date approval status, **please
file an issue** at https://github.com/smaniches/uniprot-mcp/issues.
Concrete corrections are welcomed and will land in the next patch
release. Authorship will be credited via Co-Authored-By in the fix
commit.

## Citing the atlas

If the atlas informs published work, cite via the Zenodo DOI (the
concept DOI auto-resolves to the latest version):

> Maniches S. (2026). *uniprot-mcp — disease & target atlas*. Zenodo. https://doi.org/10.5281/zenodo.19817710

For a specific pinned version (e.g. v1.1.2) use the corresponding
version DOI: https://doi.org/10.5281/zenodo.19826135. The full
identifier registry lives in `CITATION.cff`.

## Epistemic stance

The author has been formally trained in the relevant disciplines
(`cum laude`, with prior research output in this domain) and built
this atlas by hand against UniProt's public REST API. Despite that
preparation, no human-curated corpus is free of errors. The
discipline is to (a) make every claim machine-checkable where
possible, (b) be explicit about what is not yet machine-checkable,
and (c) invite community correction. The radioactive-material
analogy — the cost of a false biological negative is high — drives
the choice of automated gates over claims of perfection.
