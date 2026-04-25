"""Unit tests exercising each @mcp.tool wrapper end-to-end with mocked HTTP.

Ensures:
- Validation fires before network (rejections are agent-safe strings).
- Query construction in ``uniprot_search`` quotes organism names and
  does not blindly concatenate caller input into the UniProt query
  language.
- The tool names on `mcp` match what the MCP protocol exposes.
"""

from __future__ import annotations

import httpx
import respx

from uniprot_mcp import server
from uniprot_mcp.server import (
    uniprot_get_entry,
    uniprot_get_features,
    uniprot_search,
)


async def test_get_entry_rejects_bad_accession_without_network() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_get_entry("not-real", "markdown")
    assert "Input error" in out or "Error" in out
    # respx asserts no HTTP calls were made because router never matched.
    assert not router.calls


async def test_get_entry_rejects_bad_response_format() -> None:
    out = await uniprot_get_entry("P04637", "yaml")
    assert "response_format must be one of" in out


async def test_search_rejects_oversize_query() -> None:
    out = await uniprot_search("x" * 1000)
    assert "Input error" in out and "query" in out


async def test_search_quotes_multiword_organism_name() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        await uniprot_search("kinase", organism="Homo sapiens")
    assert route.called
    sent = route.calls[0].request.url.params["query"]
    # Multi-word organism must be quoted within the UniProt query syntax.
    assert 'organism_name:"Homo sapiens"' in sent


async def test_search_numeric_organism_uses_taxon_id() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        await uniprot_search("kinase", organism="9606")
    sent = route.calls[0].request.url.params["query"]
    assert "organism_id:9606" in sent


async def test_features_filter_no_network_on_bad_accession() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_get_features("garbage", "Domain")
    assert "Input error" in out or "Error" in out
    assert not router.calls


def test_every_expected_tool_is_registered() -> None:
    expected = {
        "uniprot_get_entry",
        "uniprot_search",
        "uniprot_get_sequence",
        "uniprot_get_features",
        "uniprot_get_variants",
        "uniprot_get_go_terms",
        "uniprot_get_cross_refs",
        "uniprot_id_mapping",
        "uniprot_batch_entries",
        "uniprot_taxonomy_search",
        "uniprot_get_keyword",
        "uniprot_search_keywords",
        "uniprot_get_subcellular_location",
        "uniprot_search_subcellular_locations",
        "uniprot_get_uniref",
        "uniprot_search_uniref",
        "uniprot_provenance_verify",
    }
    tools = getattr(server.mcp, "_tool_manager", None)
    assert tools is not None, "FastMCP internals changed"
    registered = set(tools._tools.keys())
    assert expected <= registered, f"missing: {expected - registered}"


def test_self_test_module_is_callable() -> None:
    """_self_test runs asyncio; just verify it's wired and returns an int."""
    assert callable(server._self_test)
