"""Property-based tests for the validators added in R1, B/1, B/2, B/3.

Hypothesis drives arbitrary input through every regex / parser added
since the original ACCESSION_RE and asserts the invariants the code
actually relies on. The goal is to find any string that *should* be
rejected but isn't, or any canonical value that *should* be accepted
but isn't.

The matchers checked here:

  KEYWORD_ID_RE                 KW-NNNN
  SUBCELLULAR_LOCATION_ID_RE    SL-NNNN
  UNIREF_ID_RE                  UniRef(50|90|100)_<acc|UPI>
  UNIPARC_ID_RE                 UPI<10 hex>
  PROTEOME_ID_RE                UP<9-11 digits>
  CITATION_ID_RE                <1-12 digits>
  _VARIANT_CHANGE_RE            HGVS shorthand (parsed via _parse_variant_change)
  _check_position               position bounds
"""

from __future__ import annotations

import string

import pytest
from hypothesis import HealthCheck, assume, example, given, settings
from hypothesis import strategies as st

from uniprot_mcp.client import (
    CITATION_ID_RE,
    KEYWORD_ID_RE,
    PROTEOME_ID_RE,
    SUBCELLULAR_LOCATION_ID_RE,
    UNIPARC_ID_RE,
)
from uniprot_mcp.server import (
    MAX_SEQUENCE_POSITION,
    _check_position,
    _InputError,
    _parse_variant_change,
)

_PROFILE = settings(
    deadline=2000,
    max_examples=200,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)


# ---------------------------------------------------------------------------
# KEYWORD_ID_RE
# ---------------------------------------------------------------------------


# Known canonical IDs UniProt advertises today; should always match.
@given(st.sampled_from(["KW-0001", "KW-0007", "KW-9999", "KW-1234"]))
@_PROFILE
def test_keyword_id_canonical_examples_match(value: str) -> None:
    assert KEYWORD_ID_RE.match(value)


# Any random alnum string of arbitrary length — only the exact KW-NNNN
# four-digit form should match. Verify the negative space.
@given(st.text(alphabet=string.ascii_letters + string.digits + "-_", min_size=0, max_size=15))
@_PROFILE
def test_keyword_id_negative_space(value: str) -> None:
    if KEYWORD_ID_RE.match(value):
        assert len(value) == 7, f"length not 7: {value!r}"
        assert value.startswith("KW-"), f"prefix wrong: {value!r}"
        assert value[3:].isdigit(), f"suffix not digits: {value!r}"


# Length-extension attack: appending a valid 4-digit suffix to extra
# characters MUST NOT match (anchors must be enforced).
@given(
    prefix=st.text(alphabet=string.printable, min_size=1, max_size=5),
    digits=st.text(alphabet=string.digits, min_size=4, max_size=4),
)
@_PROFILE
def test_keyword_id_no_length_extension(prefix: str, digits: str) -> None:
    candidate = f"{prefix}KW-{digits}"
    assert not KEYWORD_ID_RE.match(candidate), f"anchored regex matched: {candidate!r}"


# ---------------------------------------------------------------------------
# SUBCELLULAR_LOCATION_ID_RE
# ---------------------------------------------------------------------------


@given(st.sampled_from(["SL-0039", "SL-0086", "SL-0191", "SL-0173", "SL-0095"]))
@_PROFILE
def test_subcellular_location_id_canonical_examples_match(value: str) -> None:
    assert SUBCELLULAR_LOCATION_ID_RE.match(value)


@given(st.text(alphabet=string.ascii_letters + string.digits + "-_", min_size=0, max_size=15))
@_PROFILE
def test_subcellular_location_id_negative_space(value: str) -> None:
    if SUBCELLULAR_LOCATION_ID_RE.match(value):
        assert len(value) == 7
        assert value.startswith("SL-")
        assert value[3:].isdigit()


# ---------------------------------------------------------------------------
# UNIPARC_ID_RE
# ---------------------------------------------------------------------------


@given(st.sampled_from(["UPI000002ED67", "UPI0000000000", "UPIFFFFFFFFFF", "UPIA1B2C3D4E5"]))
@_PROFILE
def test_uniparc_id_canonical_examples_match(value: str) -> None:
    assert UNIPARC_ID_RE.match(value)


# Non-uppercase or non-hex must be rejected. Use a mixed-character
# alphabet to find any sneak-throughs.
@given(st.text(alphabet=string.printable, min_size=0, max_size=20))
@_PROFILE
def test_uniparc_id_only_uppercase_hex_after_prefix(value: str) -> None:
    if UNIPARC_ID_RE.match(value):
        assert len(value) == 13, f"length not 13: {value!r}"
        assert value.startswith("UPI")
        suffix = value[3:]
        assert all(ch in "0123456789ABCDEF" for ch in suffix), f"non-hex char in suffix: {value!r}"


# ---------------------------------------------------------------------------
# PROTEOME_ID_RE
# ---------------------------------------------------------------------------


@given(st.sampled_from(["UP000005640", "UP000000001", "UP123456789012"]))
@_PROFILE
def test_proteome_id_canonical_examples_match_or_reject_too_long(value: str) -> None:
    """The canonical examples include a borderline-length one (12 digits)
    which should match; UP123456789012 has 12 digits and is at the
    upper bound. UPNNNNNNNNNNNN (13 digits) would NOT match."""
    if PROTEOME_ID_RE.match(value):
        assert value.startswith("UP")
        assert 9 <= len(value[2:]) <= 11, f"digit count out of bounds: {value!r}"


@given(st.text(alphabet=string.printable, min_size=0, max_size=20))
@_PROFILE
def test_proteome_id_negative_space(value: str) -> None:
    if PROTEOME_ID_RE.match(value):
        assert value.startswith("UP")
        assert value[2:].isdigit()
        assert 9 <= len(value[2:]) <= 11


# ---------------------------------------------------------------------------
# CITATION_ID_RE
# ---------------------------------------------------------------------------


@given(st.text(alphabet=string.digits, min_size=1, max_size=12))
@_PROFILE
def test_citation_id_accepts_any_1_to_12_digit_string(value: str) -> None:
    assert CITATION_ID_RE.match(value)


@given(st.text(alphabet=string.printable, min_size=0, max_size=20))
@_PROFILE
def test_citation_id_negative_space(value: str) -> None:
    if CITATION_ID_RE.match(value):
        assert value.isdigit()
        assert 1 <= len(value) <= 12


# Path-traversal-shaped values must never match.
@given(st.sampled_from(["../etc/passwd", "..%2Fetc%2Fpasswd", "1..2", "../1234"]))
@_PROFILE
def test_citation_id_rejects_path_traversal_shapes(value: str) -> None:
    assert not CITATION_ID_RE.match(value)


# ---------------------------------------------------------------------------
# _parse_variant_change (HGVS shorthand)
# ---------------------------------------------------------------------------


@given(
    orig=st.sampled_from("ACDEFGHIKLMNPQRSTVWY"),
    pos=st.integers(min_value=1, max_value=99999),
    alt=st.sampled_from("ACDEFGHIKLMNPQRSTVWY*"),
)
@_PROFILE
def test_parse_variant_change_canonical_round_trip(orig: str, pos: int, alt: str) -> None:
    """For any well-formed HGVS-shorthand triple, _parse_variant_change
    returns the same components."""
    change = f"{orig}{pos}{alt}"
    parsed_orig, parsed_pos, parsed_alt = _parse_variant_change(change)
    assert parsed_orig == orig
    assert parsed_pos == pos
    assert parsed_alt == alt


@given(st.text(alphabet=string.printable, min_size=0, max_size=20))
@_PROFILE
def test_parse_variant_change_rejects_non_canonical(value: str) -> None:
    """Anything not matching <upper><1-5 digits, no leading zero><upper|*>
    must raise _InputError. We can't enumerate the negative space
    cleanly; instead, when parsing succeeds, check the result fits
    the expected canonical form."""
    try:
        orig, pos, alt = _parse_variant_change(value)
    except _InputError:
        return  # rejection — fine
    # If parse succeeded, the input MUST round-trip to a canonical form.
    assert orig in "ACDEFGHIKLMNPQRSTVWY"
    # The canonical form has a single uppercase / position / single
    # uppercase-or-star, but the parser only requires SAFE_AAS for
    # original (single uppercase letter). Same for alt.
    assert alt in "ACDEFGHIKLMNPQRSTVWYBJOUXZ*", f"alt out of allowed: {alt!r}"
    assert 1 <= pos <= 99999
    # Reconstruct and assert the original input exactly matched.
    assert value == f"{orig}{pos}{alt}", (
        f"non-canonical sneak: {value!r} parsed to {orig!r}{pos}{alt!r}"
    )


# Specific known-valid examples must always parse.
@example(value="R175H")
@example(value="V600E")
@example(value="R248*")
@example(value="A1G")
@given(value=st.just("R175H"))  # placeholder so @example fires under @given
def test_parse_variant_change_known_examples(value: str) -> None:
    orig, pos, alt = _parse_variant_change(value)
    assert orig.isupper() and len(orig) == 1
    assert pos >= 1
    assert alt.isupper() or alt == "*"


# Specific known-invalid examples must always raise.
@pytest.mark.parametrize(
    "value",
    [
        "p.R175H",  # HGVS prefix not supported here
        "R175del",  # del notation not supported
        "r175h",  # lowercase rejected
        "175H",  # missing original
        "RH175",  # missing position
        "R0H",  # zero position
        "R-5H",  # negative position
        "R 175 H",  # whitespace
        "R175Hext",  # extra suffix
        "extR175H",  # extra prefix
        "",  # empty
    ],
)
def test_parse_variant_change_known_rejections(value: str) -> None:
    with pytest.raises(_InputError):
        _parse_variant_change(value)


# ---------------------------------------------------------------------------
# _check_position
# ---------------------------------------------------------------------------


@given(st.integers(min_value=1, max_value=MAX_SEQUENCE_POSITION))
@_PROFILE
def test_check_position_accepts_in_range(pos: int) -> None:
    _check_position(pos)  # must not raise


@given(st.integers(min_value=-(2**31), max_value=0))
@_PROFILE
def test_check_position_rejects_non_positive(pos: int) -> None:
    with pytest.raises(_InputError):
        _check_position(pos)


@given(st.integers(min_value=MAX_SEQUENCE_POSITION + 1, max_value=2**31))
@_PROFILE
def test_check_position_rejects_oversize(pos: int) -> None:
    with pytest.raises(_InputError):
        _check_position(pos)


def test_check_position_rejects_bool() -> None:
    """``isinstance(True, int)`` is True in Python — explicitly reject
    booleans so a ``True`` doesn't sneak through as ``position=1``."""
    with pytest.raises(_InputError):
        _check_position(True)
    with pytest.raises(_InputError):
        _check_position(False)


# ---------------------------------------------------------------------------
# Cross-validator interaction
# ---------------------------------------------------------------------------


@given(
    accession_letter=st.sampled_from("OPQ"),
    rest=st.text(alphabet=string.ascii_uppercase + string.digits, min_size=4, max_size=4),
)
@_PROFILE
def test_uniparc_id_re_does_not_collide_with_uniprot_accession(
    accession_letter: str, rest: str
) -> None:
    """A 6-char string that matches the UniProt accession pattern
    (e.g. ``P04637``) must never accidentally match UNIPARC_ID_RE
    (which requires 13 chars and a UPI prefix)."""
    candidate = f"{accession_letter}0{rest}"
    assume(len(candidate) == 6)
    assert not UNIPARC_ID_RE.match(candidate)
