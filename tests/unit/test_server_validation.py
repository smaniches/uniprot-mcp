"""Unit tests for input validation + agent-safe error envelopes in server.py.

These protect two properties:
- Malformed input never hits the network (cost + abuse control).
- Internal exception text does not leak back to the LLM through tool
  return values.
"""

from __future__ import annotations

import pytest

from uniprot_mcp.server import (
    ALLOWED_RESPONSE_FORMATS,
    MAX_ACCESSION_LEN,
    MAX_QUERY_LEN,
    _check_accession,
    _check_format,
    _check_len,
    _InputError,
    _safe_error,
)


def test_check_format_accepts_allowlist() -> None:
    for fmt in ALLOWED_RESPONSE_FORMATS:
        _check_format(fmt)


def test_check_format_rejects_others() -> None:
    with pytest.raises(_InputError):
        _check_format("yaml")
    with pytest.raises(_InputError):
        _check_format("")


def test_check_accession_accepts_valid() -> None:
    _check_accession("P04637")
    _check_accession("A0A1B2C3D4")


def test_check_accession_rejects_invalid() -> None:
    with pytest.raises(_InputError):
        _check_accession("NOPE")
    with pytest.raises(_InputError):
        _check_accession("")
    with pytest.raises(_InputError):
        _check_accession("P04637;DROP")  # injection-adjacent garbage


def test_check_accession_is_case_lenient() -> None:
    """Lowercase input is accepted (normalised upstream). Intentional UX choice."""
    _check_accession("p04637")


def test_check_accession_rejects_oversize() -> None:
    with pytest.raises(_InputError, match="exceeds"):
        _check_accession("P" * (MAX_ACCESSION_LEN + 1))


def test_check_len_blocks_oversize_query() -> None:
    with pytest.raises(_InputError, match="query exceeds"):
        _check_len("query", "x" * (MAX_QUERY_LEN + 1), MAX_QUERY_LEN)


def test_safe_error_hides_internal_exception_text() -> None:
    exc = RuntimeError("sensitive/internal stacktrace bits 0xdeadbeef")
    msg = _safe_error("uniprot_get_entry", exc)
    assert "0xdeadbeef" not in msg
    assert "sensitive" not in msg
    assert "uniprot_get_entry" in msg


def test_safe_error_input_errors_are_forwarded() -> None:
    exc = _InputError("accession must match the UniProt format")
    msg = _safe_error("uniprot_get_entry", exc)
    assert "accession must match" in msg
