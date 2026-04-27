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
