# Reproducibility and limits of the UniProt source index

**Active content.** Only two CSV-compatible TSV exports and their integrity manifest are retained in this folder. The historical 25-case manually written clinical atlas is retired from the active repository. This is a deliberate reduction in scientific claim surface, **not** a change to the UniProt MCP tools.

**Source.** The [UniProt REST API](https://rest.uniprot.org/) supplied the entries captured as of 2026-04-26 by [build_comprehensive_index.py](build_comprehensive_index.py). The human TSV contains 7,250 disease–protein rows drawn from 5,296 reviewed accessions; the pathogen TSV contains 4,340 selected reviewed pathogen protein rows. These are different row types and should not be merged as a homogeneous clinical population.

**Integrity.** [manifest.json](manifest.json) binds each TSV to an exact SHA-256 digest, byte length, row count, and the exact extraction script SHA-256. [tests/contract/test_atlas_manifest.py](../../tests/contract/test_atlas_manifest.py) enforces these commitments in CI. Hash matches show **unchanged snapshot bytes**, not that upstream annotations or biological claims are infallible.

**Limits.** UniProt annotations may derive from experiments, manual literature curation, computational prediction, or other sources. These rows are source-attributed historical data, not current lab measurements, diagnoses, prescribing recommendations, or proof of causal gene–disease relations. The pathogen index is an organism-selected sample. No MONDO, HPO, PharmGKB or clinical drug mappings are asserted by the active snapshot.

**Use.** Resolve a candidate accession from these files, then query the current UniProt MCP tools for the latest source evidence, literature citations, experimental/predicted annotation status, and provenance receipt. Rebuild the index from a specified UniProt release when freshness matters and preserve the old snapshot alongside the new one rather than silently changing its historical meaning.

**Historical correction.** Former curated examples were withdrawn from the active branch after identification of stale treatment descriptions (including references to voxelotor as an available sickle-cell therapy despite its 2024 worldwide withdrawal) and the difficulty of ensuring every changing clinical narrative was independently reviewed. The live MCP data retrieval and its source provenance are unaffected.
