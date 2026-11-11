"""Theoretical pI and net charge against external references.

The pI and net-charge calculation uses the Bjellqvist pK set. These tests
hold it to two references that share no code with this package:

* **ExPASy ProtParam** (https://web.expasy.org/protparam/), queried on
  2026-11-11 with each sequence below. ProtParam reports the theoretical
  pI to two decimals.
* **Biopython 1.88** ``Bio.SeqUtils.IsoelectricPoint``, for the net charge
  at pH 7, which ProtParam does not report.

The protein rows are UniProt canonical sequences of release 2026_04. Only
the inputs the charge model consumes are kept here: the first residue and
the counts of the seven ionizable side chains. ``docs/sequence-chemistry.md``
lists the entries with their sequence versions and says how to repeat the
queries.

Biopython and the ExPASy tools differ on one rule. After a C-terminal Asp
or Glu, Biopython 1.88 raises the pK of the carboxyl terminus from 3.55 to
4.55 or 4.75; ProtParam returns the same pI whether the Asp or Glu is last
or one position earlier. This package keeps one C-terminal pK, so the pI is
checked against ProtParam for every row, and the net charge is checked
against Biopython only where the two agree, that is for sequences that do
not end in Asp or Glu.
"""

from __future__ import annotations

import pytest

from uniprot_mcp import proteinchem
from uniprot_mcp.proteinchem import (
    compute_protein_properties,
    isoelectric_point,
    net_charge_at_pH,
)

_IONIZABLE = "CDEHKRY"

# (sequence, ProtParam pI). Each group isolates one rule of the convention.
_PROBES = [
    # Amino terminus: one His plus the terminus carry the positive charge.
    ("GGGHGGGGGG", 6.74),  # default N-terminal pK 7.5
    ("AGGHGGGGGG", 6.79),  # Ala 7.59
    ("MGGHGGGGGG", 6.49),  # Met 7.0
    ("PGGHGGGGGG", 7.17),  # Pro 8.36
    ("SGGHGGGGGG", 6.46),  # Ser 6.93
    ("TGGHGGGGGG", 6.40),  # Thr 6.82
    ("VGGHGGGGGG", 6.71),  # Val 7.44
    ("EGGHGGKGGG", 6.85),  # Glu 7.7
    ("QGGHGGKGGE", 6.75),  # default again, C-terminal Glu
    # Carboxyl terminus: Asp or Glu last, or one position earlier.
    ("GGGGGGGGGD", 3.80),
    ("GGGGGGGGDG", 3.80),
    ("GGGGGGGGGE", 4.00),
    ("GGGGGGGGEG", 4.00),
    ("GGHGGGGGGD", 5.08),
    ("GGHGGGGGGE", 5.24),
    # Roots near or beyond the ends of the usual pH range.
    ("DDDDDDDDDD", 2.98),
    ("EEEEEEEEEE", 3.29),
    ("KKKKKKKKKK", 10.95),
    ("RRRRRRRRRR", 12.95),
    # Cys and Tyr side chains, and the two doctest peptides of Biopython.
    ("GGCGGGGGKG", 8.22),
    ("GGYGGGGGKG", 8.59),
    ("INGAR", 9.75),
    ("PETER", 4.53),
]

# (accession, first residue, last residue, counts of C D E H K R Y,
#  ProtParam pI, Biopython 1.88 charge at pH 7 or None when the sequence
#  ends in Asp or Glu).
_PROTEINS = [
    ("P00533", "M", "A", (60, 61, 77, 31, 66, 60, 36), 6.26, -10.209),
    ("P00698", "M", "L", (9, 7, 2, 1, 6, 12, 3), 9.36, 8.5028),
    ("P00918", "M", "K", (1, 19, 13, 12, 24, 7, 8), 6.87, -0.4377),
    ("P01112", "M", "S", (6, 15, 14, 3, 11, 12, 9), 5.16, -6.2615),
    ("P01308", "M", "N", (6, 2, 8, 2, 2, 5, 4), 5.22, -3.366),
    ("P02144", "M", "G", (1, 8, 14, 9, 20, 2, 2), 7.14, 0.3013),
    ("P02768", "M", "L", (35, 36, 62, 16, 60, 27, 19), 5.92, -10.316),
    ("P04637", "M", "D", (10, 20, 30, 12, 20, 26, 9), 6.33, None),
    ("P05067", "M", "N", (18, 50, 92, 25, 41, 37, 20), 4.73, -62.2452),
    ("P0CG48", "M", "V", (0, 45, 54, 9, 63, 36, 9), 7.16, 0.4148),
    ("P0DP23", "M", "K", (0, 17, 21, 1, 8, 6, 2), 4.09, -24.3444),
    ("P10636", "M", "L", (4, 43, 59, 20, 64, 30, 6), 6.25, -6.652),
    ("P12931", "M", "L", (9, 21, 42, 9, 31, 32, 23), 7.10, 0.2831),
    ("P38398", "M", "Y", (44, 85, 198, 49, 137, 76, 31), 5.29, -66.1806),
    ("P42212", "M", "K", (2, 18, 16, 10, 20, 6, 11), 5.67, -7.6136),
    ("P61626", "M", "V", (8, 8, 3, 1, 6, 14, 6), 9.38, 8.5136),
    ("P62942", "M", "E", (1, 6, 7, 3, 8, 6, 3), 7.89, None),
    ("P68431", "M", "A", (2, 4, 7, 2, 13, 18, 3), 11.13, 19.6629),
    ("P68871", "M", "H", (2, 7, 8, 9, 11, 3, 3), 6.74, -0.7186),
    ("P69905", "M", "R", (1, 8, 4, 10, 11, 3, 3), 8.72, 2.3684),
    # Acidic proteins, five of them ending in Asp or Glu: the rows on which
    # Biopython 1.88 and ProtParam part by up to 0.05 pH.
    ("P04271", "M", "E", (2, 7, 16, 5, 8, 1, 1), 4.52, None),
    ("P06454", "M", "D", (0, 19, 35, 0, 8, 2, 0), 3.66, None),
    ("P07900", "M", "D", (7, 54, 97, 12, 80, 30, 25), 4.94, None),
    ("P08238", "M", "D", (6, 51, 96, 13, 75, 32, 24), 4.96, None),
    ("P0DMV8", "M", "D", (5, 45, 47, 7, 50, 31, 15), 5.47, None),
    ("P27797", "M", "L", (3, 55, 54, 7, 42, 8, 14), 4.29, -58.7617),
    ("P37840", "M", "A", (0, 6, 18, 1, 15, 0, 4), 4.67, -9.3741),
]

# Canonical sequences of two short entries, for the path that starts from a
# sequence string. FKBP1A is the entry on which the previous pK table was
# furthest from ProtParam (8.81 against 7.89).
_INS_HUMAN = (
    "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGG"
    "PGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN"
)
_FKB1A_HUMAN = (
    "MGVQVETISPGDGRTFPKRGQTCVVHYTGMLEDGKKFDSSRDRNKPFKFMLGKQEVIRGWEEGVAQMSVG"
    "QRAKLTISPDYAYGATGHPGIIPPHATLVFDVELLKLE"
)


def _counts(ionizable: tuple[int, ...]) -> dict[str, int]:
    return dict(zip(_IONIZABLE, ionizable, strict=True))


@pytest.mark.parametrize("sequence,protparam_pi", _PROBES)
def test_probe_pi_equals_protparam(sequence: str, protparam_pi: float) -> None:
    assert compute_protein_properties(sequence)["theoretical_pi"] == protparam_pi


def test_pi_without_side_chains_is_within_one_rounding_step_of_protparam() -> None:
    """Ten glycines: the root is exactly (7.5 + 3.55) / 2 = 5.525, a tie at
    two decimals. ProtParam prints 5.52; either neighbour is a correct
    rounding, so this one case is held to 0.01 instead of to equality."""
    pi = compute_protein_properties("GGGGGGGGGG")["theoretical_pi"]
    assert pi in (5.52, 5.53)


@pytest.mark.parametrize("accession,first,last,ionizable,protparam_pi,charge", _PROTEINS)
def test_protein_pi_equals_protparam(
    accession: str,
    first: str,
    last: str,
    ionizable: tuple[int, ...],
    protparam_pi: float,
    charge: float | None,
) -> None:
    assert isoelectric_point(_counts(ionizable), n_terminal=first) == protparam_pi, accession


@pytest.mark.parametrize(
    "accession,first,last,ionizable,protparam_pi,charge",
    [row for row in _PROTEINS if row[5] is not None],
)
def test_protein_charge_at_ph7_equals_biopython(
    accession: str,
    first: str,
    last: str,
    ionizable: tuple[int, ...],
    protparam_pi: float,
    charge: float,
) -> None:
    assert last not in "DE"
    computed = net_charge_at_pH(_counts(ionizable), 7.0, n_terminal=first)
    assert abs(computed - charge) <= 1e-4, accession


@pytest.mark.parametrize("accession,first,last,ionizable,protparam_pi,charge", _PROTEINS)
def test_reported_pi_brackets_the_zero_of_the_net_charge(
    accession: str,
    first: str,
    last: str,
    ionizable: tuple[int, ...],
    protparam_pi: float,
    charge: float | None,
) -> None:
    """The pI is the pH of zero net charge, reported to two decimals: the
    charge is positive just below the reported value and negative just
    above it. This holds for any pK table, so it checks the root search
    and not the constants."""
    counts = _counts(ionizable)
    pi = isoelectric_point(counts, n_terminal=first)
    assert net_charge_at_pH(counts, pi - 0.0051, n_terminal=first) > 0, accession
    assert net_charge_at_pH(counts, pi + 0.0051, n_terminal=first) < 0, accession


def test_c_terminal_acid_takes_the_same_pk_as_an_internal_one() -> None:
    """The one rule on which this package follows ProtParam and not
    Biopython 1.88, which returns 4.30 and 4.60 for the first sequence of
    each pair."""
    asp_last = compute_protein_properties("GGGGGGGGGD")["theoretical_pi"]
    asp_internal = compute_protein_properties("GGGGGGGGDG")["theoretical_pi"]
    glu_last = compute_protein_properties("GGGGGGGGGE")["theoretical_pi"]
    glu_internal = compute_protein_properties("GGGGGGGGEG")["theoretical_pi"]
    assert asp_last == asp_internal == 3.80
    assert glu_last == glu_internal == 4.00


@pytest.mark.parametrize(
    "sequence,protparam_pi,protparam_mw,protparam_eps_reduced,protparam_gravy",
    [
        (_INS_HUMAN, 5.22, 11980.91, 16960, 0.193),
        (_FKB1A_HUMAN, 7.89, 11950.71, 9970, -0.411),
    ],
)
def test_full_record_from_a_sequence_equals_protparam(
    sequence: str,
    protparam_pi: float,
    protparam_mw: float,
    protparam_eps_reduced: int,
    protparam_gravy: float,
) -> None:
    """From the sequence string: the pI, and the three properties this
    change leaves alone (ProtParam prints the mass to two decimals and
    GRAVY to three)."""
    p = compute_protein_properties(sequence)
    assert p["theoretical_pi"] == protparam_pi
    assert round(p["molecular_weight"], 2) == protparam_mw
    assert p["extinction_coefficient_280nm"] == protparam_eps_reduced
    assert round(p["gravy"], 3) == protparam_gravy
    assert p["charge_model"]["n_terminal_residue"] == "M"
    assert p["charge_model"]["n_terminus_pk"] == 7.0


def test_charge_model_names_every_constant_applied() -> None:
    model = compute_protein_properties("AGK")["charge_model"]
    assert model == {
        "pk_set": "Bjellqvist",
        "n_terminal_residue": "A",
        "n_terminus_pk": 7.59,
        "c_terminus_pk": 3.55,
        "side_chain_pk": {
            "C": 9.0,
            "D": 4.05,
            "E": 4.45,
            "H": 5.98,
            "K": 10.0,
            "R": 12.0,
            "Y": 10.0,
        },
    }
    assert proteinchem.PK_SET_NAME == "Bjellqvist"
    assert list(model["side_chain_pk"]) == sorted(model["side_chain_pk"])


@pytest.mark.parametrize(
    "sequence,first,pk",
    [
        ("GAK", "G", 7.5),  # no value of its own
        ("xGK", "X", 7.5),  # a non-standard first letter takes the default
        ("mGK", "M", 7.0),  # lower case is the same residue
        ("", "", 7.5),  # empty input still describes the model
    ],
)
def test_charge_model_reports_the_first_residue_and_its_pk(
    sequence: str, first: str, pk: float
) -> None:
    model = compute_protein_properties(sequence)["charge_model"]
    assert model["n_terminal_residue"] == first
    assert model["n_terminus_pk"] == pk


def test_first_residue_changes_the_result_only_through_its_terminal_pk() -> None:
    """Thr first (6.82) against Gly first (7.5), same side chains: the
    weaker base gives the lower pI and the lower charge at pH 7."""
    thr = compute_protein_properties("TGGHGGGGGG")
    gly = compute_protein_properties("GGGHGGGGGG")
    assert thr["theoretical_pi"] < gly["theoretical_pi"]
    assert thr["net_charge_pH7"] < gly["net_charge_pH7"]
