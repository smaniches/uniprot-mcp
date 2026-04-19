# Architecture

This document records the design decisions behind `uniprot-mcp` so that
future contributors (and future-us) can understand *why* the code looks
the way it does, not just *what* it does.

## Goals

1. **Reference-quality MCP** for bio-data. If someone is building an
   MCP for ChEMBL, PDB, or Ensembl, this repo should be what they copy.
2. **Zero-config usability.** The server should start with `python
   server.py` and require no API key, no database, no setup.
3. **Trustworthy in agents.** Every tool is read-only, validated
   client-side, and produces deterministic, parseable output.
4. **Verifiable correctness.** Tests cover behaviour against recorded
   real responses plus property-based invariants. CI is hermetic; live
   integration is opt-in and scheduled.

## Shape

```
┌──────────────────────────────┐
│  MCP client (Claude, Cline,  │
│  Cursor, Continue, …)        │
└──────────────┬───────────────┘
               │  JSON-RPC 2.0 over stdio
┌──────────────▼───────────────┐
│  server.py     (FastMCP)     │   10 @mcp.tool decorated funcs
│  ├─ tool wrappers            │   - input validation
│  ├─ error envelope           │   - format dispatch (md / json)
│  └─ main()                   │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│  client.py     (httpx)       │   - retry/back-off (429, 5xx)
│  ├─ UniProtClient            │   - ACCESSION_RE validation
│  ├─ ACCESSION_RE             │   - id-mapping poll loop
│  └─ batch_entries partition  │   - batch_entries partitions
└──────────────┬───────────────┘
               │  HTTPS
┌──────────────▼───────────────┐
│  rest.uniprot.org            │
└──────────────────────────────┘

┌──────────────────────────────┐
│  formatters.py               │   pure, no I/O,
│  fmt_entry / fmt_search / …  │   markdown + json emitters
└──────────────────────────────┘
```

Three modules, in strict dependency order: `formatters` (pure) ←
`client` (I/O) ← `server` (MCP wiring). Tests mirror this layering.

## Key invariants

1. **`formatters` is pure and offline.** No network, no I/O. Any call
   must be deterministic given its inputs.
2. **`client` is the only module that touches the network.**
3. **`server` adds no logic beyond dispatch, validation, and error
   envelopes.** No data transformation happens here — everything is
   delegated to `client` + `formatters`.
4. **Accession validation happens client-side.** `ACCESSION_RE` is the
   single source of truth for what a valid UniProt accession looks
   like. `batch_entries` filters input with it *before* any HTTP call
   so a malformed token cannot poison the batch.
5. **Retries are bounded.** `MAX_RETRIES = 3`, with exponential back-off
   (1.5^n seconds) on 429/5xx/timeout. 4xx client errors other than 429
   are not retried — they are the caller's bug, not a transient failure.
6. **ID-mapping polling is bounded.** 30 attempts at 1s intervals, then
   `TimeoutError`. Never unbounded.

## Why FastMCP?

FastMCP is the highest-level ergonomic API in the `mcp` Python SDK.
Decorator-driven tool registration keeps server.py declarative. We
avoid the `lifespan` context-injection pattern because it has a race
where FastMCP fails to inject `ctx` under some transports — the module-
level lazy `UniProtClient` singleton is simpler and equally correct for
a stateless client.

## Why client-side accession validation (not server-side)?

Three reasons:

1. **Failure isolation.** UniProt rejects an entire batch search if one
   accession is malformed. Client-side filtering lets us preserve
   the good tokens and report the bad ones.
2. **Fewer HTTP calls.** All-invalid input short-circuits with no
   network I/O.
3. **Clearer errors.** The caller sees exactly which tokens we skipped,
   not a generic `400 Bad Request`.

## Why Apache-2.0?

Explicit patent grant. Compatible with MIT consumers. Matches the
license of a number of bio-data standards (e.g. HL7 FHIR is CC BY-ND;
but Apache is the closest permissive license with patent protection).

## Why property-based tests?

The accession regex and the batch partition are both specifications,
not implementations. They must hold for *any* input, not just the
examples we think of. Hypothesis finds the trailing-newline edge-case
and the anchoring edge-case without us writing them down.

## Why snapshot tests?

Formatters emit markdown for human + LLM consumption. Snapshot tests
(syrupy) lock the exact output; any change is visible in a PR diff.
They catch accidental formatting regressions that assertion-based tests
miss.

## Non-goals

- **OAuth / authentication.** UniProt is public. Adding auth would
  create friction for no gain.
- **Caching / persistence.** UniProt's rate limits are generous and
  per-call latency is low. Caching inside the MCP would create stale-
  data bugs. If callers want caching, they should do it at the agent
  level.
- **Writing to UniProt.** The API is read-only upstream. `readOnlyHint:
  true` on every tool.
- **Remote / streamable HTTP transport.** stdio is what Claude
  Desktop / Claude Code / Cursor / Continue all speak today. A remote
  variant is a separate project (likely Cloudflare Workers + OAuth)
  tracked in the `smaniches/topologica` roadmap.

## Open design questions

- **Output format defaults.** We default to markdown because LLMs parse
  it well and humans read it well. Some callers may want JSON — we
  expose `response_format="json"` but could make it negotiable via MCP
  tool metadata once the spec supports it.
- **Field projection.** `search` and `batch_entries` accept a `fields`
  filter but don't yet expose it via the MCP tool signature. Worth
  adding when LLMs routinely hit context limits on large responses.
