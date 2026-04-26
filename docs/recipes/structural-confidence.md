# Recipe: Trusting an AlphaFold model

You are about to design a point mutation, dock a small molecule, or
write a result paragraph that hinges on the predicted structure of a
protein. The first question is always: **how much should I trust
this AlphaFold model?**

`uniprot_get_alphafold_confidence(accession)` answers that without
parsing the structure file.

## Example: TP53 (P04637)

```text
> What is the AlphaFold pLDDT confidence summary for P04637?
```

Tool call: `uniprot_get_alphafold_confidence("P04637")`.

Output (illustrative):

```
## AlphaFold confidence — AF-P04637-F1: Homo sapiens

**Gene:** TP53
**Residues modelled:** 1-393
**Model version:** v6
**Global pLDDT (mean):** 76.4  (confident)

**pLDDT band distribution:**
- Very high (≥ 90):  32.0%
- Confident (70-90): 40.0%
- Low (50-70):       20.0%
- Very low (< 50):    8.0%
```

## What the bands mean

| Band | pLDDT range | Trust level | Typical region |
|---|---|---|---|
| Very high | ≥ 90 | Position-level accuracy comparable to a 1.5 Å crystal structure | Folded domains with reliable templates |
| Confident | 70-90 | Backbone-level accuracy; sidechain placement reasonable | Folded domains with weaker templates, or surface |
| Low | 50-70 | Topology may be right; do not trust local geometry | Surface loops, flexible linkers |
| Very low | < 50 | Treat as **disordered**; structural reasoning is unsafe | Intrinsically disordered regions, signal peptides |

Source: [AlphaFold-DB FAQ](https://alphafold.ebi.ac.uk/faq).

## How to use the bands

A protein is rarely uniform. The four-band distribution is more
useful than the global mean:

- **TP53 (above)**: 72 % confident-or-better. The DNA-binding core
  is `very high`; the N- and C-terminal regulatory regions sit in
  the `low` and `very low` bands. → Structural reasoning about the
  core is sound; reasoning about the tails is not.

- **An intrinsically disordered protein** (e.g. some transcription
  factors, prion proteins): may show 60-90 % `very low`. → The
  AlphaFold model is essentially a guess; do not run docking on it,
  do not interpret a single-residue contact.

- **A typical enzyme** (e.g. CYP450, kinase): often 90 %+ `very high`.
  → Publication-grade. Structural reasoning, sidechain analysis,
  surface-pocket identification are all on solid ground.

## Pairing with the per-residue tools

`uniprot_get_alphafold_confidence` gives the **global picture**. To
zoom into a specific residue, pair with:

```text
> What features are at residue 175 of TP53? Is that residue in a
> high-confidence region of the AlphaFold model?
```

Tool calls: `uniprot_features_at_position("P04637", 175)` plus the
confidence summary above. Cross-reference: residue 175 sits in the
DNA-binding domain (positions 102-292), which from the band
distribution falls in the `very high` confidence range.

The combination — feature context + structural confidence — is the
**evidence packet** any structural-biology decision should rest on.

## What this tool does *not* do

- **Does not download the structure file.** Structures are large
  (~50-500 kB CIF; bigger PDB). The agent gets the URL
  (`https://alphafold.ebi.ac.uk/files/AF-<acc>-F1-model_v<N>.cif`)
  and can fetch or display it separately.
- **Does not return per-residue scores.** The metadata endpoint
  aggregates pLDDT into the four bands; per-residue scores live in
  the structure file itself. For most decisions the bands are enough;
  if you need per-residue, parse the CIF (the B-factor column carries
  pLDDT in AlphaFold-DB convention).
- **Does not run AlphaFold.** This is purely a confidence-summary
  retriever for models AlphaFold-DB has already published. Custom
  predictions live in [AlphaFold-3](https://alphafoldserver.com/) or
  [ColabFold](https://github.com/sokrypton/ColabFold).

## Provenance for structural claims

Every confidence-summary response carries the standard provenance
footer:

```
_Source: AlphaFoldDB release v6 (2024-09-01) • Retrieved 2026-04-25T12:00:00Z_
_Query: https://alphafold.ebi.ac.uk/api/prediction/P04637_
_SHA-256: …_
```

A year later, you can call `uniprot_provenance_verify` with those
fields. If AlphaFold-DB has issued a new model version (`v7`, `v8`),
the verifier returns `release_drift` — useful, because new
AlphaFold releases sometimes change structural predictions
materially (e.g. when a new template lands).

## Operational note

This tool calls a different origin from the main UniProt surface
(`alphafold.ebi.ac.uk`). The cross-origin allowlist is documented
in [the threat model](../THREAT_MODEL.md#t3b-cross-origin-allowlist-for-non-uniprot-endpoints)
and the third-party listing is in [PRIVACY.md](https://github.com/smaniches/uniprot-mcp/blob/main/PRIVACY.md).
