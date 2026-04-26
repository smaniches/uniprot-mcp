"""Tests for the ``--pin-release`` opt-in.

When the client is constructed with ``pin_release=YYYY_MM`` (or the
``UNIPROT_PIN_RELEASE`` environment variable is set), every successful
upstream response is checked against the pinned release tag. Mismatches
raise :class:`ReleaseMismatchError`. UniProt does not honour a
release-selector query parameter, so pinning is assertion-only — the
client refuses results from any other release rather than silently
accepting drift.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from uniprot_mcp.client import (
    PIN_RELEASE_ENV,
    ReleaseMismatchError,
    UniProtClient,
)
from uniprot_mcp.server import _safe_error, uniprot_get_entry

# ---------------------------------------------------------------------------
# Construction sources: explicit arg, env var, neither
# ---------------------------------------------------------------------------


async def test_unpinned_client_has_no_pin_attribute() -> None:
    client = UniProtClient()
    try:
        assert client.pin_release is None
    finally:
        await client.close()


async def test_explicit_pin_argument_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PIN_RELEASE_ENV, "2025_01")
    client = UniProtClient(pin_release="2026_02")
    try:
        assert client.pin_release == "2026_02"
    finally:
        await client.close()


async def test_env_var_picked_up_when_no_explicit_arg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PIN_RELEASE_ENV, "2026_03")
    client = UniProtClient()
    try:
        assert client.pin_release == "2026_03"
    finally:
        await client.close()


async def test_blank_env_var_means_unpinned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PIN_RELEASE_ENV, "")
    client = UniProtClient()
    try:
        assert client.pin_release is None
    finally:
        await client.close()


# ---------------------------------------------------------------------------
# Behaviour at request time
# ---------------------------------------------------------------------------


async def test_pinned_request_passes_through_when_release_matches() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P04637"},
                headers={"X-UniProt-Release": "2026_02"},
            )
        )
        client = UniProtClient(pin_release="2026_02")
        try:
            data = await client.get_entry("P04637")
        finally:
            await client.close()
    assert data["primaryAccession"] == "P04637"


async def test_pinned_request_raises_on_release_mismatch() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P04637"},
                headers={"X-UniProt-Release": "2026_04"},
            )
        )
        client = UniProtClient(pin_release="2026_02")
        try:
            with pytest.raises(ReleaseMismatchError) as excinfo:
                await client.get_entry("P04637")
        finally:
            await client.close()
    assert excinfo.value.pinned == "2026_02"
    assert excinfo.value.observed == "2026_04"
    assert "uniprotkb/P04637" in excinfo.value.url


async def test_pinned_request_raises_when_release_header_absent() -> None:
    """An upstream response that omits the release header cannot satisfy
    the pin — raise rather than silently accept."""
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(200, json={"primaryAccession": "P04637"})
        )
        client = UniProtClient(pin_release="2026_02")
        try:
            with pytest.raises(ReleaseMismatchError) as excinfo:
                await client.get_entry("P04637")
        finally:
            await client.close()
    assert excinfo.value.observed is None


async def test_pinned_request_id_mapping_submit_also_validated() -> None:
    """``id_mapping_submit`` bypasses the ``_req`` helper and has its
    own retry loop. Pinning must be enforced there too."""
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.post("/idmapping/run").mock(
            return_value=httpx.Response(
                200,
                json={"jobId": "J1"},
                headers={"X-UniProt-Release": "2030_01"},
            )
        )
        client = UniProtClient(pin_release="2026_02")
        try:
            with pytest.raises(ReleaseMismatchError):
                await client.id_mapping_submit("Gene_Name", "UniProtKB", ["BRCA1"])
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# Server-side error envelope shape
# ---------------------------------------------------------------------------


async def test_server_tool_returns_agent_safe_release_mismatch_message() -> None:
    """The MCP tool wrapper must surface ReleaseMismatchError as a
    structured, agent-actionable string — not the raw exception text."""
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P04637"},
                headers={"X-UniProt-Release": "2030_01"},
            )
        )
        # Fresh client with pin; install via env so the singleton picks it up.
        from uniprot_mcp import server as srv

        if srv._uniprot is not None:
            await srv._uniprot.close()
            srv._uniprot = None
        try:
            srv._uniprot = UniProtClient(pin_release="2026_02")
            out = await uniprot_get_entry("P04637", "markdown")
        finally:
            if srv._uniprot is not None:
                await srv._uniprot.close()
                srv._uniprot = None
    assert "Release mismatch" in out
    assert "'2026_02'" in out
    assert "'2030_01'" in out
    assert PIN_RELEASE_ENV in out  # advice mentions how to opt out


def test_safe_error_formats_release_mismatch_distinctly() -> None:
    """Direct unit test on _safe_error so the error envelope shape is
    pinned regardless of the specific tool wrapper that raised."""
    exc = ReleaseMismatchError(
        pinned="2026_02",
        observed="2026_04",
        url="https://rest.uniprot.org/uniprotkb/P04637",
    )
    msg = _safe_error("uniprot_get_entry", exc)
    assert "Release mismatch" in msg
    assert "'2026_02'" in msg
    assert "'2026_04'" in msg
    assert "uniprot_get_entry" in msg
