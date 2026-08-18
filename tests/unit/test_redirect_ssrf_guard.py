"""Fail-closed origin guards for UniProt and declared external APIs.

Every HTTPX client follows redirects for compatibility, but a request hook
checks each prepared request immediately before network dispatch. This keeps
same-origin redirects working while blocking HTTP downgrade, alternate hosts,
non-standard ports, and cross-origin 3xx hops before a socket is opened.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from uniprot_mcp.client import (
    ALPHAFOLD_API_BASE,
    BASE_URL,
    NCBI_EUTILS_BASE,
    UniProtClient,
    UntrustedRedirectError,
    _assert_trusted_redirect,
)

# ---------------------------------------------------------------------------
# Direct helper checks
# ---------------------------------------------------------------------------


def test_legit_rest_uniprot_redirect_passes() -> None:
    _assert_trusted_redirect("https://rest.uniprot.org/idmapping/results/job1")


def test_explicit_default_https_port_passes() -> None:
    _assert_trusted_redirect("https://rest.uniprot.org:443/idmapping/results/job1")


def test_bare_uniprot_org_host_raises() -> None:
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("https://uniprot.org/idmapping/results/job1")


def test_other_uniprot_subdomain_raises() -> None:
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("https://api.uniprot.org/idmapping/results/job1")


def test_http_downgrade_raises() -> None:
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("http://rest.uniprot.org/idmapping/results/job1")


def test_non_standard_port_raises() -> None:
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("https://rest.uniprot.org:444/idmapping/results/job1")


def test_invalid_port_raises() -> None:
    with pytest.raises(UntrustedRedirectError, match="invalid port"):
        _assert_trusted_redirect("https://rest.uniprot.org:notaport/idmapping/results/job1")


def test_off_origin_link_local_raises() -> None:
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("http://169.254.169.254/latest/meta-data/")


def test_off_origin_evil_host_raises() -> None:
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("https://evil.com/idmapping/results/job1")


def test_suffix_spoof_subdomain_attack_raises() -> None:
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("https://uniprot.org.evil.com/idmapping/results/job1")


def test_prefix_spoof_host_raises() -> None:
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("https://evil-uniprot.org/idmapping/results/job1")


def test_non_http_scheme_raises() -> None:
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("file:///etc/passwd")


def test_relative_url_without_host_raises() -> None:
    with pytest.raises(UntrustedRedirectError):
        _assert_trusted_redirect("/idmapping/results/job1")


# ---------------------------------------------------------------------------
# End-to-end through HTTPX redirect handling
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


async def test_same_origin_httpx_redirect_is_followed() -> None:
    with respx.mock(assert_all_called=False) as router:
        start = router.get(f"{BASE_URL}/uniprotkb/P04637").mock(
            return_value=httpx.Response(307, headers={"Location": "/uniprotkb/P04637-final"})
        )
        final = router.get(f"{BASE_URL}/uniprotkb/P04637-final").mock(
            return_value=httpx.Response(200, json={"primaryAccession": "P04637"})
        )
        client = UniProtClient()
        try:
            out = await client.get_entry("P04637")
        finally:
            await client.close()
    assert start.called
    assert final.called
    assert out["primaryAccession"] == "P04637"


async def test_cross_origin_httpx_redirect_is_blocked_before_dispatch() -> None:
    escaped = "https://evil.example/steal"
    with respx.mock(assert_all_called=False) as router:
        start = router.get(f"{BASE_URL}/uniprotkb/P04637").mock(
            return_value=httpx.Response(307, headers={"Location": escaped})
        )
        escaped_route = router.get(escaped).mock(return_value=httpx.Response(200, json={}))
        client = UniProtClient()
        try:
            with pytest.raises(UntrustedRedirectError):
                await client.get_entry("P04637")
        finally:
            await client.close()
    assert start.called
    assert not escaped_route.called


async def test_ncbi_cross_origin_redirect_is_blocked_before_dispatch() -> None:
    escaped = "https://evil.example/ncbi"
    with respx.mock(assert_all_called=False) as router:
        start = router.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi").mock(
            return_value=httpx.Response(307, headers={"Location": escaped})
        )
        escaped_route = router.get(escaped).mock(return_value=httpx.Response(200, json={}))
        client = UniProtClient()
        try:
            with pytest.raises(UntrustedRedirectError):
                await client.get_clinvar_records("BRCA1")
        finally:
            await client.close()
    assert start.called
    assert not escaped_route.called


async def test_alphafold_cross_origin_redirect_is_blocked_before_dispatch() -> None:
    escaped = "https://evil.example/alphafold"
    with respx.mock(assert_all_called=False) as router:
        start = router.get(f"{ALPHAFOLD_API_BASE}/api/prediction/P04637").mock(
            return_value=httpx.Response(307, headers={"Location": escaped})
        )
        escaped_route = router.get(escaped).mock(return_value=httpx.Response(200, json={}))
        client = UniProtClient()
        try:
            with pytest.raises(UntrustedRedirectError):
                await client.get_alphafold_summary("P04637")
        finally:
            await client.close()
    assert start.called
    assert not escaped_route.called
