"""Pure-Python protein chemistry primitives.

Computed from the 20-letter amino-acid composition of a sequence.
No external API call — these are derived properties anyone can
recompute from the FASTA. References:

  pK values (Lehninger)        — pI by binary search over net charge
  Kyte-Doolittle hydropathy    — GRAVY (J. Mol. Biol. 157, 105-132, 1982)
  Aromaticity (F + W + Y)      — Lobry & Gautier (1994)
  Extinction coefficient 280nm — Pace et al. (1995): ε = 1490·Trp + 5500·Tyr
                                  (assumes reduced cysteines; +125 per cystine
                                  if disulfide count is supplied)
  Monoisotopic residue masses  — IUPAC, water-loss form (M_residue = M_aa - H2O)

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

# Average residue masses (monoisotopic of the residue, i.e. the amino
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

# pK values for ionizable side chains and termini (Lehninger).
_PK_SIDE_CHAIN_ACIDIC: Final[dict[str, float]] = {
    "C": 8.5,  # cysteine thiol
    "D": 3.9,  # aspartate carboxyl
    "E": 4.07,  # glutamate carboxyl
    "Y": 10.46,  # tyrosine hydroxyl
}
_PK_SIDE_CHAIN_BASIC: Final[dict[str, float]] = {
    "H": 6.04,  # histidine imidazole
    "K": 10.54,  # lysine ε-amine
    "R": 12.48,  # arginine guanidinium
}
_PK_N_TERMINUS: Final[float] = 9.69
_PK_C_TERMINUS: Final[float] = 2.34


class ProteinProperties(TypedDict):
    """Derived sequence-chemistry record."""

    length: int
    molecular_weight: float
    theoretical_pi: float
    net_charge_pH7: float
    gravy: float
    aromaticity: float
    extinction_coefficient_280nm: int
    amino_acid_counts: dict[str, int]


def _count_amino_acids(sequence: str) -> dict[str, int]:
    """Count each standard amino acid + an 'other' bucket for non-standard
    letters (X, B, Z, U, O, gaps, whitespace, …)."""
    counts: dict[str, int] = {aa: 0 for aa in STANDARD_AA}
    counts["other"] = 0
    for ch in sequence.upper():
        if ch in counts:
            counts[ch] += 1
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


def net_charge_at_pH(counts: dict[str, int], pH: float) -> float:  # noqa: N802, N803
    """Henderson-Hasselbalch net charge over all ionizable groups
    (N-terminus, C-terminus, and acidic / basic side chains).

    The function name and ``pH`` argument deliberately use the standard
    chemistry capitalisation rather than PEP-8 lowercase; the convention
    is universal across pH-related code in computational biology and
    overriding it here would harm readability for the audience.
    """
    charge = 0.0
    # N-terminus contributes a +1 fraction at the N-term pK.
    charge += 1.0 / (1.0 + 10 ** (pH - _PK_N_TERMINUS))
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


def isoelectric_point(counts: dict[str, int]) -> float:
    """Theoretical pI: pH at which the net charge is zero. Found by
    bisection on [0, 14]; convergence is monotone because net charge is
    a strictly decreasing function of pH on that interval."""
    lo, hi = 0.0, 14.0
    for _ in range(60):  # 60 iterations gives ~1e-18 precision; overkill
        mid = (lo + hi) / 2.0
        c = net_charge_at_pH(counts, mid)
        if c > 0:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2.0, 2)


def extinction_coefficient_280nm(counts: dict[str, int], cystines: int = 0) -> int:
    """ε at 280 nm in M⁻¹·cm⁻¹ (Pace et al. 1995). Default assumes all
    cysteines reduced; pass ``cystines`` (the count of disulfide bonds,
    NOT free cysteines) to add 125 per S-S bond."""
    return int(1490 * counts.get("W", 0) + 5500 * counts.get("Y", 0) + 125 * cystines)


def compute_protein_properties(sequence: str, *, cystines: int = 0) -> ProteinProperties:
    """Compute the full derived-chemistry record for a protein sequence.

    Args:
      sequence: amino-acid sequence string (standard 20 letters, plus any
        non-standard chars which go into the 'other' bucket).
      cystines: count of disulfide bonds (NOT free cysteines). When 0 the
        extinction coefficient assumes all cysteines reduced.

    Returns:
      A :class:`ProteinProperties` record.
    """
    seq = "".join(c for c in sequence if c.isalpha())
    counts = _count_amino_acids(seq)
    length = sum(counts[aa] for aa in STANDARD_AA)  # excludes 'other'
    return ProteinProperties(
        length=length,
        molecular_weight=molecular_weight(counts),
        theoretical_pi=isoelectric_point(counts) if length > 0 else 0.0,
        net_charge_pH7=round(net_charge_at_pH(counts, 7.0), 4) if length > 0 else 0.0,
        gravy=gravy_index(counts, length),
        aromaticity=aromaticity(counts, length),
        extinction_coefficient_280nm=extinction_coefficient_280nm(counts, cystines),
        amino_acid_counts=counts,
    )


__all__ = [
    "STANDARD_AA",
    "ProteinProperties",
    "aromaticity",
    "compute_protein_properties",
    "extinction_coefficient_280nm",
    "gravy_index",
    "isoelectric_point",
    "molecular_weight",
    "net_charge_at_pH",
]
