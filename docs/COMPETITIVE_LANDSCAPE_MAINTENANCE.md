# Competitive landscape — maintenance procedure

This document describes how to keep
[`docs/COMPETITIVE_LANDSCAPE.md`](COMPETITIVE_LANDSCAPE.md) accurate.
The survey is only as strong as its freshness; stale data undermines
the differentiation claims that depend on it.

## Review cadence

The survey should be reviewed **quarterly** or whenever a new
`uniprot-mcp` minor release ships, whichever comes first. The
"Last full review" date at the top of
`docs/COMPETITIVE_LANDSCAPE.md` records when this was last done.

## How to identify comparator repositories

Run the following searches and record the date:

1. **GitHub code search:**
   `bio mcp`, `uniprot mcp`, `bioinformatics mcp`,
   `provenance_verify`, `hash_drift`, `release_drift`,
   `protein mcp`, `clinical mcp`.
2. **MCP Registry:** browse
   `registry.modelcontextprotocol.io` for bio/health categories.
3. **Smithery:** browse `smithery.ai` bio category.
4. **Anthropic Connectors Directory:** check for new bio-tagged
   connectors.
5. **PyPI:** search for `*-mcp` packages in bio/health domains.

For each candidate found, read the README for:
- Per-response digest or hash behaviour
- Verify-style primitives (re-fetch + compare)
- Release-pinning semantics
- Supply-chain attestations (SLSA, Sigstore, SBOM)
- `.well-known/mcp.json` presence

Where the README is ambiguous, inspect the source.

## What qualifies as a counterexample

A counterexample to the "no other surveyed bio-MCP has [feature X]"
claim is a public repository that:

1. Is a Model Context Protocol server (not a REST API, CLI tool, or
   library).
2. Targets a biomedical data source (UniProt, PDB, ClinVar, ChEMBL,
   KEGG, etc.).
3. Implements the specific feature in question (e.g., per-response
   SHA-256 of canonical body, a verify primitive, release pinning).

A server that plans to implement a feature but has not shipped it is
not a counterexample. A server that hashes its installer (not its
per-query responses) is not a counterexample to "per-response
SHA-256."

## How to file corrections

If you find a counterexample or an error in the survey table:

1. **Open an issue** at
   `https://github.com/smaniches/uniprot-mcp/issues` with:
   - The repository URL
   - The specific feature it implements
   - A link to the relevant code or documentation
2. The maintainer will verify the claim, update
   `docs/COMPETITIVE_LANDSCAPE.md`, and adjust the README's
   differentiation language if needed.
3. The correction will be recorded in the CHANGELOG under the next
   release.

## How to update the survey table

1. Run the searches listed above.
2. For each new candidate, add a row to the survey table in
   `docs/COMPETITIVE_LANDSCAPE.md` with all columns filled.
3. For each existing candidate, check for recent pushes and update
   the "Last push" column if needed. Re-read the README for feature
   changes.
4. Update the "Last full review" date at the top of the document.
5. Review the "What `uniprot-mcp` does that no surveyed bio-MCP
   does" section. If a counterexample has appeared, soften the claim
   to "in the reviewed set" or remove it.
6. Update `docs/CLAIMS.md` claim C10 with the new review date.
7. Commit with a message like
   `docs: update competitive landscape survey (YYYY-MM-DD)`.

## Language discipline

- Use "in the reviewed set documented here" rather than absolute
  novelty claims like "no other bio-MCP" or "the only server."
- Use "as of [date]" to time-bound every comparative statement.
- Use "to the best of our survey" when the search method is
  described but exhaustive coverage is not guaranteed.
- Invite corrections: every comparative claim should end with a
  pointer to the issue tracker.
