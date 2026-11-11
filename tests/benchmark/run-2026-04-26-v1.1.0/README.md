# Benchmark answer-key verification — 2026-04-26 (v1.1.0)

> **Correction dated 2026-11-11.** This record was first titled
> "Benchmark run" and closed by saying that the result confirmed the live
> `uniprot-mcp` tools. It does not. The two commands recorded here check
> the sealed answer key: `verify.py` confirms that the local plaintext
> matches the committed SHA-256 values, and `verify_answers.py` re-derives
> each answer from the UniProt REST API. Neither imports or calls
> `uniprot-mcp`, and no model, server or baseline answered the prompts.
> The 30 / 30 below is the number of expected answers confirmed against
> UniProt on that date. It is not a score for any system. The benchmark
> itself has not been run: `run.py` and `score.py` are scaffolds.
>
> Only the title and the closing paragraph were corrected. The commands,
> their output and `verify-output.txt` are unchanged, and the original
> wording remains readable at
> [the v1.3.17 revision](https://github.com/smaniches/uniprot-mcp/blob/ba34026d8c831a840ddee23c4c8c768d1d03d3e6/tests/benchmark/run-2026-04-26-v1.1.0/README.md).

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

## Scope of this record

The verifier talks directly to the upstream REST API and goes around the
MCP layer. It therefore establishes one thing: on 2026-04-26 the sealed
answers agreed with UniProt.

_Withdrawn on 2026-11-11:_ the earlier closing statement that the sealed
answers, the upstream UniProt response and the live `uniprot-mcp` tools
were shown to be mutually consistent. No `uniprot-mcp` tool was called in
this verification, so it carries no evidence about them.
