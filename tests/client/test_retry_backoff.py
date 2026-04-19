"""Verify retry and back-off behaviour of UniProtClient using respx."""
from __future__ import annotations

from itertools import cycle

import httpx
import pytest
import respx

from client import MAX_RETRIES, UniProtClient


async def test_retries_on_429_then_succeeds() -> None:
    responses = cycle(
        [
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"primaryAccession": "P04637"}),
        ]
    )
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/P04637").mock(side_effect=lambda req: next(responses))
        client = UniProtClient()
        try:
            data = await client.get_entry("P04637")
        finally:
            await client.close()
        assert data["primaryAccession"] == "P04637"
        assert route.call_count == 2, "should retry once after 429"


async def test_retries_on_5xx_then_succeeds() -> None:
    responses = cycle(
        [
            httpx.Response(503),
            httpx.Response(200, json={"primaryAccession": "P38398"}),
        ]
    )
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/P38398").mock(side_effect=lambda req: next(responses))
        client = UniProtClient()
        try:
            data = await client.get_entry("P38398")
        finally:
            await client.close()
        assert data["primaryAccession"] == "P38398"
        assert route.call_count == 2


async def test_gives_up_after_max_retries_on_persistent_5xx() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(503))
        client = UniProtClient()
        try:
            with pytest.raises(RuntimeError, match="Request failed"):
                await client.get_entry("P04637")
        finally:
            await client.close()
        assert route.call_count == MAX_RETRIES + 1


async def test_4xx_client_error_does_not_retry() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/NOPE").mock(return_value=httpx.Response(400))
        client = UniProtClient()
        try:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_entry("NOPE")
        finally:
            await client.close()
        assert route.call_count == 1, "4xx (non-429) must not be retried"
