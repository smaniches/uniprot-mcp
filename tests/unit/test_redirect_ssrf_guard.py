"""SSRF guard on the id-mapping ``redirectURL`` (FIX 1).

The id-mapping poll loop follows ``status["redirectURL"]`` as an absolute
URL. httpx does not constrain absolute URLs to ``base_url``, so a malicious
or MITM'd ``redirectURL`` would be fetched verbatim. ``_assert_trusted_redirect``
restricts the host to ``*.uniprot.org`` / ``uniprot.org`` before dispatch.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from uniprot_mcp.client import (
    BASE_URL,
    UniProtClient,
    UntrustedRedirectError,
    _assert_trusted_redirect,
)

# ---------------------------------------------------------------------------
# Direct helper checks
# ---------------------------------------------------------------------------


def test_legit_rest_uniprot_redirect_passes() -> None:
    # The real id-mapping redirect target; must not raise.
    _assert_trusted_redirect("https://rest.uniprot.org/idmapping/results/job1")


def test_bare_uniprot_org_host_passes() -> None:
    _assert_trusted_redirect("https://uniprot.org/idmapping/results/job1")


def test_off_origin_link_local_raises() -> None:
    # Classic SSRF metadata target.
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("http://169.254.169.254/latest/meta-data/")


def test_off_origin_evil_host_raises() -> None:
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("https://evil.com/idmapping/results/job1")


def test_suffix_spoof_subdomain_attack_raises() -> None:
    # uniprot.org as a left-label of a hostile domain must NOT pass.
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("https://uniprot.org.evil.com/idmapping/results/job1")


def test_prefix_spoof_host_raises() -> None:
    # netloc.endswith("uniprot.org") would wrongly accept this; hostname
    # suffix match on ".uniprot.org" rejects it.
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("https://evil-uniprot.org/idmapping/results/job1")


def test_non_http_scheme_raises() -> None:
    # Exercises the scheme branch (file:// is not http/https).
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("file:///etc/passwd")


def test_relative_url_without_host_raises() -> None:
    # No scheme/host -> not an absolute http(s) URL.
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("/idmapping/results/job1")


# ---------------------------------------------------------------------------
# End-to-end through id_mapping_results
# ---------------------------------------------------------------------------


async def test_id_mapping_follows_legit_redirect() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/idmapping/status/JOBOK").mock(
            return_value=httpx.Response(
                200,
                json={"redirectURL": "https://rest.uniprot.org/idmapping/results/JOBOK"},
            )
        )
        redirect_route = router.get("/idmapping/results/JOBOK").mock(
            return_value=httpx.Response(200, json={"results": [{"from": "X", "to": "Y"}]})
        )
        client = UniProtClient()
        try:
            out = await client.id_mapping_results("JOBOK", size=10)
        finally:
            await client.close()
    assert redirect_route.called
    assert out["results"][0]["from"] == "X"


async def test_id_mapping_rejects_untrusted_redirect() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/idmapping/status/JOBBAD").mock(
            return_value=httpx.Response(200, json={"redirectURL": "https://evil.com/steal"})
        )
        client = UniProtClient()
        try:
            with pytest.raises(UntrustedRedirectError):
                await client.id_mapping_results("JOBBAD")
        finally:
            await client.close()
