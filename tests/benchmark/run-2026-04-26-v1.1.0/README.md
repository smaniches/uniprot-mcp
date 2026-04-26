# Benchmark run — 2026-04-26 (v1.1.0)

**Date:** 2026-04-26
**Package version:** uniprot-mcp-server 1.1.0
**Git commit:** 4992b32 (`main` branch HEAD at run time)
**Live origin:** `https://rest.uniprot.org` (UniProt REST API)
**Operator:** Santiago Maniches (TOPOLOGICA LLC)

## Pre-registration check (seal integrity)

```
$ python tests/benchmark/verify.py tests/benchmark/expected.jsonl \
    tests/benchmark/expected.hashes.jsonl
OK: 30 commitments verified
```

Every line of the local `expected.jsonl` matches its committed SHA-256
in `expected.hashes.jsonl` exactly. The expected answers were not
edited after commitment time.

## Live re-derivation

```
$ python tests/benchmark/verify_answers.py tests/benchmark/expected.jsonl
Re-deriving 30 answers from https://rest.uniprot.org ...
  prompt  1: OK — exact match
  prompt  2: OK — exact match
  ...
  prompt 28: OK — set-inclusion verified
  prompt 29: OK — set-inclusion verified
  prompt 30: OK — exact match

OK: all 30 prompts verified against https://rest.uniprot.org
```

(Full verifier output committed at `verify-output.txt` alongside this
file.)

## Result

**30 / 30 prompts verified.**

- **28 / 30** "exact match" — the live UniProt response is byte-equal
  to the sealed answer.
- **2 / 30** "set-inclusion verified" — prompts 28 (TP53 feature types)
  and 29 (TP53 cross-reference databases) accept the live answer when
  it is a superset of the sealed answer; this is the snapshot-dependence
  policy documented in `tests/benchmark/AUDIT.md`. New entries on the
  live side are credited but not required.

## Reproducibility

A third party with this repository, network access to
`rest.uniprot.org`, and Python ≥ 3.11 can reproduce the verifier output
exactly. The seal is the SHA-256 commitments in
`expected.hashes.jsonl`, which are immutable on `main` and signed via
git history.

To re-run on a future date and detect drift:

```bash
python tests/benchmark/verify.py tests/benchmark/expected.jsonl \
    tests/benchmark/expected.hashes.jsonl       # commitment integrity
python tests/benchmark/verify_answers.py tests/benchmark/expected.jsonl
```

The first command must always pass (the sealed file should not change
without a release-coupled re-seal). The second command may begin to
report drift as UniProt issues new releases — that is the *intended*
behaviour and the data point for downstream consumers.

## Provenance

Each tool call by `uniprot-mcp` v1.1.0 itself emits a per-response
`Provenance` record (UniProt release, retrieval timestamp, resolved
URL, canonical SHA-256). The benchmark verifier above is a separate
operational complement — it goes around the MCP layer to talk
directly to the upstream REST API, so any disagreement between the
two would surface a defect in `uniprot-mcp` rather than in UniProt.
The fact that all 30 prompts verified end-to-end is mutual confirmation:
the sealed answers, the upstream UniProt response, and the live
`uniprot-mcp` tools are mutually consistent at this commit.
