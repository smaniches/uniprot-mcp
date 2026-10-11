"""End-to-end MCP JSON-RPC protocol test.

Spawns `server.py` as a subprocess over stdio, performs `initialize` →
`tools/list` → `tools/call`, and asserts every tool is exposed with the
required safety annotations.

Runs only with `pytest --integration` because `tools/call` hits the live
UniProt API.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.mcp_protocol]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SERVER_PATH = REPO_ROOT / "src" / "uniprot_mcp" / "server.py"

# The historical v0.1.0 core tools — always present. We assert the live
# server's tool inventory is a *superset* of these so the protocol-level
# test does not break every time a new tool is added (the
# `.well-known/mcp.json` consistency test in tests/contract/ is the
# authoritative gate on the full registered set).
EXPECTED_CORE_TOOLS = {
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
}


async def _rpc(proc: asyncio.subprocess.Process, req: dict) -> dict:
    line = (json.dumps(req) + "\n").encode("utf-8")
    assert proc.stdin is not None
    proc.stdin.write(line)
    await proc.stdin.drain()
    assert proc.stdout is not None
    raw = await proc.stdout.readline()
    return json.loads(raw.decode("utf-8"))


async def test_mcp_handshake_and_tool_inventory() -> None:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(SERVER_PATH),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        init = await _rpc(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "0.0.0"},
                },
            },
        )
        assert init.get("result", {}).get("protocolVersion")

        # notifications/initialized
        notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        assert proc.stdin is not None
        proc.stdin.write((json.dumps(notif) + "\n").encode("utf-8"))
        await proc.stdin.drain()

        listed = await _rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in listed["result"]["tools"]}
        # Every historical core tool must still be present. New tools
        # are welcome — the contract test in tests/contract/ pins the
        # full set against `.well-known/mcp.json`.
        missing_core = EXPECTED_CORE_TOOLS - names
        assert not missing_core, f"missing core tools: {sorted(missing_core)}"
        # Sanity: server registers the v1.1.0 surface (41 tools). If
        # the count drops below the v1.0.1 baseline, that's a regression.
        assert len(names) >= 38, f"only {len(names)} tools; expected at least 38"

        # ``uniprot_replay_from_cache`` is the one tool that intentionally
        # does NOT carry ``openWorldHint`` — it reads only the local cache
        # and never touches the network. README documents this explicitly:
        # "All but uniprot_replay_from_cache interact with at least one
        # upstream service (openWorldHint: true)".
        no_openworld = {"uniprot_replay_from_cache"}
        for t in listed["result"]["tools"]:
            ann = t.get("annotations", {})
            assert ann.get("readOnlyHint") is True, f"{t['name']} missing readOnlyHint"
            if t["name"] not in no_openworld:
                assert ann.get("openWorldHint") is True, (
                    f"{t['name']} missing openWorldHint (only {sorted(no_openworld)} are exempt)"
                )
            assert len(t.get("description", "")) >= 30, f"{t['name']} description too short"
    finally:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except TimeoutError:
            proc.kill()


async def test_mcp_alphafold_confidence_live() -> None:
    """Verify an actual MCP tool invocation against the live AlphaFold DB.

    This is deliberately separate from the inventory test: listing a tool
    does not prove that its JSON-RPC call path, upstream schema, or returned
    provenance work together. Runs only with --integration.
    """
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(SERVER_PATH),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        # TP53's full UniProt JSON can exceed asyncio's 64 KiB stream
        # line limit; MCP stdio sends each JSON-RPC response on one line.
        limit=4 * 1024 * 1024,
    )
    try:
        initialized = await asyncio.wait_for(
            _rpc(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "live-protocol-smoke", "version": "0.0.0"},
                    },
                },
            ),
            timeout=20.0,
        )
        assert "result" in initialized
        assert proc.stdin is not None
        proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        await proc.stdin.drain()

        result = await asyncio.wait_for(
            _rpc(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "uniprot_get_alphafold_confidence",
                        "arguments": {
                            "accession": "P04637",
                            "response_format": "json",
                        },
                    },
                },
            ),
            timeout=150.0,
        )
        output = result["result"]
        assert output.get("isError") is not True, output
        content = output["content"]
        assert content and content[0]["type"] == "text"
        payload = json.loads(content[0]["text"])
        assert payload["data"]["accession"] == "P04637"
        model = payload["data"]["alphafold"]
        assert model["uniprotAccession"] == "P04637"
        assert model.get("modelEntityId") or model.get("entryId")
        assert payload["provenance"]["source"] == "AlphaFoldDB"

        # Exercise the other side of the UniProt + AlphaFold boundary in
        # the *same live MCP session*, rather than assuming that successful
        # AlphaFold calls establish UniProt API connectivity.
        entry_result = await asyncio.wait_for(
            _rpc(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "uniprot_get_entry",
                        "arguments": {
                            "accession": "P04637",
                            "response_format": "json",
                        },
                    },
                },
            ),
            timeout=150.0,
        )
        entry_output = entry_result["result"]
        assert entry_output.get("isError") is not True, entry_output
        entry = json.loads(entry_output["content"][0]["text"])
        assert entry["data"]["primaryAccession"] == model["uniprotAccession"]
        assert entry["provenance"]["source"] == "UniProt"
        assert entry["provenance"]["response_sha256"]
    finally:
        if proc.returncode is None:
            proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except TimeoutError:
            proc.kill()
            await proc.wait()
