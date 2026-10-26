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

Output (captured 2026-10-15 from AlphaFold DB; excerpt, verbatim):

```
## AlphaFold confidence — AF-P04637-F1: Homo sapiens

**Gene:** TP53
**Residues modelled:** 1-393
**Model version:** v6
**Global pLDDT (mean):** 75.1  (confident)

**pLDDT band distribution:**
- Very high (≥ 90):  52.7%
- Confident (70-90):   7.1%
- Low (50-70):  10.4%
- Very low (< 50):  29.8%
```

The full response, footer and source bytes are in
[`examples/captures/2026-10-15_tp53_r175h/`](https://github.com/smaniches/uniprot-mcp/tree/main/examples/captures/2026-10-15_tp53_r175h).

## What the bands mean

| Band | pLDDT range | Trust level | Typical region |
|---|---|---|---|
| Very high | ≥ 90 | Often reliable local geometry; not a guarantee of experimental accuracy | Well-modelled regions |
| Confident | 70-90 | Generally good backbone confidence; side-chain uncertainty remains | Structured regions |
| Low | 50-70 | Local model uncertainty; interpret cautiously | Loops and less certain regions |
| Very low | < 50 | Coordinates should not be interpreted; may indicate disorder or missing structural context | Flexible or poorly modelled regions |

Source: [AlphaFold-DB FAQ](https://alphafold.ebi.ac.uk/faq).

## How to use the bands

A protein is rarely uniform. The four-band distribution is more
useful than the global mean:

- **TP53 (above)**: 59.8 % confident-or-better and 29.8 % `very low`.
  The summary does not say *which* residues fall in each band; to judge
  a specific region (e.g. the DNA-binding domain versus the termini),
  read per-residue pLDDT from the model file before relying on it.

- **A protein with a large low-confidence fraction** may contain
  disordered or context-dependent regions. Do not use coordinates of
  those regions for residue contacts or docking without independent
  validation. The global fraction alone does not identify which
  residues are affected.

- **A high-confidence model** can still have uncertain loops,
  interfaces, ligands, or domain orientations. A high global fraction
  alone does not establish publication readiness or justify a binding
  site, docking, or mutational-effect claim.

## Pairing with the per-residue tools

`uniprot_get_alphafold_confidence` gives the **global picture**. To
zoom into a specific residue, pair with:

```text
> What features are at residue 175 of TP53? Is that residue in a
> high-confidence region of the AlphaFold model?
```

Tool calls: `uniprot_features_at_position("P04637", 175)` plus the
confidence summary above. The annotation places residue 175 in the
DNA-binding region, but **the global pLDDT distribution cannot tell
which confidence band residue 175 occupies**. Inspect the model's
per-residue pLDDT before drawing any residue-specific structural conclusion.

These sources provide annotation context and a model-wide confidence
summary. Residue-specific or mechanistic claims require additional
position-level evidence and, where appropriate, experimental validation.

## What this tool does *not* do

- **Does not download the structure file.** Structures are large
  (~50-500 kB CIF; bigger PDB). The agent gets the URL
  (`https://alphafold.ebi.ac.uk/files/AF-<acc>-F1-model_v<N>.cif`)
  and can fetch or display it separately.
- **Does not return per-residue scores.** The metadata endpoint
  aggregates pLDDT into the four bands; per-residue scores live in
  the structure file itself. For most decisions the bands are enough;
  if you need per-residue, parse the CIF (the B-factor column carries
  pLDDT in AlphaFold-DB convention). For any residue-specific or
  docking inference, do not substitute the global mean for these values.
- **Does not run AlphaFold.** This is purely a confidence-summary
  retriever for models AlphaFold-DB has already published. Custom
  predictions live in [AlphaFold-3](https://alphafoldserver.com/) or
  [ColabFold](https://github.com/sokrypton/ColabFold).

## Provenance for structural claims

The returned confidence summary records the AlphaFold DB provider,
retrieval URL, timestamp, and response digest; where available, it also
records the prediction model version. The [October 15, 2026
capture](https://github.com/smaniches/uniprot-mcp/tree/main/examples/captures/2026-10-15_tp53_r175h)
contains dated source bytes for independent inspection.

`uniprot_provenance_verify` currently verifies **UniProt REST URLs only**.
It does not re-fetch or validate the AlphaFold DB prediction endpoint.
To check a later AlphaFold result, retrieve the same accession from
AlphaFold DB, compare the response, model identity, and version with the
recorded source, and separately evaluate the scientific interpretation.
A digest match proves source-byte consistency, not structure accuracy.

## Operational note

This tool calls a different origin from the main UniProt surface
(`alphafold.ebi.ac.uk`). The cross-origin allowlist is documented
in [the threat model](../THREAT_MODEL.md#t3b-cross-origin-allowlist-for-non-uniprot-endpoints)
and the third-party listing is in [PRIVACY.md](https://github.com/smaniches/uniprot-mcp/blob/main/PRIVACY.md).
