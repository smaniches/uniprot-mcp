# Benchmark v1 — `uniprot-mcp` pre-registered evaluation

> The single artifact that converts "another bio MCP" into "the reference." Pre-registered prompts, SHA-256-committed expected answers, third-party-reproducible scoring under three independent conditions. See [`AUDIT.md`](AUDIT.md) for per-prompt independence.

## Why this exists

Marketing-grade benchmarks select for the system author's preferences. This benchmark is engineered to **exclude** that selection bias by three structural choices:

1. **Pre-registration before scoring.** The prompts and the expected answers are frozen and SHA-256 committed *before* any system is run against them. Editing the expected answers post-hoc is a cryptographic break, not an unreviewable git diff.
2. **Three comparators per run.** Every prompt is answered by `uniprot-mcp` v1.0.1, by vanilla Claude with WebFetch, and by a manual primary-source pass. The comparison is a delta, not an absolute.
3. **Independent grading.** Two graders score blind, one arbitrator resolves disagreements. Grader names and affiliations are recorded in `graders.md` per run.

A reader who only trusts cryptographic guarantees can:

```bash
python tests/benchmark/verify.py tests/benchmark/expected.jsonl tests/benchmark/expected.hashes.jsonl
```

If `verify.py` exits 0, the expected-answer file has not been altered since the commit that introduced `expected.hashes.jsonl`. If it exits non-zero, the benchmark for this run is invalidated.

## Files

| File | Purpose | Commit timing |
|---|---|---|
| `prompts.jsonl` | The 30 prompts. Tier A / B / C × 10. Frozen at v1; any change requires a new tag. | At benchmark introduction (this commit). |
| `expected.hashes.jsonl` | One line per prompt: `{"prompt_id": int, "sha256": "..."}`. SHA-256 of the canonical JSON of the corresponding `expected.jsonl` line. | At sealing time, before any system is run. |
| `expected.jsonl` | Plaintext expected answers. **Local-only**; gitignored until publication. | At scoring time, in the same commit as `run-YYYY-MM-DD/`. |
| `AUDIT.md` | Per-prompt source attribution. Names the primary-source URL or DOI consulted to author each expected answer. Independence statement: `uniprot-mcp` was **not** used during answer authoring. | Updated each time `expected.jsonl` is sealed. |
| `seal.py` | Reads `expected.jsonl` → produces `expected.hashes.jsonl`. Apache-2.0. | — |
| `verify.py` | Reads both → exits 0 iff hashes match. Apache-2.0. | — |
| `run.py` | Driver: executes one prompt under one comparator, captures transcript. Skeleton in v1; full wire post-billing. | Filled at scoring time. |
| `score.py` | Driver: takes a run directory + grader names, produces aggregate score table. Skeleton in v1. | Filled at scoring time. |
| `run-YYYY-MM-DD/` | One directory per run. Per-prompt comparator transcripts, per-grader scoresheets, arbitration decisions, final aggregate. | At scoring time. |
| `graders.md` | Named graders, affiliations, blind-protocol attestation. | At scoring time, per run. |

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

The compliance-officer test: a 2030 reviewer should find a sealed-and-verified benchmark on `main`. The test fails until the follow-up sealing commit lands.
