# Reviewer quick-start guide

This page is for a reviewer who wants to verify this repository's
claims in under 15 minutes. Every step is a shell command; no step
requires contacting the author.

**Prerequisites:** Python >= 3.11, pip, git, network access to
`rest.uniprot.org` (for live steps). Optional: `gh` CLI (for
supply-chain verification).

---

## 1. Install from PyPI (~1 min)

```bash
pip install uniprot-mcp-server
```

Or, for an isolated install that does not touch your global
environment:

```bash
python -m venv /tmp/uniprot-review && source /tmp/uniprot-review/bin/activate
pip install uniprot-mcp-server
```

## 2. Self-test — live UniProt smoke check (~30 s)

```bash
uniprot-mcp --self-test
```

Expected output:

```
[tools] registered: 41/41
[live] P04637 -> TP53 OK
[PASS]
```

This confirms the binary works, all 41 tools registered, and a live
UniProt fetch succeeds.

## 3. Run one UniProt query (~30 s)

Start the server and invoke a tool via the MCP protocol. The simplest
way is via Claude Desktop or Claude Code:

```bash
claude mcp add uniprot -- uniprot-mcp
```

Then ask:

```
What gene does UniProt entry P04637 encode?
```

Expected: the agent calls `uniprot_get_entry("P04637")` and returns
information about TP53 (tumor protein p53), with a provenance footer
containing the UniProt release, retrieval timestamp, URL, and
SHA-256.

## 4. Verify provenance (~1 min)

Copy the provenance footer from step 3 (or use the values from the
committed transcript at
`tests/benchmark/run-2026-04-25-roundtrip/transcript.md`) and ask the
agent:

```
Verify the provenance for P04637 using URL
https://rest.uniprot.org/uniprotkb/P04637
```

The agent calls `uniprot_provenance_verify` and returns one of five
verdicts. If the UniProt release has not changed since the recorded
provenance, the verdict is `verified`. If UniProt has released a new
version, the verdict is `release_drift` or `release_and_hash_drift`
with an advice string explaining next steps.

## 5. Run the offline test suite (~2 min)

```bash
git clone https://github.com/smaniches/uniprot-mcp.git
cd uniprot-mcp
pip install -e ".[test,dev]"
pytest tests/unit tests/property tests/client tests/contract -v
```

This runs the full offline suite (744 tests at v1.1.6). No network
access is needed; `pytest-socket` blocks outbound connections.

## 6. Run lint, type-check, and security scan (~1 min)

```bash
ruff check . && ruff format --check .
mypy src/uniprot_mcp
bandit -r src/uniprot_mcp
```

All three should exit cleanly.

## 7. Verify supply-chain provenance (~3 min)

Requires: `gh` CLI with attestation support, `curl`, `jq`.

```bash
bash scripts/replicate.sh
```

This script:

1. Downloads the published wheel from PyPI and computes its SHA-256.
2. Cross-checks the hash against PyPI's registry, the GitHub Release
   asset, and the SLSA build-provenance attestation.
3. Runs `gh attestation verify` to confirm the cryptographic chain.
4. Installs in an isolated venv and runs `--self-test`.
5. Re-derives benchmark answers from live UniProt and compares to the
   committed SHA-256 seal.

Exit code 0 means every step passed.

## 8. Verify benchmark hash commitments (~2 min)

```bash
python tests/benchmark/verify_against_hashes.py \
  tests/benchmark/expected.hashes.jsonl
```

Expected: `OK: 28 hash commitment(s) verified live (2 set-inclusion
prompt(s) skipped)`. This re-derives every Tier A / Tier B answer
from live UniProt and compares its canonical SHA-256 to the committed
commitments. No plaintext seal file is needed.

## 9. Run live integration tests (optional, ~5 min)

```bash
pytest --integration tests/integration -v
```

These 42 tests contact the live UniProt, AlphaFold, and ClinVar APIs.
They are opt-in and may fail if an upstream is temporarily
unavailable or has released a new version.

---

## Time estimate summary

| Step | Time | Network needed |
|------|------|----------------|
| 1. Install | ~1 min | yes (PyPI) |
| 2. Self-test | ~30 s | yes (UniProt) |
| 3. One query | ~30 s | yes (UniProt) |
| 4. Verify provenance | ~1 min | yes (UniProt) |
| 5. Offline tests | ~2 min | no |
| 6. Lint/type/security | ~1 min | no |
| 7. Supply-chain verify | ~3 min | yes (PyPI, GitHub) |
| 8. Benchmark hashes | ~2 min | yes (UniProt) |
| 9. Integration tests | ~5 min | yes (UniProt, AlphaFold, ClinVar) |
| **Total** | **~15 min** | |

Steps 5 and 6 are fully offline. Steps 1-4 and 7-9 require network
access. Steps 3 and 4 require an MCP client (Claude Desktop or
Claude Code); all other steps use the shell only.

---

## Where to find more

| Document | What it covers |
|----------|----------------|
| [`docs/CLAIMS.md`](docs/CLAIMS.md) | Every public claim mapped to evidence, verify commands, and limitations. |
| [`docs/COMPETITIVE_LANDSCAPE.md`](docs/COMPETITIVE_LANDSCAPE.md) | 14-server survey of the bio-MCP space. |
| [`docs/provenance-guide.md`](docs/provenance-guide.md) | Deep dive on the provenance record format and verification tool. |
| [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md) | STRIDE-shaped threat model. |
| [`AUDIT.md`](AUDIT.md) | Pre-1.0.1 professional audit with P0/P1 remediations. |
| [`CHANGELOG.md`](CHANGELOG.md) | Per-release change log. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Development setup and contribution guidelines. |
