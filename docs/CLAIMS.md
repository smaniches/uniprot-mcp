# Claims-to-evidence map

Every public differentiation claim this repository makes is listed
below with: the evidence that supports it, a command a reviewer can
run to verify it, the known limitations, and the date of the last
review. If any entry is wrong or out of date, please file an issue.

Last full review: **2026-05-26**.

---

## C1. 41 tools across 8 families

**Claim (README, OVERVIEW.md).** The server exposes 41 read-only MCP
tools organised into eight endpoint families.

**Evidence.**
- `src/uniprot_mcp/server.py` — each `@mcp.tool` decorator registers
  one tool.
- `.well-known/mcp.json` and `server.json` — manifest files listing
  the tool surface.
- `tests/contract/test_manifest_consistency.py` — contract test
  enforcing equality between code and manifest.

**Verify.**
```bash
grep -c "@mcp.tool" src/uniprot_mcp/server.py
# expected: 41
pytest tests/contract/test_manifest_consistency.py -v
```

**Limitation.** The count includes `uniprot_replay_from_cache`, which
is a read primitive over an externally-populated cache directory (not
a tool that contacts UniProt). All 41 tools are registered and
callable; the count is mechanically verified by CI.

**Last reviewed:** 2026-05-26.

---

## C2. Per-response SHA-256 provenance on every successful response

**Claim (README, OVERVIEW.md, provenance-guide.md).** Every
successful tool response carries a `Provenance` record: UniProt
release, retrieval timestamp, resolved URL, and a SHA-256 of the
canonical response body.

**Evidence.**
- `src/uniprot_mcp/client.py` — `_extract_provenance` and
  `canonical_response_hash` functions.
- `src/uniprot_mcp/formatters.py` — every `fmt_*` function appends
  the provenance footer.
- `tests/unit/test_provenance.py` — unit tests for hash computation
  and provenance extraction.
- `tests/benchmark/run-2026-04-25-roundtrip/transcript.md` — live
  demonstration with real values.

**Verify.**
```bash
uniprot-mcp --self-test
# observe the provenance footer in the output
pytest tests/unit/test_provenance.py -v
```

**Limitation.** JSON canonicalisation sorts dictionary keys but does
not sort array elements. If UniProt returns list elements in a
different order between requests within the same release, the
canonical hash may differ. This is documented in
`docs/provenance-guide.md`.

**Last reviewed:** 2026-05-26.

---

## C3. `uniprot_provenance_verify` with five enumerated verdicts

**Claim (README, OVERVIEW.md).** The `uniprot_provenance_verify` tool
re-fetches a previously recorded URL and compares the release tag and
canonical response SHA-256, returning one of five verdicts:
`verified`, `release_drift`, `hash_drift`, `release_and_hash_drift`,
`url_unreachable`.

**Evidence.**
- `src/uniprot_mcp/server.py` — the tool registration and verdict
  logic.
- `tests/unit/test_provenance_verify.py` — unit tests covering all
  five verdict paths.
- `tests/benchmark/run-2026-04-25-roundtrip/transcript.md` — live
  `verified` verdict.

**Verify.**
```bash
pytest tests/unit/test_provenance_verify.py -v
```

**Limitation.** Verification requires network access to
`rest.uniprot.org`. The tool bypasses any `--pin-release`
configuration to compare against the live API. Cross-origin URLs
(AlphaFold, ClinVar) are not yet verifiable via this tool.

**Last reviewed:** 2026-05-26.

---

## C4. `--pin-release` strict release pinning

**Claim (README).** `--pin-release=YYYY_MM` (or
`UNIPROT_PIN_RELEASE` env var) causes the server to raise
`ReleaseMismatchError` when the upstream release differs from the
pinned value.

**Evidence.**
- `src/uniprot_mcp/client.py` — pin-release check in `_req`.
- `src/uniprot_mcp/server.py` — CLI argument forwarding.
- `tests/unit/test_pin_release.py` — unit tests for match and
  mismatch paths.

**Verify.**
```bash
pytest tests/unit/test_pin_release.py -v
```

**Limitation.** UniProt's REST API does not honour a release-selector
query parameter. Pinning is assertion-only: the server refuses drift
rather than requesting a specific release. For byte-level
reproducibility of a historical answer, use the UniProt FTP snapshot.

**Last reviewed:** 2026-05-26.

---

## C5. Offline replay via `uniprot_replay_from_cache` (read primitive)

**Claim (README).** `uniprot_replay_from_cache` reads a previously
recorded response from `$UNIPROT_MCP_CACHE_DIR` without hitting
UniProt.

**Evidence.**
- `src/uniprot_mcp/cache.py` — `ProvenanceCache` class.
- `src/uniprot_mcp/server.py` — tool registration.
- `tests/unit/test_cache.py` — unit tests for read/write/miss paths.

**Verify.**
```bash
pytest tests/unit/test_cache.py -v
```

**Limitation.** This is a **read primitive** in v1.1.x. The cache
directory must be populated externally (e.g., by the benchmark capture
script or by a user wrapper). Automatic write-through on every
successful tool call is a v1.2.0 roadmap item. This was explicitly
retracted in v1.1.3 (see CHANGELOG.md).

**Last reviewed:** 2026-05-26.

---

## C6. 744 offline + 42 live integration tests

**Claim (README badge, testing section).** The offline test suite
contains 744 tests; the live integration suite contains 42 tests.

**Evidence.**
- `pytest --collect-only --ignore=tests/integration -q` — offline
  count.
- `pytest --collect-only tests/integration -q` — integration count.
- Counts last reconciled at v1.1.6 (README testing section documents
  the jump from 446 at v1.1.0).

**Verify.**
```bash
pytest --collect-only --ignore=tests/integration -q 2>/dev/null | tail -1
pytest --collect-only tests/integration -q 2>/dev/null | tail -1
```

**Limitation.** Test counts change with each release. The README
badge is a static shield; it is manually updated and may lag by one
patch release. The authoritative count is always
`pytest --collect-only`.

**Last reviewed:** 2026-05-26.

---

## C7. 91.85% line + branch coverage (measured at v1.1.0)

**Claim (README, OVERVIEW.md, pyproject.toml).** Measured coverage is
91.85%.

**Evidence.**
- `pyproject.toml` `[tool.coverage.report]` — `fail_under = 91`.
- README testing section documents the regression from 100% at
  v1.0.0 and the v1.2.0 uplift commitment.
- `.github/workflows/ci.yml` — coverage report uploaded on each CI
  run.

**Verify.**
```bash
pytest tests/unit tests/property tests/client tests/contract --cov --cov-report=term-missing
```

**Limitation.** The 91.85% figure was measured at v1.1.0. Releases
v1.1.1 through v1.1.7 are metadata-and-correctness releases that did
not change source-code paths, so the measurement remains operative
but has not been independently re-measured at a later tag. The CI
gate enforces a floor of 91%.

**Last reviewed:** 2026-05-26.

---

## C8. 30/30 sealed-prompt benchmark verified against live UniProt

**Claim (README, OVERVIEW.md).** A 30-prompt benchmark with
SHA-256-committed expected answers was verified 30/30 against live
UniProt on 2026-04-26 at v1.1.0.

**Evidence.**
- `tests/benchmark/expected.hashes.jsonl` — committed SHA-256
  commitments.
- `tests/benchmark/run-2026-04-26-v1.1.0/` — transcript of the
  verification run.
- `tests/benchmark/verify_against_hashes.py` — third-party
  verification script (no plaintext seal needed).
- `tests/benchmark/AUDIT.md` — per-prompt source attribution and
  independence statement.

**Verify.**
```bash
python tests/benchmark/verify_against_hashes.py \
  tests/benchmark/expected.hashes.jsonl
# expected: 28 hash commitments verified live (2 set-inclusion skipped)
```

**Limitation.** The benchmark was verified at UniProt release
`2026_01`. If UniProt has since released a new version, some hashes
may legitimately differ (`release_drift`). Tier C set-inclusion
prompts (28, 29) are skipped by the hash verifier because the live
answer may be a legitimate superset. `run.py` and `score.py` are
scaffolded (argparse-wired, stubbed bodies); the full comparative
scoring driver is a v2 benchmark item.

**Last reviewed:** 2026-05-26.

---

## C9. SLSA + Sigstore + CycloneDX SBOM on every release

**Claim (README, OVERVIEW.md, COMPETITIVE_LANDSCAPE.md).** Every
release artifact ships with SLSA build provenance, Sigstore keyless
signatures, and a CycloneDX SBOM.

**Evidence.**
- `.github/workflows/release.yml` — the release workflow that
  produces these artifacts.
- `.github/workflows/release-verify.yml` — post-release verification
  that all four links of the chain landed.
- GitHub Releases page — each release has attached `.sigstore` and
  SBOM files.

**Verify.**
```bash
bash scripts/replicate.sh
# step 3 runs: gh attestation verify
```

**Limitation.** Requires `gh` CLI with attestation support. The
`replicate.sh` script defaults to a specific version (update the
`VERSION` env var for other releases). PyPI Trusted Publishing (OIDC)
is used — no long-lived API tokens — but verifying the full chain
end-to-end requires network access to both PyPI and GitHub.

**Last reviewed:** 2026-05-26.

---

## C10. Provenance+verify stack absent from every other surveyed bio-MCP

**Claim (README, COMPETITIVE_LANDSCAPE.md).** The combination of
per-response SHA-256, a verify primitive with five verdicts, release
pinning, offline replay, pre-registered benchmark, and SLSA/Sigstore
supply chain is, in the reviewed set, absent from every other bio-MCP
server surveyed.

**Evidence.**
- `docs/COMPETITIVE_LANDSCAPE.md` — 14-server survey conducted
  2026-04-26, with method, per-server assessment, and honest
  weaknesses section.

**Verify.** The competitive landscape document describes the survey
method. A reviewer can re-run the same searches (GitHub code search,
MCP Registry, Smithery, Anthropic Connectors Directory, PyPI) and
check whether any new server has appeared with the same feature set.

**Limitation.** This is a **survey-dated claim**, not an absolute
statement. The survey was conducted on 2026-04-26. The bio-MCP
ecosystem is moving fast; a counterexample may have appeared since
the survey date. The claim is hedged as "to the best of my survey"
and "in the reviewed set documented here." The maintenance procedure
at `docs/COMPETITIVE_LANDSCAPE_MAINTENANCE.md` describes how to
update the survey. If you find a counterexample, file an issue.

**Last reviewed:** 2026-05-26 (claim language reviewed; survey data
from 2026-04-26).

---

## C11. Mutation testing scores: cache 82%, proteinchem 92%, client 70%

**Claim (README, OVERVIEW.md, docs/MUTATION_SCORES.md).** Per-module
mutation kill rates measured via mutmut.

**Evidence.**
- `docs/MUTATION_SCORES.md` — full per-module table with CI run
  links, survivor breakdowns, and uplift action items.
- `.github/workflows/mutation.yml` — the matrix workflow.
- CI run links in MUTATION_SCORES.md point to specific GitHub Actions
  runs with downloadable artifacts.

**Verify.**
```bash
pip install mutmut
mutmut run --paths-to-mutate=src/uniprot_mcp/cache.py
mutmut results
```

**Limitation.** The gate threshold is currently 0.0
(measurement-first). The >=95% gate is the v1.2.0 target, not the
current state. `formatters` and `server` modules timed out mid-pass
and have only partial measurements. The scores are from specific CI
runs dated 2026-04-28; subsequent code changes could shift the
numbers.

**Last reviewed:** 2026-05-26.

---

## C12. PyPI wheel built from this exact repo

**Claim (README, OVERVIEW.md).** The published PyPI wheel can be
cryptographically traced back to a specific git commit in this
repository.

**Evidence.**
- `scripts/replicate.sh` (POSIX) / `scripts/replicate.ps1`
  (Windows) — end-to-end verification script.
- `.github/workflows/release.yml` — PyPI Trusted Publishing (OIDC),
  SLSA attestation, Sigstore signing.

**Verify.**
```bash
bash scripts/replicate.sh
# cross-checks SHA-256 across PyPI / GitHub Release / SLSA attestation
# exit 0 iff every step passes
```

**Limitation.** Requires `gh` CLI, `curl`, `jq`, Python >= 3.11, and
network access to PyPI and GitHub. The script verifies a single
version (default in the `VERSION` variable); override to check other
releases.

**Last reviewed:** 2026-05-26.
