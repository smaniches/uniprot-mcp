"""Targeted tests that close the last coverage arcs in client.py and
proteinchem.py.

Each test is pinned to a specific uncovered line/branch reported by
``pytest --cov --cov-branch``:

  - client.py 50-51   : version-lookup ``except`` fallback to "dev"
  - client.py ``_extract_provenance``: reads the accept header from the
    response's request
  - client.py 546->544: ClinVar esummary loop skips non-dict records
  - proteinchem.py 118->115: ``_count_amino_acids`` skips non-alpha chars
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import respx

from uniprot_mcp.client import (
    NCBI_EUTILS_BASE,
    UniProtClient,
    _extract_provenance,
)
from uniprot_mcp.proteinchem import _count_amino_acids

# ---------------------------------------------------------------------------
# client.py 50-51 — version-lookup ``except`` fallback to "dev"
#
# This is an import-time try/except. Exercising it requires patching
# ``importlib.metadata.version`` and reloading the module, which rebinds the
# package's exception classes (ReleaseMismatchError) to new objects and breaks
# ``except`` identity in already-imported modules (server.py), making other
# tests fail order-dependently. It is therefore marked ``# pragma: no cover``
# in the source with that justification rather than tested here.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# client.py — _extract_provenance reads the accept header from the request.
# ``response.request`` is always set when this function runs: the Provenance
# also reads ``response.url``, which httpx derives from ``Response.request``
# (the property RAISES if unset), so a request-less response can never reach
# the accept-header line. The header is therefore read directly, no guard.
# ---------------------------------------------------------------------------


def test_extract_provenance_reads_request_accept_header() -> None:
    """When a request is attached, provenance copies its accept header."""
    req = httpx.Request("GET", "https://rest.uniprot.org/x", headers={"accept": "text/x-fasta"})
    resp = httpx.Response(200, content=b"{}", request=req)
    prov = _extract_provenance(resp, now=datetime(2026, 1, 1, tzinfo=UTC))
    assert prov["accept_header"] == "text/x-fasta"
    assert prov["retrieved_at"] == "2026-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# client.py 546->544 — esummary "uids" entry that is not a dict is skipped
# ---------------------------------------------------------------------------


@respx.mock
async def test_get_clinvar_records_skips_non_dict_summary_entries() -> None:
    """eutils sometimes lists a uid that resolves to a non-dict value
    (e.g. an error string). Those entries must be skipped, not appended."""
    respx.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi").mock(
        return_value=httpx.Response(
            200, json={"esearchresult": {"idlist": ["111", "222"], "count": "2"}}
        )
    )
    respx.get(f"{NCBI_EUTILS_BASE}/esummary.fcgi").mock(
        return_value=httpx.Response(
            200,
            json={
                "result": {
                    "uids": ["111", "222"],
                    "111": {"uid": "111", "title": "kept"},
                    "222": "not-a-dict-skip-me",
                }
            },
        )
    )
    c = UniProtClient()
    try:
        out = await c.get_clinvar_records("TP53")
    finally:
        await c.close()
    # total reflects the unfiltered esearch count; only the dict survives.
    assert out["total"] == 2
    assert len(out["records"]) == 1
    assert out["records"][0]["uid"] == "111"


# ---------------------------------------------------------------------------
# proteinchem.py 118->115 — _count_amino_acids skips non-alpha characters
# ---------------------------------------------------------------------------


def test_count_amino_acids_skips_non_alpha_directly() -> None:
    """``compute_protein_properties`` pre-strips non-alpha input, so the
    ``elif ch.isalpha()`` False arc is only reachable by calling
    ``_count_amino_acids`` directly. Digits and whitespace must increment
    neither a standard AA nor the 'other' bucket."""
    counts = _count_amino_acids("A 1\tA")
    assert counts["A"] == 2
    assert counts["other"] == 0
    # Spot-check a couple of standard residues stay zero.
    assert counts["C"] == 0
