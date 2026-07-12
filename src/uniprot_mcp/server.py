"""TOPOLOGICA UniProt MCP Server. 41 tools. FastMCP. stdio transport.

Hardened against the common class of MCP-server defects:

- Inputs are length-capped before reaching httpx (DoS / abuse mitigation).
- ``response_format`` is validated against an allow-list.
- Error envelopes do not leak raw exception text back to the LLM; we
  emit a stable, agent-safe message and log detail server-side.
- Every successful tool response carries a machine-verifiable
  :class:`~uniprot_mcp.client.Provenance` record — UniProt release
  number, release date, retrieval timestamp, the resolved query URL,
  AND a SHA-256 of the canonical response body — rendered inline as a
  Markdown footer, a JSON envelope, or a PIR-style comment block
  depending on the output format. ``uniprot_provenance_verify``
  re-fetches a recorded URL and compares both the release header and
  the canonical response hash to detect post-hoc upstream drift.
- ``--pin-release=YYYY_MM`` (or ``UNIPROT_PIN_RELEASE`` env var) opts
  into strict release pinning: a successful response from any other
  release raises ``ReleaseMismatchError`` and the tool returns an
  agent-safe error envelope.
- Module-level lazy client avoids the FastMCP lifespan ctx-injection
  race that broke ``Failed to connect`` in the first implementation.

Author: Santiago Maniches <santiago.maniches@gmail.com>
        ORCID https://orcid.org/0009-0005-6480-1987
        TOPOLOGICA LLC
License: Apache-2.0
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from typing import Annotated, Any, Final, NoReturn

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from uniprot_mcp.cache import (
    CACHE_DIR_ENV,
    ProvenanceCache,
    cache_dir_from_env,
)
from uniprot_mcp.client import (
    ACCESSION_RE,
    CITATION_ID_RE,
    KEYWORD_ID_RE,
    PIN_RELEASE_ENV,
    PROTEOME_ID_RE,
    SUBCELLULAR_LOCATION_ID_RE,
    UA,
    UNIPARC_ID_RE,
    UNIREF_ID_RE,
    UNIREF_IDENTITY_TIERS,
    ReleaseMismatchError,
    UniProtClient,
    canonical_response_hash,
)
from uniprot_mcp.eco import ECO_HUMAN_LABELS, confidence_markdown_lines, score_evidence
from uniprot_mcp.formatters import (
    ACTIVE_SITE_FEATURE_TYPES,
    PROCESSING_FEATURE_TYPES,
    PTM_FEATURE_TYPES,
    fmt_active_sites,
    fmt_alphafold,
    fmt_alphafold_confidence,
    fmt_chembl,
    fmt_citation,
    fmt_citation_search,
    fmt_clinvar,
    fmt_crossrefs,
    fmt_disease_associations,
    fmt_entry,
    fmt_fasta,
    fmt_features,
    fmt_features_at_position,
    fmt_go,
    fmt_idmapping,
    fmt_interpro,
    fmt_keyword,
    fmt_keyword_search,
    fmt_orthology,
    fmt_pdb,
    fmt_processing_features,
    fmt_properties,
    fmt_proteome,
    fmt_proteome_search,
    fmt_ptms,
    fmt_publications,
    fmt_search,
    fmt_subcellular_location,
    fmt_subcellular_location_search,
    fmt_target_dossier,
    fmt_taxonomy,
    fmt_uniparc,
    fmt_uniparc_search,
    fmt_uniref,
    fmt_uniref_search,
    fmt_variant_lookup,
    fmt_variants,
)
from uniprot_mcp.proteinchem import compute_protein_properties

logger = logging.getLogger("topologica.uniprot")
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)

mcp = FastMCP("topologica_uniprot_mcp")

# Input caps. Short enough to block abuse, long enough for any realistic query.
MAX_ACCESSION_LEN: Final[int] = 20
MAX_QUERY_LEN: Final[int] = 500
MAX_IDS_LEN: Final[int] = 5_000  # ~500 comma-separated ids of realistic length
MAX_ORGANISM_LEN: Final[int] = 100
MAX_DATABASE_LEN: Final[int] = 50
MAX_FEATURE_TYPES_LEN: Final[int] = 200
# UniProt KW-NNNN / SL-NNNN are exactly 7 characters; cap modestly above
# to leave headroom for any future numeric expansion without uncapping.
MAX_VOCAB_ID_LEN: Final[int] = 12
# UniRef IDs: ``UniRef100_`` (10) + UniProt accession (≤ 10) or UPI (13).
# 30 covers either with margin.
MAX_UNIREF_ID_LEN: Final[int] = 30
# UniParc UPI is exactly 13 characters; cap at 16 for headroom.
MAX_UNIPARC_ID_LEN: Final[int] = 16
# Proteome UP ID is up to 13 characters; cap at 16.
MAX_PROTEOME_ID_LEN: Final[int] = 16
# Citation IDs (PubMed) up to 12 digits; cap at 16.
MAX_CITATION_ID_LEN: Final[int] = 16
# HGVS-style protein change: <orig><pos><alt> e.g. R175H, R248*, V600E.
# Realistic max position in any protein is ~38000 residues (titin); cap
# generously at 8 chars total to allow stop ('*'), three-letter-style
# stop ('Ter'), or simply position-only short forms.
MAX_VARIANT_CHANGE_LEN: Final[int] = 16
# Sequence-position upper bound. Titin (UniProt Q8WZ42) is the longest
# human protein at 34,350 residues; round up generously.
MAX_SEQUENCE_POSITION: Final[int] = 100_000
# Provenance-verify URL cap. Real UniProt URLs are well under this.
MAX_PROVENANCE_URL_LEN: Final[int] = 1_000
# UniProt release tag is YYYY_MM (7 chars). 16 covers any plausible
# future schema with ample margin.
MAX_RELEASE_TAG_LEN: Final[int] = 16
ALLOWED_RESPONSE_FORMATS: Final[frozenset[str]] = frozenset({"markdown", "json"})
ALLOWED_ACCEPT_HEADERS: Final[frozenset[str]] = frozenset(
    {
        "application/json",
        "text/plain;format=fasta",
    }
)

# Shared parameter annotations. FastMCP reads ``Field(description=...)``
# on an ``Annotated`` parameter into the tool's JSON-schema property
# description, so every tool that reuses one of these gets the same
# precise, example-bearing guidance for free — one definition, applied
# consistently across the whole surface, instead of re-explaining
# "what does 'accession' mean" 30 separate times with 30 chances to drift.
AccessionParam = Annotated[
    str,
    Field(
        description=(
            "UniProt accession, e.g. 'P04637' (human TP53) or 'P38398' "
            "(human BRCA1). Both reviewed (Swiss-Prot) and unreviewed "
            "(TrEMBL) accessions are accepted; case-sensitive."
        )
    ),
]
ResponseFormatParam = Annotated[
    str,
    Field(
        description=(
            "'markdown' (default) for a human-readable report with a "
            "provenance footer, or 'json' for a machine-parseable "
            "structured payload with the same data. Any other value is "
            "rejected."
        )
    ),
]
QueryParam = Annotated[
    str,
    Field(
        description=(
            "UniProt query-language expression, e.g. "
            "'(gene:TP53) AND (organism_id:9606)'. Field syntax follows "
            "https://www.uniprot.org/help/query-fields."
        )
    ),
]
SizeParam = Annotated[
    int,
    Field(description="Maximum number of results to return; capped at 500 server-side."),
]

# Module-level lazy client. No lifespan. No ctx injection. Just works.
_uniprot: UniProtClient | None = None


def _client() -> UniProtClient:
    global _uniprot
    if _uniprot is None:
        _uniprot = UniProtClient()
    return _uniprot


class _InputError(ValueError):
    """Raised when caller-supplied input fails validation. Agent-safe."""


def _check_len(name: str, value: str, limit: int) -> None:
    if len(value) > limit:
        raise _InputError(f"{name} exceeds {limit}-character limit")


def _check_accession(value: str) -> None:
    _check_len("accession", value, MAX_ACCESSION_LEN)
    if not ACCESSION_RE.match(value.upper()):
        raise _InputError("accession must match the UniProt format (e.g. P04637, A0A1B2C3D4)")


def _check_format(value: str) -> None:
    if value not in ALLOWED_RESPONSE_FORMATS:
        raise _InputError(f"response_format must be one of {sorted(ALLOWED_RESPONSE_FORMATS)}")


def _check_keyword_id(value: str) -> None:
    _check_len("keyword_id", value, MAX_VOCAB_ID_LEN)
    if not KEYWORD_ID_RE.match(value):
        raise _InputError("keyword_id must match the UniProt format (e.g. KW-0007)")


def _check_subcellular_location_id(value: str) -> None:
    _check_len("location_id", value, MAX_VOCAB_ID_LEN)
    if not SUBCELLULAR_LOCATION_ID_RE.match(value):
        raise _InputError("location_id must match the UniProt format (e.g. SL-0086)")


def _check_uniref_id(value: str) -> None:
    _check_len("uniref_id", value, MAX_UNIREF_ID_LEN)
    if not UNIREF_ID_RE.match(value):
        raise _InputError(
            "uniref_id must match the UniProt format (e.g. UniRef50_P04637, UniRef90_P04637, UniRef100_P04637)"
        )


def _check_uniparc_id(value: str) -> None:
    _check_len("upi", value, MAX_UNIPARC_ID_LEN)
    if not UNIPARC_ID_RE.match(value):
        raise _InputError("upi must match the UniParc format (e.g. UPI000002ED67)")


def _check_proteome_id(value: str) -> None:
    _check_len("proteome_id", value, MAX_PROTEOME_ID_LEN)
    if not PROTEOME_ID_RE.match(value):
        raise _InputError("proteome_id must match the UniProt format (e.g. UP000005640)")


def _check_citation_id(value: str) -> None:
    _check_len("citation_id", value, MAX_CITATION_ID_LEN)
    if not CITATION_ID_RE.match(value):
        raise _InputError(
            "citation_id must be a numeric identifier (typically a PubMed ID, e.g. 12345678)"
        )


def _check_position(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise _InputError("position must be a positive integer")
    if value < 1:
        raise _InputError("position must be a positive integer (residues are 1-indexed)")
    if value > MAX_SEQUENCE_POSITION:
        raise _InputError(
            f"position exceeds {MAX_SEQUENCE_POSITION:,}; the longest human protein "
            f"(titin) has 34,350 residues."
        )


# HGVS-style protein change: <single-letter-original><position><single-letter-alt
# OR '*' for stop>. ``*`` is the unambiguous stop-codon convention.
# Restrict to the 20 standard amino acid letters for both the original
# residue and the alternative residue. The previous regex accepted any
# uppercase letter, which silently allowed non-amino-acid inputs like
# `X1A` or `B5J` (caught by the Hypothesis property test). Stop codon
# `*` is permitted only for the alternative residue (canonical
# nonsense-mutation HGVS shorthand). UniProt's natural-variant
# annotations only ever use these 20 letters + `*`.
_AMINO_ACID_LETTERS = "ACDEFGHIKLMNPQRSTVWY"
_VARIANT_CHANGE_RE = re.compile(
    rf"\A([{_AMINO_ACID_LETTERS}])([1-9][0-9]{{0,4}})([{_AMINO_ACID_LETTERS}*])\Z"
)


def _parse_variant_change(value: str) -> tuple[str, int, str]:
    """Parse an HGVS-shorthand protein change into (original, position, alt).

    Examples accepted: ``R175H``, ``V600E``, ``R248*`` (stop). Examples
    rejected: ``p.R175H`` (HGVS prefix not supported here), ``R175del``,
    ``A1B2`` (multiple residues), case-mixed.
    """
    _check_len("change", value, MAX_VARIANT_CHANGE_LEN)
    m = _VARIANT_CHANGE_RE.match(value)
    if m is None:
        raise _InputError(
            "change must be HGVS-shorthand <original><position><alt>, e.g. "
            "R175H, V600E, or R248* (stop). Position is 1-indexed."
        )
    original, position_str, alt = m.group(1), m.group(2), m.group(3)
    return original, int(position_str), alt


def _safe_error(tool: str, exc: BaseException) -> str:
    """Build an agent-safe error message. Detail goes to the stderr log,
    not the LLM.

    Output is intentionally human-readable plain text with no structured
    error codes. This message becomes the body of the :class:`ToolError`
    raised by :func:`_raise_tool_error`, so the MCP client receives it as
    the content of an ``isError=True`` result; automation should branch on
    that flag rather than parse this string.
    """
    logger.exception("tool=%s failed", tool)
    if isinstance(exc, _InputError):
        return f"Input error in {tool}: {exc}"
    if isinstance(exc, ReleaseMismatchError):
        # Agent-actionable: the message names the pinned release and the
        # observed release verbatim. Safe because both values come from
        # our own state plus an upstream header, not a raw exception trace.
        return (
            f"Release mismatch in {tool}: pinned {exc.pinned!r}, observed "
            f"{exc.observed!r} at {exc.url}. Re-run against a release-{exc.pinned} "
            f"snapshot or unset {PIN_RELEASE_ENV}."
        )
    # Do not echo the raw exception text; agents sometimes treat it as data.
    return f"Error in {tool}: upstream request failed; see server logs for details."


def _raise_tool_error(tool: str, exc: BaseException) -> NoReturn:
    """Raise a sanitized :class:`ToolError` for a failed tool call.

    The message is built by :func:`_safe_error`, so the same sanitized,
    traceback-free text is used regardless of how the client surfaces it.
    Raising (rather than returning the string) makes FastMCP mark the
    result ``isError=True`` with this message as its content, giving MCP
    clients a real error signal instead of an error-shaped success result.
    Always raises; never returns.
    """
    raise ToolError(_safe_error(tool, exc)) from exc


@mcp.tool(
    name="uniprot_get_entry",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_entry(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Fetch a UniProt protein entry by accession (e.g. P04637 for p53, P38398 for BRCA1).
    Returns function, gene, organism, disease associations, cross-references."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        return fmt_entry(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_entry", exc)


@mcp.tool(name="uniprot_search", annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
async def uniprot_search(
    query: QueryParam,
    size: SizeParam = 10,
    reviewed_only: Annotated[
        bool, Field(description="If true, restrict results to reviewed Swiss-Prot entries only.")
    ] = False,
    organism: Annotated[
        str,
        Field(
            description=(
                "Optional organism filter: a taxonomy ID ('9606') or a scientific "
                "name ('Homo sapiens'). Applied as an additional AND clause on top "
                "of ``query``; leave empty to search all organisms."
            )
        ),
    ] = "",
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """The general-purpose entry point for finding UniProtKB proteins by any
    combination of gene, organism, keyword, or free text. Use this first when
    you don't already have an accession; use ``uniprot_get_entry`` once you
    do. Examples: '(gene:TP53) AND (organism_id:9606)', 'kinase AND reviewed:true'.
    ``reviewed_only`` and ``organism`` are convenience shortcuts equivalent to
    adding the corresponding clause to ``query`` yourself."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_len("organism", organism, MAX_ORGANISM_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        q = query
        if reviewed_only and "reviewed:" not in q.lower():
            q = f"({q}) AND reviewed:true"
        if organism:
            if organism.isdigit():
                q = f"({q}) AND (organism_id:{organism})"
            else:
                # UniProt query language: organism_name needs quoting for multi-word.
                safe = organism.replace('"', "'")
                q = f'({q}) AND (organism_name:"{safe}")'
        client = _client()
        data = await client.search(q, size=size)
        return fmt_search(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_search", exc)


@mcp.tool(
    name="uniprot_get_sequence",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_sequence(accession: AccessionParam) -> str:
    """Fetch the canonical protein sequence in FASTA format. Use this when
    you need the raw residue string itself (e.g. for local sequence
    analysis); for pre-computed chemistry derived from this same sequence
    (molecular weight, pI, hydrophobicity) call ``uniprot_compute_properties``
    instead, which fetches the FASTA internally so you don't have to parse
    it yourself. Always returns markdown/plain-text FASTA — there is no
    ``response_format`` parameter because FASTA is already the interchange
    format."""
    try:
        _check_accession(accession)
        client = _client()
        fasta = await client.get_fasta(accession)
        return fmt_fasta(fasta, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_sequence", exc)


@mcp.tool(
    name="uniprot_get_features",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_features(
    accession: AccessionParam,
    feature_types: Annotated[
        str,
        Field(
            description=(
                "Optional comma-separated allow-list of UniProt feature type "
                "names, e.g. 'Domain,Active site,Binding site,Modified residue'. "
                "Leave empty to return every feature on the entry."
            )
        ),
    ] = "",
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Return the full, unfiltered feature array for an entry: domains,
    binding sites, PTMs, signal peptides, and every other annotated region,
    optionally narrowed by ``feature_types``. For a residue-specific view
    ('what's at position 175?') use ``uniprot_features_at_position``
    instead; for the curated subsets (active/binding sites, processing,
    PTMs alone) the dedicated ``uniprot_get_active_sites`` /
    ``uniprot_get_processing_features`` / ``uniprot_get_ptms`` tools apply
    the same filter server-side."""
    try:
        _check_accession(accession)
        _check_len("feature_types", feature_types, MAX_FEATURE_TYPES_LEN)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        features = data.get("features", []) or []
        if feature_types:
            types = {t.strip().lower() for t in feature_types.split(",") if t.strip()}
            features = [f for f in features if str(f.get("type", "")).lower() in types]
        return fmt_features(features, accession, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_features", exc)


@mcp.tool(
    name="uniprot_get_go_terms",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_go_terms(
    accession: AccessionParam,
    aspect: Annotated[
        str,
        Field(
            description=(
                "Optional Gene Ontology aspect filter: 'F' (molecular function), "
                "'P' (biological process), 'C' (cellular component), or empty for all three."
            )
        ),
    ] = "",
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Get GO annotations grouped by aspect."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        if aspect and aspect not in {"F", "P", "C"}:
            raise _InputError("aspect must be empty or one of 'F', 'P', 'C'")
        client = _client()
        data = await client.get_entry(accession)
        xrefs = data.get("uniProtKBCrossReferences", []) or []
        return fmt_go(
            xrefs, accession, aspect or None, response_format, provenance=client.last_provenance
        )
    except Exception as exc:
        _raise_tool_error("uniprot_get_go_terms", exc)


@mcp.tool(
    name="uniprot_get_cross_refs",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_cross_refs(
    accession: AccessionParam,
    database: Annotated[
        str,
        Field(
            description=(
                "Optional exact database name to filter to, e.g. 'PDB', 'Pfam', "
                "'Ensembl', 'Reactome', 'KEGG', 'STRING'. Leave empty to return "
                "cross-references to every linked database."
            )
        ),
    ] = "",
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """List every external-database cross-reference UniProt has curated for
    an entry (PDB, Pfam, Ensembl, Reactome, KEGG, STRING, and dozens more),
    optionally narrowed to one ``database``. For the common single-database
    cases there are dedicated, richer tools that resolve structured details
    beyond a bare ID: ``uniprot_resolve_pdb`` (structures with
    method/resolution), ``uniprot_resolve_alphafold``, ``uniprot_resolve_interpro``,
    and ``uniprot_resolve_chembl``. Use this tool for any other database or
    to see the full cross-reference set at once."""
    try:
        _check_accession(accession)
        _check_len("database", database, MAX_DATABASE_LEN)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        xrefs = data.get("uniProtKBCrossReferences", []) or []
        return fmt_crossrefs(
            xrefs, accession, database or None, response_format, provenance=client.last_provenance
        )
    except Exception as exc:
        _raise_tool_error("uniprot_get_cross_refs", exc)


@mcp.tool(
    name="uniprot_get_variants",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_variants(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """List every literature-described natural variant UniProt has curated
    for an entry, including disease-associated mutations. Use this to see
    the full variant catalogue for a protein; to check one specific
    HGVS-shorthand change (e.g. 'R175H') use ``uniprot_lookup_variant``
    instead, which does the position/residue matching for you. UniProt's
    natural-variant annotations only cover literature-described variants —
    for population-scale clinical significance data use
    ``uniprot_resolve_clinvar``."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        features = data.get("features", []) or []
        return fmt_variants(features, accession, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_variants", exc)


@mcp.tool(
    name="uniprot_id_mapping",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_id_mapping(
    ids: Annotated[
        str, Field(description="Comma-separated identifiers to map, up to 100 per call.")
    ],
    from_db: Annotated[
        str,
        Field(
            description=(
                "Source database code, e.g. 'UniProtKB_AC-ID', 'PDB', 'Ensembl', "
                "'GeneID' (Entrez), or 'Gene_Name'."
            )
        ),
    ],
    to_db: Annotated[str, Field(description="Target database code, same code set as ``from_db``.")],
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Map identifiers between UniProt and external databases (or between
    two external databases) via UniProt's ID mapping service. Submits an
    async job and polls it to completion server-side, so the call may take
    a few seconds for large batches."""
    try:
        _check_len("ids", ids, MAX_IDS_LEN)
        _check_len("from_db", from_db, MAX_DATABASE_LEN)
        _check_len("to_db", to_db, MAX_DATABASE_LEN)
        _check_format(response_format)
        id_list = [i.strip() for i in ids.split(",") if i.strip()]
        if len(id_list) > 100:
            raise _InputError("ids cannot exceed 100 entries per call")
        if not id_list:
            raise _InputError("ids must contain at least one non-empty identifier")
        client = _client()
        job_id = await client.id_mapping_submit(from_db, to_db, id_list)
        data = await client.id_mapping_results(job_id)
        return fmt_idmapping(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_id_mapping", exc)


@mcp.tool(
    name="uniprot_batch_entries",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_batch_entries(
    accessions: Annotated[
        str,
        Field(
            description=(
                "Comma-separated UniProt accessions, e.g. 'P04637,P38398'. "
                "Invalid accessions are skipped rather than failing the whole "
                "call; only the first 100 valid accessions are fetched."
            )
        ),
    ],
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Fetch multiple entries in a single call. Use this instead of repeated
    ``uniprot_get_entry`` calls when you already have a list of accessions —
    one network round-trip instead of N, with invalid accessions reported
    rather than aborting the batch."""
    try:
        _check_len("accessions", accessions, MAX_IDS_LEN)
        _check_format(response_format)
        acc_list = [a.strip() for a in accessions.split(",") if a.strip()]
        client = _client()
        prov_before = client.last_provenance
        data = await client.batch_entries(acc_list)
        # batch_entries skips the network entirely when no accession is valid.
        # In that case last_provenance still holds a previous call's value
        # (shared client), so only attach provenance when this call fetched.
        attached = client.last_provenance if client.last_provenance is not prov_before else None
        out = fmt_search({"results": data["results"]}, response_format, provenance=attached)
        if data.get("invalid"):
            out += (
                f"\n\n_Skipped {len(data['invalid'])} invalid accession(s): "
                f"{', '.join(data['invalid'])}_"
            )
        if data.get("truncated"):
            out += (
                f"\n\n_Showing the first 100 of {data['n_valid']} valid accessions; "
                f"the remaining {data['n_valid'] - 100} were not fetched._"
            )
        return out
    except Exception as exc:
        _raise_tool_error("uniprot_batch_entries", exc)


@mcp.tool(
    name="uniprot_taxonomy_search",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_taxonomy_search(
    query: Annotated[
        str,
        Field(
            description=(
                "Organism name or partial name to search for, e.g. 'Homo sapiens' "
                "or 'coli'. Matches against scientific and common names."
            )
        ),
    ],
    size: SizeParam = 5,
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Resolve an organism name to its NCBI taxonomy ID(s) — the numeric ID
    other UniProt tools expect (e.g. the ``organism`` parameter of
    ``uniprot_search``, or ``organism_id:`` in a query string). Returns
    each match's taxonomy ID, scientific name, common name, and rank
    (species / genus / etc.); a name can resolve to multiple IDs when
    it's ambiguous (e.g. a genus with several species), so inspect the
    rank and full scientific name before picking one. Use this before
    filtering any other search by organism if you only know the name,
    not the numeric ID."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        client = _client()
        data = await client.taxonomy_search(query, size)
        return fmt_taxonomy(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_taxonomy_search", exc)


@mcp.tool(
    name="uniprot_get_keyword",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_keyword(
    keyword_id: Annotated[
        str,
        Field(
            description="UniProt keyword ID, e.g. 'KW-0007' (Acetylation). Always starts with 'KW-'."
        ),
    ],
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Fetch a UniProt keyword by ID (e.g. KW-0007 for Acetylation, KW-0539 for Nucleus).
    Returns name, definition, category, synonyms, GO cross-refs, and parent/child hierarchy."""
    try:
        _check_keyword_id(keyword_id)
        _check_format(response_format)
        client = _client()
        data = await client.get_keyword(keyword_id)
        return fmt_keyword(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_keyword", exc)


@mcp.tool(
    name="uniprot_search_keywords",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_keywords(
    query: Annotated[
        str,
        Field(
            description=(
                "Free-text to match against UniProt keyword names, synonyms, and "
                "definitions, e.g. 'acetylation', 'nucleus', 'kinase activity'. "
                "Plain words, not a UniProtKB field query."
            )
        ),
    ],
    size: SizeParam = 10,
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Search UniProt's controlled keyword vocabulary (the ``KW-####`` terms)
    by name or definition. Use this to discover a keyword ID from a concept;
    once you have the ``KW-####`` ID, call ``uniprot_get_keyword`` for its full
    record (definition, category, hierarchy, GO cross-references). Returns up
    to ``size`` matches, or an empty list if nothing matches.
    Examples: 'acetylation', 'nucleus', 'kinase activity'."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        client = _client()
        data = await client.search_keywords(query, size=size)
        return fmt_keyword_search(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_search_keywords", exc)


@mcp.tool(
    name="uniprot_get_subcellular_location",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_subcellular_location(
    location_id: Annotated[
        str,
        Field(
            description="UniProt subcellular-location ID, e.g. 'SL-0039' (Cell membrane). Always starts with 'SL-'."
        ),
    ],
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Fetch a UniProt subcellular-location term by ID (e.g. SL-0039 Cell membrane, SL-0086 Cytoplasm, SL-0191 Nucleus).
    Returns name, definition, category, GO cross-refs, and the is-a / part-of hierarchy."""
    try:
        _check_subcellular_location_id(location_id)
        _check_format(response_format)
        client = _client()
        data = await client.get_subcellular_location(location_id)
        return fmt_subcellular_location(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_subcellular_location", exc)


@mcp.tool(
    name="uniprot_search_subcellular_locations",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_subcellular_locations(
    query: Annotated[
        str,
        Field(
            description=(
                "Free-text to match against UniProt subcellular-location names, "
                "synonyms, and definitions, e.g. 'membrane', 'mitochondrion', "
                "'cytoplasm'. Plain words, not a UniProtKB field query."
            )
        ),
    ],
    size: SizeParam = 10,
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Search UniProt's controlled subcellular-location vocabulary (the
    ``SL-####`` terms) by name or definition. Use this to discover a location
    ID from a concept; once you have the ``SL-####`` ID, call
    ``uniprot_get_subcellular_location`` for its full record (definition,
    category, hierarchy, GO cross-references). Returns up to ``size`` matches,
    or an empty list if nothing matches.
    Examples: 'membrane', 'mitochondrion', 'cytoplasm'."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        client = _client()
        data = await client.search_subcellular_locations(query, size=size)
        return fmt_subcellular_location_search(
            data, response_format, provenance=client.last_provenance
        )
    except Exception as exc:
        _raise_tool_error("uniprot_search_subcellular_locations", exc)


@mcp.tool(
    name="uniprot_get_uniref",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_uniref(
    uniref_id: Annotated[
        str,
        Field(
            description=(
                "UniRef cluster ID, e.g. 'UniRef90_P04637'. Prefix is "
                "'UniRef50_'/'UniRef90_'/'UniRef100_' followed by the "
                "representative member's accession."
            )
        ),
    ],
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Fetch a UniRef cluster by ID. Examples:
    UniRef100_P04637 (100 % identity, only exact-match members),
    UniRef90_P04637 (90 % identity), UniRef50_P04637 (50 %, broadest grouping).
    Returns representative member, member list, common taxon, last-updated date."""
    try:
        _check_uniref_id(uniref_id)
        _check_format(response_format)
        client = _client()
        data = await client.get_uniref(uniref_id)
        return fmt_uniref(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_uniref", exc)


@mcp.tool(
    name="uniprot_search_uniref",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_uniref(
    query: QueryParam,
    identity_tier: Annotated[
        str,
        Field(
            description=(
                "Cluster identity threshold: '50' (loosest grouping), '90', "
                "'100' (tightest, only exact-match members), or empty for all "
                "tiers. Higher values return more, smaller, tighter clusters."
            )
        ),
    ] = "",
    size: SizeParam = 10,
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Search for UniRef clusters by content (not by a known cluster ID —
    for that, use ``uniprot_get_uniref`` directly). Example: query='kinase'
    identity_tier='90' returns the 90% clusters matching 'kinase'. Use a
    looser tier (50) to find broad homology groups, a tighter tier (100)
    to find near-identical sequence sets."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        if identity_tier and identity_tier not in UNIREF_IDENTITY_TIERS:
            raise _InputError(
                f"identity_tier must be one of {list(UNIREF_IDENTITY_TIERS)} or empty"
            )
        size = max(1, min(size, 500))
        q = query
        if identity_tier:
            # UniProt query language uses decimal identity values.
            decimal = {"50": "0.5", "90": "0.9", "100": "1.0"}[identity_tier]
            q = f"({q}) AND identity:{decimal}"
        client = _client()
        data = await client.search_uniref(q, size=size)
        return fmt_uniref_search(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_search_uniref", exc)


_ORTHOLOGY_DATABASES: Final[frozenset[str]] = frozenset(
    {
        "KEGG",
        "OMA",
        "OrthoDB",
        "eggNOG",
        "HOGENOM",
        "PhylomeDB",
        "InParanoid",
        "TreeFam",
        "GeneTree",
        "PAN-GO",
        "PANTHER",
        "OrthoInspector",
    }
)


@mcp.tool(
    name="uniprot_resolve_orthology",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_resolve_orthology(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Group every orthology cross-reference in a UniProt entry by source
    database (KEGG / OMA / OrthoDB / eggNOG / HOGENOM / PhylomeDB /
    InParanoid / TreeFam / GeneTree / PAN-GO / PANTHER / OrthoInspector).
    Different databases use different inference methods; surfacing them
    side-by-side lets the agent reason about consensus when comparing
    orthologs across species. Pure-Python — no extra HTTP call beyond
    the entry fetch."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        xrefs = data.get("uniProtKBCrossReferences", []) or []
        grouped: dict[str, list[str]] = {}
        for x in xrefs:
            db = str(x.get("database", "") or "")
            if db in _ORTHOLOGY_DATABASES:
                xid = str(x.get("id", "") or "")
                if xid:
                    grouped.setdefault(db, []).append(xid)
        return fmt_orthology(grouped, accession, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_resolve_orthology", exc)


@mcp.tool(
    name="uniprot_target_dossier",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_target_dossier(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """One-call comprehensive characterisation of a UniProt entry,
    structured for drug-discovery / clinical workflows. Composes nine
    views over the same entry plus one FASTA fetch (so two upstream
    network calls, not nine):

      Identity  ·  Function  ·  Sequence chemistry  ·  Structural
      evidence (PDB count + best-resolution + AlphaFold model id +
      InterPro count)  ·  Drug-target context (ChEMBL ids, DrugBank
      count)  ·  Disease associations (with MIM IDs)  ·  Variants
      count  ·  Functional annotations (top GO MF, subcellular, ECO
      diversity)  ·  Cross-references summary

    For per-residue pLDDT confidence call ``uniprot_get_alphafold_confidence``
    separately. For full disease detail call
    ``uniprot_get_disease_associations``. The dossier is the entry-
    level summary that decides which deeper tools are worth calling."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        # Capture the entry's provenance now: the dossier is built from this
        # entry JSON, and the FASTA fetch below would otherwise overwrite
        # last_provenance on the shared client and mis-attribute the footer.
        entry_provenance = client.last_provenance
        # Sequence chemistry needs the FASTA. One extra request.
        try:
            fasta = await client.get_fasta(accession)
            sequence = "".join(
                line
                for line in fasta.splitlines()
                if not line.startswith(">") and not line.startswith(";")
            )
            chemistry = dict(compute_protein_properties(sequence))
            chemistry.pop("amino_acid_counts", None)  # too verbose for the dossier
        except Exception:  # pragma: no cover — fasta-fetch failure is non-fatal
            chemistry = {}
        dossier = _assemble_target_dossier(data, chemistry)
        return fmt_target_dossier(dossier, accession, response_format, provenance=entry_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_target_dossier", exc)


def _assemble_target_dossier(entry: dict[str, Any], chemistry: dict[str, Any]) -> dict[str, Any]:
    """Assemble the structured dossier from a single UniProt entry.

    Pure-data manipulation — no I/O. Each section is a dict with the
    fields the formatter expects; missing data renders as "n/a" sections
    rather than crashes.
    """
    pd_block = entry.get("proteinDescription") or {}
    if isinstance(pd_block, dict):
        rec = pd_block.get("recommendedName") or {}
        full_name = (rec.get("fullName") or {}).get("value", "") if isinstance(rec, dict) else ""
    else:
        full_name = ""
    genes = entry.get("genes") or []
    gene_name = ""
    if genes and isinstance(genes, list) and isinstance(genes[0], dict):
        g = genes[0].get("geneName") or {}
        if isinstance(g, dict):
            gene_name = str(g.get("value", "") or "")
    organism = entry.get("organism") or {}
    organism_name = ""
    if isinstance(organism, dict):
        organism_name = str(organism.get("scientificName", "") or "")
    sequence = entry.get("sequence") or {}
    seq_length = sequence.get("length") if isinstance(sequence, dict) else None
    entry_type = str(entry.get("entryType", "") or "")
    reviewed = (
        "Swiss-Prot (reviewed)"
        if entry_type.startswith("UniProtKB reviewed")
        else "TrEMBL (unreviewed)"
        if entry_type
        else None
    )

    # Function comment
    function_text = ""
    for c in entry.get("comments") or []:
        if isinstance(c, dict) and c.get("commentType") == "FUNCTION":
            for t in c.get("texts") or []:
                if isinstance(t, dict) and t.get("value"):
                    function_text = str(t["value"])
                    break
            if function_text:
                break

    # Cross-reference helpers
    xrefs = entry.get("uniProtKBCrossReferences") or []
    if not isinstance(xrefs, list):
        xrefs = []

    def _by_db(db_name: str) -> list[dict[str, Any]]:
        return [x for x in xrefs if isinstance(x, dict) and x.get("database") == db_name]

    def _props(x: dict[str, Any]) -> dict[str, str]:
        return {
            str(p.get("key", "")): str(p.get("value", ""))
            for p in (x.get("properties") or [])
            if isinstance(p, dict)
        }

    pdbs = _by_db("PDB")
    best_pdb: dict[str, Any] = {}
    best_resolution_value: float | None = None
    for x in pdbs:
        props = _props(x)
        res_str = props.get("Resolution", "")
        try:
            res_val = float(res_str.split()[0])
        except (ValueError, IndexError):
            continue
        if best_resolution_value is None or res_val < best_resolution_value:
            best_resolution_value = res_val
            best_pdb = {
                "id": x.get("id"),
                "method": props.get("Method"),
                "resolution": res_str,
            }

    af_xrefs = _by_db("AlphaFoldDB")
    af_id = af_xrefs[0].get("id") if af_xrefs else None

    interpros = _by_db("InterPro")
    chembls = _by_db("ChEMBL")
    drugbank = _by_db("DrugBank")

    # Disease associations
    diseases: list[dict[str, Any]] = []
    for c in entry.get("comments") or []:
        if not isinstance(c, dict) or c.get("commentType") != "DISEASE":
            continue
        d = c.get("disease") or {}
        if not isinstance(d, dict) or not d:
            continue
        x = d.get("diseaseCrossReference") or {}
        mim = ""
        if isinstance(x, dict) and x.get("database") == "MIM":
            mim = str(x.get("id", ""))
        diseases.append({"name": d.get("diseaseId"), "mim_id": mim or None})

    # Variants count
    variant_count = sum(
        1
        for f in (entry.get("features") or [])
        if isinstance(f, dict) and f.get("type") == "Natural variant"
    )

    # GO molecular function
    go_mf: list[str] = []
    for x in xrefs:
        if not (isinstance(x, dict) and x.get("database") == "GO"):
            continue
        props = _props(x)
        term = props.get("GoTerm", "")
        if term.startswith("F:"):
            go_mf.append(term[2:])
        if len(go_mf) >= 5:
            break

    # Subcellular locations
    subcell_locs: list[str] = []
    for c in entry.get("comments") or []:
        if isinstance(c, dict) and c.get("commentType") == "SUBCELLULAR LOCATION":
            for loc in c.get("subcellularLocations") or []:
                if isinstance(loc, dict):
                    name = (loc.get("location") or {}).get("value")
                    if name:
                        subcell_locs.append(str(name))

    # Distinct ECO codes
    eco_codes: set[str] = set()

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            evs = node.get("evidences")
            if isinstance(evs, list):
                for ev in evs:
                    if isinstance(ev, dict):
                        code = str(ev.get("evidenceCode", "") or "")
                        if code:
                            eco_codes.add(code)
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    _walk(entry)

    # Cross-reference summary
    db_counts: dict[str, int] = {}
    for x in xrefs:
        if isinstance(x, dict):
            db = str(x.get("database", "?"))
            db_counts[db] = db_counts.get(db, 0) + 1
    top_dbs = [db for db, _ in sorted(db_counts.items(), key=lambda kv: -kv[1])][:8]

    return {
        "identity": {
            "name": full_name or None,
            "gene": gene_name or None,
            "organism": organism_name or None,
            "length": seq_length,
            "reviewed": reviewed,
            "entry_id": entry.get("primaryAccession"),
        },
        "function": function_text,
        "chemistry": chemistry,
        "structure": {
            "pdb_count": len(pdbs),
            "best_pdb": best_pdb,
            "alphafold_model_id": af_id,
            "interpro_count": len(interpros),
        },
        "drug_target": {
            "chembl_ids": [str(x.get("id", "") or "") for x in chembls if x.get("id")],
            "drugbank_count": len(drugbank),
        },
        "diseases": diseases,
        "variants": {"count": variant_count},
        "functional_annotations": {
            "go_molecular_function": go_mf,
            "subcellular_locations": subcell_locs[:5],
            "evidence_distinct_codes": len(eco_codes),
        },
        "cross_reference_summary": {
            "total": len(xrefs),
            "database_count": len(db_counts),
            "top_databases": top_dbs,
        },
    }


@mcp.tool(
    name="uniprot_replay_from_cache",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def uniprot_replay_from_cache(url: str, response_format: str = "markdown") -> str:
    """Read a previously-cached UniProt response without hitting the
    upstream. The local provenance cache is opt-in via the
    ``UNIPROT_MCP_CACHE_DIR`` environment variable; when unset, this
    tool always reports cache-disabled.

    Useful for: reproducing a year-old answer from a sealed cache
    snapshot; working offline / behind air-gaps; reducing UniProt's
    load when running benchmarks twice.

    Returns the cached body text wrapped in the recorded Provenance.
    The annotation ``openWorldHint=False`` reflects that this tool
    consults the local file system only — no upstream call."""
    try:
        _check_len("url", url, MAX_PROVENANCE_URL_LEN)
        _check_format(response_format)
        cache_dir = cache_dir_from_env()
        if cache_dir is None:
            return (
                "## Cache replay\n\n"
                f"_Provenance cache is disabled. Set `{CACHE_DIR_ENV}=/path/to/cache` "
                "to enable cache replay._"
            )
        cache = ProvenanceCache(cache_dir)
        entry = cache.read(url)
        if entry is None:
            return f"## Cache replay\n\n_No cache entry for `{url}` under `{cache_dir}`._"
        if response_format == "json":
            return json.dumps(entry, indent=2, ensure_ascii=False)
        body = str(entry.get("body_text", "") or "")
        prov = entry.get("provenance") or {}
        body_truncated = body[:4000]
        truncation_note = (
            "" if len(body) <= 4000 else f"\n_(truncated; full body is {len(body)} bytes)_"
        )
        lines = [
            f"## Cache replay  —  `{url}`",
            "",
            "**Body (verbatim from cache):**",
            "",
            "```",
            body_truncated,
            "```" + truncation_note,
            "",
            "**Recorded provenance:**",
            "",
            "```json",
            json.dumps(prov, indent=2, ensure_ascii=False),
            "```",
        ]
        return "\n".join(lines)
    except Exception as exc:
        _raise_tool_error("uniprot_replay_from_cache", exc)


@mcp.tool(
    name="uniprot_resolve_clinvar",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_resolve_clinvar(
    accession: AccessionParam,
    change: Annotated[
        str,
        Field(
            description=(
                "Optional HGVS-shorthand protein change to filter to, e.g. "
                "'R175H'. Leave empty to return all ClinVar records for the gene."
            )
        ),
    ] = "",
    size: Annotated[
        int, Field(description="Maximum number of ClinVar records to return; capped at 50.")
    ] = 10,
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Look up ClinVar records for the gene encoded by a UniProt entry.
    First fetches the entry to extract the canonical gene symbol, then
    queries NCBI eutils ClinVar by gene (and optional protein-change
    filter, e.g. ``R175H``). Returns clinical-significance classification,
    review status, condition list (trait_set), molecular consequence,
    and the protein-change list per record.

    Critical for clinical workflows — UniProt's natural-variant
    annotations stop at literature-described variants. ClinVar carries
    every variant submitted by clinical labs, with curated significance
    classifications. Combine ``uniprot_lookup_variant`` (UniProt side)
    with ``uniprot_resolve_clinvar`` (population side) for a full
    variant-effect picture.

    Calls https://eutils.ncbi.nlm.nih.gov — declared in PRIVACY.md."""
    try:
        _check_accession(accession)
        if change:
            _parse_variant_change(change)  # validate HGVS shape
        _check_format(response_format)
        size = max(1, min(size, 50))
        client = _client()
        # Phase 1: get gene name from the UniProt entry.
        entry = await client.get_entry(accession)
        genes = entry.get("genes") or []
        gene = ""
        if genes and isinstance(genes, list):
            g_first = genes[0] if isinstance(genes[0], dict) else {}
            gene_name_block = g_first.get("geneName") or {}
            if isinstance(gene_name_block, dict):
                gene = str(gene_name_block.get("value", "") or "")
        if not gene:
            raise _InputError(
                f"UniProt entry {accession} has no canonical gene name; "
                "ClinVar resolution requires a gene symbol."
            )
        # Phase 2: query ClinVar.
        payload = await client.get_clinvar_records(gene, change=change, retmax=size)
        return fmt_clinvar(
            payload,
            accession,
            gene,
            change,
            response_format,
            provenance=client.last_provenance,
        )
    except Exception as exc:
        _raise_tool_error("uniprot_resolve_clinvar", exc)


@mcp.tool(
    name="uniprot_get_alphafold_confidence",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_alphafold_confidence(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Fetch the per-residue confidence (pLDDT) summary for an entry's
    AlphaFold model, not just its existence. Returns the global mean pLDDT
    score plus the four-band distribution (very high ≥ 90 / confident
    70-90 / low 50-70 / very low < 50) so the agent can decide whether to
    trust the model: 95% 'very high' is publication-grade, 40% 'very low'
    is largely disordered and structural inference is unsafe. Call
    ``uniprot_resolve_alphafold`` first if you only need the model ID and
    viewer link, not its confidence.

    This tool calls https://alphafold.ebi.ac.uk — declared in PRIVACY.md
    as a third party. Provenance carries source = AlphaFoldDB."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        record = await client.get_alphafold_summary(accession)
        return fmt_alphafold_confidence(
            record, accession, response_format, provenance=client.last_provenance
        )
    except Exception as exc:
        _raise_tool_error("uniprot_get_alphafold_confidence", exc)


@mcp.tool(
    name="uniprot_get_publications",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_publications(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """List the publications UniProt cites on an entry, with PubMed IDs,
    DOIs, titles, authors, journal, year, and the 'reference position'
    annotation (the experimental work each citation supports — e.g.
    'CRYSTALLIZATION', 'PHOSPHORYLATION AT SER-15', 'INVOLVEMENT IN
    LI-FRAUMENI SYNDROME'). Pure composition over the entry's
    ``references`` block — no extra HTTP call beyond the entry fetch."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        publications = _extract_publications(data)
        return fmt_publications(
            publications, accession, response_format, provenance=client.last_provenance
        )
    except Exception as exc:
        _raise_tool_error("uniprot_get_publications", exc)


def _extract_publications(entry: dict[str, object]) -> list[dict[str, object]]:
    """Pull a structured publication list out of a UniProt entry's
    ``references`` field. Each citation may carry one or more
    ``citationCrossReferences`` (PubMed, DOI); we surface both when
    present plus the ``referencePositions`` (curated list of the
    experiments each reference supports)."""
    out: list[dict[str, object]] = []
    references = entry.get("references") or []
    if not isinstance(references, list):
        return out
    for ref in references:
        if not isinstance(ref, dict):
            continue
        citation = ref.get("citation") or {}
        if not isinstance(citation, dict):
            continue
        xrefs = citation.get("citationCrossReferences") or []
        pmid = ""
        doi = ""
        for x in xrefs if isinstance(xrefs, list) else []:
            if not isinstance(x, dict):
                continue
            db = str(x.get("database", ""))
            xid = str(x.get("id", ""))
            if db == "PubMed" and xid:
                pmid = xid
            elif db == "DOI" and xid:
                doi = xid
        out.append(
            {
                "title": str(citation.get("title", "") or ""),
                "authors": list(citation.get("authors") or []),
                "journal": str(citation.get("journal", "") or ""),
                "year": str(citation.get("publicationDate") or citation.get("year") or "") or None,
                "pubmed_id": pmid or None,
                "doi": doi or None,
                "reference_positions": list(ref.get("referencePositions") or []),
            }
        )
    return out


@mcp.tool(
    name="uniprot_compute_properties",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_compute_properties(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Derived sequence chemistry for a UniProt entry: molecular weight,
    theoretical pI, GRAVY hydrophobicity, aromaticity, net charge at pH 7,
    extinction coefficient at 280 nm, amino-acid composition. Computed
    from the canonical FASTA via standard methods (Lehninger pK values,
    Kyte-Doolittle hydropathy, Pace 1995 ε₂₈₀ formula). Pure-Python — no
    additional external API call beyond the FASTA fetch."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        fasta = await client.get_fasta(accession)
        # Drop the FASTA header and any PIR-style ;-comments; the
        # remaining lines concatenated are the residues.
        sequence = "".join(
            line
            for line in fasta.splitlines()
            if not line.startswith(">") and not line.startswith(";")
        )
        properties = compute_protein_properties(sequence)
        return fmt_properties(
            dict(properties), accession, response_format, provenance=client.last_provenance
        )
    except Exception as exc:
        _raise_tool_error("uniprot_compute_properties", exc)


@mcp.tool(
    name="uniprot_features_at_position",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_features_at_position(
    accession: AccessionParam,
    position: Annotated[
        int, Field(description="1-indexed residue position within the protein sequence.")
    ],
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """List every UniProt feature that overlaps a residue position
    (1-indexed). Answers the question 'what's at residue 175 of TP53?'
    by intersecting the entry's features with the given position. Useful
    for variant-effect interpretation — surfaces every domain, binding
    site, modification, mutagenesis annotation, and natural variant at a
    single residue in one call."""
    try:
        _check_accession(accession)
        _check_position(position)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        all_features = data.get("features", []) or []
        overlapping = []
        for f in all_features:
            loc = f.get("location") or {}
            start = (loc.get("start") or {}).get("value")
            end = (loc.get("end") or {}).get("value")
            if not isinstance(start, int) or not isinstance(end, int):
                continue
            if start <= position <= end:
                overlapping.append(f)
        return fmt_features_at_position(
            overlapping,
            accession,
            position,
            response_format,
            provenance=client.last_provenance,
        )
    except Exception as exc:
        _raise_tool_error("uniprot_features_at_position", exc)


def _filter_features_by_type(
    features: list[dict[str, Any]], allowed_types: frozenset[str]
) -> list[dict[str, Any]]:
    """Return the subset of features whose ``type`` is in ``allowed_types``.

    Shared filter for the active-sites, processing, and PTM tools. Kept
    here (server module) rather than in formatters because it is a
    server-side selection: the formatters render whatever is handed to
    them, and the property tests rely on the server tools and the
    formatters using the same canonical type sets."""
    return [f for f in features if str(f.get("type", "")) in allowed_types]


@mcp.tool(
    name="uniprot_get_active_sites",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_active_sites(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Return the active sites, binding sites, metal-binding residues,
    and DNA-binding regions annotated on a UniProt entry. Filtered view
    over the entry's feature array — this is the residue-level chemistry
    of the protein, the input to enzyme drug-design and antibiotic
    target-validation workflows."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        features = data.get("features", []) or []
        filtered = _filter_features_by_type(features, ACTIVE_SITE_FEATURE_TYPES)
        return fmt_active_sites(
            filtered, accession, response_format, provenance=client.last_provenance
        )
    except Exception as exc:
        _raise_tool_error("uniprot_get_active_sites", exc)


@mcp.tool(
    name="uniprot_get_processing_features",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_processing_features(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Return the maturation and processing features (signal peptide,
    propeptide, transit peptide, initiator methionine, chain, peptide).
    These describe how the translated polypeptide is cleaved and
    targeted into its mature form — essential for therapeutic-protein
    engineering and pathogen-secretion-system analysis. A pre-filtered
    view over ``uniprot_get_features``; for post-translational chemical
    modifications instead of cleavage/targeting, use ``uniprot_get_ptms``."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        features = data.get("features", []) or []
        filtered = _filter_features_by_type(features, PROCESSING_FEATURE_TYPES)
        return fmt_processing_features(
            filtered, accession, response_format, provenance=client.last_provenance
        )
    except Exception as exc:
        _raise_tool_error("uniprot_get_processing_features", exc)


@mcp.tool(
    name="uniprot_get_ptms",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_ptms(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Return the post-translational modification features (modified
    residues, glycosylation sites, lipidation sites, disulfide bonds,
    cross-links). PTMs are functionally critical: they switch enzymes
    on, target proteins for degradation, anchor them to membranes, and
    fold them via disulfides. A pre-filtered view over
    ``uniprot_get_features``; for cleavage/targeting features instead of
    chemical modifications, use ``uniprot_get_processing_features``. The
    empty case carries an honest pointer to mass-spec databases
    (PhosphoSitePlus, GlyConnect) for additional evidence."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        features = data.get("features", []) or []
        filtered = _filter_features_by_type(features, PTM_FEATURE_TYPES)
        return fmt_ptms(filtered, accession, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_ptms", exc)


@mcp.tool(
    name="uniprot_lookup_variant",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_lookup_variant(
    accession: AccessionParam,
    change: Annotated[
        str,
        Field(
            description=(
                "HGVS-shorthand amino-acid change, e.g. 'R175H', 'V600E', "
                "'R248*' (stop). Format: <original residue><1-indexed "
                "position><alt residue or '*'>."
            )
        ),
    ],
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Look up an HGVS-shorthand amino-acid change (e.g. ``R175H``,
    ``V600E``, ``R248*``) in the UniProt entry's natural-variant
    annotations. Returns the matching variant feature(s) including the
    UniProt-curated description (often a disease association). A null
    result here does NOT mean a variant is benign — UniProt only
    annotates literature-described variants; ClinVar / dbSNP carry
    population-level data."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        original, position, alt = _parse_variant_change(change)
        client = _client()
        data = await client.get_entry(accession)
        features = data.get("features", []) or []
        matches = []
        for f in features:
            if f.get("type") != "Natural variant":
                continue
            loc = f.get("location") or {}
            start = (loc.get("start") or {}).get("value")
            if start != position:
                continue
            alt_seq = f.get("alternativeSequence") or {}
            orig_recorded = str(alt_seq.get("originalSequence", "") or "")
            alts_recorded = [str(a) for a in (alt_seq.get("alternativeSequences") or [])]
            if orig_recorded.upper() == original.upper() and alt.upper() in {
                a.upper() for a in alts_recorded
            }:
                matches.append(f)
        return fmt_variant_lookup(
            matches, accession, change, response_format, provenance=client.last_provenance
        )
    except Exception as exc:
        _raise_tool_error("uniprot_lookup_variant", exc)


@mcp.tool(
    name="uniprot_get_disease_associations",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_disease_associations(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Structured disease associations for a UniProt entry. Returns the
    diseases recorded in DISEASE-type comments with name, acronym,
    UniProt disease ID, OMIM cross-reference, description, and the
    annotation note. Critical for clinical interpretation — distinguishes
    a UniProt-curated disease association (literature-anchored) from a
    raw cross-reference. Empty result does not imply disease-irrelevant;
    see Open Targets / OMIM / DisGeNET for population-level evidence."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        comments = data.get("comments", []) or []
        associations: list[dict[str, object]] = []
        for c in comments:
            if c.get("commentType") != "DISEASE":
                continue
            disease = c.get("disease") or {}
            if not disease:
                continue
            cross_refs = disease.get("diseaseCrossReference") or {}
            xrefs_list: list[dict[str, str]] = []
            if isinstance(cross_refs, dict) and cross_refs.get("id"):
                xrefs_list.append(
                    {
                        "database": str(cross_refs.get("database", "?")),
                        "id": str(cross_refs.get("id", "?")),
                    }
                )
            associations.append(
                {
                    "name": str(disease.get("diseaseId", "")) or None,
                    "disease_id": str(disease.get("diseaseAccession", "")) or None,
                    "acronym": str(disease.get("acronym", "")) or None,
                    "description": str(disease.get("description", "")) or None,
                    "note": (
                        " ".join(
                            str(t.get("value", ""))
                            for t in (c.get("note", {}) or {}).get("texts", []) or []
                        )
                        or None
                    ),
                    "cross_references": xrefs_list,
                    "evidences": disease.get("evidences") or [],
                }
            )
        return fmt_disease_associations(
            associations, accession, response_format, provenance=client.last_provenance
        )
    except Exception as exc:
        _raise_tool_error("uniprot_get_disease_associations", exc)


@mcp.tool(
    name="uniprot_get_uniparc",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_uniparc(
    upi: Annotated[
        str,
        Field(description="UniParc identifier, e.g. 'UPI000002ED67'. Always starts with 'UPI'."),
    ],
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Fetch a UniParc sequence-archive record by its known UPI. Returns
    sequence, MD5/CRC64 checksums, cross-reference counts, linked
    UniProtKB accessions, and the common-taxa list. UniParc is the
    non-redundant sequence archive — every protein sequence ever submitted
    to a major public database has exactly one UniParc record, making this
    the tool to use when a UniProtKB accession doesn't exist for a
    sequence you have. Don't have a UPI yet? Use ``uniprot_search_uniparc``
    to find one first."""
    try:
        _check_uniparc_id(upi)
        _check_format(response_format)
        client = _client()
        data = await client.get_uniparc(upi)
        return fmt_uniparc(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_uniparc", exc)


@mcp.tool(
    name="uniprot_search_uniparc",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_uniparc(
    query: QueryParam, size: SizeParam = 10, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Search the UniParc non-redundant sequence archive by taxonomy,
    source database, or other UniParc query fields — the entry point when
    you don't already have a UPI. Examples: 'taxonomy_id:9606' for human
    sequences, 'database:Ensembl' for Ensembl-derived entries. Once you
    have a UPI from the results, use ``uniprot_get_uniparc`` for the full
    record."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        client = _client()
        data = await client.search_uniparc(query, size=size)
        return fmt_uniparc_search(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_search_uniparc", exc)


@mcp.tool(
    name="uniprot_get_proteome",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_proteome(
    proteome_id: Annotated[
        str,
        Field(
            description="UniProt proteome ID, e.g. 'UP000005640' (human reference). Always starts with 'UP'."
        ),
    ],
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Fetch a UniProt proteome by UP ID (e.g. UP000005640 = human reference).
    Returns organism, taxonomy lineage, protein count, gene count, BUSCO
    completeness score, annotation score, and component breakdown
    (chromosomes / contigs)."""
    try:
        _check_proteome_id(proteome_id)
        _check_format(response_format)
        client = _client()
        data = await client.get_proteome(proteome_id)
        return fmt_proteome(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_proteome", exc)


@mcp.tool(
    name="uniprot_search_proteomes",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_proteomes(
    query: Annotated[
        str,
        Field(
            description=(
                "Proteome query using UniProt proteome fields, e.g. "
                "'organism_id:9606' (human), 'proteome_type:1' (reference "
                "proteomes only), or 'taxonomy_name:bacteria'. Plain text also "
                "matches organism names."
            )
        ),
    ],
    size: SizeParam = 10,
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Search UniProt proteomes (whole-organism protein sets) by organism or
    proteome field. Use this to find a proteome's ``UP#########`` ID; once you
    have it, call ``uniprot_get_proteome`` for the full record (protein / gene
    counts, BUSCO completeness, component breakdown). Returns up to ``size``
    matches, or an empty list if nothing matches. Examples: 'organism_id:9606'
    for human, 'proteome_type:1' for reference proteomes only,
    'taxonomy_name:bacteria' for all bacterial proteomes."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        client = _client()
        data = await client.search_proteomes(query, size=size)
        return fmt_proteome_search(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_search_proteomes", exc)


@mcp.tool(
    name="uniprot_get_citation",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_citation(
    citation_id: Annotated[
        str, Field(description="Citation ID, typically a numeric PubMed ID, e.g. '9840937'.")
    ],
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Fetch a UniProt citation record by ID (typically a PubMed ID, e.g. 9840937).
    Returns title, authors, journal, year, volume, pages, and cross-references."""
    try:
        _check_citation_id(citation_id)
        _check_format(response_format)
        client = _client()
        data = await client.get_citation(citation_id)
        return fmt_citation(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_citation", exc)


@mcp.tool(
    name="uniprot_search_citations",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_citations(
    query: Annotated[
        str,
        Field(
            description=(
                "Citation query using UniProt citation fields, e.g. "
                "'p53 AND author:Vogelstein' or 'BRCA1 AND year:[2020 TO 2024]'. "
                "Supports free text plus 'author:', 'title:', and 'year:' ranges."
            )
        ),
    ],
    size: SizeParam = 10,
    response_format: ResponseFormatParam = "markdown",
) -> str:
    """Search the UniProt citations index (the literature UniProt references)
    by title, author, or year. Use this to find a citation's ID (typically a
    PubMed ID); once you have it, call ``uniprot_get_citation`` for the full
    record. For the publications attached to one specific protein entry, use
    ``uniprot_get_publications`` instead. Returns up to ``size`` matches, or an
    empty list if nothing matches. Examples: 'p53 AND author:Vogelstein',
    'BRCA1 AND year:[2020 TO 2024]'."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        client = _client()
        data = await client.search_citations(query, size=size)
        return fmt_citation_search(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_search_citations", exc)


@mcp.tool(
    name="uniprot_resolve_pdb",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_resolve_pdb(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """List every PDB structure cross-referenced from a UniProt entry, with
    method, resolution, and chain coverage. Faster than parsing the raw
    cross-references blob — returns a structured list typed for downstream
    analysis."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        return fmt_pdb(data, accession, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_resolve_pdb", exc)


@mcp.tool(
    name="uniprot_resolve_alphafold",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_resolve_alphafold(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Resolve the AlphaFoldDB cross-reference for a UniProt entry — typically
    one canonical model per accession. Includes a direct EBI viewer link."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        return fmt_alphafold(data, accession, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_resolve_alphafold", exc)


@mcp.tool(
    name="uniprot_resolve_interpro",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_resolve_interpro(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """List InterPro signatures (domain / family classifications) for a
    UniProt entry, with names extracted from the entry's cross-reference
    properties."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        return fmt_interpro(data, accession, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_resolve_interpro", exc)


@mcp.tool(
    name="uniprot_resolve_chembl",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_resolve_chembl(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Resolve ChEMBL drug-target cross-references for a UniProt entry.
    Returns the ChEMBL target IDs with EBI viewer links — empty if the
    protein has no documented bioactivity data in ChEMBL."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        return fmt_chembl(data, accession, response_format, provenance=client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_resolve_chembl", exc)


@mcp.tool(
    name="uniprot_get_evidence_summary",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_evidence_summary(
    accession: AccessionParam, response_format: ResponseFormatParam = "markdown"
) -> str:
    """Summarise and grade the ECO (Evidence and Conclusion Ontology) codes
    attached to a UniProt entry's annotations. Counts how many features and
    comments cite each evidence code, then classifies every occurrence as
    experimental (wet-lab, ECO:0000269), manual (curator-reviewed inference),
    or automatic (un-reviewed pipeline call) and collapses that into a single
    0-100 evidence-confidence score with a high / moderate / low / very-low
    band. A score near 100 means the entry is dominated by direct experimental
    evidence; a score near 10 means it is almost entirely computationally
    inferred. Critical for any downstream agent that must distinguish
    'wet-lab confirmed' annotations from 'inferred by similarity'. JSON output
    adds an ``evidence_confidence`` block (score, band, per-class breakdown,
    weights) alongside the raw ``evidence_counts``."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        return _format_evidence_summary(data, accession, response_format, client.last_provenance)
    except Exception as exc:
        _raise_tool_error("uniprot_get_evidence_summary", exc)


def _format_evidence_summary(
    data: dict[str, object], accession: str, fmt: str, provenance: object
) -> str:
    """Aggregate every evidence code referenced in features and comments."""
    counts: dict[str, int] = {}

    def visit(node: object) -> None:
        if isinstance(node, dict):
            evidences = node.get("evidences")
            if isinstance(evidences, list):
                for ev in evidences:
                    if isinstance(ev, dict):
                        code = str(ev.get("evidenceCode", "") or "")
                        if code:
                            counts[code] = counts.get(code, 0) + 1
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)

    visit(data)

    confidence = score_evidence(counts)

    if fmt == "json":
        from uniprot_mcp.formatters import _json_envelope

        return _json_envelope(
            {
                "accession": accession,
                "evidence_counts": counts,
                "evidence_confidence": confidence,
            },
            provenance,  # type: ignore[arg-type]
        )

    from uniprot_mcp.formatters import _provenance_md_footer  # local import — cheap

    lines: list[str] = [f"## Evidence summary: {accession} ({len(counts)} distinct ECO codes)", ""]
    if not counts:
        lines.append("_No evidence annotations on this entry._")
    else:
        lines.extend(confidence_markdown_lines(confidence))
        lines.extend(["", "**ECO codes by occurrence:**"])
        for code, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            description = ECO_HUMAN_LABELS.get(code, "")
            suffix = f"  —  {description}" if description else ""
            lines.append(f"- **{code}**: {n} occurrence(s){suffix}")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))  # type: ignore[arg-type]
    return "\n".join(lines)


@mcp.tool(
    name="uniprot_provenance_verify",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_provenance_verify(
    url: str,
    release: str = "",
    response_sha256: str = "",
    accept_header: str = "application/json",
    response_format: str = "markdown",
) -> str:
    """Re-fetch a previously recorded UniProt URL and verify it still
    returns the same release identifier and the same canonical response
    body (SHA-256). Pass the values from a prior response's provenance
    footer (`url`, `release`, `response_sha256`, `accept_header`); empty
    optional fields skip the corresponding check. Returns a verification
    report with explicit pass / drift / unreachable verdicts per check.

    ``accept_header`` must match the Accept header used for the original
    request (default ``application/json``; use ``text/plain;format=fasta``
    for FASTA-originated provenance). Replaying the wrong header causes a
    guaranteed hash mismatch because the upstream serves different content
    depending on content negotiation.

    This is the single tool that converts every prior uniprot-mcp
    response into an independently auditable artefact — a year from
    now, a third party can take the recorded provenance footer and
    confirm the upstream still serves the exact same bytes."""
    try:
        _check_len("url", url, MAX_PROVENANCE_URL_LEN)
        _check_len("release", release, MAX_RELEASE_TAG_LEN)
        _check_len("response_sha256", response_sha256, 64)
        _check_format(response_format)
        if accept_header not in ALLOWED_ACCEPT_HEADERS:
            raise _InputError(f"accept_header must be one of {sorted(ALLOWED_ACCEPT_HEADERS)}")
        if not url.startswith("https://rest.uniprot.org/"):
            raise _InputError(
                "url must begin with https://rest.uniprot.org/ — only UniProt REST "
                "URLs are verifiable through this tool."
            )
        return await _provenance_verify_impl(
            url=url,
            recorded_release=release or None,
            recorded_sha256=response_sha256 or None,
            accept_header=accept_header,
            response_format=response_format,
        )
    except Exception as exc:
        _raise_tool_error("uniprot_provenance_verify", exc)


async def _provenance_verify_impl(
    *,
    url: str,
    recorded_release: str | None,
    recorded_sha256: str | None,
    accept_header: str,
    response_format: str,
) -> str:
    """Worker for ``uniprot_provenance_verify``. Re-fetches ``url`` with
    a fresh httpx client (bypasses the singleton's pin-release config)
    and produces a structured verdict. Uses the supplied ``accept_header``
    to replicate the content negotiation of the original request.
    """
    report: dict[str, object] = {
        "url": url,
        "recorded_release": recorded_release,
        "recorded_sha256": recorded_sha256,
    }
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        headers={"User-Agent": UA, "Accept": accept_header},
        follow_redirects=True,
    ) as client:
        try:
            resp = await client.get(url)
        except httpx.HTTPError as exc:
            report["status"] = "url_unreachable"
            report["url_resolves"] = False
            report["error"] = type(exc).__name__
            return _format_verify_report(report, response_format)
        report["url_resolves"] = resp.is_success
        report["http_status"] = resp.status_code
        if not resp.is_success:
            report["status"] = "url_unreachable"
            return _format_verify_report(report, response_format)

        current_release = resp.headers.get("X-UniProt-Release")
        current_sha = canonical_response_hash(resp)
        report["current_release"] = current_release
        report["current_sha256"] = current_sha

        release_match: bool | None = None
        if recorded_release is not None:
            release_match = current_release == recorded_release
            report["release_match"] = release_match

        hash_match: bool | None = None
        if recorded_sha256 is not None:
            hash_match = current_sha == recorded_sha256
            report["hash_match"] = hash_match

        if release_match is False and hash_match is False:
            report["status"] = "release_and_hash_drift"
        elif release_match is False:
            report["status"] = "release_drift"
        elif hash_match is False:
            report["status"] = "hash_drift"
        else:
            report["status"] = "verified"

    return _format_verify_report(report, response_format)


def _format_verify_report(report: dict[str, object], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(report, indent=2, ensure_ascii=False, default=str)
    status = report.get("status", "?")
    lines: list[str] = ["## Provenance Verification", "", f"**Status:** {status}", ""]
    lines.append(f"**URL:** {report.get('url', '?')}")
    if "url_resolves" in report:
        check = "✓" if report["url_resolves"] else "✗"
        lines.append(f"- {check} URL resolves (HTTP {report.get('http_status', '?')})")
    if "release_match" in report:
        check = "✓" if report["release_match"] else "✗"
        lines.append(
            f"- {check} Release: recorded {report.get('recorded_release')!r}, "
            f"current {report.get('current_release')!r}"
        )
    if "hash_match" in report:
        check = "✓" if report["hash_match"] else "✗"
        rec = report.get("recorded_sha256") or ""
        cur = report.get("current_sha256") or ""
        lines.append(
            f"- {check} Response SHA-256: recorded {str(rec)[:16]}…, current {str(cur)[:16]}…"
        )
    if "error" in report:
        lines.append("")
        lines.append(f"**Error:** {report['error']}")
    checks_run = ("release_match" in report) + ("hash_match" in report)
    advice = _verify_advice(str(status), checks_run)
    if advice:
        lines.extend(["", f"**Advice:** {advice}"])
    return "\n".join(lines)


def _verify_advice(status: str, checks_run: int = 2) -> str:
    if status == "verified":
        if checks_run == 0:
            return (
                "The URL is reachable, but no recorded release or response hash was "
                "supplied, so content reproducibility was not verified. Re-run with "
                "the recorded release and response_sha256 to confirm the bytes are "
                "unchanged."
            )
        if checks_run == 1:
            return (
                "The one supplied check passed, but only release or hash was provided. "
                "Supply both for full byte-level reproducibility assurance."
            )
        return (
            "Both checks passed. The recorded provenance is reproducible against the "
            "live UniProt API."
        )
    return {
        "release_drift": (
            "UniProt has moved past the release recorded in this provenance. The "
            "underlying entry may also have changed; if you need byte-level "
            "reproducibility, fetch the recorded release from the UniProt FTP "
            "snapshot archive."
        ),
        "hash_drift": (
            "The release tag still matches but the canonical response body has "
            "changed. Investigate: UniProt may have edited the entry within the "
            "release, or our canonicalisation differs."
        ),
        "release_and_hash_drift": (
            "Both the release tag and the response body have moved on. Use a "
            "release-specific FTP snapshot if you need the historical answer."
        ),
        "url_unreachable": (
            "The recorded URL did not return a successful response. The endpoint "
            "may have been retired, rate-limited, or temporarily unavailable."
        ),
    }.get(status, "")


def _self_test() -> int:
    """Quick end-to-end smoke check without needing an MCP client."""
    import asyncio

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
        "uniprot_get_uniparc",
        "uniprot_search_uniparc",
        "uniprot_get_proteome",
        "uniprot_search_proteomes",
        "uniprot_get_citation",
        "uniprot_search_citations",
        "uniprot_resolve_pdb",
        "uniprot_resolve_alphafold",
        "uniprot_resolve_interpro",
        "uniprot_resolve_chembl",
        "uniprot_get_evidence_summary",
        "uniprot_compute_properties",
        "uniprot_features_at_position",
        "uniprot_lookup_variant",
        "uniprot_get_disease_associations",
        "uniprot_get_alphafold_confidence",
        "uniprot_get_publications",
        "uniprot_resolve_orthology",
        "uniprot_resolve_clinvar",
        "uniprot_target_dossier",
        "uniprot_replay_from_cache",
        "uniprot_provenance_verify",
        "uniprot_get_active_sites",
        "uniprot_get_processing_features",
        "uniprot_get_ptms",
    }

    # Count via the public MCP API (``list_tools`` is async) rather than
    # reaching into FastMCP internals like ``mcp._tool_manager._tools``.
    registered: set[str] = {tool.name for tool in asyncio.run(mcp.list_tools())}

    missing = expected - registered
    extra = registered - expected
    print(f"[tools] registered: {len(registered)}/{len(expected)}", file=sys.stderr)
    if missing:
        print(f"[FAIL] missing tools: {sorted(missing)}", file=sys.stderr)
        return 1
    if extra:
        print(f"[WARN] unexpected tools: {sorted(extra)}", file=sys.stderr)

    async def _live() -> int:
        client = _client()
        try:
            data = await client.get_entry("P04637")
            gene = data.get("genes", [{}])[0].get("geneName", {}).get("value")
            if gene != "TP53":
                print(f"[FAIL] P04637 gene is {gene!r}, expected TP53", file=sys.stderr)
                return 2
            print("[live] P04637 -> TP53 OK", file=sys.stderr)
            # Emit the real per-response output (claim C2) so a reviewer
            # running ``--self-test`` can observe the provenance footer —
            # the trailing ``---``-delimited Source / Query / SHA-256
            # block — not just smoke-check status. This is the exact
            # markdown an MCP tool returns, rendered through the same
            # public ``client.last_provenance`` accessor every tool uses.
            rendered = fmt_entry(data, "markdown", provenance=client.last_provenance)
            print("[provenance] per-response footer:", file=sys.stderr)
            print(rendered, file=sys.stderr)
            return 0
        finally:
            await client.close()

    rc = asyncio.run(_live())
    print("[PASS]" if rc == 0 else "[FAIL]", file=sys.stderr)
    return rc


def main() -> None:
    args = sys.argv[1:]
    # ``--pin-release=YYYY_MM`` opts into strict release pinning. The flag
    # is consumed here and forwarded as an environment variable so the
    # lazily-constructed UniProtClient picks it up at first instantiation.
    for arg in args:
        if arg.startswith("--pin-release="):
            os.environ[PIN_RELEASE_ENV] = arg.split("=", 1)[1]
        elif arg == "--pin-release":
            print(
                "ERROR: --pin-release requires a value (e.g. --pin-release=2026_02)",
                file=sys.stderr,
            )
            sys.exit(2)
    if "--self-test" in args:
        sys.exit(_self_test())
    mcp.run()


if __name__ == "__main__":
    main()
