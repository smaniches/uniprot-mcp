"""UniProt REST API client.

Async, with exponential back-off on 429 / 5xx, strict accession
validation, HTTP-date-aware Retry-After parsing, and a polling loop
for the ID-mapping job API.

Every successful request updates :attr:`UniProtClient.last_provenance`
with the release-number, release-date, retrieval timestamp, and the
final resolved URL. Callers (MCP tool handlers) read that property
immediately after a request and pass the record into the formatter,
which surfaces it to the LLM or downstream consumer.

Thread-safety: provenance is stored in a request-scoped
:class:`~contextvars.ContextVar`, so a single :class:`UniProtClient` is
safe to share across concurrent asyncio tasks — each task reads the
provenance of its own request, never another in-flight request's. The
stdio MCP transport serializes tool invocations today; the context
scoping also keeps the module-level singleton in ``server.py`` correct
under a future parallel HTTP/SSE transport.

Author: Santiago Maniches <santiago.maniches@gmail.com>
        ORCID https://orcid.org/0009-0005-6480-1987
        TOPOLOGICA LLC
License: Apache-2.0
"""

from __future__ import annotations

import asyncio
import contextvars
import hashlib
import json
import math
import os
import re
import urllib.parse
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from importlib.metadata import version as _pkg_version
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
try:
    _v = _pkg_version("uniprot-mcp-server") or "dev"
except Exception:  # pragma: no cover  # import-time fallback when running uninstalled from source (PackageNotFoundError); cannot be exercised without an import-time reload that breaks exception-class identity across the package
    _v = "dev"
UA = f"uniprot-mcp/{_v} (+https://github.com/smaniches/uniprot-mcp)"

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


class UntrustedRedirectError(RuntimeError):
    """An id-mapping redirectURL pointed outside the trusted UniProt origin.

    The id-mapping poll loop follows the server-supplied ``redirectURL`` as
    an *absolute* URL. ``httpx`` does not constrain absolute URLs to the
    client's ``base_url``, so a malicious or MITM'd ``redirectURL`` would be
    fetched verbatim. The client therefore validates the host against a
    suffix allowlist (``*.uniprot.org`` / ``uniprot.org``) and raises this
    error rather than dispatching a request to an untrusted origin.
    """


def _assert_trusted_redirect(url: str) -> None:
    """Raise :class:`UntrustedRedirectError` unless ``url`` targets UniProt.

    The legitimate id-mapping redirect target is ``rest.uniprot.org``. We
    accept only ``http``/``https`` URLs whose host is ``uniprot.org`` or a
    subdomain of it. The check is a hostname *suffix* match on
    ``.uniprot.org`` (not ``netloc.endswith("uniprot.org")``, which would
    also match a hostile ``evil-uniprot.org`` or ``uniprot.org.evil.com``).
    """
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    if parsed.scheme not in ("http", "https") or host is None:
        raise UntrustedRedirectError(
            f"id-mapping redirectURL is not an absolute http(s) URL: {url!r}"
        )
    if host != "uniprot.org" and not host.endswith(".uniprot.org"):
        raise UntrustedRedirectError(
            f"id-mapping redirectURL points outside the trusted UniProt origin: {url!r}"
        )


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
      accept_header     — the ``Accept`` request header value used for the
                          original request. Required by the verification
                          tool to re-fetch with the correct content
                          negotiation (e.g. ``"text/plain;format=fasta"``
                          vs ``"application/json"``).
    """

    source: str
    release: str | None
    release_date: str | None
    retrieved_at: str
    url: str
    response_sha256: str
    accept_header: str


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
    "UntrustedRedirectError",
    "canonical_response_hash",
    "parse_retry_after",
]


# Request-scoped provenance. Each successful request stores its provenance
# here; the ``last_provenance`` property reads it back when a tool renders
# its footer. Storing it in a :class:`~contextvars.ContextVar` (rather than a
# shared instance attribute) makes provenance per-request: concurrent MCP tool
# calls run as separate asyncio tasks, each with its own context copy, so a
# footer can never attest the bytes of a different in-flight request. The
# stdio transport serialises calls today, but this also makes the shared
# module-level client safe under a future parallel HTTP/SSE transport.
_request_provenance: contextvars.ContextVar[Provenance | None] = contextvars.ContextVar(
    "uniprot_request_provenance", default=None
)


def parse_retry_after(value: str | None, attempt: int) -> float:
    """Parse an RFC 7231 ``Retry-After`` response header.

    Accepts delta-seconds or HTTP-date; returns a clamped float.
    Falls back to exponential back-off when missing or malformed.
    """
    fallback = 1.5 ** (attempt + 1)
    if not value:
        return fallback
    try:
        seconds = float(value)
    except ValueError:
        pass
    else:
        # ``float()`` accepts "nan"/"inf", so a hostile or broken upstream
        # can drive the numeric branch non-finite. ``min(nan, 120)`` is
        # ``nan`` and ``min(inf, 120)`` is ``120``; a ``nan`` delay then
        # reaches ``asyncio.sleep``, which on CPython treats it as a
        # non-positive (immediate) wait -- i.e. zero-effective-backoff
        # hot-retry against a rate-limited server (and other runtimes may
        # reject it outright). Reject non-finite to the back-off fallback.
        # Clamp negatives to 0.0, mirroring the HTTP-date branch -- RFC 7231
        # 7.1.3 delta-seconds is a non-negative integer, so a negative
        # value is malformed and must not yield a negative sleep.
        if not math.isfinite(seconds):
            return fallback
        return min(max(seconds, 0.0), MAX_RETRY_AFTER_SECONDS)
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


async def _get_with_retry(
    client: httpx.AsyncClient, url: str, *, params: dict[str, Any] | None = None
) -> httpx.Response:
    """GET ``url`` through a bounded retry policy mirroring ``_req``.

    Used by the cross-origin callers (NCBI eutils, AlphaFold-DB) which open
    their own short-lived :class:`httpx.AsyncClient`. Retries on HTTP 429
    (honouring ``Retry-After``), HTTP >= 500, and :class:`httpx.TimeoutException`
    with ``1.5 ** (attempt + 1)`` back-off, up to ``MAX_RETRIES + 1`` attempts.

    Any other response — including 404 — is returned to the caller unchanged.
    This matters for AlphaFold-DB, where 404 is a legitimate "no model"
    answer the caller must see and not a transient failure to retry.
    """
    last_detail = "no response"
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 429:
                last_detail = "HTTP 429 (rate limited)"
                await asyncio.sleep(parse_retry_after(resp.headers.get("Retry-After"), attempt))
                continue
            if resp.status_code >= 500:
                last_detail = f"HTTP {resp.status_code}"
                await asyncio.sleep(1.5 ** (attempt + 1))
                continue
            return resp
        except httpx.TimeoutException:
            last_detail = "timeout"
            await asyncio.sleep(1.5 ** (attempt + 1))
    raise RuntimeError(f"Request to {url} failed after {MAX_RETRIES + 1} attempts ({last_detail})")


def _extract_provenance(response: httpx.Response, *, now: datetime | None = None) -> Provenance:
    """Build a Provenance record from a UniProt HTTP response.

    ``now`` is exposed for test determinism; production callers leave
    it at ``None`` so retrieval time is captured at extraction moment.
    """
    moment = now if now is not None else datetime.now(tz=UTC)
    # ``response.request`` is guaranteed set here: the Provenance below also
    # reads ``response.url``, which httpx derives from ``Response.request``
    # (the property RAISES if the request is unset). So the accept header can
    # be read directly — no None-guard (the property never returns None) and
    # no pragma.
    accept = response.request.headers.get("accept", "application/json")
    return Provenance(
        source=SOURCE_NAME,
        release=response.headers.get(_RELEASE_HEADER),
        release_date=response.headers.get(_RELEASE_DATE_HEADER),
        retrieved_at=moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        url=str(response.url),
        response_sha256=canonical_response_hash(response),
        accept_header=accept,
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
        if pin_release is None:
            pin_release = os.environ.get(PIN_RELEASE_ENV, "").strip() or None
        self._pin_release: str | None = pin_release

    @property
    def pin_release(self) -> str | None:
        """Pinned UniProt release identifier, or ``None`` for unpinned."""
        return self._pin_release

    @property
    def last_provenance(self) -> Provenance | None:
        """Provenance of the most recent successful request in the current
        request context, or ``None`` if no request has completed yet in it.

        Backed by a request-scoped :class:`~contextvars.ContextVar`, so under
        concurrent tool calls each task reads the provenance of its own
        request — never another in-flight request's."""
        return _request_provenance.get()

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
        last_detail = "no response"
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.request(method, path, params=params, headers=headers)
                if resp.status_code == 429:
                    last_detail = "HTTP 429 (rate limited)"
                    await asyncio.sleep(parse_retry_after(resp.headers.get("Retry-After"), attempt))
                    continue
                if resp.status_code >= 500:
                    last_detail = f"HTTP {resp.status_code}"
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
                _request_provenance.set(provenance)
                return resp
            except httpx.TimeoutException:
                last_detail = "timeout"
                await asyncio.sleep(1.5 ** (attempt + 1))
        raise RuntimeError(f"Request failed after {MAX_RETRIES + 1} attempts ({last_detail})")

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
        last_detail = "no response"
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.post(
                    "/idmapping/run",
                    data={"from": from_db, "to": to_db, "ids": ",".join(ids)},
                )
                if resp.status_code == 429:
                    last_detail = "HTTP 429 (rate limited)"
                    await asyncio.sleep(parse_retry_after(resp.headers.get("Retry-After"), attempt))
                    continue
                if resp.status_code >= 500:
                    last_detail = f"HTTP {resp.status_code}"
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
                _request_provenance.set(provenance)
                job_id: str = resp.json()["jobId"]
                return job_id
            except httpx.TimeoutException:
                last_detail = "timeout"
                await asyncio.sleep(1.5 ** (attempt + 1))
        raise RuntimeError(
            f"id_mapping_submit failed after {MAX_RETRIES + 1} attempts ({last_detail})"
        )

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
                _assert_trusted_redirect(url)
                return (await self._req("GET", url, params={"size": size})).json()  # type: ignore[no-any-return]
            job_status = status.get("jobStatus")
            if job_status is not None and job_status not in ("NEW", "RUNNING"):
                # UniProt's reference id-mapping client
                # (``check_id_mapping_results_ready``) polls only while
                # ``jobStatus`` is "NEW" or "RUNNING" and treats any other
                # value as a terminal failure. A terminal status (e.g.
                # "ERROR") returned with HTTP 200 must raise immediately
                # rather than spin 30 polls to a misleading TimeoutError;
                # surface the upstream status and any message/error detail.
                detail = status.get("messages") or status.get("errors") or status.get("message")
                if isinstance(detail, list):
                    # UniProt returns ``messages``/``errors`` as JSON arrays;
                    # join them so the error reads as text rather than a raw
                    # Python list repr (``['msg']``).
                    detail = "; ".join(str(item) for item in detail)
                suffix = f": {detail}" if detail else ""
                raise RuntimeError(f"ID mapping failed (jobStatus={job_status!r}){suffix}")
            await asyncio.sleep(1.0)
        raise TimeoutError("ID mapping did not complete in 30s")

    async def batch_entries(
        self, accessions: list[str], fields: list[str] | None = None
    ) -> dict[str, Any]:
        """Fetch up to 100 entries.

        Invalid accessions are filtered client-side so a single bad token
        does not cause UniProt to reject the whole batch. The raw invalid
        tokens are returned under the ``invalid`` key for the caller to
        surface. When more than 100 valid accessions are supplied the batch
        is capped at 100 and ``truncated`` is set to ``True`` so the caller
        can signal the elision rather than silently dropping the tail.
        ``n_valid`` reports the total number of valid accessions supplied
        before the cap, so the caller can report "showing 100 of N".
        """
        valid = [a for a in accessions if ACCESSION_RE.match(a.upper())]
        valid_set = set(valid)
        invalid = [a for a in accessions if a not in valid_set]
        n_valid = len(valid)
        truncated = n_valid > 100
        if truncated:
            valid = valid[:100]
        if not valid:
            return {"results": [], "invalid": invalid, "truncated": truncated, "n_valid": n_valid}
        query = " OR ".join(f"accession:{a}" for a in valid)
        params: dict[str, Any] = {"query": query, "size": len(valid)}
        if fields:
            params["fields"] = ",".join(fields)
        results = (
            (await self._req("GET", "/uniprotkb/search", params=params)).json().get("results", [])
        )
        return {"results": results, "invalid": invalid, "truncated": truncated, "n_valid": n_valid}

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
            r_search = await _get_with_retry(
                ext, f"{NCBI_EUTILS_BASE}/esearch.fcgi", params=params_search
            )
            r_search.raise_for_status()
            search_payload = r_search.json()
            esearch_result = search_payload.get("esearchresult", {})
            ids: list[str] = list(esearch_result.get("idlist") or [])
            total = int(esearch_result.get("count") or 0)
            if not ids:
                _request_provenance.set(
                    Provenance(
                        source="NCBI ClinVar (eutils)",
                        release=None,
                        release_date=None,
                        retrieved_at=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        url=str(r_search.url),
                        response_sha256=canonical_response_hash(r_search),
                        accept_header="application/json",
                    )
                )
                return {"records": [], "total": total}
            r_summary = await _get_with_retry(
                ext,
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
        _request_provenance.set(
            Provenance(
                source="NCBI ClinVar (eutils)",
                release=None,
                release_date=None,
                retrieved_at=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                url=str(r_summary.url),
                response_sha256=canonical_response_hash(r_summary),
                accept_header="application/json",
            )
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
            resp = await _get_with_retry(ext, f"{ALPHAFOLD_API_BASE}/api/prediction/{accession}")
            # The prediction endpoint returns 404 for accessions with no
            # AlphaFold model (e.g. Q8WZ42). That is a legitimate
            # "no model" answer, not an error -- route it into the same
            # graceful empty-record branch as an empty ``[]`` body. Any
            # other non-2xx status still raises ``HTTPStatusError``.
            if resp.status_code == 404:
                payload: list[dict[str, Any]] = []
            else:
                resp.raise_for_status()
                payload = resp.json()
        if not payload:
            _request_provenance.set(
                Provenance(
                    source="AlphaFoldDB",
                    release=None,
                    release_date=None,
                    retrieved_at=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    url=str(resp.url),
                    response_sha256=canonical_response_hash(resp),
                    accept_header="application/json",
                )
            )
            return {}
        record: dict[str, Any] = payload[0]
        version_value = record.get("latestVersion")
        version = f"v{version_value}" if version_value is not None else None
        _request_provenance.set(
            Provenance(
                source="AlphaFoldDB",
                release=version,
                release_date=str(record.get("modelCreatedDate") or "") or None,
                retrieved_at=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                url=str(resp.url),
                response_sha256=canonical_response_hash(resp),
                accept_header="application/json",
            )
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
