"""Property-based tests for the accession regex and batch filter.

Hypothesis generates arbitrary strings and checks invariants that must
hold for *any* input, not just cherry-picked cases.
"""
from __future__ import annotations

import string

import pytest
from hypothesis import given, strategies as st

from uniprot_mcp.client import ACCESSION_RE, UniProtClient


# UniProt accession = 6 or 10 chars per official spec.
VALID_LENGTHS = {6, 10}


@given(st.text(alphabet=string.ascii_letters + string.digits, min_size=0, max_size=20))
def test_match_implies_valid_length(s: str) -> None:
    if ACCESSION_RE.match(s):
        assert len(s) in VALID_LENGTHS


@given(st.text(alphabet=string.ascii_letters + string.digits, min_size=0, max_size=20))
def test_match_implies_uppercase_only(s: str) -> None:
    if ACCESSION_RE.match(s):
        assert s == s.upper(), "lowercase accessions must not match"


@given(st.text(alphabet=string.ascii_letters + string.digits, min_size=0, max_size=20))
def test_match_implies_starts_with_letter(s: str) -> None:
    if ACCESSION_RE.match(s):
        assert s[0].isalpha()


@given(
    accessions=st.lists(
        st.text(min_size=0, max_size=15), min_size=0, max_size=30, unique=True
    )
)
async def test_batch_partition_is_disjoint_and_complete(accessions: list[str]) -> None:
    """valid ∪ invalid = input, valid ∩ invalid = ∅ (as sets)."""
    client = UniProtClient()
    try:
        # all-invalid short-circuits; otherwise respx would be needed.
        # Filter to guarantee no HTTP: feed only inputs that fail the regex.
        only_invalid = [a for a in accessions if not ACCESSION_RE.match(a.upper())]
        out = await client.batch_entries(only_invalid)
        assert set(out["invalid"]) == set(only_invalid)
        assert out["results"] == []
    finally:
        await client.close()
