# Recipe: Clinical variant interpretation

A clinician received a sequencing report that includes a missense
variant `TP53 R175H`. The clinical question: **how confident should
they be that this is pathogenic, and what does the molecular evidence
look like?**

Walk-through:

## Step 1 — anchor on the canonical UniProt entry

```text
> Look up the canonical UniProt entry for human TP53.
```

Tool call: `uniprot_search` with `gene_exact:TP53 AND organism_id:9606
AND reviewed:true` → primary accession `P04637`.

Confirms you're looking at the Swiss-Prot reviewed entry, not a
TrEMBL fragment.

## Step 2 — what's at residue 175?

```text
> What features are annotated at residue 175 of P04637?
```

Tool call: `uniprot_features_at_position("P04637", 175)`.

Typical output: the residue lies inside the **DNA-binding domain
(102-292)**, is itself a known **Modified residue** (phosphoserine in
some isoforms), and has multiple **Natural variant** annotations
including R175H. The structural context alone — DNA-binding-domain,
post-translationally modified — is a strong signal that any
substitution is functionally important.

## Step 3 — is R175H specifically annotated by UniProt?

```text
> Is R175H a known UniProt-annotated TP53 variant?
```

Tool call: `uniprot_lookup_variant("P04637", "R175H")`.

Output (paraphrased):

> **R175H** — In a sporadic cancer; loss of DNA binding; one of the
> most frequent p53 mutations in human cancers. Evidence: ECO:0000269.

The `ECO:0000269` evidence code marks this as **experimental evidence
used in manual assertion** — wet-lab confirmed, not inferred by
similarity. (Distinction matters: roughly half of UniProt features
carry only sequence-similarity evidence and should be treated as
hypotheses, not facts.)

## Step 4 — what does ClinVar say at the population level?

```text
> Look up ClinVar records for this variant.
```

Tool call: `uniprot_resolve_clinvar("P04637", change="R175H", size=10)`.

Output: typically ten or more ClinVar submissions, with classifications
like *Pathogenic*, *Likely pathogenic*, and review status ranging
from *criteria provided, single submitter* up to *reviewed by expert
panel*. The molecular consequence is **missense variant**; the
trait set centres on **Li-Fraumeni syndrome** and several specific
cancers.

A clinician now has both:

- **UniProt side**: literature-anchored functional annotation.
- **ClinVar side**: population-level clinical-lab classifications.

## Step 5 — how confident is the structural prediction at this residue?

```text
> What's the AlphaFold confidence summary for P04637?
```

Tool call: `uniprot_get_alphafold_confidence("P04637")`.

Output: global mean pLDDT plus the four-band distribution. For TP53
the DNA-binding core has high pLDDT (`very high` band, > 90 — the
model is publication-grade), while the N- and C-terminal regions are
disordered (`very low` band, < 50 — structural inference unsafe).

Position 175 sits inside the well-modelled core, so any structural
reasoning ("R175 forms a specific contact with the DNA backbone") is
on solid ground. If the variant had been in a `very low` region, that
caveat would dominate the interpretation.

## Step 6 — disease associations recorded on the entry

```text
> What diseases does UniProt record for this protein?
```

Tool call: `uniprot_get_disease_associations("P04637")`.

Output: a structured list with names, acronyms, OMIM cross-references,
and free-text notes. For TP53 this typically includes Li-Fraumeni
syndrome (MIM:151623), several somatic-cancer entries, and an
adrenal-cortical carcinoma association. The OMIM IDs are clickable
in a clinical-genetics workflow.

## Step 7 — sealed provenance for the report

Every tool response above carries a footer like:

```
---
_Source: UniProt release 2026_01 (28-January-2026) • Retrieved 2026-04-25T12:00:00Z_
_Query: https://rest.uniprot.org/uniprotkb/P04637_
_SHA-256: 0040d79bb39e2f7386d55f81071e87858ec2e5c2cd9552e93c3633897f78345e_
```

Six months later, the clinician (or a regulator) can call:

```text
> Verify this provenance from a previous report.
> URL: https://rest.uniprot.org/uniprotkb/P04637
> Release: 2026_01
> SHA-256: 0040d79b…345e
```

Tool call: `uniprot_provenance_verify(url, release, response_sha256)`.

If the verdict is `verified`, the report's UniProt evidence is
unchanged. If it's `release_drift`, UniProt has moved on (typically
fine — the underlying biology is stable across recent releases). If
it's `hash_drift`, the entry has been edited within the same release
— that's an alert worth investigating.

## What this recipe demonstrates

- **Composition over passthrough**: six tool calls produce a complete
  variant-interpretation packet — UniProt evidence, ClinVar evidence,
  structural confidence, disease associations, and a
  cryptographically-verifiable audit trail.
- **Evidence-aware**: the ECO code distinguishes experimental from
  inferred annotations; the AlphaFold pLDDT distinguishes
  trustworthy from disordered regions.
- **Reproducible**: every datum carries a SHA-256 footer; six months
  later the same clinician (or a different one) can verify the
  evidence base hasn't drifted.

## What's deliberately absent

- We don't predict pathogenicity. The agent reports the evidence;
  the clinical decision is the clinician's. ClinVar is the closest
  thing to a curated answer; everything else is supporting context.
- We don't dive into population frequency. gnomAD is the right
  source for that and is out of scope for `uniprot-mcp`.
- We don't model the structural impact of R175H specifically. That
  needs MD or specialised tools (FoldX, PROVEAN, etc.). The pLDDT
  band tells you the *model* is reliable enough that downstream
  structural reasoning is meaningful; it does not tell you the
  variant's effect itself.

The agent's job is to assemble defensible evidence. The clinician's
job is to weigh it.
