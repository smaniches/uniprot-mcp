"""Verify the id_mapping poll loop exits correctly."""
from __future__ import annotations

from itertools import cycle

import httpx
import respx

from uniprot_mcp.client import UniProtClient


async def test_poll_exits_on_results() -> None:
    statuses = iter(
        [
            httpx.Response(200, json={"jobStatus": "RUNNING"}),
            httpx.Response(200, json={"jobStatus": "RUNNING"}),
            httpx.Response(
                200,
                json={
                    "results": [
                        {"from": "BRCA1", "to": {"primaryAccession": "P38398"}}
                    ],
                    "failedIds": [],
                },
            ),
        ]
    )
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/idmapping/status/JOB123").mock(side_effect=lambda req: next(statuses))
        client = UniProtClient()
        try:
            out = await client.id_mapping_results("JOB123")
        finally:
            await client.close()
        assert out["results"][0]["from"] == "BRCA1"
        assert out["results"][0]["to"]["primaryAccession"] == "P38398"


async def test_poll_exits_on_failedIds() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/idmapping/status/JOB456").mock(
            return_value=httpx.Response(200, json={"failedIds": ["BAD"]})
        )
        client = UniProtClient()
        try:
            out = await client.id_mapping_results("JOB456")
        finally:
            await client.close()
        assert out["failedIds"] == ["BAD"]
