"""Live end-to-end round-trip for provenance + verification.

This is the test that grounds every architectural claim in observed
behaviour against real UniProt. Each test:

1. Issues a real REST request through ``UniProtClient``.
2. Captures the resulting :class:`Provenance` record.
3. Calls ``uniprot_provenance_verify`` with the captured fields.
4. Asserts the verifier reaches the expected verdict.

Goal: prove that the chain
    upstream response  →  Provenance extraction  →  Markdown / JSON
    surface  →  agent reads URL / release / hash  →  verify tool
    re-fetches and matches
works end-to-end with the real API. Mocked unit tests cover the
permutations; this file proves the wiring.

Marked ``integration`` — skipped unless ``pytest --integration`` is
passed.
"""

from __future__ import annotations

import json

import pytest

from uniprot_mcp.client import UniProtClient
from uniprot_mcp.server import uniprot_provenance_verify

pytestmark = pytest.mark.integration


@pytest.fixture
async def client():
    c = UniProtClient()
    yield c
    await c.close()


async def test_roundtrip_verifies_against_live_uniprot(client: UniProtClient) -> None:
    """The happy path — record a Provenance from a real query, then
    re-verify it. Status must be ``verified`` with both checks
    green."""
    await client.get_entry("P04637")
    prov = client.last_provenance
    assert prov is not None
    assert prov["release"], "live UniProt should set X-UniProt-Release"
    assert len(prov["response_sha256"]) == 64
    assert prov["url"].endswith("/uniprotkb/P04637")

    out = await uniprot_provenance_verify(
        url=prov["url"],
        release=prov["release"],
        response_sha256=prov["response_sha256"],
        response_format="json",
    )
    payload = json.loads(out)
    assert payload["status"] == "verified", f"unexpected verdict: {payload}"
    assert payload["url_resolves"] is True
    assert payload["release_match"] is True
    assert payload["hash_match"] is True


async def test_roundtrip_detects_hash_drift_against_live_uniprot(
    client: UniProtClient,
) -> None:
    """Synthesise a hash-drift scenario by passing a wrong recorded
    hash. The verifier must report ``hash_drift`` (release still
    matches, body does not)."""
    await client.get_entry("P04637")
    prov = client.last_provenance
    assert prov is not None

    out = await uniprot_provenance_verify(
        url=prov["url"],
        release=prov["release"] or "",
        response_sha256="0" * 64,  # wrong on purpose
        response_format="json",
    )
    payload = json.loads(out)
    assert payload["status"] == "hash_drift", f"unexpected verdict: {payload}"
    assert payload["release_match"] is True
    assert payload["hash_match"] is False
    assert payload["recorded_sha256"] == "0" * 64
    assert payload["current_sha256"] == prov["response_sha256"]


async def test_roundtrip_detects_release_drift_against_live_uniprot(
    client: UniProtClient,
) -> None:
    """Pass a deliberately-wrong release tag. The verifier must report
    ``release_drift`` and surface both the recorded and current values
    so the agent can reason about how stale the cached answer is."""
    await client.get_entry("P04637")
    prov = client.last_provenance
    assert prov is not None

    out = await uniprot_provenance_verify(
        url=prov["url"],
        release="1999_01",  # impossibly old
        response_sha256=prov["response_sha256"],
        response_format="json",
    )
    payload = json.loads(out)
    assert payload["status"] == "release_drift", f"unexpected verdict: {payload}"
    assert payload["release_match"] is False
    assert payload["hash_match"] is True
    assert payload["recorded_release"] == "1999_01"
    assert payload["current_release"] == prov["release"]


async def test_roundtrip_url_unreachable_against_live_uniprot() -> None:
    """A real UniProt URL that cannot exist (made-up accession that
    fails the REST endpoint) must return ``url_unreachable`` rather
    than crashing."""
    out = await uniprot_provenance_verify(
        url="https://rest.uniprot.org/uniprotkb/Q99999_NOT_A_REAL_ACC_42",
        response_format="json",
    )
    payload = json.loads(out)
    assert payload["status"] == "url_unreachable", f"unexpected verdict: {payload}"
    assert payload["url_resolves"] is False
