# Benchmark authoring audit — `uniprot-mcp` v1

> Per-prompt audit trail. This file exists so an external reviewer can verify that the system under test (`uniprot-mcp`) was **not** consulted when authoring expected answers. Every fact is traceable to a primary-source URL or a published canonical fact.

**Authoring session:** 2026-04-24
**Author:** Santiago Maniches (ORCID 0009-0005-6480-1987, TOPOLOGICA LLC) with research assistance from Claude Opus 4.7
**Status:** Prompts frozen at v1; expected-answer authoring + sealing live in the immediate follow-up commit.
**Independence statement:** None of the prompts or expected answers were authored by invoking `uniprot-mcp`'s tool surface. All primary-source queries were executed against `https://rest.uniprot.org/...` directly via `curl` or via training-data factual recall that was then verified against the live REST API.

---

## Method

For each prompt, the expected answer is determined by **one of**:

1. **Live primary-source REST query** against `https://rest.uniprot.org/...` at authoring time. The exact URL queried is recorded in this file.
2. **Canonical published fact** from the UniProt help pages (`https://www.uniprot.org/help/...`) or from the UniProt Consortium's most recent annual NAR paper.
3. **Structurally trivial answer** that needs no external query (e.g. "the UniRef100 cluster ID for representative member P04637 is `UniRef100_P04637` by construction of the UniRef ID format").

Each entry below names the rule above (1, 2, or 3) used.

When a fact is **snapshot-dependent** (a number that can change between UniProt releases — e.g. "the count of variants on TP53 in the current release"), the prompt is rewritten to be release-stable, OR the AUDIT entry below explicitly names the caveat and the scoring rubric for graders.

---

## Per-prompt sources (Tier A — single-fact lookup)

| # | Method | Source / Reasoning |
|---|---|---|
| 1 | (1) | `GET https://rest.uniprot.org/uniprotkb/search?query=gene_exact:TP53+AND+organism_id:9606+AND+reviewed:true&fields=accession&size=1` → `P04637`. Confirmed against published literature; Swiss-Prot entry. |
| 2 | (1) | Same shape, gene `BRCA1` → `P38398`. |
| 3 | (1) | `GET https://rest.uniprot.org/uniprotkb/P38398?fields=length` → 1863. |
| 4 | (1) | `GET https://rest.uniprot.org/uniprotkb/P04637?fields=gene_primary` → `TP53`. |
| 5 | (1) | `GET https://rest.uniprot.org/uniprotkb/P0DTC2?fields=organism_name` → `Severe acute respiratory syndrome coronavirus 2`. |
| 6 | (1) | Search `gene_exact:INS AND organism_id:9606 AND reviewed:true` → `P01308`. |
| 7 | (1) | Search `gene_exact:HBB AND organism_id:9606 AND reviewed:true` → `P68871`. |
| 8 | (1) | Search `gene_exact:KRAS AND organism_id:9606 AND reviewed:true` → `P01116`. |
| 9 | (1) | Search `gene_exact:EGFR AND organism_id:9606 AND reviewed:true` → `P00533`. |
| 10 | (1) | Search `gene_exact:DMD AND organism_id:9606 AND reviewed:true` → `P11532`. |

## Per-prompt sources (Tier B — structured single-entry)

| # | Method | Source / Reasoning |
|---|---|---|
| 11 | (1) | `GET https://rest.uniprot.org/keywords/search?query=name:%22Acetylation%22&size=3&format=json` → `KW-0007`. Verified at authoring time. |
| 12 | (1) | Same shape, name=Glycoprotein → `KW-0325`. |
| 13 | (1) | `GET https://rest.uniprot.org/locations/search?query=name:%22Cell+membrane%22&size=3` → `SL-0039`. **Note**: not `SL-0086` (which is `Cytoplasm`). Documentation in earlier commits erroneously said `SL-0086 = Cell membrane`; corrected in this same commit's authorship pass. |
| 14 | (1) | Same shape, name=Nucleus → `SL-0191`. |
| 15 | (1) | Same shape, name=Mitochondrion → `SL-0173`. |
| 16 | (1) | `GET https://rest.uniprot.org/uniprotkb/P04637.fasta` → first record's first line of sequence is `MEEPQSDPSV...`. The first 10 residues are `MEEPQSDPSV`. |
| 17 | (3) | UniRef ID format: `UniRef100_<accession>` for the cluster representative-member identity tier. Trivial by construction → `UniRef100_P04637`. |
| 18 | (3) | Same construction → `UniRef50_P04637`. |
| 19 | (1) | Search `gene_exact:TP63 AND organism_id:9606 AND reviewed:true` → `Q9H3D4`. |
| 20 | (1) | Search `gene_exact:TP73 AND organism_id:9606 AND reviewed:true` → `O15350`. |

## Per-prompt sources (Tier C — structured checklists)

| # | Method | Source / Reasoning |
|---|---|---|
| 21 | (1) × 5 | Five gene-symbol → accession queries; concatenated into a JSON object. BRCA2 = `P51587`. |
| 22 | (1) × 5 | Five name → SL- queries; concatenated. **Cytoplasm = SL-0086** (not SL-0039). **Cell membrane = SL-0039**. **Nucleus = SL-0191**. **Mitochondrion = SL-0173**. **Endoplasmic reticulum = SL-0095**. |
| 23 | (1) × 5 | Five name → KW- queries. **Acetylation = KW-0007**, **Phosphoprotein = KW-0597**, **Glycoprotein = KW-0325**, **Methylation = KW-0488**, **Disulfide bond = KW-1015**. |
| 24 | (3) × 3 | UniRef IDs by construction: `UniRef50_P04637`, `UniRef90_P04637`, `UniRef100_P04637`. |
| 25 | (1) × 3 | KRAS = P01116, NRAS = (verify), HRAS = (verify). Recorded in expected.jsonl after primary-source REST verification at sealing time. |
| 26 | (1) × 3 | TP53 = P04637, TP63 = Q9H3D4, TP73 = O15350. (Already verified in prompts 1, 19, 20.) |
| 27 | (1) × 3 | CYP3A4 = (verify), CYP2D6 = (verify), CYP1A2 = (verify). Recorded at sealing time. |
| 28 | (1) | `GET https://rest.uniprot.org/uniprotkb/P04637?fields=ft_*` → enumerate the unique `type` values of features. Snapshot-dependent (UniProt may add new feature types). Scoring caveat: graders credit a response that contains the canonical types known at sealing time; missing-newer-types is not penalised. |
| 29 | (1) | `GET https://rest.uniprot.org/uniprotkb/P04637?fields=xref_*` → enumerate distinct `database` field values. Snapshot-dependent on the same caveat; databases UniProt added cross-references to *after* sealing time are credit-but-not-required. |
| 30 | (1) × 3 | Hox-A1, Hox-A9, Hox-A13 → searches at authoring time. Recorded at sealing time. |

---

## Snapshot-dependence policy

Three prompts (28, 29, plus any future Tier-C set-inclusion prompt that depends on UniProt's evolving feature type or cross-reference inventory) are scored **set-inclusion**, not equality. Graders verify that every item in the canonical sealed set appears in the response; items present in the response that are **not** in the sealed set are accepted only if they are themselves verifiable against the UniProt release current at scoring time.

This rule exists because UniProt is a living database. A prompt that asks "list every X in P04637" will, six months later, return a slightly larger set as the curators annotate more features. Penalising a comparator for being more complete than the seal would invert the benchmark's intent.

---

## Sealing checklist (next commit)

- [ ] `expected.jsonl` written with one `{"prompt_id": int, "answer": <typed>, "rationale": str}` per prompt. The `answer` field is structured (string for Tier A, JSON for Tier B/C) so it canonicalises identically across machines.
- [ ] `python tests/benchmark/seal.py` produces `expected.hashes.jsonl` with 30 commitments.
- [ ] `python tests/benchmark/verify.py expected.jsonl expected.hashes.jsonl` exits 0.
- [ ] `expected.jsonl` is in `.gitignore` (added in this commit).
- [ ] `expected.hashes.jsonl` and this `AUDIT.md` are committed to `main`.
- [ ] Backup of `expected.jsonl` to a separate filesystem (the user's responsibility — file loss = benchmark unrunnable without re-authoring).

## Independence statement (formal)

I, Santiago Maniches, attest that during the authoring of `prompts.jsonl` v1 and the sealing of `expected.jsonl` v1, the system under test (`uniprot-mcp` versions 0.1.0 and 1.0.x) was **not** invoked. Every primary-source query in this audit table was executed against `https://rest.uniprot.org/...` directly. Any subsequent revision of this benchmark (v2, v3, …) carries an updated independence statement.
