# Provenance & verification — deep dive

Every successful response from `uniprot-mcp` carries a
machine-verifiable record of where it came from. This page is the
deep-dive reference for what's recorded, how it's used, and how a
third party can re-check any prior answer.

## The Provenance record

```python
class Provenance(TypedDict):
    source: str  # "UniProt" / "AlphaFoldDB" / "NCBI ClinVar (eutils)"
    release: str | None  # e.g. "2026_01"; None when origin doesn't version
    release_date: str | None
    retrieved_at: str  # ISO-8601 UTC, second precision
    url: str  # fully resolved request URL incl. query string
    response_sha256: str  # SHA-256 of the canonical body
    accept_header: str  # Accept header used ("application/json" or "text/plain;format=fasta")
```

`response_sha256` is computed on a **canonical** serialization:

- For JSON responses: parsed and re-serialized with `sort_keys=True`
  + compact separators. Within-release key reordering does NOT break
  verification; real content drift DOES.
- For non-JSON (FASTA, plain text): raw response bytes hashed
  unchanged.

**Limitation:** JSON canonicalization sorts dictionary keys but does
**not** sort array elements. If UniProt returns list elements (e.g.,
cross-references, features) in a different order between requests
within the same release, the canonical hash may differ. This is a
known edge case; the `hash_drift` verdict covers it. For byte-level
reproducibility of a specific answer, use the FTP release snapshot
rather than the live REST API.

## How it's surfaced

### Actual recorded UniProt response

The [October 15, 2026 TP53 capture](https://github.com/smaniches/uniprot-mcp/blob/main/examples/01_clinical_variant_interpretation.jsonl)
contains this footer from a real `P04637` retrieval:

```text
---
_Source: UniProt release 2026_03 (02-September-2026) • Retrieved 2026-10-15T10:32:43Z_
_Query: https://rest.uniprot.org/uniprotkb/P04637_
_SHA-256: 112540dcb662c3ce2feba05272ce0e946ce76089a5bcf8346eb55141892f7fcf_
_Accept: application/json_
```

The exact source bytes and capture manifest are stored in
[the capture directory](https://github.com/smaniches/uniprot-mcp/tree/main/examples/captures/2026-10-15_tp53_r175h/).
`tests/contract/test_tp53_capture_binding.py` recomputes the
recorded hashes; this verifies the capture, not the biological
meaning of the record.

### Other response formats

The JSON response envelope includes the source metadata as a
`provenance` field. The FASTA sequence tool uses comment-prefixed
metadata lines. Both formats must derive their **own real hash**
from the response bytes actually returned; a JSON hash must never
be reused as the hash of a different FASTA payload.

For reproducible demonstrations, capture the live bytes and persist
them with the tool output. Do not publish simulated source receipts.

## Verification tool

`uniprot_provenance_verify(url, release="", response_sha256="", accept_header="application/json")`
re-fetches the URL with a fresh HTTP client (bypasses any
pin-release configuration) using the supplied `accept_header` for
content negotiation, and compares:

1. URL reachability (HTTP success).
2. Release tag (the `X-UniProt-Release` header) — only checked if
   `release` is supplied.
3. Canonical response SHA-256 — only checked if `response_sha256` is
   supplied.

### Five verdicts

| Verdict | Meaning | What to do |
|---|---|---|
| `verified` | Both checks passed | The recorded provenance is reproducible against the live API. |
| `release_drift` | UniProt has released a new version; body unchanged | If you need byte-level reproducibility, fetch from the FTP snapshot for the recorded release; otherwise the live answer is current and equivalent. |
| `hash_drift` | Same release, different body | An in-release edit. Investigate: UniProt may have edited the entry within the release, or our canonicalisation differs. |
| `release_and_hash_drift` | Both moved on | Use a release-specific FTP snapshot for the historical answer. |
| `url_unreachable` | Endpoint dropped, rate-limited, or 4xx | Retry, or report to UniProt if the endpoint should still exist. |

Each verdict carries an **advice** string — a one-sentence next-step
recommendation included in the markdown output.

## Strict release pinning

If you need byte-level reproducibility *during* querying (not just
verifying afterwards), opt into pinning:

```bash
export UNIPROT_MCP_CACHE_DIR=/path/to/cache  # optional, but recommended for offline replay
export UNIPROT_PIN_RELEASE=2026_01
uniprot-mcp
```

When `UNIPROT_PIN_RELEASE` is set, every successful upstream response
is checked against the pinned release. Any drift raises
`ReleaseMismatchError`, which the server surfaces as an
agent-actionable error envelope:

> **Release mismatch in `uniprot_get_entry`**: pinned `'2026_01'`,
> observed `'2026_03'` at `https://rest.uniprot.org/uniprotkb/P04637`.
> Re-run against a release-2026_01 snapshot or unset
> `UNIPROT_PIN_RELEASE`.

UniProt's REST API does **not** honour a release-selector query
parameter — the upstream always serves the latest release. Pinning
is therefore *assertion-only*: we refuse to silently accept drift
rather than transparently rewrite the request.

## The cache layer (optional)

`UNIPROT_MCP_CACHE_DIR=/path/to/cache` opts in to local caching.

**Scope in v1.1.x — read primitive only.** The cache is a *read*
surface for offline replay. `uniprot_replay_from_cache(url)` reads
from `<cache_dir>/<sha256(url)>.json` and returns the record without
hitting UniProt. **Automatic cache write-through is not currently wired
into the request path; cache entries must be populated explicitly or by
an external capture workflow.**
Today the cache directory must be populated externally — either by a
prior export, or by tests that explicitly call `ProvenanceCache.write`.
This was clarified in v1.1.3 (see `CHANGELOG.md` — the v1.1.2 wording
that promised "every successful response is mirrored to disk" was
retracted).

When the cache is populated, each entry is a JSON record with the
schema:

```json
{
  "url": "https://rest.uniprot.org/uniprotkb/P04637",
  "body_text": "<raw response>",
  "provenance": { ... }
}
```

`ProvenanceCache.write` (used by the test fixtures and by future
auto-write code paths) uses atomic file replacement (tempfile +
`os.replace`) so a crashed process never leaves a half-written entry
behind.

The `uniprot_replay_from_cache(url)` tool reads from that cache
without touching the upstream. Use cases once the directory is
populated:

- **Air-gapped clinical workflows.** Pre-export a sealed snapshot of
  the UniProt entries a workflow consults; run analyses on a machine
  with no network access to UniProt.
- **Reproducing a year-old answer.** The same Provenance record in
  your six-month-old report points at the same cache entry (the cache
  key is `sha256(url)`), so `replay_from_cache` returns the exact
  bytes the report cited.
- **Reducing UniProt's load.** When iterating on a notebook or test
  suite, pre-populate the cache from one round of live calls and
  replay for subsequent iterations.

## Compliance-officer model

> *Would a regulated bio-pharma compliance officer who has never met
> me trust this artifact in 2030?*

The provenance + verify + pin + cache stack is engineered to answer
that question with **yes**:

- **Reproducible without contacting the author?** Yes —
  `uniprot_provenance_verify` is one tool call.
- **Audit trail intact?** Yes — append-only Markdown footers, JSON
  envelopes, FASTA headers; every datum tagged.
- **What happens when something breaks?** Yes — release-mismatch
  raises loudly, the cache lets you replay sealed snapshots, the
  verify tool distinguishes drift modes.
- **Differentiating feature in the reviewed set?** At the time of
  the most recent survey (2026-04-26, recorded in
  [`docs/COMPETITIVE_LANDSCAPE.md`](COMPETITIVE_LANDSCAPE.md)) no
  other public bioinformatics MCP in the reviewed set attached
  per-query verifiable provenance to its responses. That survey is
  open to corrections; file an issue if you know of one.

That is the operational value proposition.

## See also

- [Threat model](THREAT_MODEL.md) — the cross-origin allowlist and
  SSRF posture.
- [Incident policy](INCIDENT_POLICY.md) — what happens when the
  nightly integration suite goes red.
- [Tools reference](tools.md) — the full surface.
