"""Truth table for the UniProt accession regex.

UniProt specifies accession format as:
  [OPQ][0-9][A-Z, 0-9]{3}[0-9]            (6 chars)
  [A-NR-Z][0-9]([A-Z][A-Z, 0-9]{2}[0-9]){1,2}  (6 or 10 chars)

Reference: https://www.uniprot.org/help/accession_numbers
"""

from __future__ import annotations

import pytest

from uniprot_mcp.client import ACCESSION_RE


@pytest.mark.parametrize(
    "accession",
    [
        "P04637",  # p53
        "P38398",  # BRCA1
        "P00533",  # EGFR
        "P01308",  # Insulin
        "Q8IWU6",  # random Q-prefix 6-char
        "O95467",  # O-prefix
        "A0A1B2C3D4",  # 10-char extended
        "A2BC19",  # 6-char non-OPQ
    ],
)
def test_valid_accessions_match(accession: str) -> None:
    assert ACCESSION_RE.match(accession), f"expected {accession!r} to match"


@pytest.mark.parametrize(
    "junk",
    [
        "",  # empty
        "p04637",  # lowercase
        "123456",  # digits only
        "INVALIDXYZ",  # all letters, wrong pattern
        "P0463",  # too short
        "P046377",  # 7 chars, not a valid length
        "A0A1B2C3D",  # 9 chars, not a valid length
        "A0A1B2C3D4E",  # 11 chars
        "P04637 ",  # trailing space
        " P04637",  # leading space
        "P04637\n",  # trailing newline
        "P04637;P38398",  # separator leaked in
    ],
)
def test_invalid_accessions_reject(junk: str) -> None:
    assert not ACCESSION_RE.match(junk), f"expected {junk!r} to NOT match"


def test_regex_is_anchored() -> None:
    """Regex must reject strings with valid-looking prefixes/suffixes."""
    assert not ACCESSION_RE.match("XP04637")
    assert not ACCESSION_RE.match("P04637X")
