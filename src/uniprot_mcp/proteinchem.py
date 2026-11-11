"""Pure-Python protein chemistry primitives.

Computed from the 20-letter amino-acid composition of a sequence.
No external API call — these are derived properties anyone can
recompute from the FASTA. References:

  Bjellqvist pK set            — theoretical pI and net charge (pK table
                                  below; Electrophoresis 14, 1023-1031, 1993
                                  and 15, 529-539, 1994)
  Kyte-Doolittle hydropathy    — GRAVY (J. Mol. Biol. 157, 105-132, 1982)
  Aromaticity (F + W + Y)      — Lobry & Gautier (1994)
  Extinction coefficient 280nm — Pace et al. (1995): ε = 5500·Trp + 1490·Tyr
                                  (assumes reduced cysteines; +125 per cystine
                                  if disulfide count is supplied)
  Average residue masses       — IUPAC, water-loss form (M_residue = M_aa - H2O)

The functions are deliberately small and standalone so they can be
audited line-by-line. None of them depends on `httpx` or any non-stdlib
library; all are O(n) in sequence length.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from typing import Final, TypedDict

# Standard 20 amino acids. ``X``, ``B``, ``Z``, ``U``, ``O`` etc. are
# tolerated but skipped from chemistry calculations (they are
# explicitly counted under ``other``).
STANDARD_AA: Final[str] = "ACDEFGHIKLMNPQRSTVWY"

# Average residue masses (average mass of the residue, i.e. the amino
# acid minus one water). Source: IUPAC / Unimod.
_RESIDUE_MASS: Final[dict[str, float]] = {
    "A": 71.0788,
    "C": 103.1388,
    "D": 115.0886,
    "E": 129.1155,
    "F": 147.1766,
    "G": 57.0519,
    "H": 137.1411,
    "I": 113.1594,
    "K": 128.1741,
    "L": 113.1594,
    "M": 131.1926,
    "N": 114.1038,
    "P": 97.1167,
    "Q": 128.1307,
    "R": 156.1875,
    "S": 87.0782,
    "T": 101.1051,
    "V": 99.1326,
    "W": 186.2132,
    "Y": 163.1760,
}
_WATER: Final[float] = 18.01528  # average mass; added once at the end

# Kyte-Doolittle hydropathy values (J. Mol. Biol. 157, 105-132, 1982).
_KYTE_DOOLITTLE: Final[dict[str, float]] = {
    "A": 1.8,
    "C": 2.5,
    "D": -3.5,
    "E": -3.5,
    "F": 2.8,
    "G": -0.4,
    "H": -3.2,
    "I": 4.5,
    "K": -3.9,
    "L": 3.8,
    "M": 1.9,
    "N": -3.5,
    "P": -1.6,
    "Q": -3.5,
    "R": -4.5,
    "S": -0.8,
    "T": -0.7,
    "V": 4.2,
    "W": -0.9,
    "Y": -1.3,
}

# pK values for the theoretical pI and the net charge: the Bjellqvist set.
# The numbers are those tabulated in Biopython 1.88
# (``Bio.SeqUtils.IsoelectricPoint``), which attributes them to Bjellqvist
# et al., Electrophoresis 14, 1023-1031 (1993) and 15, 529-539 (1994).
#
# One rule differs from Biopython on purpose. Here the carboxyl terminus has
# pK 3.55 whatever the last residue is; Biopython raises it to 4.55 / 4.75
# after a C-terminal Asp / Glu. The ExPASy tools (ProtParam, Compute pI/Mw)
# return the same pI for a C-terminal and an internal Asp or Glu, and with a
# single C-terminal pK this module reproduces the ExPASy values recorded in
# ``tests/unit/test_proteinchem_pi_reference.py``. ``docs/sequence-chemistry.md``
# has the measurements and their limits.
PK_SET_NAME: Final[str] = "Bjellqvist"
_PK_SIDE_CHAIN_ACIDIC: Final[dict[str, float]] = {
    "C": 9.0,  # cysteine thiol
    "D": 4.05,  # aspartate carboxyl
    "E": 4.45,  # glutamate carboxyl
    "Y": 10.0,  # tyrosine hydroxyl
}
_PK_SIDE_CHAIN_BASIC: Final[dict[str, float]] = {
    "H": 5.98,  # histidine imidazole
    "K": 10.0,  # lysine ε-amine
    "R": 12.0,  # arginine guanidinium
}
_PK_N_TERMINUS: Final[float] = 7.5
# The amino terminus is the one group whose pK depends on the residue that
# carries it; residues not listed take ``_PK_N_TERMINUS``.
_PK_N_TERMINUS_BY_RESIDUE: Final[dict[str, float]] = {
    "A": 7.59,
    "E": 7.7,
    "M": 7.0,
    "P": 8.36,
    "S": 6.93,
    "T": 6.82,
    "V": 7.44,
}
_PK_C_TERMINUS: Final[float] = 3.55


class ChargeModel(TypedDict):
    """The pK values behind ``theoretical_pi`` and ``net_charge_pH7``.

    Carried in every :class:`ProteinProperties` record so that a reported pI
    or charge names the constants it was computed with.
    """

    pk_set: str
    n_terminal_residue: str
    n_terminus_pk: float
    c_terminus_pk: float
    side_chain_pk: dict[str, float]


class ProteinProperties(TypedDict):
    """Derived sequence-chemistry record."""

    length: int
    molecular_weight: float
    theoretical_pi: float
    net_charge_pH7: float
    charge_model: ChargeModel
    gravy: float
    aromaticity: float
    extinction_coefficient_280nm: int
    amino_acid_counts: dict[str, int]


def _count_amino_acids(sequence: str) -> dict[str, int]:
    """Count each standard amino acid + an 'other' bucket for non-standard
    letters (X, B, Z, U, O, gaps, whitespace, …)."""
    counts: dict[str, int] = dict.fromkeys(STANDARD_AA, 0)
    counts["other"] = 0
    for ch in sequence:
        up = ch.upper()
        if up in counts:
            counts[up] += 1
        elif ch.isalpha():
            counts["other"] += 1
        # whitespace / digits silently skipped
    return counts


def molecular_weight(counts: dict[str, int]) -> float:
    """Average molecular weight in Daltons. The common convention is
    sum of residue masses + one water (the polymer has one water more
    than the residues stack)."""
    total = sum(_RESIDUE_MASS.get(aa, 0.0) * n for aa, n in counts.items() if aa != "other")
    return round(total + _WATER, 4) if total > 0 else 0.0


def gravy_index(counts: dict[str, int], length: int) -> float:
    """Grand Average of Hydropathicity. Negative = hydrophilic, positive
    = hydrophobic. Length here excludes 'other' so the index is computed
    over the residues with defined hydropathy."""
    if length <= 0:
        return 0.0
    s = sum(_KYTE_DOOLITTLE.get(aa, 0.0) * n for aa, n in counts.items() if aa != "other")
    return round(s / length, 4)


def aromaticity(counts: dict[str, int], length: int) -> float:
    """Fraction of aromatic residues (F + W + Y)."""
    if length <= 0:
        return 0.0
    aromatic = counts.get("F", 0) + counts.get("W", 0) + counts.get("Y", 0)
    return round(aromatic / length, 4)


def _n_terminus_pk(n_terminal: str | None) -> float:
    """pK of the amino terminus when ``n_terminal`` is the first residue."""
    return _PK_N_TERMINUS_BY_RESIDUE.get((n_terminal or "").upper(), _PK_N_TERMINUS)


def _charge_model(n_terminal: str | None) -> ChargeModel:
    """The pK values applied to a sequence whose first residue is ``n_terminal``."""
    side_chains = {**_PK_SIDE_CHAIN_ACIDIC, **_PK_SIDE_CHAIN_BASIC}
    return ChargeModel(
        pk_set=PK_SET_NAME,
        n_terminal_residue=(n_terminal or "").upper(),
        n_terminus_pk=_n_terminus_pk(n_terminal),
        c_terminus_pk=_PK_C_TERMINUS,
        side_chain_pk={aa: side_chains[aa] for aa in sorted(side_chains)},
    )


def net_charge_at_pH(  # noqa: N802
    counts: dict[str, int],
    pH: float,  # noqa: N803
    *,
    n_terminal: str | None = None,
) -> float:
    """Henderson-Hasselbalch net charge over all ionizable groups
    (N-terminus, C-terminus, and acidic / basic side chains), each treated
    as independent with the fixed pK of the Bjellqvist set.

    ``n_terminal`` is the first residue of the sequence (one letter). It
    selects the residue-specific pK of the amino terminus; without it, or
    for a residue that has no value of its own, the default 7.5 applies.

    The function name and ``pH`` argument deliberately use the standard
    chemistry capitalisation rather than PEP-8 lowercase; the convention
    is universal across pH-related code in computational biology and
    overriding it here would harm readability for the audience.
    """
    charge = 0.0
    # N-terminus contributes a +1 fraction at the N-term pK.
    charge += 1.0 / (1.0 + 10 ** (pH - _n_terminus_pk(n_terminal)))
    # Basic side chains
    for aa, pk in _PK_SIDE_CHAIN_BASIC.items():
        n = counts.get(aa, 0)
        if n:
            charge += n * (1.0 / (1.0 + 10 ** (pH - pk)))
    # C-terminus and acidic side chains contribute negative fractions.
    charge -= 1.0 / (1.0 + 10 ** (_PK_C_TERMINUS - pH))
    for aa, pk in _PK_SIDE_CHAIN_ACIDIC.items():
        n = counts.get(aa, 0)
        if n:
            charge -= n * (1.0 / (1.0 + 10 ** (pk - pH)))
    return charge


def isoelectric_point(counts: dict[str, int], *, n_terminal: str | None = None) -> float:
    """Theoretical pI: pH at which the net charge is zero. Found by
    bisection on [0, 14]; convergence is monotone because net charge is
    a strictly decreasing function of pH on that interval.

    ``n_terminal`` has the meaning it has in :func:`net_charge_at_pH`.
    The whole pH scale is searched, so a strongly acidic or basic
    composition gets its own root rather than an interval bound."""
    lo, hi = 0.0, 14.0
    for _ in range(60):  # 60 iterations gives ~1e-18 precision; overkill
        mid = (lo + hi) / 2.0
        c = net_charge_at_pH(counts, mid, n_terminal=n_terminal)
        if c > 0:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2.0, 2)


def extinction_coefficient_280nm(counts: dict[str, int], cystines: int = 0) -> int:
    """ε at 280 nm in M⁻¹·cm⁻¹ (Pace et al. 1995). Default assumes all
    cysteines reduced; pass ``cystines`` (the count of disulfide bonds,
    NOT free cysteines) to add 125 per S-S bond."""
    return int(5500 * counts.get("W", 0) + 1490 * counts.get("Y", 0) + 125 * cystines)


def compute_protein_properties(sequence: str, *, cystines: int = 0) -> ProteinProperties:
    """Compute the full derived-chemistry record for a protein sequence.

    Args:
      sequence: amino-acid sequence string (standard 20 letters, plus any
        non-standard chars which go into the 'other' bucket).
      cystines: count of disulfide bonds (NOT free cysteines). When 0 the
        extinction coefficient assumes all cysteines reduced.

    Returns:
      A :class:`ProteinProperties` record. ``theoretical_pi`` and
      ``net_charge_pH7`` are computed for the sequence exactly as given,
      first residue included, and ``charge_model`` names the pK values
      that were applied.
    """
    seq = "".join(c for c in sequence if c.isalpha())
    counts = _count_amino_acids(seq)
    length = sum(counts[aa] for aa in STANDARD_AA)  # excludes 'other'
    n_terminal = seq[:1]
    return ProteinProperties(
        length=length,
        molecular_weight=molecular_weight(counts),
        theoretical_pi=isoelectric_point(counts, n_terminal=n_terminal) if length > 0 else 0.0,
        net_charge_pH7=(
            round(net_charge_at_pH(counts, 7.0, n_terminal=n_terminal), 4) if length > 0 else 0.0
        ),
        charge_model=_charge_model(n_terminal),
        gravy=gravy_index(counts, length),
        aromaticity=aromaticity(counts, length),
        extinction_coefficient_280nm=extinction_coefficient_280nm(counts, cystines),
        amino_acid_counts=counts,
    )


__all__ = [
    "PK_SET_NAME",
    "STANDARD_AA",
    "ChargeModel",
    "ProteinProperties",
    "aromaticity",
    "compute_protein_properties",
    "extinction_coefficient_280nm",
    "gravy_index",
    "isoelectric_point",
    "molecular_weight",
    "net_charge_at_pH",
]
