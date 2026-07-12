"""Evidence & Conclusion Ontology (ECO) grading for UniProt annotations.

Pure data and pure functions — no I/O, mypy-strict clean.

UniProt attaches one or more ECO codes to every annotated feature and
comment. Each code encodes two orthogonal facts:

* the *kind* of evidence — an experimental result, sequence similarity,
  an author statement, a curator's inference, a pipeline match, …; and
* the *assertion method* — a human curator reviewed it (an ECO term
  "used in manual assertion") versus a pipeline emitted it with no human
  review (an ECO term "used in automatic assertion").

For an agent deciding whether to *trust* an annotation, the single most
useful collapse of that space is a three-rung ladder::

    experimental  >  manually curated  >  automatically inferred

This module maps every ECO code UniProt emits onto that ladder
(:data:`ECO_EVIDENCE_CLASS`), attaches a confidence weight to each rung
(:data:`CLASS_WEIGHTS`), and turns an ECO code-count histogram into a
single ``0-100`` evidence-confidence score plus a four-band label
(:func:`score_evidence`). The banding deliberately mirrors the pLDDT
four-band idiom used by the AlphaFold-confidence tool so the two
"how much should I trust this?" surfaces read the same way.

The class boundary is UniProt's own: only :data:`ECO_EXPERIMENTAL`
(``ECO:0000269``) means "a wet-lab experiment was performed and a curator
recorded it". Everything else in the "manual assertion" family is a
curator-reviewed *inference*; everything in the "automatic assertion"
family is an *un-reviewed* pipeline call. Codes we do not recognise are
reported as :data:`ECO_OTHER` and excluded from the weighted score
rather than silently folded into a rung.

ECO term labels were taken verbatim from the Evidence & Conclusion
Ontology (https://www.evidenceontology.org / EBI OLS ``eco``). The
weights are a deliberate, documented choice — see :data:`CLASS_WEIGHTS`.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, TypedDict

__all__ = [
    "CLASS_WEIGHTS",
    "ECO_AUTOMATIC",
    "ECO_CLASS_ORDER",
    "ECO_EVIDENCE_CLASS",
    "ECO_EXPERIMENTAL",
    "ECO_HUMAN_LABELS",
    "ECO_MANUAL",
    "ECO_OTHER",
    "ClassBreakdown",
    "EvidenceConfidence",
    "classify_eco",
    "confidence_markdown_lines",
    "evidence_confidence_band",
    "score_evidence",
]

# --------------------------------------------------------------------- #
# Evidence classes                                                      #
# --------------------------------------------------------------------- #

#: A wet-lab experiment was performed and recorded by a curator. The only
#: rung that means "directly observed" rather than "inferred".
ECO_EXPERIMENTAL: Final = "experimental"
#: A human curator reviewed the annotation, but the underlying evidence is
#: an inference (sequence similarity, an author statement, a curator's own
#: reasoning, a high-throughput dataset).
ECO_MANUAL: Final = "manual"
#: A pipeline emitted the annotation with no human review.
ECO_AUTOMATIC: Final = "automatic"
#: An ECO code this module does not classify. Reported for transparency
#: and excluded from the weighted score.
ECO_OTHER: Final = "other"

#: Rungs in descending confidence order. Drives every deterministic
#: iteration (breakdown tables, markdown rows) so output ordering is
#: stable regardless of ``dict`` insertion order.
ECO_CLASS_ORDER: Final[tuple[str, ...]] = (
    ECO_EXPERIMENTAL,
    ECO_MANUAL,
    ECO_AUTOMATIC,
    ECO_OTHER,
)

# --------------------------------------------------------------------- #
# ECO code knowledge                                                    #
#                                                                       #
# Labels are verbatim Evidence & Conclusion Ontology term names. This is #
# the single source of truth for the human labels the evidence-summary  #
# tool renders — the server imports them from here.                     #
# --------------------------------------------------------------------- #

#: Human-readable labels for the ECO codes UniProt emits in practice. The
#: full ontology has thousands of terms; this curated subset covers the
#: overwhelming majority of UniProtKB usage.
ECO_HUMAN_LABELS: Final[dict[str, str]] = {
    # -- experimental --------------------------------------------------
    "ECO:0000269": "experimental evidence used in manual assertion",
    # -- manual assertion (curator-reviewed inference) -----------------
    "ECO:0000250": "sequence similarity evidence used in manual assertion",
    "ECO:0000244": "combinatorial evidence used in manual assertion",
    "ECO:0000255": "match to InterPro member signature evidence used in manual assertion",
    "ECO:0000303": "non-traceable author statement used in manual assertion",
    "ECO:0000304": "traceable author statement used in manual assertion",
    "ECO:0000305": "curator inference used in manual assertion",
    "ECO:0000312": "imported information used in manual assertion",
    "ECO:0007744": "combinatorial computational and experimental evidence used in manual assertion",
    # -- automatic assertion (un-reviewed pipeline call) ---------------
    "ECO:0000256": "match to sequence model evidence used in automatic assertion",
    "ECO:0000259": "match to InterPro member signature evidence used in automatic assertion",
    "ECO:0000213": "combinatorial evidence used in automatic assertion",
    "ECO:0000313": "imported information used in automatic assertion",
    "ECO:0007829": "combinatorial computational and experimental evidence used in automatic assertion",
    "ECO:0000501": "evidence used in automatic assertion",
}

#: Maps each known ECO code onto its evidence class. Kept explicit rather
#: than parsed from the label text: the "manual/automatic assertion"
#: suffix is a stable ECO convention, but an explicit table is auditable,
#: cannot silently mis-bucket a re-worded label, and documents exactly
#: which codes the score covers.
ECO_EVIDENCE_CLASS: Final[dict[str, str]] = {
    "ECO:0000269": ECO_EXPERIMENTAL,
    "ECO:0000250": ECO_MANUAL,
    "ECO:0000244": ECO_MANUAL,
    "ECO:0000255": ECO_MANUAL,
    "ECO:0000303": ECO_MANUAL,
    "ECO:0000304": ECO_MANUAL,
    "ECO:0000305": ECO_MANUAL,
    "ECO:0000312": ECO_MANUAL,
    # Combines a computational and an experimental component but denotes
    # high-throughput datasets (e.g. proteome-wide PTM/MS studies), so it
    # is graded as curator-reviewed rather than pooled with low-throughput
    # ECO:0000269 wet-lab evidence. A conservative, deliberate choice.
    "ECO:0007744": ECO_MANUAL,
    "ECO:0000256": ECO_AUTOMATIC,
    "ECO:0000259": ECO_AUTOMATIC,
    "ECO:0000213": ECO_AUTOMATIC,
    "ECO:0000313": ECO_AUTOMATIC,
    # Automatic counterpart of ECO:0007744; one of the most common codes on
    # TrEMBL/PDB/PeptideAtlas entries, so omitting it would silently drop a
    # large share of real annotations into the unscored ``other`` bucket.
    "ECO:0007829": ECO_AUTOMATIC,
    "ECO:0000501": ECO_AUTOMATIC,
}

#: Confidence weight per rung, used to collapse a class histogram into a
#: single score. The ratios encode the intended ranking, not a calibrated
#: probability: direct observation (1.0) is worth twice a curator-reviewed
#: inference (0.5), which is worth five times an un-reviewed pipeline call
#: (0.1). :data:`ECO_OTHER` carries no weight and never enters the score.
CLASS_WEIGHTS: Final[dict[str, float]] = {
    ECO_EXPERIMENTAL: 1.0,
    ECO_MANUAL: 0.5,
    ECO_AUTOMATIC: 0.1,
}


class ClassBreakdown(TypedDict):
    """Per-class tally: absolute occurrences and the fraction they are of
    *all* evidence occurrences (including unclassified ``other``)."""

    occurrences: int
    fraction: float


class EvidenceConfidence(TypedDict):
    """Result of :func:`score_evidence`.

    ``score`` is ``None`` exactly when no *classified* evidence exists
    (an entry with only unrecognised codes, or none at all); ``band`` is
    then ``"n/a"``.
    """

    score: float | None
    band: str
    classified_occurrences: int
    total_occurrences: int
    breakdown: dict[str, ClassBreakdown]
    weights: dict[str, float]


def classify_eco(code: str) -> str:
    """Return the evidence class for an ECO code.

    Unrecognised codes map to :data:`ECO_OTHER` so the caller can surface
    them without letting them distort the weighted score.
    """
    return ECO_EVIDENCE_CLASS.get(code, ECO_OTHER)


def evidence_confidence_band(score: float) -> str:
    """Map a ``0-100`` evidence-confidence score to a semantic band.

    Boundaries (mirroring the pLDDT four-band idiom): ``>= 70`` high,
    ``>= 40`` moderate, ``>= 15`` low, otherwise very low. A pure
    experimental entry scores 100 (high); pure sequence-similarity 50
    (moderate); pure automatic 10 (very low).
    """
    if score >= 70:
        return "high"
    if score >= 40:
        return "moderate"
    if score >= 15:
        return "low"
    return "very low"


def score_evidence(counts: Mapping[str, int]) -> EvidenceConfidence:
    """Collapse an ECO code-count histogram into a confidence verdict.

    ``counts`` maps ECO code -> number of annotations citing it (the
    histogram the evidence-summary tool already builds). Every occurrence
    is bucketed by :func:`classify_eco`; the score is the weighted mean of
    the class weights over the *classified* occurrences, scaled to
    ``0-100``. Unclassified (``other``) occurrences are reported in the
    breakdown but excluded from the score's denominator.
    """
    by_class: dict[str, int] = dict.fromkeys(ECO_CLASS_ORDER, 0)
    for code, n in counts.items():
        by_class[classify_eco(code)] += n

    total = sum(by_class.values())
    classified = total - by_class[ECO_OTHER]

    score: float | None
    if classified > 0:
        weighted = sum(CLASS_WEIGHTS[cls] * by_class[cls] for cls in CLASS_WEIGHTS)
        score = round(100.0 * weighted / classified, 1)
        band = evidence_confidence_band(score)
    else:
        score = None
        band = "n/a"

    breakdown: dict[str, ClassBreakdown] = {
        cls: ClassBreakdown(
            occurrences=by_class[cls],
            fraction=round(by_class[cls] / total, 3) if total else 0.0,
        )
        for cls in ECO_CLASS_ORDER
    }

    return EvidenceConfidence(
        score=score,
        band=band,
        classified_occurrences=classified,
        total_occurrences=total,
        breakdown=breakdown,
        weights=dict(CLASS_WEIGHTS),
    )


#: Markdown row labels per rung — the human-facing gloss of each class.
_CLASS_MD_LABELS: Final[dict[str, str]] = {
    ECO_EXPERIMENTAL: "Experimental (wet-lab)",
    ECO_MANUAL: "Manual (curator-reviewed)",
    ECO_AUTOMATIC: "Automatic (pipeline-inferred)",
    ECO_OTHER: "Other (unclassified)",
}


def confidence_markdown_lines(confidence: EvidenceConfidence) -> list[str]:
    """Render an :class:`EvidenceConfidence` as Markdown lines.

    A headline ``score / 100 (band)`` line followed by one per-rung row.
    The three graded rungs always appear (an explicit "0 (0.0%)" is
    itself informative); the ``other`` rung is shown only when non-empty.
    """
    score = confidence["score"]
    if score is None:
        head = "**Evidence confidence:** n/a — only unclassified ECO codes present"
    else:
        head = f"**Evidence confidence:** {score:.1f} / 100 ({confidence['band']})"

    lines = [head]
    breakdown = confidence["breakdown"]
    for cls in ECO_CLASS_ORDER:
        entry = breakdown[cls]
        if cls == ECO_OTHER and entry["occurrences"] == 0:
            continue
        pct = entry["fraction"] * 100
        lines.append(f"- {_CLASS_MD_LABELS[cls]}: {entry['occurrences']} ({pct:.1f}%)")
    return lines
