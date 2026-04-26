"""Tests for ``uniprot_provenance_verify`` and ``canonical_response_hash``.

The verifier closes the loop on provenance: every prior response's
provenance footer can be re-checked against the live UniProt API at any
later time. Three failure modes are distinguished:

1. ``release_drift`` — UniProt has moved past the release the response
   was retrieved from.
2. ``hash_drift`` — the release tag still matches but the canonical
   response body has changed (an in-release edit).
3. ``url_unreachable`` — the URL no longer returns a successful response.

When both release and hash differ, the verdict is
``release_and_hash_drift``.
"""

from __future__ import annotations

import json

import httpx
import respx

from uniprot_mcp.client import canonical_response_hash
from uniprot_mcp.server import uniprot_provenance_verify

_TP53_URL = "https://rest.uniprot.org/uniprotkb/P04637"
_TP53_BODY = {"primaryAccession": "P04637", "entryType": "UniProtKB reviewed (Swiss-Prot)"}


def _fake_response(body: dict, release: str | None = "2026_02") -> httpx.Response:
    headers: dict[str, str] = {}
    if release is not None:
        headers["X-UniProt-Release"] = release
    return httpx.Response(200, json=body, headers=headers)


# ---------------------------------------------------------------------------
# canonical_response_hash — JSON canonicalisation + non-JSON byte hash
# ---------------------------------------------------------------------------


def test_canonical_hash_stable_under_key_reordering() -> None:
    """Two JSON responses with the same logical content but different
    key order must produce the same canonical hash."""
    a = httpx.Response(200, json={"a": 1, "b": 2}, headers={"content-type": "application/json"})
    b = httpx.Response(200, json={"b": 2, "a": 1}, headers={"content-type": "application/json"})
    assert canonical_response_hash(a) == canonical_response_hash(b)


def test_canonical_hash_changes_on_real_content_diff() -> None:
    a = httpx.Response(200, json={"a": 1}, headers={"content-type": "application/json"})
    b = httpx.Response(200, json={"a": 2}, headers={"content-type": "application/json"})
    assert canonical_response_hash(a) != canonical_response_hash(b)


def test_canonical_hash_falls_back_to_bytes_for_non_json() -> None:
    fasta = ">sp|P04637|P53_HUMAN\nMEEPQSDPSV\n"
    resp = httpx.Response(200, text=fasta, headers={"content-type": "text/plain"})
    digest = canonical_response_hash(resp)
    # 64 lowercase hex chars
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


# ---------------------------------------------------------------------------
# uniprot_provenance_verify — input validation
# ---------------------------------------------------------------------------


async def test_verify_rejects_non_uniprot_url() -> None:
    out = await uniprot_provenance_verify("https://example.com/foo", "")
    assert "Input error" in out
    assert "https://rest.uniprot.org/" in out


async def test_verify_rejects_oversize_url() -> None:
    out = await uniprot_provenance_verify("https://rest.uniprot.org/" + "x" * 2000)
    assert "Input error" in out and "url" in out


async def test_verify_rejects_oversize_release() -> None:
    out = await uniprot_provenance_verify(_TP53_URL, release="2026_02_with_an_unreasonable_suffix")
    assert "Input error" in out


# ---------------------------------------------------------------------------
# Verified — both checks pass
# ---------------------------------------------------------------------------


async def test_verify_passes_when_release_and_hash_match() -> None:
    body = dict(_TP53_BODY)
    fake = _fake_response(body, release="2026_02")
    recorded_hash = canonical_response_hash(fake)
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=_fake_response(body, release="2026_02"))
        out = await uniprot_provenance_verify(
            _TP53_URL,
            release="2026_02",
            response_sha256=recorded_hash,
            response_format="json",
        )
    payload = json.loads(out)
    assert payload["status"] == "verified"
    assert payload["url_resolves"] is True
    assert payload["release_match"] is True
    assert payload["hash_match"] is True


async def test_verify_passes_with_no_optional_fields() -> None:
    """Verifying just URL reachability should succeed without forcing
    the caller to supply release / hash."""
    body = dict(_TP53_BODY)
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=_fake_response(body, release="2026_02"))
        out = await uniprot_provenance_verify(_TP53_URL, response_format="json")
    payload = json.loads(out)
    assert payload["status"] == "verified"
    assert payload["url_resolves"] is True
    # No release / hash check requested -> not present in the report
    assert "release_match" not in payload
    assert "hash_match" not in payload


# ---------------------------------------------------------------------------
# Drift verdicts
# ---------------------------------------------------------------------------


async def test_verify_reports_release_drift() -> None:
    body = dict(_TP53_BODY)
    correct_hash = canonical_response_hash(_fake_response(body, release="2026_02"))
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=_fake_response(body, release="2026_04"))
        out = await uniprot_provenance_verify(
            _TP53_URL,
            release="2026_02",
            response_sha256=correct_hash,  # body unchanged -> hash matches
            response_format="json",
        )
    payload = json.loads(out)
    assert payload["status"] == "release_drift"
    assert payload["release_match"] is False
    assert payload["hash_match"] is True
    assert payload["recorded_release"] == "2026_02"
    assert payload["current_release"] == "2026_04"


async def test_verify_reports_hash_drift() -> None:
    body = dict(_TP53_BODY)
    fake_now = _fake_response(body, release="2026_02")
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=fake_now)
        out = await uniprot_provenance_verify(
            _TP53_URL,
            release="2026_02",
            response_sha256="0" * 64,  # bogus recorded hash
            response_format="json",
        )
    payload = json.loads(out)
    assert payload["status"] == "hash_drift"
    assert payload["release_match"] is True
    assert payload["hash_match"] is False
    assert payload["recorded_sha256"] == "0" * 64


async def test_verify_reports_combined_drift() -> None:
    body = {"primaryAccession": "P04637", "newField": "added by upstream"}
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=_fake_response(body, release="2026_04"))
        out = await uniprot_provenance_verify(
            _TP53_URL,
            release="2026_02",
            response_sha256="0" * 64,
            response_format="json",
        )
    payload = json.loads(out)
    assert payload["status"] == "release_and_hash_drift"
    assert payload["release_match"] is False
    assert payload["hash_match"] is False


# ---------------------------------------------------------------------------
# Unreachable
# ---------------------------------------------------------------------------


async def test_verify_reports_url_unreachable_on_4xx() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(404))
        out = await uniprot_provenance_verify(_TP53_URL, response_format="json")
    payload = json.loads(out)
    assert payload["status"] == "url_unreachable"
    assert payload["url_resolves"] is False
    assert payload["http_status"] == 404


async def test_verify_reports_url_unreachable_on_network_error() -> None:
    def _connection_error(_request):
        raise httpx.ConnectError("dns failure")

    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(side_effect=_connection_error)
        out = await uniprot_provenance_verify(_TP53_URL, response_format="json")
    payload = json.loads(out)
    assert payload["status"] == "url_unreachable"
    assert payload["url_resolves"] is False
    assert "ConnectError" in payload["error"]


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


async def test_verify_markdown_renders_status_and_advice() -> None:
    body = dict(_TP53_BODY)
    correct_hash = canonical_response_hash(_fake_response(body, release="2026_02"))
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=_fake_response(body, release="2026_02"))
        out = await uniprot_provenance_verify(
            _TP53_URL,
            release="2026_02",
            response_sha256=correct_hash,
            response_format="markdown",
        )
    assert "## Provenance Verification" in out
    assert "**Status:** verified" in out
    assert "✓ URL resolves" in out
    assert "✓ Release" in out
    assert "✓ Response SHA-256" in out
    assert "**Advice:**" in out


async def test_verify_markdown_renders_drift_with_advice_pointing_at_ftp() -> None:
    body = dict(_TP53_BODY)
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=_fake_response(body, release="2026_04"))
        out = await uniprot_provenance_verify(
            _TP53_URL,
            release="2026_02",
            response_format="markdown",
        )
    assert "**Status:** release_drift" in out
    assert "FTP snapshot" in out  # advice text mentions the recommended remediation
