"""Protocol-level error-contract tests.

The per-tool unit tests assert that a failing tool *raises* ``ToolError``.
These tests close the loop one layer up: they drive the registered MCP
``tools/call`` handler in-process and assert that a failure becomes a
``CallToolResult`` with ``isError=True`` (the signal automation must branch
on), while a success does not. This pins the contract end-to-end so a future
refactor cannot silently return an error-shaped *success* result.

Both cases run without the network: the failure path is rejected by input
validation before any HTTP call, and the success path mocks the upstream
response with ``respx``.
"""

from __future__ import annotations

import httpx
import respx
from mcp import types

from uniprot_mcp.server import mcp


async def _call_tool(name: str, arguments: dict[str, object]) -> types.CallToolResult:
    """Invoke the registered MCP ``tools/call`` handler and return its result."""
    handler = mcp._mcp_server.request_handlers[types.CallToolRequest]
    req = types.CallToolRequest(
        method="tools/call",
        params=types.CallToolRequestParams(name=name, arguments=arguments),
    )
    return (await handler(req)).root


async def test_failed_tool_call_sets_iserror_without_network() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        result = await _call_tool("uniprot_get_entry", {"accession": "not-real"})
    assert result.isError is True
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    # The client receives the sanitized validation message, never a traceback.
    assert "Input error" in result.content[0].text
    assert "Traceback" not in result.content[0].text
    assert not router.calls  # validation failed before any upstream call


async def test_successful_tool_call_is_not_iserror() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/search").mock(return_value=httpx.Response(200, json={"results": []}))
        result = await _call_tool("uniprot_search", {"query": "kinase"})
    assert not result.isError
    assert len(result.content) == 1
    assert result.content[0].type == "text"
