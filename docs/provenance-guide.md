# Provenance & verification — deep dive

Every successful response from `uniprot-mcp` carries a
machine-verifiable record of where it came from. This page is the
deep-dive reference for what's recorded, how it's used, and how a
third party can re-check any prior answer.

## The Provenance record

```python
class Provenance(TypedDict):
    source: str            # "UniProt" / "AlphaFoldDB" / "NCBI ClinVar (eutils)"
    release: str | None    # e.g. "2026_01"; None when origin doesn't version
    release_date: str | None
    retrieved_at: str      # ISO-8601 UTC, second precision
    url: str               # fully resolved request URL incl. query string
    response_sha256: str   # SHA-256 of the canonical body
```

`response_sha256` is computed on a **canonical** serialization:

- For JSON responses: parsed and re-serialized with `sort_keys=True`
  + compact separators. Within-release key reordering does NOT break
  verification; real content drift DOES.
- For non-JSON (FASTA, plain text): raw response bytes hashed
  unchanged.

## How it's surfaced

### Markdown footer (default)

```
---
_Source: UniProt release 2026_01 (28-January-2026) • Retrieved 2026-04-25T12:00:00Z_
_Query: https://rest.uniprot.org/uniprotkb/P04637_
_SHA-256: 0040d79bb39e2f7386d55f81071e87858ec2e5c2cd9552e93c3633897f78345e_
```

### JSON envelope (when `response_format="json"`)

```json
{
  "data": { ... },
  "provenance": {
    "source": "UniProt",
    "release": "2026_01",
    "release_date": "28-January-2026",
    "retrieved_at": "2026-04-25T12:00:00Z",
    "url": "https://rest.uniprot.org/uniprotkb/P04637",
    "response_sha256": "0040d79bb39e2f7386d55f81071e87858ec2e5c2cd9552e93c3633897f78345e"
  }
}
```

### PIR-style FASTA header (sequence tool only)

```
;Source: UniProt
;Release: 2026_01 (28-January-2026)
;Retrieved: 2026-04-25T12:00:00Z
;URL: https://rest.uniprot.org/uniprotkb/P04637
;SHA-256: 0040d79bb39e2f7386d55f81071e87858ec2e5c2cd9552e93c3633897f78345e
>sp|P04637|P53_HUMAN ...
ATCG...
```

PIR (`;`-prefix) lines are recognised as comments by every major
FASTA parser (BLAST+, biopython `SeqIO`, emboss `seqret`). The
sequence remains a valid FASTA record.

## Verification tool

`uniprot_provenance_verify(url, release="", response_sha256="")`
re-fetches the URL with a fresh HTTP client (bypasses any
pin-release configuration) and compares:

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
Every successful response is written to disk as
`<cache_dir>/<sha256(url)>.json` with the schema:

```json
{
  "url": "https://rest.uniprot.org/uniprotkb/P04637",
  "body_text": "<raw response>",
  "provenance": { ... }
}
```

Atomic writes (tempfile + `os.replace`) — a crashed process never
leaves a half-written entry behind.

The `uniprot_replay_from_cache(url)` tool reads from that cache
without touching the upstream. Useful for:

- **Air-gapped clinical workflows.** A clinical informatician can
  cache a sealed snapshot of UniProt and run analyses offline.
- **Reproducing a year-old answer.** The same Provenance record
  that's in your six-month-old report points at the same cache
  entry.
- **Reducing UniProt's load.** When running a benchmark or test
  suite twice in close succession, the cache absorbs the duplicate
  traffic.

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
- **Compliance-grade differentiator?** Yes — no other public
  bioinformatics MCP carries per-query verifiable provenance.

That's the wedge.

## See also

- [Threat model](THREAT_MODEL.md) — the cross-origin allowlist and
  SSRF posture.
- [Incident policy](INCIDENT_POLICY.md) — what happens when the
  nightly integration suite goes red.
- [Tools reference](tools.md) — the full surface.
