# Capture: TP53 R175H walkthrough, 2026-10-15

This directory binds `examples/01_clinical_variant_interpretation.jsonl`
to the source bytes it was rendered from.

- **Recorded:** 2026-10-15 between 10:32:43Z and 10:32:45Z (UTC), live, by
  `capture.py` in this directory. After the run, the script was only reformatted for
  the repository's ruff gate and had one import restyled for CodeQL; its
  logic is unchanged.
- **Software:** uniprot-mcp 1.3.9 working tree with the provenance
  source-attribution footer fix applied (unreleased). Exact interpreter and httpx versions
  are in `capture_manifest.json`.
- **Upstream:** UniProt REST (release `2026_03`, release date
  02-September-2026), NCBI ClinVar E-utilities, AlphaFold DB
  (`AF-P04637-F1`, model v6, created 2025-08-01).
- **Files:**
  - `tool_outputs.json` holds every tool call's arguments and verbatim output.
  - `capture_manifest.json` holds, for each upstream response, the URL,
    status, receive time, selected headers, the SHA-256 of the raw bytes,
    and the canonical SHA-256 that the tool footer reports.
  - `upstream/*.body.gz` holds the response bodies. They are gzip-compressed
    with mtime 0, and identical bodies are stored once.
- **Digest method:** for JSON bodies the footer SHA-256 is computed over
  `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`
  encoded as UTF-8 (`uniprot_mcp.client.canonical_response_hash`). For other
  bodies it is computed over the raw bytes.
  `tests/contract/test_tp53_capture_binding.py` recomputes every digest from
  the stored bytes and checks it against the transcript footers.

The transcript that this capture replaced (repository state
`0b378ba2dd949da999f5d3f50f9a108fb995802f`) was illustrative text, not a
capture. Its footers, ClinVar accession, record count, AlphaFold scores and
the modified-residue line at position 175 do not correspond to source
records. Find it in git history if you need it.

Upstream data licences: UniProt (CC BY 4.0), AlphaFold DB (CC BY 4.0),
NCBI ClinVar (NCBI data-use policies; public domain in the US).
