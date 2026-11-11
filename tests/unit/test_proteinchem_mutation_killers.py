"""Surgical tests targeting the operator- and constant-level mutations
that the existing proteinchem test suite does not catch.

The 2026-04-27 mutation-matrix baseline (run 25015528542) reported
89 killed / 160 survived = 35.7% raw kill rate on
``src/uniprot_mcp/proteinchem.py``. The bulk of the survivors are
constant flips inside the residue-mass dict, the Kyte-Doolittle
hydropathy dict, the side-chain pK dicts, the extinction-coefficient
magic numbers, and the N/C-terminus pK constants — all of which the
``test_round_one_clinical.py`` battery missed because it asserts at
``math.isclose(..., abs_tol=0.01)`` or 1e-3 tolerances that swallow
single-digit constant changes.

This file pins each constant via single-residue / hand-crafted
sequences with hardcoded expected literals (computed once against
the unmutated source on 2026-04-27, then frozen). Importing
source-derived values would defeat the kill — when mutmut mutates a
constant, both sides of the assertion would shift together. The
literals below are therefore typed by hand from a one-time
computation, not derived from the live module.

The pI and net-charge literals were replaced on 2026-11-11, when the
pK table changed to the Bjellqvist set. The earlier literals were
snapshots of the previous table and could not survive that change.
The current ones come from a separate evaluation of the
Henderson-Hasselbalch sum, cross-checked against Biopython 1.88 for
every sequence that does not end in Asp or Glu (see
``docs/sequence-chemistry.md``).

Why this matters for adoption: a wrong residue mass that passes the
existing tests but produces a different MW for any non-trivial
protein is exactly the kind of silent correctness defect a
bio-pharma reviewer would flag. These tests close that gap.

Tolerances:
  - integer outputs (extinction coefficient, length, counts) → exact equality
  - float outputs rounded to 4 dp by the source → abs_tol=1e-6
    (large enough to ignore IEEE-754 repr noise on rounded values,
    far below the 1e-4 minimum impact of any constant-digit flip)
  - pI rounded to 2 dp by the source, compared with a 4 dp reference →
    abs_tol=5.1e-3 (the rounding step, and no more)
"""

from __future__ import annotations

import math

import pytest

from uniprot_mcp.proteinchem import (
    STANDARD_AA,
    aromaticity,
    compute_protein_properties,
    extinction_coefficient_280nm,
    gravy_index,
    isoelectric_point,
    molecular_weight,
    net_charge_at_pH,
)

# ---------------------------------------------------------------------------
# _RESIDUE_MASS — pin every entry via single-residue molecular_weight
# ---------------------------------------------------------------------------

# (single-letter AA, expected MW for a 1-residue "protein" rounded to 4 dp)
# MW = _RESIDUE_MASS[aa] + _WATER (18.01528), rounded to 4 dp by the source.
# Any mutation of either the per-AA residue mass or the water constant
# shifts the result by >= 1e-4 — well above abs_tol=1e-6.
_SINGLE_RESIDUE_MW = [
    ("A", 89.0941),
    ("C", 121.1541),
    ("D", 133.1039),
    ("E", 147.1308),
    ("F", 165.1919),
    ("G", 75.0672),
    ("H", 155.1564),
    ("I", 131.1747),
    ("K", 146.1894),
    ("L", 131.1747),
    ("M", 149.2079),
    ("N", 132.1191),
    ("P", 115.132),
    ("Q", 146.146),
    ("R", 174.2028),
    ("S", 105.0935),
    ("T", 119.1204),
    ("V", 117.1479),
    ("W", 204.2285),
    ("Y", 181.1913),
]


@pytest.mark.parametrize("aa,expected_mw", _SINGLE_RESIDUE_MW)
def test_single_residue_mw_pins_residue_mass_table(aa: str, expected_mw: float) -> None:
    """Each AA's residue mass must produce the expected MW for a
    single-residue 'protein'. Mutating any entry of _RESIDUE_MASS or
    _WATER shifts the result by >=1e-4 and fails the assertion."""
    p = compute_protein_properties(aa)
    assert math.isclose(p["molecular_weight"], expected_mw, abs_tol=1e-6), (
        f"{aa}: expected MW {expected_mw}, got {p['molecular_weight']}"
    )


# ---------------------------------------------------------------------------
# _KYTE_DOOLITTLE — pin every entry via single-residue GRAVY
# ---------------------------------------------------------------------------

# A single-residue homopolymer's GRAVY is exactly the AA's KD value
# (since GRAVY = sum(KD * count) / length = KD * 1 / 1 = KD), rounded to
# 4 dp by the source. Mutating any entry of _KYTE_DOOLITTLE shifts the
# result by >= 1e-1 — far above abs_tol=1e-6.
_SINGLE_RESIDUE_GRAVY = [
    ("A", 1.8),
    ("C", 2.5),
    ("D", -3.5),
    ("E", -3.5),
    ("F", 2.8),
    ("G", -0.4),
    ("H", -3.2),
    ("I", 4.5),
    ("K", -3.9),
    ("L", 3.8),
    ("M", 1.9),
    ("N", -3.5),
    ("P", -1.6),
    ("Q", -3.5),
    ("R", -4.5),
    ("S", -0.8),
    ("T", -0.7),
    ("V", 4.2),
    ("W", -0.9),
    ("Y", -1.3),
]


@pytest.mark.parametrize("aa,expected_gravy", _SINGLE_RESIDUE_GRAVY)
def test_single_residue_gravy_pins_kd_table(aa: str, expected_gravy: float) -> None:
    """Each AA's KD value must produce the expected GRAVY for a
    single-residue 'protein'."""
    p = compute_protein_properties(aa)
    assert math.isclose(p["gravy"], expected_gravy, abs_tol=1e-6), (
        f"{aa}: expected GRAVY {expected_gravy}, got {p['gravy']}"
    )


# ---------------------------------------------------------------------------
# pK constants — pin via net_charge at pH 7 for each single residue
# ---------------------------------------------------------------------------

# Each single-residue net_charge_pH7 reflects: the N-terminal pK of that
# residue (default 7.5; A 7.59, E 7.7, M 7.0, P 8.36, S 6.93, T 6.82,
# V 7.44), _PK_C_TERMINUS (3.55), and the residue's own side-chain pK if
# it has one (acidic: C 9.0, D 4.05, E 4.45, Y 10.0; basic: H 5.98,
# K 10.0, R 12.0). Reference values of 2026-11-11, see the module docstring.
_NET_CHARGE_PH7_SINGLE_RESIDUE = [
    ("A", -0.2041),  # N-terminal pK 7.59
    ("C", -0.2498),
    ("D", -1.2388),
    ("E", -1.1632),  # N-terminal pK 7.7 and the side chain
    ("F", -0.2399),  # no ionizable side chain, default N-terminal pK
    ("G", -0.2399),
    ("H", -0.1527),
    ("I", -0.2399),
    ("K", 0.7591),
    ("L", -0.2399),
    ("M", -0.4996),  # N-terminal pK 7.0
    ("N", -0.2399),
    ("P", -0.0415),  # N-terminal pK 8.36
    ("Q", -0.2399),
    ("R", 0.7601),
    ("S", -0.5399),  # N-terminal pK 6.93
    ("T", -0.6018),  # N-terminal pK 6.82
    ("V", -0.2660),  # N-terminal pK 7.44
    ("W", -0.2399),
    ("Y", -0.2409),
]


@pytest.mark.parametrize("aa,expected_charge", _NET_CHARGE_PH7_SINGLE_RESIDUE)
def test_single_residue_net_charge_pH7_pins_pk_constants(aa: str, expected_charge: float) -> None:
    """Each single-residue net charge at pH 7 pins the relevant pK
    constants (N-term, C-term, and side-chain if applicable)."""
    p = compute_protein_properties(aa)
    assert math.isclose(p["net_charge_pH7"], expected_charge, abs_tol=1e-4), (
        f"{aa}: expected charge {expected_charge}, got {p['net_charge_pH7']}"
    )


# ---------------------------------------------------------------------------
# Extinction coefficient — pin 1490, 5500, 125 magic numbers
# ---------------------------------------------------------------------------


def test_extinction_one_W_zero_Y_pins_5500() -> None:
    """Pace 1995: epsilon_Trp = 5500. With 1 Trp, 0 Tyr, 0 cystines,
    epsilon must equal exactly 5500 (any mutation of the magic number
    fails)."""
    assert extinction_coefficient_280nm({"W": 1, "Y": 0}) == 5500


def test_extinction_zero_W_one_Y_pins_1490() -> None:
    """Pace 1995: epsilon_Tyr = 1490."""
    assert extinction_coefficient_280nm({"W": 0, "Y": 1}) == 1490


def test_extinction_zero_W_zero_Y_one_cystine_pins_125() -> None:
    """1 cystine bond contributes 125 even with no W or Y."""
    assert extinction_coefficient_280nm({"W": 0, "Y": 0}, cystines=1) == 125


def test_extinction_combined_pins_full_formula() -> None:
    """5 W + 3 Y + 2 cystines → 5500*5 + 1490*3 + 125*2 = 32220."""
    assert extinction_coefficient_280nm({"W": 5, "Y": 3}, cystines=2) == 32220


def test_extinction_zero_inputs_returns_zero() -> None:
    """No W, no Y, no cystines → 0 (kills mutations that introduce a
    nonzero baseline)."""
    counts = {aa: 0 for aa in STANDARD_AA}
    counts["other"] = 0
    assert extinction_coefficient_280nm(counts) == 0


def test_extinction_returns_int_not_float() -> None:
    """The signature returns int. A mutation removing int(...) wrap
    would return float for non-integer cystine counts."""
    e = extinction_coefficient_280nm({"W": 5, "Y": 3})
    assert isinstance(e, int)
    assert e == 5500 * 5 + 1490 * 3  # 31970, no cystines


# ---------------------------------------------------------------------------
# pI — pin bisection precision and pK constants jointly
# ---------------------------------------------------------------------------

# Reference pI values to 4 dp (2026-11-11, see the module docstring).
# Source rounds to 2 dp. Mutations of pK constants OR the bisection
# range (lo=0, hi=14) OR the iteration count (60) shift these.
_PI_PINNED = [
    ("A", 5.5700),
    ("D", 3.7998),
    ("E", 3.9998),
    ("K", 8.7500),
    ("R", 9.7500),
    ("H", 6.7411),
    ("KKKKK", 10.6025),
    ("DDDDD", 3.2403),
    ("EEEEE", 3.5149),
    ("AAAAAAAAAA", 5.5700),
    ("WYC", 5.5174),
]


@pytest.mark.parametrize("seq,expected_pi", _PI_PINNED)
def test_pi_pinned_per_composition(seq: str, expected_pi: float) -> None:
    """Hardcoded pI values for representative compositions. Pins pK
    constants jointly with the bisection algorithm."""
    p = compute_protein_properties(seq)
    assert math.isclose(p["theoretical_pi"], expected_pi, abs_tol=5.1e-3), (
        f"{seq}: expected pI {expected_pi}, got {p['theoretical_pi']}"
    )


# ---------------------------------------------------------------------------
# Aromaticity — pin F+W+Y arithmetic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "seq,expected_aro",
    [
        ("F", 1.0),
        ("W", 1.0),
        ("Y", 1.0),
        ("A", 0.0),
        ("FWY", 1.0),
        ("FFFFAAAA", 0.5),
        ("FFFFFFAAAA", 0.6),
    ],
)
def test_aromaticity_pinned_values(seq: str, expected_aro: float) -> None:
    """Aromaticity = (F + W + Y) / length. Mutating the addend set
    (e.g., dropping Y) flips these."""
    p = compute_protein_properties(seq)
    assert math.isclose(p["aromaticity"], expected_aro, abs_tol=1e-9), (
        f"{seq}: expected aromaticity {expected_aro}, got {p['aromaticity']}"
    )


# ---------------------------------------------------------------------------
# STANDARD_AA — pin the canonical 20-letter alphabet
# ---------------------------------------------------------------------------


def test_standard_aa_is_exactly_the_20_canonical_letters() -> None:
    """STANDARD_AA must be the 20 standard one-letter amino-acid codes
    in the canonical order. Mutating any character (e.g., 'A' → 'a')
    breaks downstream tests that match against the set."""
    assert STANDARD_AA == "ACDEFGHIKLMNPQRSTVWY"
    assert len(STANDARD_AA) == 20
    assert len(set(STANDARD_AA)) == 20  # all distinct


def test_each_canonical_aa_recognised_separately() -> None:
    """compute_protein_properties on a single residue of each AA must
    return length=1 (NOT 0) and the residue must be counted under that
    AA's bucket. Kills any mutation that drops one of the 20 letters."""
    for aa in "ACDEFGHIKLMNPQRSTVWY":
        p = compute_protein_properties(aa)
        assert p["length"] == 1, f"{aa} not recognised as a standard AA"
        assert p["amino_acid_counts"][aa] == 1, f"{aa} not counted under itself"
        assert p["amino_acid_counts"]["other"] == 0, f"{aa} leaked to 'other'"


# ---------------------------------------------------------------------------
# Empty-sequence and edge-case guards
# ---------------------------------------------------------------------------


def test_empty_sequence_returns_zero_for_every_field() -> None:
    """Length-0 sequence: every numeric field must be 0/0.0 (and not
    raise). Pins the `if length > 0` guards."""
    p = compute_protein_properties("")
    assert p["length"] == 0
    assert p["molecular_weight"] == 0.0
    assert p["theoretical_pi"] == 0.0
    assert p["net_charge_pH7"] == 0.0
    assert p["gravy"] == 0.0
    assert p["aromaticity"] == 0.0
    assert p["extinction_coefficient_280nm"] == 0


def test_empty_sequence_amino_acid_counts_all_zero() -> None:
    p = compute_protein_properties("")
    assert p["amino_acid_counts"]["other"] == 0
    for aa in "ACDEFGHIKLMNPQRSTVWY":
        assert p["amino_acid_counts"][aa] == 0


def test_non_standard_letters_increment_other_only() -> None:
    """X, B, Z, U, O are non-standard one-letter codes; they must NOT
    increment any standard AA count, and must increment 'other'."""
    p = compute_protein_properties("XBZUO")
    for aa in "ACDEFGHIKLMNPQRSTVWY":
        assert p["amino_acid_counts"][aa] == 0
    assert p["amino_acid_counts"]["other"] == 5
    assert p["length"] == 0  # length excludes 'other'


def test_whitespace_digits_dashes_silently_skipped() -> None:
    """compute_protein_properties first strips non-alpha characters via
    ``"".join(c for c in sequence if c.isalpha())``. Digits, whitespace,
    and dashes must NOT count anywhere — neither in standard AA nor in
    'other'."""
    p = compute_protein_properties("A 1 -A")
    assert p["amino_acid_counts"]["A"] == 2
    assert p["amino_acid_counts"]["other"] == 0
    assert p["length"] == 2


def test_lowercase_letters_normalised_to_uppercase() -> None:
    """_count_amino_acids calls .upper(). A mutation removing it (or
    flipping to .lower()) would mis-count lowercase input."""
    p = compute_protein_properties("aaa")
    assert p["amino_acid_counts"]["A"] == 3
    assert p["length"] == 3


# ---------------------------------------------------------------------------
# Helper functions called directly (kills mutations inside helper bodies)
# ---------------------------------------------------------------------------


def test_molecular_weight_direct_for_single_A() -> None:
    """Call molecular_weight directly with a counts dict — pins the
    helper's body, not just the orchestrator path."""
    counts = {aa: 0 for aa in "ACDEFGHIKLMNPQRSTVWY"}
    counts["A"] = 1
    counts["other"] = 0
    mw = molecular_weight(counts)
    assert math.isclose(mw, 89.0941, abs_tol=1e-6)


def test_molecular_weight_returns_zero_for_all_zero_counts() -> None:
    """No standard AAs counted → MW = 0.0 (the `if total > 0` guard)."""
    counts = {aa: 0 for aa in "ACDEFGHIKLMNPQRSTVWY"}
    counts["other"] = 0
    assert molecular_weight(counts) == 0.0


def test_gravy_direct_for_zero_length_returns_zero() -> None:
    """gravy_index(_, length=0) must return 0.0, not raise ZeroDivisionError.
    Pins the `if length <= 0` guard."""
    counts = {aa: 0 for aa in "ACDEFGHIKLMNPQRSTVWY"}
    counts["other"] = 0
    assert gravy_index(counts, 0) == 0.0


def test_aromaticity_direct_for_zero_length_returns_zero() -> None:
    counts = {aa: 0 for aa in "ACDEFGHIKLMNPQRSTVWY"}
    counts["other"] = 0
    assert aromaticity(counts, 0) == 0.0


def test_isoelectric_point_from_counts_alone_is_mean_of_default_terminal_pks() -> None:
    """Counts only, no first residue named: the default N-terminal pK
    (7.5) applies, so with no ionizable side chain the pI is the mean of
    7.5 and the C-terminal pK 3.55 = 5.525, rounded to 2 dp either way."""
    counts = {aa: 0 for aa in "ACDEFGHIKLMNPQRSTVWY"}
    counts["A"] = 1
    counts["other"] = 0
    assert math.isclose(isoelectric_point(counts), 5.525, abs_tol=5.1e-3)


def test_isoelectric_point_uses_the_named_first_residue() -> None:
    """The same counts with the first residue named take that residue's
    N-terminal pK: Ala 7.59 gives (7.59 + 3.55) / 2 = 5.57, Pro 8.36
    gives 5.955, and a residue without its own value changes nothing."""
    counts = {aa: 0 for aa in "ACDEFGHIKLMNPQRSTVWY"}
    counts["A"] = 1
    counts["other"] = 0
    assert math.isclose(isoelectric_point(counts, n_terminal="A"), 5.57, abs_tol=5.1e-3)
    assert math.isclose(isoelectric_point(counts, n_terminal="P"), 5.955, abs_tol=5.1e-3)
    assert isoelectric_point(counts, n_terminal="G") == isoelectric_point(counts)
    # Lower case names the same residue.
    assert isoelectric_point(counts, n_terminal="a") == isoelectric_point(counts, n_terminal="A")


def test_net_charge_pH7_from_counts_alone_uses_default_terminal_pks() -> None:
    """No side chain, no first residue named, pH 7:
    1/(1 + 10**(7-7.5)) - 1/(1 + 10**(3.55-7)) = 0.75975 - 0.99965 = -0.2399.
    Pins both default terminus pKs jointly."""
    counts = {aa: 0 for aa in "ACDEFGHIKLMNPQRSTVWY"}
    counts["A"] = 1
    counts["other"] = 0
    charge = net_charge_at_pH(counts, 7.0)
    assert math.isclose(charge, -0.2399, abs_tol=1e-4)
    # With the first residue named, the Ala value 7.59 raises the positive part.
    assert math.isclose(net_charge_at_pH(counts, 7.0, n_terminal="A"), -0.2041, abs_tol=1e-4)


# ---------------------------------------------------------------------------
# P53[1:10] (MEEPQSDPSV) — full snapshot of every derived property
# ---------------------------------------------------------------------------


def test_p53_n_terminal_10_residue_full_snapshot() -> None:
    """First 10 residues of P53 (M E E P Q S D P S V) — snapshot every
    derived property. Hardcoded values from one-time computation
    against the unmutated source on 2026-04-27 (pI and net charge:
    reference values of 2026-11-11, equal to Biopython 1.88). Any
    constant or operator mutation that changes any of these values
    fails one of the assertions below.
    """
    p = compute_protein_properties("MEEPQSDPSV")
    assert p["length"] == 10
    assert math.isclose(p["molecular_weight"], 1118.1806, abs_tol=1e-4)
    assert math.isclose(p["theoretical_pi"], 3.5743, abs_tol=5.1e-3)
    assert math.isclose(p["net_charge_pH7"], -3.4929, abs_tol=1e-4)
    assert math.isclose(p["gravy"], -1.27, abs_tol=1e-2)
    assert math.isclose(p["aromaticity"], 0.0, abs_tol=1e-9)
    assert p["extinction_coefficient_280nm"] == 0
    # AA counts: M=1 E=2 P=2 Q=1 S=2 D=1 V=1
    assert p["amino_acid_counts"]["M"] == 1
    assert p["amino_acid_counts"]["E"] == 2
    assert p["amino_acid_counts"]["P"] == 2
    assert p["amino_acid_counts"]["Q"] == 1
    assert p["amino_acid_counts"]["S"] == 2
    assert p["amino_acid_counts"]["D"] == 1
    assert p["amino_acid_counts"]["V"] == 1
    # Total of all standard AAs counts == length
    assert sum(p["amino_acid_counts"][aa] for aa in "ACDEFGHIKLMNPQRSTVWY") == 10


def test_multichar_uppercase_letter_falls_to_other() -> None:
    """A letter whose uppercase form is multi-character (e.g. the German
    eszett -> "SS") must NOT inflate the residue count or fabricate residues.

    Counting over ``sequence.upper()`` first expands the eszett to "SS", so the
    single input character was double-counted as two Ser. Counting per input
    character (uppercasing each one) keeps the length invariant and routes the
    eszett to the "other" bucket instead.
    """
    eszett = chr(0xDF)
    p = compute_protein_properties("A" + eszett + "A")
    assert p["length"] == 2
    assert p["amino_acid_counts"]["A"] == 2
    assert p["amino_acid_counts"]["S"] == 0
    assert p["amino_acid_counts"]["other"] == 1
    # MW = 2 * Ala residue mass + one water, derived from ExPASy/IUPAC values
    # (Ala residue 71.0788, water 18.01528) -- independent of code output.
    assert math.isclose(p["molecular_weight"], round(2 * 71.0788 + 18.01528, 4), abs_tol=1e-6)
