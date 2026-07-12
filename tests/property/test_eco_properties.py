"""Property-based tests for the ECO evidence scorer.

Hypothesis generates arbitrary code-count histograms and checks
invariants that must hold for *any* input, not just cherry-picked cases.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from uniprot_mcp.eco import (
    CLASS_WEIGHTS,
    ECO_AUTOMATIC,
    ECO_EVIDENCE_CLASS,
    ECO_EXPERIMENTAL,
    ECO_OTHER,
    classify_eco,
    score_evidence,
)

# Draw histograms over the real ECO vocabulary plus a synthetic unknown
# code, so the `other` bucket is exercised alongside the graded rungs.
_CODES = [*sorted(ECO_EVIDENCE_CLASS), "ECO:9999999"]
_histograms = st.dictionaries(
    keys=st.sampled_from(_CODES),
    values=st.integers(min_value=1, max_value=1000),
    max_size=len(_CODES),
)


@given(counts=_histograms)
def test_score_is_bounded_or_none(counts: dict[str, int]) -> None:
    conf = score_evidence(counts)
    score = conf["score"]
    if score is None:
        # No score exactly when nothing classified.
        assert conf["classified_occurrences"] == 0
        assert conf["band"] == "n/a"
    else:
        assert 0.0 <= score <= 100.0
        assert conf["classified_occurrences"] > 0


@given(counts=_histograms)
def test_totals_and_breakdown_are_consistent(counts: dict[str, int]) -> None:
    conf = score_evidence(counts)
    breakdown = conf["breakdown"]
    # Occurrences across all rungs reconstruct the total.
    assert sum(b["occurrences"] for b in breakdown.values()) == conf["total_occurrences"]
    # Classified = total minus the unclassified rung.
    assert (
        conf["classified_occurrences"]
        == conf["total_occurrences"] - breakdown[ECO_OTHER]["occurrences"]
    )
    assert conf["total_occurrences"] == sum(counts.values())


@given(n=st.integers(min_value=1, max_value=10_000))
def test_pure_experimental_is_always_100(n: int) -> None:
    assert score_evidence({"ECO:0000269": n})["score"] == 100.0


@given(n=st.integers(min_value=1, max_value=10_000))
def test_pure_automatic_is_always_weight_times_100(n: int) -> None:
    expected = round(CLASS_WEIGHTS[ECO_AUTOMATIC] * 100.0, 1)
    assert score_evidence({"ECO:0000256": n})["score"] == expected


@given(counts=_histograms)
def test_every_occurrence_lands_in_exactly_one_rung(counts: dict[str, int]) -> None:
    for code, n in counts.items():
        cls = classify_eco(code)
        # A histogram of a single code puts all n occurrences in that rung.
        single = score_evidence({code: n})
        assert single["breakdown"][cls]["occurrences"] == n
    # The experimental rung never receives an automatic-only histogram.
    auto_only = score_evidence({"ECO:0000256": 1})
    assert auto_only["breakdown"][ECO_EXPERIMENTAL]["occurrences"] == 0
