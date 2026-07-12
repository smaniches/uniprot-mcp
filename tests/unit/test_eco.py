"""Unit tests for the ECO evidence-scoring module (:mod:`uniprot_mcp.eco`).

The module is pure data + pure functions, so every branch is exercised
directly here — no HTTP, no server. Covers:

* the taxonomy's internal consistency (every labelled code is classified
  and vice versa; weights and class-order are well-formed);
* :func:`classify_eco` for each rung and the unknown-code fallback;
* :func:`evidence_confidence_band` at and around every boundary;
* :func:`score_evidence` for pure, mixed, unknown-only, and empty inputs;
* :func:`confidence_markdown_lines` for scored, unscored, and
  other-present renderings.
"""

from __future__ import annotations

import pytest

from uniprot_mcp.eco import (
    CLASS_WEIGHTS,
    ECO_AUTOMATIC,
    ECO_CLASS_ORDER,
    ECO_EVIDENCE_CLASS,
    ECO_EXPERIMENTAL,
    ECO_HUMAN_LABELS,
    ECO_MANUAL,
    ECO_OTHER,
    classify_eco,
    confidence_markdown_lines,
    evidence_confidence_band,
    score_evidence,
)

# ---------------------------------------------------------------------------
# Taxonomy integrity
# ---------------------------------------------------------------------------


def test_every_classified_code_has_a_human_label() -> None:
    """A classified code with no label would render a bare ECO id."""
    missing = set(ECO_EVIDENCE_CLASS) - set(ECO_HUMAN_LABELS)
    assert not missing, f"classified codes lack a label: {sorted(missing)}"


def test_every_labelled_code_is_classified() -> None:
    """A labelled-but-unclassified code would silently fall to `other`."""
    missing = set(ECO_HUMAN_LABELS) - set(ECO_EVIDENCE_CLASS)
    assert not missing, f"labelled codes lack a class: {sorted(missing)}"


def test_evidence_classes_are_from_the_known_set() -> None:
    graded = {ECO_EXPERIMENTAL, ECO_MANUAL, ECO_AUTOMATIC}
    assert set(ECO_EVIDENCE_CLASS.values()) <= graded


def test_class_order_lists_every_rung_once() -> None:
    assert ECO_CLASS_ORDER == (ECO_EXPERIMENTAL, ECO_MANUAL, ECO_AUTOMATIC, ECO_OTHER)
    assert len(set(ECO_CLASS_ORDER)) == len(ECO_CLASS_ORDER)


def test_weights_cover_exactly_the_graded_rungs_and_rank_correctly() -> None:
    assert set(CLASS_WEIGHTS) == {ECO_EXPERIMENTAL, ECO_MANUAL, ECO_AUTOMATIC}
    assert (
        CLASS_WEIGHTS[ECO_EXPERIMENTAL] > CLASS_WEIGHTS[ECO_MANUAL] > CLASS_WEIGHTS[ECO_AUTOMATIC]
    )
    assert ECO_OTHER not in CLASS_WEIGHTS


def test_eco_0007744_is_corrected_to_manual_computational_experimental() -> None:
    """Regression guard: ECO:0007744 was previously mislabelled as an
    'automatic assertion'. It is a *manual* combinatorial term."""
    assert ECO_HUMAN_LABELS["ECO:0007744"] == (
        "combinatorial computational and experimental evidence used in manual assertion"
    )
    assert classify_eco("ECO:0007744") == ECO_MANUAL


# ---------------------------------------------------------------------------
# classify_eco
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("ECO:0000269", ECO_EXPERIMENTAL),
        ("ECO:0000250", ECO_MANUAL),
        ("ECO:0000305", ECO_MANUAL),
        ("ECO:0000256", ECO_AUTOMATIC),
        ("ECO:0000313", ECO_AUTOMATIC),
    ],
)
def test_classify_known_codes(code: str, expected: str) -> None:
    assert classify_eco(code) == expected


def test_classify_unknown_code_falls_back_to_other() -> None:
    assert classify_eco("ECO:9999999") == ECO_OTHER
    assert classify_eco("not-an-eco-code") == ECO_OTHER


def test_current_combinatorial_automatic_code_is_classified() -> None:
    """ECO:0007829 (combinatorial computational + experimental, automatic) is
    one of the most common codes on TrEMBL/PDB/PeptideAtlas entries. If it
    fell through to `other` it would be dropped from the score denominator and
    inflate confidence, so it must classify as automatic."""
    assert classify_eco("ECO:0007829") == ECO_AUTOMATIC
    # A real-world shape: 2 experimental + many ECO:0007829 must score low,
    # not n/a or artificially high.
    conf = score_evidence({"ECO:0000269": 2, "ECO:0007829": 98})
    assert conf["score"] is not None
    assert conf["breakdown"][ECO_AUTOMATIC]["occurrences"] == 98
    assert conf["breakdown"][ECO_OTHER]["occurrences"] == 0
    assert conf["band"] == "very low"


# ---------------------------------------------------------------------------
# evidence_confidence_band — boundaries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("score", "band"),
    [
        (100.0, "high"),
        (70.0, "high"),  # inclusive lower edge
        (69.9, "moderate"),
        (40.0, "moderate"),  # inclusive lower edge
        (39.9, "low"),
        (15.0, "low"),  # inclusive lower edge
        (14.9, "very low"),
        (0.0, "very low"),
    ],
)
def test_band_boundaries(score: float, band: str) -> None:
    assert evidence_confidence_band(score) == band


# ---------------------------------------------------------------------------
# score_evidence
# ---------------------------------------------------------------------------


def test_pure_experimental_scores_100_high() -> None:
    conf = score_evidence({"ECO:0000269": 7})
    assert conf["score"] == 100.0
    assert conf["band"] == "high"
    assert conf["classified_occurrences"] == 7
    assert conf["total_occurrences"] == 7
    assert conf["breakdown"][ECO_EXPERIMENTAL] == {"occurrences": 7, "fraction": 1.0}


def test_pure_manual_scores_50_moderate() -> None:
    conf = score_evidence({"ECO:0000250": 3, "ECO:0000305": 1})
    assert conf["score"] == 50.0
    assert conf["band"] == "moderate"
    assert conf["breakdown"][ECO_MANUAL]["occurrences"] == 4


def test_pure_automatic_scores_10_very_low() -> None:
    conf = score_evidence({"ECO:0000256": 5})
    assert conf["score"] == 10.0
    assert conf["band"] == "very low"


def test_mixed_experimental_and_automatic_weighted_mean() -> None:
    # 1 experimental (1.0) + 9 automatic (0.1) over 10 -> (1.0 + 0.9)/10 = 0.19
    conf = score_evidence({"ECO:0000269": 1, "ECO:0000256": 9})
    assert conf["score"] == 19.0
    assert conf["band"] == "low"
    assert conf["breakdown"][ECO_EXPERIMENTAL]["fraction"] == 0.1
    assert conf["breakdown"][ECO_AUTOMATIC]["fraction"] == 0.9


def test_unknown_codes_are_excluded_from_the_score() -> None:
    """`other` occurrences count toward the total and the breakdown but
    must not enter the weighted score's denominator."""
    conf = score_evidence({"ECO:0000269": 2, "ECO:9999999": 8})
    # score is over the 2 classified experimental occurrences only -> 100.
    assert conf["score"] == 100.0
    assert conf["classified_occurrences"] == 2
    assert conf["total_occurrences"] == 10
    assert conf["breakdown"][ECO_OTHER] == {"occurrences": 8, "fraction": 0.8}
    assert conf["breakdown"][ECO_EXPERIMENTAL]["fraction"] == 0.2


def test_only_unknown_codes_yields_no_score() -> None:
    conf = score_evidence({"ECO:9999999": 4})
    assert conf["score"] is None
    assert conf["band"] == "n/a"
    assert conf["classified_occurrences"] == 0
    assert conf["total_occurrences"] == 4
    assert conf["breakdown"][ECO_OTHER]["fraction"] == 1.0


def test_empty_histogram_is_safe() -> None:
    conf = score_evidence({})
    assert conf["score"] is None
    assert conf["band"] == "n/a"
    assert conf["total_occurrences"] == 0
    # total == 0 must not divide-by-zero; every fraction is 0.0.
    assert all(conf["breakdown"][cls]["fraction"] == 0.0 for cls in ECO_CLASS_ORDER)


def test_weights_are_echoed_for_transparency() -> None:
    conf = score_evidence({"ECO:0000269": 1})
    assert conf["weights"] == dict(CLASS_WEIGHTS)


def test_fractions_are_rounded_to_three_places() -> None:
    conf = score_evidence({"ECO:0000269": 1, "ECO:0000256": 2})  # 1/3, 2/3
    assert conf["breakdown"][ECO_EXPERIMENTAL]["fraction"] == 0.333
    assert conf["breakdown"][ECO_AUTOMATIC]["fraction"] == 0.667


# ---------------------------------------------------------------------------
# confidence_markdown_lines
# ---------------------------------------------------------------------------


def test_markdown_headline_and_graded_rows() -> None:
    lines = confidence_markdown_lines(score_evidence({"ECO:0000269": 2, "ECO:0000250": 2}))
    assert lines[0] == "**Evidence confidence:** 75.0 / 100 (high)"
    assert "- Experimental (wet-lab): 2 (50.0%)" in lines
    assert "- Manual (curator-reviewed): 2 (50.0%)" in lines
    assert "- Automatic (pipeline-inferred): 0 (0.0%)" in lines
    # `other` row is suppressed when empty.
    assert not any("Other (unclassified)" in line for line in lines)


def test_markdown_shows_other_row_when_present() -> None:
    lines = confidence_markdown_lines(score_evidence({"ECO:0000269": 1, "ECO:9999999": 1}))
    assert any(line == "- Other (unclassified): 1 (50.0%)" for line in lines)


def test_markdown_unscored_uses_na_headline() -> None:
    lines = confidence_markdown_lines(score_evidence({"ECO:9999999": 3}))
    assert lines[0] == "**Evidence confidence:** n/a — only unclassified ECO codes present"
    assert "- Other (unclassified): 3 (100.0%)" in lines
