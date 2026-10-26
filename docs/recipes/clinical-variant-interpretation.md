# Recipe: Clinical variant interpretation

A research workflow starts with a reported `TP53 R175H` substitution. The task is to **retrieve and distinguish upstream molecular and clinical annotations**, not to assign pathogenicity or make a clinical decision.

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

Output (UniProt release 2026_03, captured 2026-10-15): the residue lies
inside the annotated **DNA-binding** region (102-292) and a short helix
(174-176), within several protein-interaction regions, and carries
seven **Natural variant** annotations (R→C, G, H, L, P, Q, S), including
R175H. No **Modified residue** feature is annotated at 175. Location in
an annotated functional region is context, not by itself evidence that a
particular substitution is damaging.

## Step 3 — is R175H specifically annotated by UniProt?

```text
> Is R175H a known UniProt-annotated TP53 variant?
```

Tool call: `uniprot_lookup_variant("P04637", "R175H")`.

Output (verbatim, release 2026_03):

> **R175H** — in LFS; germline mutation and in sporadic cancers; somatic
> mutation; does not induce SNAI1 degradation; reduces interaction with
> ZNF385A; dbSNP:rs28934578. Evidence: ECO:0000269.

`ECO:0000269` is **experimental evidence used in manual assertion**: a
curator attributed the statement to published experimental work (here,
seven PubMed references on the feature). It is distinct from codes for
evidence inferred by sequence similarity, but the code alone does not say
which experiment supports which clause of the annotation.

## Step 4 — what human variant classifications does ClinVar report?

```text
> Look up ClinVar records for this variant.
```

Tool call: `uniprot_resolve_clinvar("P04637", change="R175H", size=5)`.

Output (captured 2026-10-15): the gene-plus-variant-name search returned
**one ClinVar variation record**, `VCV000012374`,
NM_000546.6(TP53):c.524G>A (p.Arg175His), with germline classification
*Pathogenic* and review status *reviewed by expert panel*; molecular
consequence **missense variant**. A variation record aggregates the
individual submissions; the tool reports records, not submission counts.
A gene/protein-change text search produces candidate records, not a verified
match to a caller's genomic allele, transcript, or protein isoform. Compare
identifiers and the submitted HGVS expression before interpreting a result.
The classification shown is ClinVar's germline classification, not somatic
(tumor) actionability or an independent conclusion by this MCP.

A clinician now has both:

- **UniProt side**: literature-anchored functional annotation.
- **ClinVar side**: source-reported human germline variant classifications.

## Step 5 — how confident is the structural prediction at this residue?

```text
> What's the AlphaFold confidence summary for P04637?
```

Tool call: `uniprot_get_alphafold_confidence("P04637")`.

Output (AlphaFold DB, captured 2026-10-15): model `AF-P04637-F1`, model
version v6 (created 2025-08-01), global mean pLDDT 75.1, with 52.7% of
residues in the `very high` band (≥ 90), 7.1% `confident`, 10.4% `low`
and 29.8% `very low` (< 50).

This is a **model-level** summary. It does not report the confidence at
residue 175, so it cannot by itself establish that structural reasoning
at that residue is reliable; residue-level pLDDT is in the model file
(e.g. the CIF B-factor column), which this tool does not fetch. pLDDT is
model confidence, not experimental validation.

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

Each tool response carries source-specific provenance. A recorded **UniProt** response has a footer like:

```
---
_Source: UniProt release 2026_03 (02-September-2026) • Retrieved 2026-10-15T10:32:43Z_
_Query: https://rest.uniprot.org/uniprotkb/P04637_
_SHA-256: 112540dcb662c3ce2feba05272ce0e946ce76089a5bcf8346eb55141892f7fcf_
_Accept: application/json_
```

The footer names the provider that served each response: ClinVar
responses show `NCBI ClinVar (eutils)` and AlphaFold DB responses show
`AlphaFoldDB model v6 (created …)`. This footer is from the 2026-10-15
capture in
[`examples/captures/2026-10-15_tp53_r175h/`](https://github.com/smaniches/uniprot-mcp/tree/main/examples/captures/2026-10-15_tp53_r175h),
which stores the upstream response bytes so the digest can be recomputed.

Later, the clinician (or a reviewer) can call:

```text
> Verify this provenance from a previous report.
> URL: https://rest.uniprot.org/uniprotkb/P04637
> Release: 2026_03
> SHA-256: 112540dc…7fcf
```

Tool call: `uniprot_provenance_verify(url, release, response_sha256)`.

If the verdict is `verified`, the fetched UniProt response matches the
recorded release and digest; this does not validate the biological
interpretation. A drift verdict means the recorded UniProt response and
the current retrieval differ and require examination. This verifier
supports UniProt REST origins, not the separate ClinVar or AlphaFold DB
responses, which must be checked against their own recorded source bytes.

## What this recipe demonstrates

- **Composition over passthrough**: six tool calls assemble a bounded
  evidence packet — UniProt annotations, a ClinVar search result,
  model-level structural confidence, disease associations, and a
  source-integrity audit trail. This is not a complete clinical
  interpretation or confirmation of allele identity.
- **Evidence-aware**: the ECO code distinguishes experimental from
  inferred annotations; the AlphaFold summary reports model-level
  confidence and states that it is not per-residue confidence.
- **Reproducible source binding**: recorded responses carry source URLs
  and hashes. UniProt REST responses can be compared with a later live
  retrieval; other providers require their own checks. Source hashes
  do not independently validate parsed scientific statements.

## What's deliberately absent

- We don't predict pathogenicity. The agent reports the evidence;
  the clinical decision is the clinician's. ClinVar reports submitted
  classifications and review statuses, not an interpretation generated
  or independently validated by this MCP.
- We don't dive into population frequency. gnomAD is the right
  source for that and is out of scope for `uniprot-mcp`.
- We don't model the structural impact of R175H specifically. That
  needs MD or specialised tools (FoldX, PROVEAN, etc.). The global
  pLDDT summary describes the model as a whole; it neither establishes
  confidence at a specific residue nor the variant's effect.

The agent's job is to assemble defensible evidence. The clinician's
job is to weigh it.
