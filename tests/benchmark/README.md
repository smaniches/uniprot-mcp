# Benchmark v1 — `uniprot-mcp` pre-registered evaluation

> Pre-registered prompts, SHA-256-committed expected answers, and a protocol for scoring three comparators. See [`AUDIT.md`](AUDIT.md) for per-prompt independence.

## Status

**The answer key is sealed and verified. The benchmark has not been run.**

| Step | State |
|---|---|
| Prompts frozen | Done, 2026-04-24. |
| Expected answers sealed (`expected.hashes.jsonl`) | Done, 2026-04-25. |
| Answer key checked against live UniProt | Done: 30 of 30 on 2026-04-25 and again on 2026-04-26 ([record](run-2026-04-26-v1.1.0/README.md)). The verifiers query the UniProt REST API directly and call no `uniprot-mcp` tool. |
| Any comparator run (`uniprot-mcp`, vanilla Claude, manual) | **Not done.** `run.py` is a scaffold that exits with status 1. |
| Grading and aggregate scores | **Not done.** `score.py` is a scaffold; there is no `graders.md` and no scored run directory. |

So there is no result for this server or for any baseline: no accuracy,
no tool-call count, no comparison. The "30 / 30" that appears in this
repository counts expected answers confirmed against UniProt, nothing
else. The sections below describe the design that a run is meant to
follow.

## Why this exists

Marketing-grade benchmarks select for the system author's preferences. This benchmark is engineered to **exclude** that selection bias by three structural choices:

1. **Pre-registration before scoring.** The prompts and the expected answers are frozen and SHA-256 committed *before* any system is run against them. Editing the expected answers post-hoc is a cryptographic break, not an unreviewable git diff.
2. **Three comparators per run.** Every prompt is to be answered by `uniprot-mcp`, by vanilla Claude with WebFetch, and by a manual primary-source pass. The comparison is a delta, not an absolute.
3. **Independent grading.** Two graders are to score blind, with one arbitrator resolving disagreements. Grader names and affiliations are to be recorded in `graders.md` per run.

### Two reproducibility paths

**Third-party (fresh checkout — no seal file required).** Re-derive every Tier A / Tier B answer live from UniProt and print it:

```bash
python tests/benchmark/verify_against_hashes.py tests/benchmark/expected.hashes.jsonl
```

This path needs only the committed repository, network access to `rest.uniprot.org`, and Python ≥ 3.11. It does **not** need `expected.jsonl` (gitignored — see below). It confirms that every answer is independently reproducible from the primary source today. It does **not** recompute the committed SHA-256 digests: those are sealed over `{prompt_id, answer, rationale}` (see `seal.py`), and the `rationale` is deliberately withheld as part of the sealed pre-registration, so the digest is not derivable from the live answer alone. The full cryptographic check is the maintainer path below. It is an informational reproducibility tool (exit 0), not a pass/fail gate.

> A *true* third-party cryptographic path would require sealing `{prompt_id, answer}` only, with the rationale held as separate metadata — so a third party could recompute the digest from the live answer alone. That is an owner methodology decision: it requires the local `expected.jsonl` and a fresh commitment, and is **not** implemented here (re-sealing the existing benchmark post-hoc would break the pre-registration covenant). See `AUDIT.md`.

**Maintainer (local plaintext seal in hand).** Once `expected.jsonl` exists in your working tree:

```bash
python tests/benchmark/verify.py tests/benchmark/expected.jsonl tests/benchmark/expected.hashes.jsonl
python tests/benchmark/verify_answers.py tests/benchmark/expected.jsonl
```

`verify.py` exit 0 confirms the local plaintext was not edited since the commit that sealed it. `verify_answers.py` confirms the live answer matches the seal (exact match for Tier A/B, set-inclusion for Tier C 28/29). If either exits non-zero, the benchmark for that run is invalidated.

## Files

| File | Purpose | Commit timing |
|---|---|---|
| `prompts.jsonl` | The 30 prompts. Tier A / B / C × 10. Frozen at v1; any change requires a new tag. | At benchmark introduction (this commit). |
| `expected.hashes.jsonl` | One line per prompt: `{"prompt_id": int, "sha256": "..."}`. SHA-256 of the canonical JSON of the corresponding `expected.jsonl` line. | At sealing time, before any system is run. |
| `expected.jsonl` | Plaintext expected answers. **Local-only**; gitignored until publication. | At scoring time, in the same commit as `run-YYYY-MM-DD/`. |
| `AUDIT.md` | Per-prompt source attribution. Names the primary-source URL or DOI consulted to author each expected answer. Independence statement: `uniprot-mcp` was **not** used during answer authoring. | Updated each time `expected.jsonl` is sealed. |
| `seal.py` | Reads `expected.jsonl` → produces `expected.hashes.jsonl`. Apache-2.0. | — |
| `verify.py` | Reads both → exits 0 iff hashes match. Apache-2.0. | — |
| `run.py` | Intended driver: execute one prompt under one comparator and capture the transcript. Today a scaffold: it parses the command line, prints a `[scaffold]` notice and exits with status 1. It runs nothing. | Filled at scoring time. |
| `score.py` | Intended driver: take a run directory and grader names and produce the aggregate score table. Today a scaffold with the same behaviour. | Filled at scoring time. |
| `run-YYYY-MM-DD/` | One directory per run. Per-prompt comparator transcripts, per-grader scoresheets, arbitration decisions, final aggregate. None exists yet. | At scoring time. |
| `run-2026-04-26-v1.1.0/` | Record of the answer-key verification of 2026-04-26. Not a benchmark run, despite the directory name. | 2026-04-26; corrected 2026-11-11. |
| `run-2026-04-25-roundtrip/` | Withdrawn provenance transcript; see the note inside. | Withdrawn 2026-10-25. |
| `graders.md` | Named graders, affiliations, blind-protocol attestation. Does not exist yet. | At scoring time, per run. |

## Tier semantics

- **Tier A** (prompts 1–10): single-fact lookup. Expected answers are short — a UniProt accession, a controlled-vocabulary ID, an integer. Scoring is exact-match-or-equivalent.
- **Tier B** (prompts 11–20): small analysis spanning 2-3 fields of one entry, or a controlled comparison across a small fixed set. Expected answers are a short structured object.
- **Tier C** (prompts 21–30): synthesis across multiple endpoints or a structured checklist that a wrong answer cannot accidentally satisfy. Scoring is **set-inclusion** against a canonical checklist, not free-text grading.

The Tier C structured-checklist choice is deliberate: free-text Tier C grading degenerates into "the grader has an opinion." Set-inclusion ("does the response contain these specific UniProt accessions / keyword IDs / counts?") is unambiguous, falsifiable, and reviewable.

## Comparator definitions

| Comparator | Definition |
|---|---|
| `uniprot-mcp` | Anthropic Claude 4.X, configured with `uniprot-mcp` as its only data tool. Must answer using the MCP's tool surface; WebFetch is disabled. |
| `vanilla-claude` | Anthropic Claude 4.X, configured with WebFetch as its only data tool. No MCP servers. Must consult primary-source UniProt URLs by hand. |
| `manual` | Human author looks up each answer using `curl` against `https://rest.uniprot.org` directly. Provides the ground-truth baseline that the other two comparators are scored against (when expected answers are snapshot-dependent). |

Each comparator's transcripts are stored as JSONL with one entry per prompt: `{"prompt_id": int, "comparator": str, "transcript": [...], "final_answer": str, "tool_calls": int, "wall_time_ms": int}`.

## Scoring

Per run:

1. Each grader receives a blinded scoresheet — the prompt, the three comparator answers (labelled `A`/`B`/`C` with the assignment seed in a sealed envelope), the expected answer.
2. Each grader scores 0 / 0.5 / 1 per prompt per comparator, plus a free-text rationale.
3. Disagreements >0.5 between graders go to the arbitrator; the arbitrator's score is final.
4. Aggregate: per-tier mean and 95 % bootstrap CI per comparator; tool-call count per comparator; wall-time per comparator.

Aggregate output is published as `run-YYYY-MM-DD/aggregate.md` plus the underlying CSVs.

## Running the benchmark

The commands below are the intended interface. They do not work yet:
`run.py` and `score.py` stop with a `[scaffold]` message and exit status 1.

```bash
# 1. Install + configure
pip install -e ".[test,dev]"
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Run each comparator
python tests/benchmark/run.py --comparator uniprot-mcp     --out run-$(date -u +%Y-%m-%d)/
python tests/benchmark/run.py --comparator vanilla-claude  --out run-$(date -u +%Y-%m-%d)/
# manual: see graders.md for the human protocol.

# 3. Score
python tests/benchmark/score.py --run-dir run-$(date -u +%Y-%m-%d)/ \
    --graders <name1>,<name2> --arbitrator <name3>

# 4. Commit plaintext expected + scoring output (single commit)
git add tests/benchmark/expected.jsonl tests/benchmark/run-*
git commit -m "benchmark run <date>: publish expected answers + scores"
```

`run.py` and `score.py` are scaffolded (importable, argparse-wired, stubbed bodies) at v1 introduction; full bodies land alongside the first run.

## Authorship statement

Prompts authored by Santiago Maniches (ORCID 0009-0005-6480-1987, TOPOLOGICA LLC). Expected answers authored against primary-source UniProt REST endpoints and the public web UniProt help pages — `uniprot-mcp` was **not** used during authoring. A future v2 prompt set authored by an independent biomedical domain expert is a roadmap item; v1 carries the author-system correlation risk that v2 will eliminate.

## State (updated on every change)

- **2026-04-24:** v1 prompts frozen; scaffold and scripts in place. Expected-answer authoring + hash sealing land in the immediate follow-up commit. The `expected.hashes.jsonl` file does not yet exist on `main`; the benchmark is **not yet sealed**.
- **2026-04-25:** expected answers sealed; `expected.hashes.jsonl` committed; answer key verified 30 / 30 against live UniProt (see `AUDIT.md`).
- **2026-04-26:** answer key verified 30 / 30 again at v1.1.0 (`run-2026-04-26-v1.1.0/`).
- **2026-11-11:** status stated explicitly at the top of this file. The answer key is sealed and verified; no comparator has been run and nothing has been scored. Earlier wording in this repository that presented the 2026-04-26 verification as a benchmark result was corrected.

The compliance-officer test: a 2030 reviewer should find a sealed-and-verified answer key on `main`, which is the case since 2026-04-25, and should be able to tell at a glance that the benchmark run itself is still open.
