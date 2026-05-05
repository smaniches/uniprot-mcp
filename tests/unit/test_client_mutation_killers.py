"""Surgical tests targeting the operator- and constant-level mutations
that the existing client.py test suite does not catch.

The 2026-04-27 mutation-matrix baseline (run 25015528542) reported
218 killed / 152 survived = 58.9% raw kill rate on
``src/uniprot_mcp/client.py``. The bulk of the survivors are
constant flips inside the module-level URL and User-Agent strings,
the seven regex identifier patterns, the magic numbers
(``TIMEOUT=30.0``, ``MAX_RETRIES=3``, ``MAX_RETRY_AFTER_SECONDS=120.0``),
the ``parse_retry_after`` fallback formula, and the
``canonical_response_hash`` JSON-canonicalisation logic.

This file pins each constant and behaviour via direct-equality
assertions, regex match/no-match parametrisation, and snapshot
hashes computed once against the unmutated source on 2026-04-28.
Importing source-derived values would defeat the kill — when mutmut
mutates a constant, both sides of the assertion would shift
together. The literals below are therefore typed by hand from a
one-time computation, not derived from the live module.

Why this matters for adoption: a wrong upstream URL or User-Agent
string that sneaks past the existing tests but mis-routes a real
request is exactly the kind of silent correctness defect a
bio-pharma reviewer would flag. These tests close that gap.

Tolerances:
  - String constants → exact equality
  - Numeric constants → exact equality (no float-repr noise on whole
    numbers like 30.0, 120.0)
  - Regex patterns → parametrised valid/invalid examples; any
    character flip in the pattern flips at least one example
  - Hash digests → exact 64-character hex equality
  - parse_retry_after numeric outputs → exact equality (the function
    returns clean values: float(int_string), the cap 120.0, or
    1.5**(attempt+1) which is exact for small attempts)
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import httpx
import pytest

from uniprot_mcp.client import (
    ACCESSION_RE,
    ALPHAFOLD_API_BASE,
    BASE_URL,
    CITATION_ID_RE,
    KEYWORD_ID_RE,
    MAX_RETRIES,
    MAX_RETRY_AFTER_SECONDS,
    NCBI_EUTILS_BASE,
    PIN_RELEASE_ENV,
    PROTEOME_ID_RE,
    SOURCE_NAME,
    SUBCELLULAR_LOCATION_ID_RE,
    TIMEOUT,
    UA,
    UNIPARC_ID_RE,
    UNIREF_ID_RE,
    UNIREF_IDENTITY_TIERS,
    Provenance,
    ReleaseMismatchError,
    UniProtClient,
    _extract_provenance,
    canonical_response_hash,
    parse_retry_after,
)

# ---------------------------------------------------------------------------
# Module-level constants — pin via direct equality
# ---------------------------------------------------------------------------


def test_base_url_is_uniprot_rest_https() -> None:
    """Mutating BASE_URL (e.g., dropping 'https' → 'http' or removing
    the dot in 'rest.uniprot.org') would route requests to the wrong
    origin. Pin to the exact string."""
    assert BASE_URL == "https://rest.uniprot.org"


def test_alphafold_api_base_is_ebi_https() -> None:
    """AlphaFold cross-origin endpoint. Pin to the exact string."""
    assert ALPHAFOLD_API_BASE == "https://alphafold.ebi.ac.uk"


def test_ncbi_eutils_base_is_correct() -> None:
    """NCBI eutils cross-origin endpoint. Pin to the exact string."""
    assert NCBI_EUTILS_BASE == "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def test_timeout_is_thirty_seconds() -> None:
    """TIMEOUT=30.0 is the per-request budget. A mutation to 0, 1, or
    300 changes runtime behaviour visibly in any timeout-sensitive
    test."""
    assert TIMEOUT == 30.0


def test_max_retries_is_three() -> None:
    """MAX_RETRIES=3 controls the retry loop in _req(). Mutation to 0
    or 4 would change the loop bounds in any retry-counted test."""
    assert MAX_RETRIES == 3


def test_max_retry_after_seconds_is_one_twenty() -> None:
    """The Retry-After cap. Mutation changes parse_retry_after's
    clamping behaviour."""
    assert MAX_RETRY_AFTER_SECONDS == 120.0


def test_user_agent_string_is_pinned_exactly() -> None:
    """UA is logged at the upstream service. The version-string portion
    is bumped lock-step with releases (currently 1.1.3). Pin both the
    product token and the URL hint."""
    assert UA == "uniprot-mcp/1.1.3 (+https://github.com/smaniches/uniprot-mcp)"


def test_source_name_is_uniprot() -> None:
    """SOURCE_NAME goes into every Provenance record's `source` field."""
    assert SOURCE_NAME == "UniProt"


def test_pin_release_env_var_name() -> None:
    """The exact env var name UNIPROT_PIN_RELEASE is documented in
    README + docs; mutating it would break the documented contract."""
    assert PIN_RELEASE_ENV == "UNIPROT_PIN_RELEASE"


def test_uniref_identity_tiers_are_50_90_100() -> None:
    """UniRef supports three identity tiers. The tuple order matters
    for ergonomics (smallest first). Pin both contents and order."""
    assert UNIREF_IDENTITY_TIERS == ("50", "90", "100")
    assert len(UNIREF_IDENTITY_TIERS) == 3


# ---------------------------------------------------------------------------
# ACCESSION_RE — UniProt accession format
# ---------------------------------------------------------------------------

# The official UniProt accession spec (https://www.uniprot.org/help/accession_numbers):
#   Pattern: [OPQ][0-9][A-Z0-9]{3}[0-9]
#         OR [A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}
# Each example below is hand-picked to exercise different parts of the
# alternation; mutating the regex at any character flips at least one
# of these examples.
_ACCESSION_VALID = [
    "P04637",  # branch 1: P0[A-Z0-9]{3}[0-9] - classic 6-char
    "Q9Y6K9",  # branch 1: Q9[A-Z0-9]{3}[0-9]
    "O00187",  # branch 1: O0[A-Z0-9]{3}[0-9]
    "A0A024R1R8",  # branch 2: 10-char extended (one repetition)
    "A2BC19",  # branch 2: 6-char alternative
    "P12345",  # branch 1
    "P0DPI2",  # branch 1
]

_ACCESSION_INVALID = [
    "p04637",  # lowercase
    "P0463",  # too short (5 chars)
    "P046377",  # 7 chars (illegal length: must be 6 or 10)
    "XXXXX",  # no digits
    "",  # empty
    "12345",  # all digits
    "P-04637",  # dash inside
    " P04637",  # leading space
    "P04637 ",  # trailing space
    "P0463A",  # branch 1 ends in non-digit
    "A0",  # too short
    "P_04637",  # underscore inside
]


@pytest.mark.parametrize("accession", _ACCESSION_VALID)
def test_accession_re_matches_valid(accession: str) -> None:
    """Each valid example must match. Pins the alternation branches and
    character classes in ACCESSION_RE."""
    assert ACCESSION_RE.match(accession) is not None, (
        f"ACCESSION_RE failed to match valid accession {accession!r}"
    )


@pytest.mark.parametrize("bad", _ACCESSION_INVALID)
def test_accession_re_rejects_invalid(bad: str) -> None:
    """Each invalid example must NOT match. Pins the anchors (\\A...\\Z)
    and length constraints in ACCESSION_RE."""
    assert ACCESSION_RE.match(bad) is None, f"ACCESSION_RE wrongly matched invalid input {bad!r}"


# ---------------------------------------------------------------------------
# KEYWORD_ID_RE — KW-NNNN
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("v", ["KW-0007", "KW-0001", "KW-9999", "KW-0000"])
def test_keyword_id_re_matches_valid(v: str) -> None:
    assert KEYWORD_ID_RE.match(v) is not None


@pytest.mark.parametrize(
    "v",
    [
        "KW-007",  # 3 digits (not 4)
        "KW-00007",  # 5 digits (not 4)
        "kw-0007",  # lowercase prefix
        "KW-ABCD",  # letters in slot
        "SL-0007",  # wrong prefix
        "",
        "KW-0007 ",  # trailing space (anchor test)
        " KW-0007",  # leading space
        "KW0007",  # missing dash
    ],
)
def test_keyword_id_re_rejects_invalid(v: str) -> None:
    assert KEYWORD_ID_RE.match(v) is None


# ---------------------------------------------------------------------------
# SUBCELLULAR_LOCATION_ID_RE — SL-NNNN
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("v", ["SL-0086", "SL-0001", "SL-9999", "SL-0039", "SL-0191"])
def test_subcellular_id_re_matches_valid(v: str) -> None:
    assert SUBCELLULAR_LOCATION_ID_RE.match(v) is not None


@pytest.mark.parametrize(
    "v",
    [
        "sl-0086",
        "SL-0",
        "KW-0086",
        "SL0086",
        "SL-00086",
        "",
        "SL-008",
    ],
)
def test_subcellular_id_re_rejects_invalid(v: str) -> None:
    assert SUBCELLULAR_LOCATION_ID_RE.match(v) is None


# ---------------------------------------------------------------------------
# UNIREF_ID_RE — UniRef{50,90,100}_<accession or UPI>
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v",
    [
        "UniRef50_P04637",
        "UniRef90_Q9Y6K9",
        "UniRef100_A0A024R1R8",
        "UniRef50_UPI0000ABCDEF",
        "UniRef90_O00187",
    ],
)
def test_uniref_id_re_matches_valid(v: str) -> None:
    """Pins the three identity tiers (50/90/100), the underscore
    separator, and the suffix alternation (accession or UPI)."""
    assert UNIREF_ID_RE.match(v) is not None


@pytest.mark.parametrize(
    "v",
    [
        "UniRef25_P04637",  # invalid tier
        "uniref50_P04637",  # lowercase prefix
        "UniRef50_p04637",  # lowercase suffix
        "UniRef50_",  # missing suffix
        "P04637",  # missing UniRef prefix
        "UniRef50_UPI0000ABCDEG",  # G is not a hex char
        "UniRef50P04637",  # missing underscore
        "",
    ],
)
def test_uniref_id_re_rejects_invalid(v: str) -> None:
    assert UNIREF_ID_RE.match(v) is None


# ---------------------------------------------------------------------------
# UNIPARC_ID_RE — UPI<10 hex chars>
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v",
    [
        "UPI0000000001",
        "UPIABCDEF1234",
        "UPI0123456789",
        "UPIFFFFFFFFFF",
    ],
)
def test_uniparc_id_re_matches_valid(v: str) -> None:
    assert UNIPARC_ID_RE.match(v) is not None


@pytest.mark.parametrize(
    "v",
    [
        "UPI",  # no hex tail
        "UPI0000",  # 4 hex chars (not 10)
        "UPI0000ABCDEFG",  # 11 chars
        "upi0000ABCDEF",  # lowercase prefix
        "UPI000abcdef0",  # lowercase hex
        "UPI0000ABCDEZ",  # Z is not [A-F0-9]
    ],
)
def test_uniparc_id_re_rejects_invalid(v: str) -> None:
    assert UNIPARC_ID_RE.match(v) is None


# ---------------------------------------------------------------------------
# PROTEOME_ID_RE — UP[0-9]{9,11}
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "v",
    [
        "UP000005640",  # 9 digits
        "UP000000001",  # 9 digits
        "UP00000000000",  # 11 digits
    ],
)
def test_proteome_id_re_matches_valid(v: str) -> None:
    assert PROTEOME_ID_RE.match(v) is not None


@pytest.mark.parametrize(
    "v",
    [
        "UP",  # no digits
        "UP12345678",  # 8 digits (not 9-11)
        "up000005640",  # lowercase
        "UP000005640A",  # trailing letter
        "UP000000000000",  # 12 digits
    ],
)
def test_proteome_id_re_rejects_invalid(v: str) -> None:
    assert PROTEOME_ID_RE.match(v) is None


# ---------------------------------------------------------------------------
# CITATION_ID_RE — [0-9]{1,12}
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("v", ["1", "12345", "12345678", "999999999999"])
def test_citation_id_re_matches_valid(v: str) -> None:
    assert CITATION_ID_RE.match(v) is not None


@pytest.mark.parametrize(
    "v",
    [
        "",
        "abc",
        "123abc",
        "1234567890123",  # 13 digits
        "1.5",
        "-1",
        " 123",
        "123 ",
    ],
)
def test_citation_id_re_rejects_invalid(v: str) -> None:
    assert CITATION_ID_RE.match(v) is None


# ---------------------------------------------------------------------------
# parse_retry_after — comprehensive coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,attempt,expected",
    [
        # Missing/empty → fallback = 1.5**(attempt+1)
        (None, 0, 1.5),
        (None, 1, 2.25),
        (None, 2, 3.375),
        ("", 0, 1.5),
        ("", 1, 2.25),
        # Integer-string delta-seconds (passthrough)
        ("0", 0, 0.0),
        ("1", 0, 1.0),
        ("30", 0, 30.0),
        ("60", 5, 60.0),
        ("119", 0, 119.0),
        # Cap at MAX_RETRY_AFTER_SECONDS = 120.0
        ("120", 0, 120.0),
        ("121", 0, 120.0),
        ("99999", 0, 120.0),
        # Malformed → fallback
        ("not-a-number", 0, 1.5),
        ("garbage 999", 0, 1.5),
        ("abc", 1, 2.25),
    ],
)
def test_parse_retry_after_pinned_outputs(value: str | None, attempt: int, expected: float) -> None:
    """Pin parse_retry_after's full decision tree: passthrough, clamp,
    fallback."""
    result = parse_retry_after(value, attempt)
    assert result == expected, (
        f"parse_retry_after({value!r}, {attempt}) returned {result}, expected {expected}"
    )


def test_parse_retry_after_fallback_uses_one_point_five_base() -> None:
    """The fallback is 1.5**(attempt+1). A mutation of the base (e.g.,
    1.5 → 2.0) would shift the fallback values."""
    assert parse_retry_after(None, 3) == 1.5**4
    assert parse_retry_after(None, 3) == 5.0625


def test_parse_retry_after_http_date_in_past_clamps_to_zero() -> None:
    """HTTP-date earlier than now → negative delta → clamped to 0.0."""
    # An RFC 7231 IMF-fixdate from 2020 is definitely in the past.
    out = parse_retry_after("Wed, 21 Oct 2020 07:28:00 GMT", 0)
    assert out == 0.0


def test_parse_retry_after_caps_at_max_constant() -> None:
    """Confirms parse_retry_after consults the same MAX_RETRY_AFTER_SECONDS
    constant (120.0). Mutating MAX_RETRY_AFTER_SECONDS changes the cap."""
    assert parse_retry_after("99999", 0) == MAX_RETRY_AFTER_SECONDS == 120.0


# ---------------------------------------------------------------------------
# canonical_response_hash — pin sort_keys + separators behaviour
# ---------------------------------------------------------------------------


def _json_response(body: str) -> httpx.Response:
    """Build an httpx.Response with Content-Type application/json."""
    req = httpx.Request("GET", "https://rest.uniprot.org/x")
    return httpx.Response(
        200, content=body.encode("utf-8"), headers={"content-type": "application/json"}, request=req
    )


def _text_response(body: str | bytes, ctype: str = "text/plain") -> httpx.Response:
    req = httpx.Request("GET", "https://rest.uniprot.org/x")
    if isinstance(body, str):
        body = body.encode("utf-8")
    return httpx.Response(200, content=body, headers={"content-type": ctype}, request=req)


# Hardcoded SHA-256 hex digests computed against the unmutated source on
# 2026-04-28. Any mutation of canonical_response_hash's body (the
# sort_keys flag, the separators tuple, the encoding, the JSON
# detection branch) shifts at least one of these.
_CANONICAL_AB12 = "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
_RAW_HELLO = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
_RAW_FASTA_P53 = "493c7dd53e8df3774af03562c49e87d5b01eb66b3c1206a1e15bb57a406a1961"
_EMPTY_BYTES = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
_UNICODE_JSON = "9c89561e273fff01e91f2c4344a1a4e78cff571e827bee15ca5a6c0ab4ec9988"


def test_canonical_response_hash_simple_json() -> None:
    """JSON {a:1, b:2} → canonical {'a':1,'b':2} → known sha256."""
    r = _json_response('{"a": 1, "b": 2}')
    assert canonical_response_hash(r) == _CANONICAL_AB12


def test_canonical_response_hash_json_key_order_invariant() -> None:
    """Same content, different key order → same hash. This is the
    headline feature: insignificant key-order differences within a
    UniProt release don't break verification."""
    r1 = _json_response('{"a": 1, "b": 2}')
    r2 = _json_response('{"b": 2, "a": 1}')
    assert canonical_response_hash(r1) == canonical_response_hash(r2)


def test_canonical_response_hash_json_whitespace_invariant() -> None:
    """sort_keys + separators=(',',':') strips JSON whitespace."""
    r1 = _json_response('{"a": 1, "b": 2}')
    r2 = _json_response('{"a":1,"b":2}')
    assert canonical_response_hash(r1) == canonical_response_hash(r2)


def test_canonical_response_hash_json_real_content_change_fails() -> None:
    """Different content → different hash."""
    r1 = _json_response('{"a": 1, "b": 2}')
    r2 = _json_response('{"a": 1, "b": 3}')
    assert canonical_response_hash(r1) != canonical_response_hash(r2)


def test_canonical_response_hash_plain_text_uses_raw_bytes() -> None:
    """Non-JSON content → raw bytes hash, no canonicalisation."""
    r = _text_response("hello", "text/plain")
    assert canonical_response_hash(r) == _RAW_HELLO


def test_canonical_response_hash_fasta_uses_raw_bytes() -> None:
    """FASTA (text/plain;format=fasta) is NOT JSON → raw bytes hash."""
    fasta = ">sp|P04637|P53_HUMAN\nMEEPQSDPSV\n"
    r = _text_response(fasta, "text/plain;format=fasta")
    assert canonical_response_hash(r) == _RAW_FASTA_P53


def test_canonical_response_hash_unicode_in_json() -> None:
    """ensure_ascii=False lets non-ASCII pass through unescaped.
    A mutation flipping ensure_ascii to True would change the hash."""
    r = _json_response('{"name": "protéine"}')
    assert canonical_response_hash(r) == _UNICODE_JSON


def test_canonical_response_hash_empty_body_falls_back_to_raw() -> None:
    """Empty body claiming Content-Type json: response.json() raises;
    fall-through hashes the raw bytes (sha256 of empty = e3b0c4...)."""
    r = _text_response(b"", "application/json")
    assert canonical_response_hash(r) == _EMPTY_BYTES


def test_canonical_response_hash_invalid_json_falls_back_to_raw() -> None:
    """JSON content-type but body is not parseable: fall-through hashes
    the raw bytes."""
    r = _text_response(b"not valid json {", "application/json")
    expected = hashlib.sha256(b"not valid json {").hexdigest()
    assert canonical_response_hash(r) == expected


def test_canonical_response_hash_returns_64_char_hex() -> None:
    """Sanity: sha256 hex digests are always 64 chars [0-9a-f]."""
    r = _json_response('{"a": 1}')
    h = canonical_response_hash(r)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_canonical_response_hash_json_sort_keys_is_actually_used() -> None:
    """If sort_keys were mutated to False, the hash would depend on
    insertion order. With sort_keys=True both these inputs hash the
    same. The previous "key_order_invariant" test asserts equality;
    this one asserts the EXACT canonical hash matches the
    sort_keys=True canonicalisation (kills a sort_keys=False
    mutation that happens to produce the same hash on a particular
    pair)."""
    canonical = json.dumps({"a": 1, "b": 2}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected_hash = hashlib.sha256(canonical).hexdigest()
    r = _json_response('{"b": 2, "a": 1}')
    assert canonical_response_hash(r) == expected_hash


# ---------------------------------------------------------------------------
# _extract_provenance — pin the Provenance TypedDict construction
# ---------------------------------------------------------------------------


_FIXED_NOW = datetime(2026, 4, 28, 12, 0, 0, tzinfo=UTC)
_FIXED_RETRIEVED_AT = "2026-04-28T12:00:00Z"


def _resp_with_url_and_headers(url: str, **headers: str) -> httpx.Response:
    req = httpx.Request("GET", url)
    return httpx.Response(200, content=b"{}", headers=headers, request=req)


def test_extract_provenance_full_headers() -> None:
    """Both X-UniProt-Release and X-UniProt-Release-Date present."""
    r = _resp_with_url_and_headers(
        "https://rest.uniprot.org/uniprotkb/P04637",
        **{
            "content-type": "application/json",
            "X-UniProt-Release": "2026_02",
            "X-UniProt-Release-Date": "2026-04-15",
        },
    )
    p = _extract_provenance(r, now=_FIXED_NOW)
    assert p["source"] == "UniProt"
    assert p["release"] == "2026_02"
    assert p["release_date"] == "2026-04-15"
    assert p["retrieved_at"] == _FIXED_RETRIEVED_AT
    assert p["url"] == "https://rest.uniprot.org/uniprotkb/P04637"
    # response_sha256 of canonical empty JSON object {}
    assert (
        p["response_sha256"] == "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
    )


def test_extract_provenance_no_release_headers() -> None:
    """Both release headers absent → release/release_date are None."""
    r = _resp_with_url_and_headers(
        "https://rest.uniprot.org/x", **{"content-type": "application/json"}
    )
    p = _extract_provenance(r, now=_FIXED_NOW)
    assert p["release"] is None
    assert p["release_date"] is None
    assert p["source"] == "UniProt"
    assert p["retrieved_at"] == _FIXED_RETRIEVED_AT


def test_extract_provenance_partial_release_only() -> None:
    """Release present, release_date absent."""
    r = _resp_with_url_and_headers(
        "https://rest.uniprot.org/x",
        **{"content-type": "application/json", "X-UniProt-Release": "2026_02"},
    )
    p = _extract_provenance(r, now=_FIXED_NOW)
    assert p["release"] == "2026_02"
    assert p["release_date"] is None


def test_extract_provenance_retrieved_at_format_is_iso_z_seconds() -> None:
    """retrieved_at format: 'YYYY-MM-DDTHH:MM:SSZ' (Z suffix, second
    precision). A mutation flipping the format string changes this."""
    r = _resp_with_url_and_headers(
        "https://rest.uniprot.org/x", **{"content-type": "application/json"}
    )
    p = _extract_provenance(r, now=datetime(2030, 1, 5, 4, 3, 2, tzinfo=UTC))
    assert p["retrieved_at"] == "2030-01-05T04:03:02Z"


# ---------------------------------------------------------------------------
# ReleaseMismatchError — pin the message format
# ---------------------------------------------------------------------------


def test_release_mismatch_error_message_with_observed() -> None:
    """The message must surface BOTH the pinned and observed releases
    so the agent / human auditor can act on the drift."""
    err = ReleaseMismatchError(
        pinned="2026_02", observed="2026_03", url="https://rest.uniprot.org/x"
    )
    msg = str(err)
    assert "'2026_02'" in msg
    assert "'2026_03'" in msg
    assert "https://rest.uniprot.org/x" in msg
    assert "release mismatch" in msg.lower()
    assert "UNIPROT_PIN_RELEASE" in msg


def test_release_mismatch_error_message_with_no_observed() -> None:
    """When observed is None (header absent), message must say
    '(absent)' — pins the disp formatter."""
    err = ReleaseMismatchError(pinned="2026_02", observed=None, url="https://rest.uniprot.org/x")
    assert "(absent)" in str(err)


def test_release_mismatch_error_attributes_preserved() -> None:
    """The exception must expose pinned / observed / url as attributes
    for programmatic handling, not just in the message."""
    err = ReleaseMismatchError(
        pinned="2026_02", observed="2026_03", url="https://rest.uniprot.org/x"
    )
    assert err.pinned == "2026_02"
    assert err.observed == "2026_03"
    assert err.url == "https://rest.uniprot.org/x"


def test_release_mismatch_error_is_runtime_error_subclass() -> None:
    """Subclass relationship — pins the class hierarchy."""
    err = ReleaseMismatchError(pinned="x", observed="y", url="https://x.test")
    assert isinstance(err, RuntimeError)


# ---------------------------------------------------------------------------
# UniProtClient construction
# ---------------------------------------------------------------------------


def test_uniprot_client_initial_provenance_is_none() -> None:
    """Before any request, last_provenance must be None (not a stale
    Provenance from a previous test, not a default Provenance with
    empty strings)."""
    c = UniProtClient()
    assert c.last_provenance is None


def test_uniprot_client_unpinned_by_default() -> None:
    """Without pin_release argument or env var, the client is unpinned."""
    # Defensive: scrub the env in case a test is run in an env where it's set.
    import os

    orig = os.environ.pop(PIN_RELEASE_ENV, None)
    try:
        c = UniProtClient()
        assert c.pin_release is None
    finally:
        if orig is not None:
            os.environ[PIN_RELEASE_ENV] = orig


def test_uniprot_client_constructor_pin_release_argument() -> None:
    """Explicit pin_release kwarg is propagated to the property."""
    c = UniProtClient(pin_release="2026_02")
    assert c.pin_release == "2026_02"


def test_uniprot_client_env_var_pin_release(monkeypatch: pytest.MonkeyPatch) -> None:
    """UNIPROT_PIN_RELEASE env var is read on construction when the
    constructor argument is absent."""
    monkeypatch.setenv(PIN_RELEASE_ENV, "2026_03")
    c = UniProtClient()
    assert c.pin_release == "2026_03"


def test_uniprot_client_constructor_arg_overrides_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Constructor argument wins over env var (None remains None and
    triggers env-var fallback; explicit non-None wins)."""
    monkeypatch.setenv(PIN_RELEASE_ENV, "2026_03")
    c = UniProtClient(pin_release="2026_99")
    assert c.pin_release == "2026_99"


def test_uniprot_client_env_var_empty_string_means_unpinned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty/whitespace env var must NOT be interpreted as a pin."""
    monkeypatch.setenv(PIN_RELEASE_ENV, "")
    c = UniProtClient()
    assert c.pin_release is None
    monkeypatch.setenv(PIN_RELEASE_ENV, "   ")
    c = UniProtClient()
    assert c.pin_release is None


# ---------------------------------------------------------------------------
# Provenance TypedDict shape
# ---------------------------------------------------------------------------


def test_provenance_dict_has_six_documented_fields() -> None:
    """The Provenance TypedDict declares exactly: source, release,
    release_date, retrieved_at, url, response_sha256."""
    expected = {"source", "release", "release_date", "retrieved_at", "url", "response_sha256"}
    assert set(Provenance.__annotations__.keys()) == expected
