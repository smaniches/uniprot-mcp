"""UniProt REST API client.

Async, with exponential back-off on 429 / 5xx, strict accession
validation, HTTP-date-aware Retry-After parsing, and a polling loop
for the ID-mapping job API.

Every successful request updates :attr:`UniProtClient.last_provenance`
with the release-number, release-date, retrieval timestamp, and the
final resolved URL. Callers (MCP tool handlers) read that property
immediately after a request and pass the record into the formatter,
which surfaces it to the LLM or downstream consumer.

Thread-safety: a single :class:`UniProtClient` is not safe to share
across concurrent tasks that care about provenance. The stdio MCP
transport serializes tool invocations, so the module-level singleton
in ``server.py`` is fine; if you ever move to HTTP/SSE with parallel
tool calls, give each invocation its own client.

Author: Santiago Maniches <santiago.maniches@gmail.com>
        ORCID https://orcid.org/0009-0005-6480-1987
        TOPOLOGICA LLC
License: Apache-2.0
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, TypedDict

import httpx

BASE_URL = "https://rest.uniprot.org"
# Curated allowlist of cross-origin endpoints uniprot-mcp may consult.
# Each entry expands the threat surface (declared in docs/THREAT_MODEL.md
# §T3) and is documented in PRIVACY.md as a third party.
ALPHAFOLD_API_BASE = "https://alphafold.ebi.ac.uk"
NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TIMEOUT = 30.0
MAX_RETRIES = 3
MAX_RETRY_AFTER_SECONDS = 120.0  # cap server-dictated waits
UA = "uniprot-mcp/1.1.2 (+https://github.com/smaniches/uniprot-mcp)"

# Official UniProt accession format.
# https://www.uniprot.org/help/accession_numbers
ACCESSION_RE = re.compile(
    r"\A(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2})\Z"
)

# UniProt controlled-vocabulary identifier formats. Both are
# zero-padded four-digit numbers behind a two-letter prefix.
# https://www.uniprot.org/keywords  -> KW-NNNN (e.g. KW-0007 = Acetylation)
# https://www.uniprot.org/locations -> SL-NNNN (e.g. SL-0086 = Cytoplasm,
#                                       SL-0039 = Cell membrane, SL-0191 = Nucleus)
KEYWORD_ID_RE = re.compile(r"\AKW-[0-9]{4}\Z")
SUBCELLULAR_LOCATION_ID_RE = re.compile(r"\ASL-[0-9]{4}\Z")

# UniRef cluster identifier. Three identity tiers (50 / 90 / 100 %)
# are encoded in the prefix; the suffix is either a UniProt accession
# (the canonical representative member) or a UniParc UPI.
# https://www.uniprot.org/help/uniref
UNIREF_ID_RE = re.compile(
    r"\AUniRef(?:50|90|100)_"
    r"(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2}|UPI[A-F0-9]{10})"
    r"\Z"
)
UNIREF_IDENTITY_TIERS = ("50", "90", "100")

# UniParc UPI (sequence-archive identifier). Always 13 chars: ``UPI``
# prefix + 10 uppercase hex digits.
# https://www.uniprot.org/help/uniparc
UNIPARC_ID_RE = re.compile(r"\AUPI[A-F0-9]{10}\Z")

# Proteome UP identifier. ``UP`` prefix + 9-11 digits.
# https://www.uniprot.org/help/proteome
PROTEOME_ID_RE = re.compile(r"\AUP[0-9]{9,11}\Z")

# UniProt's literature/citations endpoint identifies records by the
# numeric source identifier (typically a PubMed ID; sometimes a
# DOI-shaped reference for citations without a PMID). For pinning down
# the exact format we accept what UniProt accepts: 1-12 digits — wide
# enough for any real PMID, narrow enough to reject paths.
CITATION_ID_RE = re.compile(r"\A[0-9]{1,12}\Z")

# Stable identifier for the data source. Emitted in every Provenance
# record so downstream consumers can disambiguate multi-source outputs.
SOURCE_NAME = "UniProt"

# Response headers UniProt uses to announce the currently-served release.
# Documented at https://www.uniprot.org/help/api_programmatic_access.
_RELEASE_HEADER = "X-UniProt-Release"
_RELEASE_DATE_HEADER = "X-UniProt-Release-Date"

# Environment variable that opts the client into release pinning. When set
# (or when the constructor's ``pin_release`` argument is non-None), the
# client raises :class:`ReleaseMismatchError` if a successful upstream
# response carries an ``X-UniProt-Release`` header that disagrees with the
# pinned value. UniProt's REST API does not honour a release-selector
# query parameter; pinning is therefore *assertion-only* — the client
# refuses results from any release other than the pinned one rather than
# silently accepting drift.
PIN_RELEASE_ENV = "UNIPROT_PIN_RELEASE"


class ReleaseMismatchError(RuntimeError):
    """A pinned-release client received a response from a different release.

    Carries the pinned and observed release strings so the caller (or
    the agent reading the error envelope) can decide whether to retry
    against a snapshot or accept the drift.
    """

    def __init__(self, *, pinned: str, observed: str | None, url: str) -> None:
        self.pinned = pinned
        self.observed = observed
        self.url = url
        observed_disp = observed if observed is not None else "(absent)"
        super().__init__(
            f"UniProt release mismatch — pinned {pinned!r}, observed {observed_disp!r} "
            f"at {url}. Re-run against a release-{pinned} FTP snapshot, or unset "
            f"{PIN_RELEASE_ENV} to accept the live release."
        )


class Provenance(TypedDict):
    """Machine-verifiable provenance for a single UniProt response.

    Emitted on every response so (a) the LLM can cite it, (b) a human
    auditor can reproduce the request, and (c) reproducibility pipelines
    can pin to a specific release.

    Fields:
      source            — always ``"UniProt"``; lets multi-source
                          orchestrators route on origin.
      release           — UniProt release identifier (e.g. ``"2026_02"``)
                          or ``None`` when the server omitted the header.
      release_date      — ISO-8601 calendar date of that release, or ``None``.
      retrieved_at      — ISO-8601 UTC instant at which the client received
                          the response, second precision.
      url               — the fully resolved request URL including query
                          string — reproduces the exact query.
      response_sha256   — SHA-256 of a *canonical* serialization of the
                          response body. For JSON responses the body is
                          parsed and re-serialized with sorted keys and
                          compact separators, so insignificant key-order
                          changes within a release don't break verification.
                          For non-JSON (FASTA, plain text), the raw bytes
                          are hashed. The :func:`provenance_verify` MCP
                          tool re-fetches the URL and compares this hash
                          to detect post-hoc upstream drift.
    """

    source: str
    release: str | None
    release_date: str | None
    retrieved_at: str
    url: str
    response_sha256: str


__all__ = [
    "ACCESSION_RE",
    "ALPHAFOLD_API_BASE",
    "BASE_URL",
    "CITATION_ID_RE",
    "KEYWORD_ID_RE",
    "MAX_RETRIES",
    "MAX_RETRY_AFTER_SECONDS",
    "NCBI_EUTILS_BASE",
    "PIN_RELEASE_ENV",
    "PROTEOME_ID_RE",
    "SOURCE_NAME",
    "SUBCELLULAR_LOCATION_ID_RE",
    "TIMEOUT",
    "UA",
    "UNIPARC_ID_RE",
    "UNIREF_IDENTITY_TIERS",
    "UNIREF_ID_RE",
    "Provenance",
    "ReleaseMismatchError",
    "UniProtClient",
    "canonical_response_hash",
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


def canonical_response_hash(response: httpx.Response) -> str:
    """Return a SHA-256 hex digest of a *canonical* serialization of the
    response body.

    For JSON responses, the body is parsed and re-serialized with
    ``sort_keys=True`` and compact separators — insignificant key-order
    or whitespace differences within the same UniProt release will not
    break verification, but real content differences will.

    For non-JSON responses (FASTA, plain text), the raw response bytes
    are hashed unchanged.
    """
    content_type = (response.headers.get("content-type") or "").lower()
    if "json" in content_type:
        try:
            obj = response.json()
        except (ValueError, json.JSONDecodeError):
            return hashlib.sha256(response.content).hexdigest()
        canonical = json.dumps(
            obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()
    return hashlib.sha256(response.content).hexdigest()


def _extract_provenance(response: httpx.Response, *, now: datetime | None = None) -> Provenance:
    """Build a Provenance record from a UniProt HTTP response.

    ``now`` is exposed for test determinism; production callers leave
    it at ``None`` so retrieval time is captured at extraction moment.
    """
    moment = now if now is not None else datetime.now(tz=UTC)
    return Provenance(
        source=SOURCE_NAME,
        release=response.headers.get(_RELEASE_HEADER),
        release_date=response.headers.get(_RELEASE_DATE_HEADER),
        retrieved_at=moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        url=str(response.url),
        response_sha256=canonical_response_hash(response),
    )


class UniProtClient:
    """Thin async wrapper over the UniProt REST API.

    ``pin_release`` opts the client into strict release pinning. When
    set (constructor argument or ``UNIPROT_PIN_RELEASE`` environment
    variable), every successful response is checked against the pinned
    release; mismatches raise :class:`ReleaseMismatchError`. UniProt
    does not honour a release-selector query parameter, so pinning is
    assertion-only — the client refuses results from any other release
    rather than silently accepting drift.
    """

    def __init__(self, *, pin_release: str | None = None) -> None:
        self._client: httpx.AsyncClient | None = None
        self._last_provenance: Provenance | None = None
        if pin_release is None:
            pin_release = os.environ.get(PIN_RELEASE_ENV, "").strip() or None
        self._pin_release: str | None = pin_release

    @property
    def pin_release(self) -> str | None:
        """Pinned UniProt release identifier, or ``None`` for unpinned."""
        return self._pin_release

    @property
    def last_provenance(self) -> Provenance | None:
        """Provenance of the most recent successful request, or ``None``
        if no request has completed yet on this client."""
        return self._last_provenance

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
                provenance = _extract_provenance(resp)
                if self._pin_release and provenance["release"] != self._pin_release:
                    raise ReleaseMismatchError(
                        pinned=self._pin_release,
                        observed=provenance["release"],
                        url=str(resp.url),
                    )
                self._last_provenance = provenance
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
                provenance = _extract_provenance(resp)
                if self._pin_release and provenance["release"] != self._pin_release:
                    raise ReleaseMismatchError(
                        pinned=self._pin_release,
                        observed=provenance["release"],
                        url=str(resp.url),
                    )
                self._last_provenance = provenance
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

    async def get_keyword(self, keyword_id: str) -> dict[str, Any]:
        data: dict[str, Any] = (await self._req("GET", f"/keywords/{keyword_id}")).json()
        return data

    async def search_keywords(self, query: str, size: int = 10) -> dict[str, Any]:
        data: dict[str, Any] = (
            await self._req(
                "GET", "/keywords/search", params={"query": query, "size": min(size, 500)}
            )
        ).json()
        return data

    async def get_subcellular_location(self, location_id: str) -> dict[str, Any]:
        data: dict[str, Any] = (await self._req("GET", f"/locations/{location_id}")).json()
        return data

    async def search_subcellular_locations(self, query: str, size: int = 10) -> dict[str, Any]:
        data: dict[str, Any] = (
            await self._req(
                "GET", "/locations/search", params={"query": query, "size": min(size, 500)}
            )
        ).json()
        return data

    async def get_uniparc(self, upi: str) -> dict[str, Any]:
        data: dict[str, Any] = (await self._req("GET", f"/uniparc/{upi}")).json()
        return data

    async def search_uniparc(self, query: str, size: int = 10) -> dict[str, Any]:
        data: dict[str, Any] = (
            await self._req(
                "GET", "/uniparc/search", params={"query": query, "size": min(size, 500)}
            )
        ).json()
        return data

    async def get_proteome(self, upid: str) -> dict[str, Any]:
        data: dict[str, Any] = (await self._req("GET", f"/proteomes/{upid}")).json()
        return data

    async def search_proteomes(self, query: str, size: int = 10) -> dict[str, Any]:
        data: dict[str, Any] = (
            await self._req(
                "GET", "/proteomes/search", params={"query": query, "size": min(size, 500)}
            )
        ).json()
        return data

    async def get_citation(self, citation_id: str) -> dict[str, Any]:
        data: dict[str, Any] = (await self._req("GET", f"/citations/{citation_id}")).json()
        return data

    async def get_clinvar_records(
        self, gene: str, change: str = "", retmax: int = 10
    ) -> dict[str, Any]:
        """Fetch ClinVar records via NCBI eutils.

        Cross-origin call to ``eutils.ncbi.nlm.nih.gov``. Two-step:
        ``esearch`` returns ClinVar IDs matching the gene (and optional
        protein change); ``esummary`` returns the structured records.
        Returns a dict with keys ``records`` (list) and ``total``
        (the unfiltered esearch count, useful for "showing N of M").
        """
        term = f"{gene}[Gene]"
        if change:
            term += f' AND "{change}"[Variant Name]'
        params_search: dict[str, Any] = {
            "db": "clinvar",
            "term": term,
            "retmode": "json",
            "retmax": min(retmax, 50),
        }
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(TIMEOUT),
            headers={"User-Agent": UA, "Accept": "application/json"},
            follow_redirects=True,
        ) as ext:
            r_search = await ext.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi", params=params_search)
            r_search.raise_for_status()
            search_payload = r_search.json()
            esearch_result = search_payload.get("esearchresult", {})
            ids: list[str] = list(esearch_result.get("idlist") or [])
            total = int(esearch_result.get("count") or 0)
            if not ids:
                self._last_provenance = Provenance(
                    source="NCBI ClinVar (eutils)",
                    release=None,
                    release_date=None,
                    retrieved_at=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    url=str(r_search.url),
                    response_sha256=canonical_response_hash(r_search),
                )
                return {"records": [], "total": total}
            r_summary = await ext.get(
                f"{NCBI_EUTILS_BASE}/esummary.fcgi",
                params={"db": "clinvar", "id": ",".join(ids), "retmode": "json"},
            )
            r_summary.raise_for_status()
            summary_payload: dict[str, Any] = r_summary.json()
        result_block = summary_payload.get("result") or {}
        records: list[dict[str, Any]] = []
        for uid in result_block.get("uids") or []:
            rec = result_block.get(uid)
            if isinstance(rec, dict):
                records.append(rec)
        self._last_provenance = Provenance(
            source="NCBI ClinVar (eutils)",
            release=None,
            release_date=None,
            retrieved_at=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            url=str(r_summary.url),
            response_sha256=canonical_response_hash(r_summary),
        )
        return {"records": records, "total": total}

    async def get_alphafold_summary(self, accession: str) -> dict[str, Any]:
        """Fetch AlphaFold-DB prediction metadata for a UniProt accession.

        This is a *cross-origin* call to ``https://alphafold.ebi.ac.uk`` —
        the only origin uniprot-mcp consults outside ``rest.uniprot.org``.
        The endpoint returns global pLDDT statistics
        (``globalMetricValue`` plus four ``fractionPlddt*`` bands) without
        needing to download the full structure file. Provenance carries
        ``source = "AlphaFoldDB"`` and the model version as ``release``.
        """
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(TIMEOUT),
            headers={"User-Agent": UA, "Accept": "application/json"},
            follow_redirects=True,
        ) as ext:
            resp = await ext.get(f"{ALPHAFOLD_API_BASE}/api/prediction/{accession}")
            resp.raise_for_status()
            payload: list[dict[str, Any]] = resp.json()
        if not payload:
            self._last_provenance = Provenance(
                source="AlphaFoldDB",
                release=None,
                release_date=None,
                retrieved_at=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                url=str(resp.url),
                response_sha256=canonical_response_hash(resp),
            )
            return {}
        record: dict[str, Any] = payload[0]
        version_value = record.get("latestVersion")
        version = f"v{version_value}" if version_value is not None else None
        self._last_provenance = Provenance(
            source="AlphaFoldDB",
            release=version,
            release_date=str(record.get("modelCreatedDate") or "") or None,
            retrieved_at=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            url=str(resp.url),
            response_sha256=canonical_response_hash(resp),
        )
        return record

    async def search_citations(self, query: str, size: int = 10) -> dict[str, Any]:
        data: dict[str, Any] = (
            await self._req(
                "GET", "/citations/search", params={"query": query, "size": min(size, 500)}
            )
        ).json()
        return data

    async def get_uniref(self, uniref_id: str) -> dict[str, Any]:
        data: dict[str, Any] = (await self._req("GET", f"/uniref/{uniref_id}")).json()
        return data

    async def search_uniref(self, query: str, size: int = 10) -> dict[str, Any]:
        """Search UniRef clusters.

        The caller is expected to embed any identity-tier filter into
        the query string itself (UniProt query syntax: ``identity:0.5``
        / ``identity:0.9`` / ``identity:1.0`` for the 50 / 90 / 100 %
        tiers respectively). The server tool wraps that for ergonomics.
        """
        data: dict[str, Any] = (
            await self._req(
                "GET", "/uniref/search", params={"query": query, "size": min(size, 500)}
            )
        ).json()
        return data
