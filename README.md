<!-- mcp-name: io.github.smaniches/uniprot-mcp -->

# UniProt MCP Server

[![CI](https://github.com/smaniches/uniprot-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/smaniches/uniprot-mcp/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/smaniches/uniprot-mcp/badge)](https://api.securityscorecards.dev/projects/github.com/smaniches/uniprot-mcp)
[![GitHub Release](https://img.shields.io/github/v/release/smaniches/uniprot-mcp?sort=semver)](https://github.com/smaniches/uniprot-mcp/releases)
[![PyPI version](https://img.shields.io/pypi/v/uniprot-mcp-server)](https://pypi.org/project/uniprot-mcp-server/)
[![PyPI downloads/30d](https://img.shields.io/pypi/dm/uniprot-mcp-server?label=downloads%2F30d)](https://pypistats.org/packages/uniprot-mcp-server)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP compatible](https://img.shields.io/badge/MCP-compatible-6e56cf.svg)](https://modelcontextprotocol.io/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](pyproject.toml)
[![Provenance: SHA-256 + verify](https://img.shields.io/badge/provenance-SHA--256_+_verify-blue)](#provenance--verification)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0005--6480--1987-A6CE39?logo=orcid&logoColor=white)](https://orcid.org/0009-0005-6480-1987)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.19817710-3C5A99?logo=zenodo&logoColor=white)](https://doi.org/10.5281/zenodo.19817710)
[![Glama score](https://glama.ai/mcp/servers/smaniches/uniprot-mcp/badges/score.svg)](https://glama.ai/mcp/servers/smaniches/uniprot-mcp)
[![Awesome MCP Servers](https://img.shields.io/badge/Awesome_MCP-Listed-blue?logo=github)](https://github.com/punkpeye/awesome-mcp-servers#bio)

Produce verifiable, release-aware protein evidence packages from UniProt and linked scientific sources.

Use this MCP server to find proteins, assemble protein, target, and variant evidence, and keep a checkable record of where each result came from. Responses preserve source-specific provenance, including the provider, retrieval time, source URL, and a SHA-256 digest. A release identifier is present when the provider supplies one. `uniprot_provenance_verify` can compare recorded UniProt REST records with current UniProt data; it does not independently verify ClinVar or AlphaFold DB results.

The complete tool catalog remains available for specialized research workflows.

> Author: **Santiago Maniches** · ORCID [0009-0005-6480-1987](https://orcid.org/0009-0005-6480-1987) · TOPOLOGICA LLC

**Research authorship:** Santiago Maniches independently maintains this server and is the sole scientific author of its project-specific research contributions. AI-assisted tools have supported development, testing, and internal review under his direction. UniProt records, linked source data, and underlying third-party methods retain their original authorship; internal tool-assisted review is not external scientific validation.

**Run it in one line:**

```bash
uvx uniprot-mcp-server
```

---

## Provenance: a source-backed TP53 capture

The [TP53 R175H example](examples/01_clinical_variant_interpretation.jsonl)
is a **real capture from October 15, 2026**, not a hypothetical model
transcript. Its UniProt, ClinVar and AlphaFold DB responses are saved with
their original response bytes in
[the capture directory](examples/captures/2026-10-15_tp53_r175h/).
The contract test recomputes raw and canonical SHA-256 values from the
saved upstream bytes and checks their captured footer URLs and hashes.
It separately compares the transcript text with a saved tool-output
record; it does **not** independently re-derive every parsed statement
from those bytes.

For example, the captured UniProt `P04637` response has:

```text
Source: UniProt release 2026_03 (02-September-2026)
Retrieved: 2026-10-15T10:32:43Z
URL: https://rest.uniprot.org/uniprotkb/P04637
Canonical SHA-256: 112540dcb662c3ce2feba05272ce0e946ce76089a5bcf8346eb55141892f7fcf
```

To validate this **historical** capture from a repository checkout:

```bash
pytest -q tests/contract/test_tp53_capture_binding.py
```

To compare the *current* upstream record with the captured one, invoke
`uniprot_provenance_verify` with the URL, release and digest above.
A live response can legitimately differ from the October 2026 capture;
do not assume that its verification verdict will be `verified`.

This verifies source digest binding and that two recorded text copies
agree, **not** the scientific correctness of every parsed claim. ClinVar's germline classification does not
establish somatic actionability, and a model-wide AlphaFold confidence
summary does not establish confidence at a specific residue.

## Installation

Run without installing (recommended):

```bash
uvx uniprot-mcp-server
```

Or install into an environment:

```bash
pip install uniprot-mcp-server
```


> **Note:** There is an unrelated package named `uniprot-mcp` on PyPI
> (different author, 5 tools, MIT). This package is `uniprot-mcp-server`.
> Running `pip install uniprot-mcp` will install the wrong package silently.

## For researchers — where to start

If you are a biomedical researcher visiting this repo, the highest-signal places to look are:

| Resource | What it gives you |
|---|---|
| **[MCP tool documentation](docs/tools.md)** | Live UniProt source access, accession-level lookups, provenance, and optional AlphaFold structure-confidence retrieval. No separate hand-maintained clinical collection is distributed. |
| **[TP53 R175H capture](examples/01_clinical_variant_interpretation.jsonl)** | Dated live transcript, preserved upstream response bytes, digest/footer checks, and recorded text comparison. Not independently validated biomedical interpretation. The illustrative transcripts were withdrawn. |
| **[`tests/benchmark/`](tests/benchmark/)** | Pre-registered 30-prompt benchmark with SHA-256 commitments on `main`. The 2026-04-26 v1.1.0 run verified 30/30 against live UniProt — transcript at `tests/benchmark/run-2026-04-26-v1.1.0/`. |
| **[`scripts/replicate.sh`](scripts/replicate.sh)** | One-command verification that the published PyPI wheel was built from this exact repo (cross-checks SHA-256 across PyPI / GitHub Release / SLSA attestation; runs `--self-test`; re-runs the benchmark live). POSIX + `scripts/replicate.ps1` for Windows. |
| **[`docs/COMPETITIVE_LANDSCAPE.md`](docs/COMPETITIVE_LANDSCAPE.md)** | Honest 14-server survey of the bio-MCP space (April 2026) and the specific differentiation this server claims. |

Issues / corrections welcome at https://github.com/smaniches/uniprot-mcp/issues. Tool results are source-attributed; UniProt annotations and predicted structural confidence retain their upstream evidence type. No separate clinical disease index is maintained.

---

## What makes this different

| | uniprot-mcp | Vanilla LLM + WebFetch | A typical bio-MCP |
|---|---|---|---|
| Tool surface | **41 tools, 8 families** | none — caller writes URLs | usually 5–10 |
| Source provenance | provider • date • URL • SHA-256 (release where available) | none | sometimes URL only |
| UniProt REST verification | `uniprot_provenance_verify` compares recorded UniProt REST responses; external ClinVar/AlphaFold origins are outside its scope | varies | varies |
| Release pinning | `--pin-release=YYYY_MM` raises on drift | n/a | n/a |
| Pre-registered benchmark | 30 prompts, SHA-256 committed on `main` + reproducible verifier | n/a | n/a |
| Local provenance cache | `uniprot_replay_from_cache` read primitive (automatic cache write-through is not wired into the request path — see [§Provenance & verification](#provenance--verification)) | n/a | n/a |
| Clinical primitives | sequence chemistry / position-aware features / HGVS variant lookup / disease associations / AlphaFold pLDDT / ClinVar | none | none |
| Composition tool | `uniprot_target_dossier` — one call, nine sections | n/a | n/a |
| Input validation | regex + length cap before any HTTP call | none | partial |
| Error-channel safety | upstream exception text never echoed to LLM | n/a | partial |
| Cross-origin allowlist | enumerated, threat-modelled, privacy-listed | n/a | usually unaudited |
| Supply chain | SLSA build provenance + Sigstore + CycloneDX SBOM (post-flip) | n/a | rare |
| Test layers | unit + property + contract + client + integration + benchmark | n/a | usually unit only |
| Mutation testing | weekly + on-demand workflow; per-module measurement complete for `cache` 82 %, `proteinchem` 92 %, `client` 70 %; gate currently 0 % (measurement-first), ≥ 95 % is the v1.2.0 target — see `docs/MUTATION_SCORES.md` | n/a | rare |

The **provenance + verify** chain is, in my 2026-04-26 survey, absent
from every other bio-MCP I could find. A regulated user can take any
prior `uniprot-mcp` answer and prove — without contacting the author
— that UniProt still returns the same bytes, or detect exactly how the
upstream has drifted. If you find a counter-example I missed, please
file an issue and I will update the comparison.

---

## Tools (41)

Eight endpoint families. All read-only (`readOnlyHint: true`). All
but `uniprot_replay_from_cache` interact with at least one upstream
service (`openWorldHint: true`). No UniProt API key required.

### Core UniProtKB (10)

| Tool | Purpose |
|---|---|
| `uniprot_get_entry` | Full UniProt entry (e.g. `P04637` for p53). Function, gene, organism, disease, cross-refs. |
| `uniprot_search` | UniProt query language — gene, organism, taxon ID, reviewed flag, free text. |
| `uniprot_get_sequence` | FASTA. PIR-style provenance comment block above the first record (BLAST+ / biopython compatible). |
| `uniprot_get_features` | Domains, binding sites, PTMs, signal peptides — optional type filter. |
| `uniprot_get_variants` | Natural variants and disease mutations. |
| `uniprot_get_go_terms` | GO annotations grouped by aspect (F / P / C). |
| `uniprot_get_cross_refs` | Raw cross-references to PDB, Pfam, Ensembl, Reactome, KEGG, STRING … |
| `uniprot_id_mapping` | Map IDs between databases (Gene_Name → UniProtKB, PDB → UniProtKB, …). |
| `uniprot_batch_entries` | Up to 100 entries in one call; invalid accessions filtered client-side. |
| `uniprot_taxonomy_search` | Search UniProt taxonomy by organism name. |

### Controlled vocabularies (4)

| Tool | Purpose |
|---|---|
| `uniprot_get_keyword` | Keyword by ID (e.g. `KW-0007` = Acetylation). Definition, synonyms, GO refs, hierarchy. |
| `uniprot_search_keywords` | Free-text keyword search. |
| `uniprot_get_subcellular_location` | Subcellular-location term by ID (e.g. `SL-0039` = Cell membrane). |
| `uniprot_search_subcellular_locations` | Free-text location search. |

### Sequence archives & clusters (4)

| Tool | Purpose |
|---|---|
| `uniprot_get_uniref` | UniRef cluster by ID (`UniRef50_P04637`, `UniRef90_P04637`, `UniRef100_P04637`). |
| `uniprot_search_uniref` | Cluster search with `identity_tier` filter (50 / 90 / 100). |
| `uniprot_get_uniparc` | Sequence-archive record by UPI (`UPI000002ED67`). |
| `uniprot_search_uniparc` | UniParc full-text search. |

### Proteomes & literature (4)

| Tool | Purpose |
|---|---|
| `uniprot_get_proteome` | Proteome by UP ID (`UP000005640` = human). Counts, BUSCO score, components. |
| `uniprot_search_proteomes` | Filter by organism / type / completeness. |
| `uniprot_get_citation` | Citation record by ID (typically a PubMed numeric ID). |
| `uniprot_search_citations` | Index search across UniProt citations. |

### Structured cross-DB resolvers (4)

Gateway-only — no calls leave the UniProt origin. These extract the
relevant cross-references from a UniProt entry and return *structured*
records (typed lists / objects, not passthrough strings).

| Tool | Purpose |
|---|---|
| `uniprot_resolve_pdb` | PDB structures: id + method + resolution + chain coverage. |
| `uniprot_resolve_alphafold` | AlphaFold model id + EBI viewer URL (model id only — for pLDDT call the dedicated tool below). |
| `uniprot_resolve_interpro` | InterPro signatures: id + entry name. |
| `uniprot_resolve_chembl` | ChEMBL drug-target id + EBI target-card URL. |

### Biomedical features (7)

Pure-Python compositions over the entry — no extra origin. The first
four answer per-residue and per-variant questions; the last three are
the v1.1.0 expansion targeting drug discovery, therapeutic-protein
engineering, and pathogen-secretion analysis: each is a filter over the
entry's `features` array, with a structured grouping by feature type
and an honest empty-set advisory.

| Tool | Purpose |
|---|---|
| `uniprot_compute_properties` | Derived sequence chemistry from the FASTA: MW / pI / GRAVY / aromaticity / charge / ε₂₈₀. |
| `uniprot_features_at_position` | Every feature overlapping a residue position. Critical for variant-effect interpretation. |
| `uniprot_lookup_variant` | HGVS-shorthand match (`R175H`, `V600E`, `R248*`) against UniProt's natural-variant features. |
| `uniprot_get_disease_associations` | Structured disease records from DISEASE-type comments: name + acronym + UniProt disease ID + OMIM cross-ref + description. |
| `uniprot_get_active_sites` | Catalytic and ligand-binding residues: active sites, binding sites, sites, metal binding, DNA binding. The residue-level chemistry of the protein. |
| `uniprot_get_processing_features` | Maturation features: signal peptide, propeptide, transit peptide, initiator methionine, chain, peptide. Essential for therapeutic-protein engineering and pathogen-secretion analysis. |
| `uniprot_get_ptms` | Post-translational modifications: modified residues (phospho/acetyl/methyl), glycosylation, lipidation (GPI/prenyl/palmitoyl), disulfide bonds, cross-links. |

### Cross-origin enrichment (3)

The only tools that consult origins outside `rest.uniprot.org`. Each is documented in [`PRIVACY.md`](PRIVACY.md) and in the [threat model](docs/THREAT_MODEL.md#t3b-cross-origin-allowlist-for-non-uniprot-endpoints).

| Tool | Origin | Purpose |
|---|---|---|
| `uniprot_get_alphafold_confidence` | `alphafold.ebi.ac.uk` | pLDDT mean + four-band distribution; lets the agent decide whether to trust the model. |
| `uniprot_resolve_clinvar` | `eutils.ncbi.nlm.nih.gov` | Human UniProt entries only (NCBI taxon 9606); ClinVar classifications by gene + optional protein change, not transferable to nonhuman orthologs. |
| `uniprot_get_publications` | `rest.uniprot.org` | Pure-Python over the entry's references — listed here because it complements the cross-origin enrichment. |

### Composition + provenance (5)

| Tool | Purpose |
|---|---|
| `uniprot_resolve_orthology` | Group orthology cross-references by source DB (KEGG / OMA / OrthoDB / eggNOG / 8 more). |
| `uniprot_get_evidence_summary` | Summarize UniProt ECO annotation evidence and assertion methods, with a weighted 0-100 descriptive mix index. The index is uncalibrated, not a probability of annotation correctness and not comparable to AlphaFold pLDDT. |
| `uniprot_target_dossier` | One-call comprehensive characterisation: nine sections — identity / function / chemistry / structure / drug-target / disease / variants / functional annotations / cross-refs. |
| `uniprot_provenance_verify` | Re-fetch a previously recorded URL and compare release tag + canonical response SHA-256. Six verdicts (`verified`, `incomplete_evidence`, `release_drift`, `hash_drift`, `release_and_hash_drift`, `url_unreachable`) each with an advice string. |
| `uniprot_replay_from_cache` | Read a cached UniProt response without hitting the upstream. Opt-in via `UNIPROT_MCP_CACHE_DIR`. |

---

## Provenance & verification

The verifiable source receipt above comes from the stored October 2026
TP53 capture, not from an illustrative or reconstructed transcript.
The `uniprot_provenance_verify` tool compares a recorded UniProt
release and canonical SHA-256 with a newly retrieved response. It can
report a match or a drift state, depending on *current upstream bytes*.
A successful comparison is not independent clinical validation.

Do not claim a future verification result in advance. For exact
historical replay, retain the original response bytes or retrieve the
appropriate UniProt source snapshot.

If UniProt has moved on, the tool tells you exactly how:

| Verdict | Meaning | Advice |
|---|---|---|
| `verified` | Both release and hash match | The provenance is reproducible |
| `incomplete_evidence` | URL reachable, but reference checks missing | Supply recorded release and SHA-256 |
| `release_drift` | UniProt released a new version | Pin via the FTP snapshot if you need the historical answer |
| `hash_drift` | Same release, body changed | An in-release edit; investigate or re-fetch |
| `release_and_hash_drift` | Both moved on | Use a release-specific FTP snapshot |
| `url_unreachable` | Endpoint dropped or rate-limited | Retry or report to UniProt |

For strict reproducibility, opt into release pinning:

```bash
export UNIPROT_PIN_RELEASE=2026_01
uniprot-mcp
# every response is checked against the pinned release;
# any drift raises `ReleaseMismatchError`, which the server surfaces
# as an agent-actionable error envelope.
```

For offline replay, `uniprot_replay_from_cache(url)` reads a
previously-recorded response from a directory pointed at by
`UNIPROT_MCP_CACHE_DIR`:

```bash
export UNIPROT_MCP_CACHE_DIR=~/.uniprot-mcp-cache
uniprot-mcp
# uniprot_replay_from_cache(url) returns the entry at
# $UNIPROT_MCP_CACHE_DIR/<sha256(url)>.json if present.
```

> **Status note (v1.1.3).** `uniprot_replay_from_cache` is a **read
> primitive**. The cache must currently be populated by an external
> process — for example, by the maintainer-provided benchmark capture
> script, or by you wrapping `httpx` calls and writing to the directory
> yourself in the documented JSON shape (see `src/uniprot_mcp/cache.py`).
> Automatic cache write-through is not currently wired into the request
> path; cache entries must be populated explicitly or by an external
> capture workflow.

The [October 2026 TP53 example](examples/01_clinical_variant_interpretation.jsonl)
preserves actual upstream response bytes and verifies them offline.
The older April 2026 benchmark transcript was
[withdrawn as provenance evidence](tests/benchmark/run-2026-04-25-roundtrip/transcript.md)
because its source bytes were not preserved; do not use its former
verdicts as scientific or cryptographic proof.

---

## Pre-registered benchmark

`tests/benchmark/` ships a 30-prompt evaluation (Tier A / B / C × 10)
with **SHA-256-committed expected answers** on `main`. The plaintext
`expected.jsonl` is held local-only until a benchmark run is
published; the cryptographic commitments mean the author cannot
rewrite "correct" answers post-hoc.

**Third-party reproducibility path (no seal file required).** Re-derive every Tier A / B answer live from UniProt and print it — no `expected.jsonl` required. This confirms the answers are independently reproducible from the primary source today; it does **not** recompute the seal (the committed SHA-256 binds a withheld rationale — see below):

```bash
python tests/benchmark/verify_against_hashes.py tests/benchmark/expected.hashes.jsonl
# Re-derives all 30 answers live and prints them (informational; exit 0).
```

**Maintainer cryptographic verification path (with the local plaintext seal).** The committed digests in `expected.hashes.jsonl` are sealed over `{prompt_id, answer, rationale}`; the rationale is deliberately withheld as part of the sealed pre-registration, so the full cryptographic check requires the local `expected.jsonl`:

```bash
python tests/benchmark/verify_answers.py tests/benchmark/expected.jsonl
# OK: all 30 prompts verified against https://rest.uniprot.org

python tests/benchmark/verify.py tests/benchmark/expected.jsonl tests/benchmark/expected.hashes.jsonl
# OK: 30 commitments verified
```

See [`tests/benchmark/AUDIT.md`](tests/benchmark/AUDIT.md) for the
per-prompt source attribution and the formal independence statement
(`uniprot-mcp` was *not* used during answer authoring).

---

## Install

```bash
pip install uniprot-mcp-server   # PyPI distribution
# or, for a pinned, isolated install:
uvx --from uniprot-mcp-server uniprot-mcp
```

> **Why three different names?** This is the standard Python packaging pattern, exactly because PyPI's namespace is global and collisions force disambiguation:
>
> | Concept | Value | What it is |
> |---|---|---|
> | GitHub repository | `smaniches/uniprot-mcp` | source code + issue tracker |
> | PyPI distribution | `uniprot-mcp-server` | what you `pip install` (the bare `uniprot-mcp` name was already claimed on PyPI when this project published) |
> | Python module | `uniprot_mcp` | what you `import` (PEP-8 underscore form) |
> | Console script + MCP server identity | `uniprot-mcp` | what you run from the shell and what Claude Desktop sees |
>
> Cross-checks that prove the wheel you installed was built from this repo: each release ships a [Sigstore signature](https://www.sigstore.dev/), [SLSA build provenance](https://slsa.dev/), and a [CycloneDX SBOM](https://cyclonedx.org/), all attached to the [v1.1.0 GitHub Release](https://github.com/smaniches/uniprot-mcp/releases/tag/v1.1.0). Run `bash scripts/replicate.sh` (POSIX) or `pwsh scripts/replicate.ps1` (Windows) to verify the full chain end-to-end. Common precedents for the same one-thing-three-names pattern: `pillow`/`PIL`, `python-dateutil`/`dateutil`, `beautifulsoup4`/`bs4`, `python-Levenshtein`/`Levenshtein`.

From source:

```bash
git clone https://github.com/smaniches/uniprot-mcp.git
cd uniprot-mcp
pip install -e .
```

### Claude Desktop

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "uniprot": {
      "command": "uvx",
      "args": ["uniprot-mcp-server"]
    }
  }
}
```

For pinned, reproducibility-grade access:

```json
{
  "mcpServers": {
    "uniprot": {
      "command": "uniprot-mcp",
      "args": ["--pin-release=2026_01"]
    }
  }
}
```

To enable `uniprot_replay_from_cache` reads against a cache directory
you have populated yourself (automatic write-through is not wired into
the request path — see [§Provenance & verification](#provenance--verification)):

```json
{
  "mcpServers": {
    "uniprot": {
      "command": "uniprot-mcp",
      "env": {
        "UNIPROT_MCP_CACHE_DIR": "/absolute/path/to/cache"
      }
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add uniprot -- uniprot-mcp
```

### Self-test (live UniProt smoke check)

```bash
uniprot-mcp --self-test
# [tools] registered: 41/41
# [live] P04637 -> TP53 OK
# [PASS]
```

---

## Example workflows

**1. Clinical-variant interpretation packet for `TP53 R175H`.**

```
> What's at residue 175 of P04637? Is R175H a known variant? Pull
> the UniProt and ClinVar evidence and tell me how confident the
> AlphaFold model is at that residue.
→ uniprot_features_at_position("P04637", 175)
→ uniprot_lookup_variant("P04637", "R175H")
→ uniprot_resolve_clinvar("P04637", change="R175H")
→ uniprot_get_alphafold_confidence("P04637")
```

**2. Drug-target dossier in one call.**

```
> Give me a complete drug-target characterisation of human BRCA1.
→ uniprot_target_dossier("P38398")
   # nine sections, two upstream calls (entry + FASTA), one tool call.
```

**3. Sequence chemistry for buffer choice / expression-system selection.**

```
> What's the molecular weight, pI, and hydrophobicity of human insulin?
→ uniprot_compute_properties("P01308")
   # MW 11,981 Da, pI 4.93, ε₂₈₀ 24,980 M⁻¹·cm⁻¹ — pure Python on the FASTA.
```

**4. Provenance drift check using the recorded TP53 capture.**

```text
> Check the 2026-10-15 UniProt P04637 response for drift.
> Supply the captured release, URL, and canonical SHA-256:
uniprot_provenance_verify(
    url="https://rest.uniprot.org/uniprotkb/P04637",
    release="2026_03",
    response_sha256="112540dcb662c3ce2feba05272ce0e946ce76089a5bcf8346eb55141892f7fcf"
)
```

The verdict is determined by the live upstream response; no match is
pre-asserted.

**5. Replay a previously-cached answer offline (read primitive — see status note below).**

```bash
# Pre-condition: $UNIPROT_MCP_CACHE_DIR/<sha256(url)>.json already exists,
# populated by the maintainer benchmark capture script or an external
# wrapper. Automatic cache write-through is not currently wired into the
# request path; cache entries must be populated explicitly or by an
# external capture workflow.
export UNIPROT_MCP_CACHE_DIR=~/sealed-cache
> uniprot_replay_from_cache("https://rest.uniprot.org/uniprotkb/P04637")
```

---

## Testing

| Layer | Path | What |
|---|---|---|
| Unit | `tests/unit/` | Behaviour of every public function. |
| Property | `tests/property/` | Hypothesis-driven invariants on regexes + query construction. |
| Contract | `tests/contract/` | Manifest / pyproject / docs / incident-policy / benchmark drift prevention. |
| Client | `tests/client/` | Retry / back-off / id-mapping polling against `respx`-mocked HTTP. |
| Integration | `tests/integration/` | Live UniProt + AlphaFold; opt-in via `--integration`. |
| Benchmark | `tests/benchmark/` | 30 SHA-256-committed prompts + reproducible verifier. |

**Offline and optional live integration suites are enforced in CI** on `main` (real counts via `pytest --collect-only --ignore=tests/integration` and `pytest --collect-only tests/integration`; the offline count includes the v1.1.x mutation-killer files for `cache`, `proteinchem`, `client`, the contract tests for version-consistency / changelog-presence, and the coverage-gap test files that restored full coverage). Line + branch coverage is **100.00 %** across all seven source files, with the `[tool.coverage.report]` gate set to `fail_under = 100` so CI enforces it. Two branches carry a justified `# pragma: no cover` for genuinely-unreachable import-time fallbacks (documented inline and in `pyproject.toml`). Reproduce locally with `pytest tests/unit tests/property tests/client tests/contract --cov=uniprot_mcp --cov-branch --cov-report=term-missing`. Mypy (strict), ruff (check + format), bandit (0 issues at any severity), pip-audit (`--strict`, no known vulnerabilities) all clean. **Mutation testing infrastructure ships and is measurement-first:** see the per-module table at [`docs/MUTATION_SCORES.md`](docs/MUTATION_SCORES.md) for the latest matrix-workflow results; the ≥ 95 % gate is the v1.2.0 target, not the current state.

```bash
# Fast, offline (CI on every push):
pytest tests/unit tests/property tests/client tests/contract -v

# Live UniProt (opt-in, nightly in CI):
pytest --integration tests/integration -v

# Lint / type-check / security / SCA:
ruff check . && ruff format --check . && mypy src/uniprot_mcp
bandit -r src/uniprot_mcp && pip-audit --strict
```

---

## Architecture & threat model

- [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) — twelve STRIDE-shaped
  threats, each receipt-anchored to a code path or commit SHA, plus
  the cross-origin allowlist policy (§T3b).
- [`docs/INCIDENT_POLICY.md`](docs/INCIDENT_POLICY.md) +
  [`docs/POSTMORTEM_TEMPLATE.md`](docs/POSTMORTEM_TEMPLATE.md) +
  [`docs/INCIDENT_LOG.md`](docs/INCIDENT_LOG.md) — every nightly
  integration breakage triggers a postmortem entry.
- [`AUDIT.md`](AUDIT.md) — pre-1.0.1 professional audit, P0/P1
  remediations recorded.
- [`docs/RELEASE.md`](docs/RELEASE.md) — release runbook covering the
  tag → PyPI → MCP Registry → Sigstore → GitHub Release → Zenodo chain,
  including the `release-verify.yml` post-tag verification job and the
  one-time setup for the Zenodo + PyPI webhooks.
- [`docs/archive/`](docs/archive/) — pre-flip planning docs retained
  for audit trail (`PENDING_V1.md`, `MERGE_PLAN.md`,
  `RELEASE_AUDIT_v1.1.3.md`). Not part of the published docs site;
  current operational status lives in `README.md`, `CHANGELOG.md`,
  and `docs/MUTATION_SCORES.md`.
- [`mkdocs.yml`](mkdocs.yml) — Material-themed docs site, deployable to
  `gh-pages` via [`.github/workflows/docs.yml`](.github/workflows/docs.yml).
  Build locally with `pip install -e ".[docs]" && mkdocs serve`.

---

## Related MCP servers by the same author

- [`alphafold-sovereign-mcp`](https://github.com/smaniches/alphafold-sovereign-mcp) — Model Context Protocol server that integrates AlphaFold DB with eight additional public biomedical data sources, with a local SQLite knowledge graph (`pip install alphafold-sovereign-mcp`).
- [`semantic-scholar-mcp`](https://github.com/smaniches/semantic-scholar-mcp) — Model Context Protocol server for Semantic Scholar (200M+ academic papers), providing 14 tools for paper search, citation graph traversal, author profiles, and recommendations (`pip install s2-mcp-server`).

---

## Citation

Cite via [`CITATION.cff`](CITATION.cff) (GitHub renders a "Cite this
repository" button). Always also cite the UniProt Consortium:

> The UniProt Consortium. *UniProt: the Universal Protein Knowledgebase
> in 2025.* Nucleic Acids Research (2025).
> [doi:10.1093/nar/gkae1010](https://doi.org/10.1093/nar/gkae1010)

---

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).

This is a standalone, Apache-2.0-licensed UniProt MCP maintained
by TOPOLOGICA LLC. It does not require a companion product. Its source
provenance and replay features should not be mistaken for a
tamper-evident audit ledger or independent scientific validation.
Integrations that require persistent, trusted audit records must
implement and assess that functionality separately.

Copyright © 2026 Santiago Maniches. TOPOLOGICA LLC.
