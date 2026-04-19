"""UniProt REST API client.

Async, with exponential back-off on 429 / 5xx, strict accession
validation, HTTP-date-aware Retry-After parsing, and a polling loop
for the ID-mapping job API.

Author: Santiago Maniches <santiago.maniches@gmail.com>
        ORCID https://orcid.org/0009-0005-6480-1987
        TOPOLOGICA LLC
License: Apache-2.0
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

BASE_URL = "https://rest.uniprot.org"
TIMEOUT = 30.0
MAX_RETRIES = 3
MAX_RETRY_AFTER_SECONDS = 120.0  # cap server-dictated waits
UA = "uniprot-mcp/0.1.0 (+https://github.com/smaniches/uniprot-mcp)"

# Official UniProt accession format.
# https://www.uniprot.org/help/accession_numbers
ACCESSION_RE = re.compile(
    r"\A(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})\Z"
)

__all__ = [
    "ACCESSION_RE",
    "BASE_URL",
    "MAX_RETRIES",
    "MAX_RETRY_AFTER_SECONDS",
    "TIMEOUT",
    "UA",
    "UniProtClient",
    "parse_retry_after",
]


def parse_retry_after(value: str | None, attempt: int) -> float:
    """Parse an RFC 7231 ``Retry-After`` response header.

    Accepts delta-seconds or HTTP-date; returns a clamped float.
    Falls back to exponential back-off when missing or malformed.
    """
    fallback = 1.5 ** (attempt + 1)
    if not value:
        return fallback
    try:
        return min(float(value), MAX_RETRY_AFTER_SECONDS)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return fallback
    if dt is None:
        return fallback
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = (dt - datetime.now(tz=UTC)).total_seconds()
    return min(max(delta, 0.0), MAX_RETRY_AFTER_SECONDS)


class UniProtClient:
    """Thin async wrapper over the UniProt REST API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                timeout=httpx.Timeout(TIMEOUT),
                headers={"User-Agent": UA, "Accept": "application/json"},
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()

    async def _req(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        accept: str = "application/json",
    ) -> httpx.Response:
        client = await self._get_client()
        headers = {"Accept": accept} if accept else {}
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.request(method, path, params=params, headers=headers)
                if resp.status_code == 429:
                    await asyncio.sleep(parse_retry_after(resp.headers.get("Retry-After"), attempt))
                    continue
                if resp.status_code >= 500:
                    await asyncio.sleep(1.5 ** (attempt + 1))
                    continue
                resp.raise_for_status()
                return resp
            except httpx.TimeoutException:
                await asyncio.sleep(1.5 ** (attempt + 1))
        raise RuntimeError(f"Request failed after {MAX_RETRIES + 1} attempts")

    async def get_entry(self, accession: str) -> dict[str, Any]:
        data: dict[str, Any] = (await self._req("GET", f"/uniprotkb/{accession}")).json()
        return data

    async def search(
        self, query: str, size: int = 10, fields: list[str] | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"query": query, "size": min(size, 500)}
        if fields:
            params["fields"] = ",".join(fields)
        data: dict[str, Any] = (await self._req("GET", "/uniprotkb/search", params=params)).json()
        return data

    async def get_fasta(self, accession: str) -> str:
        resp = await self._req("GET", f"/uniprotkb/{accession}", accept="text/plain;format=fasta")
        return resp.text

    async def id_mapping_submit(self, from_db: str, to_db: str, ids: list[str]) -> str:
        """Submit an ID mapping job. Retries on 429 / 5xx / timeout."""
        client = await self._get_client()
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.post(
                    "/idmapping/run",
                    data={"from": from_db, "to": to_db, "ids": ",".join(ids)},
                )
                if resp.status_code == 429:
                    await asyncio.sleep(parse_retry_after(resp.headers.get("Retry-After"), attempt))
                    continue
                if resp.status_code >= 500:
                    await asyncio.sleep(1.5 ** (attempt + 1))
                    continue
                resp.raise_for_status()
                job_id: str = resp.json()["jobId"]
                return job_id
            except httpx.TimeoutException:
                await asyncio.sleep(1.5 ** (attempt + 1))
        raise RuntimeError(f"id_mapping_submit failed after {MAX_RETRIES + 1} attempts")

    async def id_mapping_results(self, job_id: str, size: int = 500) -> dict[str, Any]:
        for _ in range(30):
            status = (await self._req("GET", f"/idmapping/status/{job_id}")).json()
            if "results" in status or "failedIds" in status:
                return status  # type: ignore[no-any-return]
            if status.get("jobStatus") == "RUNNING":
                await asyncio.sleep(1.0)
                continue
            if "redirectURL" in status:
                url = status["redirectURL"]
                return (await self._req("GET", url, params={"size": size})).json()  # type: ignore[no-any-return]
            await asyncio.sleep(1.0)
        raise TimeoutError("ID mapping did not complete in 30s")

    async def batch_entries(
        self, accessions: list[str], fields: list[str] | None = None
    ) -> dict[str, list[Any]]:
        """Fetch up to 100 entries.

        Invalid accessions are filtered client-side so a single bad token
        does not cause UniProt to reject the whole batch. The raw invalid
        tokens are returned under the ``invalid`` key for the caller to
        surface.
        """
        valid = [a for a in accessions if ACCESSION_RE.match(a.upper())]
        invalid = [a for a in accessions if a not in valid]
        if len(valid) > 100:
            valid = valid[:100]
        if not valid:
            return {"results": [], "invalid": invalid}
        query = " OR ".join(f"accession:{a}" for a in valid)
        params: dict[str, Any] = {"query": query, "size": len(valid)}
        if fields:
            params["fields"] = ",".join(fields)
        results = (
            (await self._req("GET", "/uniprotkb/search", params=params)).json().get("results", [])
        )
        return {"results": results, "invalid": invalid}

    async def taxonomy_search(self, query: str, size: int = 10) -> dict[str, Any]:
        data: dict[str, Any] = (
            await self._req("GET", "/taxonomy/search", params={"query": query, "size": size})
        ).json()
        return data
