"""TOPOLOGICA UniProt MCP Server. 37 tools. FastMCP. stdio transport.

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
from typing import Any, Final

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

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
from uniprot_mcp.formatters import (
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
    fmt_properties,
    fmt_proteome,
    fmt_proteome_search,
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
_VARIANT_CHANGE_RE = re.compile(r"\A([A-Z])([1-9][0-9]{0,4})([A-Z*])\Z")


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
    """Format an agent-safe error. Detail goes to stderr log, not the LLM."""
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


@mcp.tool(
    name="uniprot_get_entry",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_entry(accession: str, response_format: str = "markdown") -> str:
    """Fetch a UniProt protein entry by accession (e.g. P04637 for p53, P38398 for BRCA1).
    Returns function, gene, organism, disease associations, cross-references."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        return fmt_entry(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_get_entry", exc)


@mcp.tool(name="uniprot_search", annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True))
async def uniprot_search(
    query: str,
    size: int = 10,
    reviewed_only: bool = False,
    organism: str = "",
    response_format: str = "markdown",
) -> str:
    """Search UniProtKB. Examples: '(gene:TP53) AND (organism_id:9606)', 'kinase AND reviewed:true'.
    Set reviewed_only=true for Swiss-Prot only. Set organism to taxonomy ID or name."""
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
        return _safe_error("uniprot_search", exc)


@mcp.tool(
    name="uniprot_get_sequence",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_sequence(accession: str) -> str:
    """Get protein sequence in FASTA format for a UniProt accession."""
    try:
        _check_accession(accession)
        client = _client()
        fasta = await client.get_fasta(accession)
        return fmt_fasta(fasta, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_get_sequence", exc)


@mcp.tool(
    name="uniprot_get_features",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_features(
    accession: str, feature_types: str = "", response_format: str = "markdown"
) -> str:
    """Get protein features: domains, binding sites, PTMs, signal peptides.
    Optional filter (comma-separated): 'Domain,Active site,Binding site,Modified residue'."""
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
        return _safe_error("uniprot_get_features", exc)


@mcp.tool(
    name="uniprot_get_go_terms",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_go_terms(
    accession: str, aspect: str = "", response_format: str = "markdown"
) -> str:
    """Get GO annotations grouped by aspect. Optional filter: 'F' (function), 'P' (process), 'C' (component)."""
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
        return _safe_error("uniprot_get_go_terms", exc)


@mcp.tool(
    name="uniprot_get_cross_refs",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_cross_refs(
    accession: str, database: str = "", response_format: str = "markdown"
) -> str:
    """Get cross-references to PDB, Pfam, ENSEMBL, Reactome, KEGG, STRING, etc. Optional database filter."""
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
        return _safe_error("uniprot_get_cross_refs", exc)


@mcp.tool(
    name="uniprot_get_variants",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_variants(accession: str, response_format: str = "markdown") -> str:
    """Get known natural variants and disease mutations for a protein."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        features = data.get("features", []) or []
        return fmt_variants(features, accession, response_format, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_get_variants", exc)


@mcp.tool(
    name="uniprot_id_mapping",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_id_mapping(
    ids: str, from_db: str, to_db: str, response_format: str = "markdown"
) -> str:
    """Map between ID types. ids=comma-separated. Common db codes: UniProtKB_AC-ID, PDB, Ensembl, GeneID, Gene_Name."""
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
        return _safe_error("uniprot_id_mapping", exc)


@mcp.tool(
    name="uniprot_batch_entries",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_batch_entries(accessions: str, response_format: str = "markdown") -> str:
    """Fetch multiple entries. accessions=comma-separated UniProt IDs (max 100)."""
    try:
        _check_len("accessions", accessions, MAX_IDS_LEN)
        _check_format(response_format)
        acc_list = [a.strip() for a in accessions.split(",") if a.strip()][:100]
        client = _client()
        data = await client.batch_entries(acc_list)
        out = fmt_search(
            {"results": data["results"]}, response_format, provenance=client.last_provenance
        )
        if data.get("invalid"):
            out += (
                f"\n\n_Skipped {len(data['invalid'])} invalid accession(s): "
                f"{', '.join(data['invalid'])}_"
            )
        return out
    except Exception as exc:
        return _safe_error("uniprot_batch_entries", exc)


@mcp.tool(
    name="uniprot_taxonomy_search",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_taxonomy_search(
    query: str, size: int = 5, response_format: str = "markdown"
) -> str:
    """Search UniProt taxonomy by organism name. Returns taxonomy IDs."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        client = _client()
        data = await client.taxonomy_search(query, size)
        return fmt_taxonomy(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_taxonomy_search", exc)


@mcp.tool(
    name="uniprot_get_keyword",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_keyword(keyword_id: str, response_format: str = "markdown") -> str:
    """Fetch a UniProt keyword by ID (e.g. KW-0007 for Acetylation, KW-0539 for Nucleus).
    Returns name, definition, category, synonyms, GO cross-refs, and parent/child hierarchy."""
    try:
        _check_keyword_id(keyword_id)
        _check_format(response_format)
        client = _client()
        data = await client.get_keyword(keyword_id)
        return fmt_keyword(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_get_keyword", exc)


@mcp.tool(
    name="uniprot_search_keywords",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_keywords(
    query: str, size: int = 10, response_format: str = "markdown"
) -> str:
    """Search UniProt's controlled keyword vocabulary by name or definition.
    Examples: 'acetylation', 'nucleus', 'kinase activity'."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        client = _client()
        data = await client.search_keywords(query, size=size)
        return fmt_keyword_search(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_search_keywords", exc)


@mcp.tool(
    name="uniprot_get_subcellular_location",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_subcellular_location(
    location_id: str, response_format: str = "markdown"
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
        return _safe_error("uniprot_get_subcellular_location", exc)


@mcp.tool(
    name="uniprot_search_subcellular_locations",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_subcellular_locations(
    query: str, size: int = 10, response_format: str = "markdown"
) -> str:
    """Search UniProt's controlled subcellular-location vocabulary.
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
        return _safe_error("uniprot_search_subcellular_locations", exc)


@mcp.tool(
    name="uniprot_get_uniref",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_uniref(uniref_id: str, response_format: str = "markdown") -> str:
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
        return _safe_error("uniprot_get_uniref", exc)


@mcp.tool(
    name="uniprot_search_uniref",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_uniref(
    query: str,
    identity_tier: str = "",
    size: int = 10,
    response_format: str = "markdown",
) -> str:
    """Search UniRef clusters. ``identity_tier`` filters by % identity:
    ``"50"`` (loosest), ``"90"``, ``"100"`` (tightest), or empty for all tiers.
    Examples: query='kinase' identity_tier='90' returns the 90 % clusters."""
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
        return _safe_error("uniprot_search_uniref", exc)


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
async def uniprot_resolve_orthology(accession: str, response_format: str = "markdown") -> str:
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
        return _safe_error("uniprot_resolve_orthology", exc)


@mcp.tool(
    name="uniprot_target_dossier",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_target_dossier(accession: str, response_format: str = "markdown") -> str:
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
        return fmt_target_dossier(
            dossier, accession, response_format, provenance=client.last_provenance
        )
    except Exception as exc:
        return _safe_error("uniprot_target_dossier", exc)


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
    name="uniprot_resolve_clinvar",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_resolve_clinvar(
    accession: str,
    change: str = "",
    size: int = 10,
    response_format: str = "markdown",
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
        return _safe_error("uniprot_resolve_clinvar", exc)


@mcp.tool(
    name="uniprot_get_alphafold_confidence",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_alphafold_confidence(
    accession: str, response_format: str = "markdown"
) -> str:
    """Fetch AlphaFold-DB pLDDT confidence summary for a UniProt accession.
    Returns the global mean pLDDT score plus the four-band distribution
    (very high ≥ 90 / confident 70-90 / low 50-70 / very low < 50) so the
    agent can decide whether to trust the model. Critical for any
    structural-biology workflow that builds on a predicted model: a
    target with 95 % residues 'very high' is publication-grade; a target
    with 40 % 'very low' is largely disordered and structural inference
    is unsafe.

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
        return _safe_error("uniprot_get_alphafold_confidence", exc)


@mcp.tool(
    name="uniprot_get_publications",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_publications(accession: str, response_format: str = "markdown") -> str:
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
        return _safe_error("uniprot_get_publications", exc)


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
async def uniprot_compute_properties(accession: str, response_format: str = "markdown") -> str:
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
        return _safe_error("uniprot_compute_properties", exc)


@mcp.tool(
    name="uniprot_features_at_position",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_features_at_position(
    accession: str, position: int, response_format: str = "markdown"
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
        return _safe_error("uniprot_features_at_position", exc)


@mcp.tool(
    name="uniprot_lookup_variant",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_lookup_variant(
    accession: str, change: str, response_format: str = "markdown"
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
        return _safe_error("uniprot_lookup_variant", exc)


@mcp.tool(
    name="uniprot_get_disease_associations",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_disease_associations(
    accession: str, response_format: str = "markdown"
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
        return _safe_error("uniprot_get_disease_associations", exc)


@mcp.tool(
    name="uniprot_get_uniparc",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_uniparc(upi: str, response_format: str = "markdown") -> str:
    """Fetch a UniParc sequence-archive record by UPI (e.g. UPI000002ED67).
    Returns sequence, MD5/CRC64 checksums, cross-reference counts, linked
    UniProtKB accessions, and the common-taxa list. UniParc is the
    non-redundant sequence archive — every protein sequence ever submitted
    to a major public database has exactly one UniParc record."""
    try:
        _check_uniparc_id(upi)
        _check_format(response_format)
        client = _client()
        data = await client.get_uniparc(upi)
        return fmt_uniparc(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_get_uniparc", exc)


@mcp.tool(
    name="uniprot_search_uniparc",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_uniparc(
    query: str, size: int = 10, response_format: str = "markdown"
) -> str:
    """Search UniParc. Examples: 'taxonomy_id:9606' for human sequences,
    'database:Ensembl' for Ensembl-derived entries."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        client = _client()
        data = await client.search_uniparc(query, size=size)
        return fmt_uniparc_search(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_search_uniparc", exc)


@mcp.tool(
    name="uniprot_get_proteome",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_proteome(proteome_id: str, response_format: str = "markdown") -> str:
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
        return _safe_error("uniprot_get_proteome", exc)


@mcp.tool(
    name="uniprot_search_proteomes",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_proteomes(
    query: str, size: int = 10, response_format: str = "markdown"
) -> str:
    """Search UniProt proteomes. Examples: 'organism_id:9606' for human,
    'proteome_type:1' for reference proteomes only, 'taxonomy_name:bacteria'
    for all bacterial proteomes."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        client = _client()
        data = await client.search_proteomes(query, size=size)
        return fmt_proteome_search(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_search_proteomes", exc)


@mcp.tool(
    name="uniprot_get_citation",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_citation(citation_id: str, response_format: str = "markdown") -> str:
    """Fetch a UniProt citation record by ID (typically a PubMed ID, e.g. 7649814).
    Returns title, authors, journal, year, volume, pages, and cross-references."""
    try:
        _check_citation_id(citation_id)
        _check_format(response_format)
        client = _client()
        data = await client.get_citation(citation_id)
        return fmt_citation(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_get_citation", exc)


@mcp.tool(
    name="uniprot_search_citations",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_search_citations(
    query: str, size: int = 10, response_format: str = "markdown"
) -> str:
    """Search the UniProt citations index. Examples: 'p53 AND author:Vogelstein',
    'BRCA1 AND year:[2020 TO 2024]'."""
    try:
        _check_len("query", query, MAX_QUERY_LEN)
        _check_format(response_format)
        size = max(1, min(size, 500))
        client = _client()
        data = await client.search_citations(query, size=size)
        return fmt_citation_search(data, response_format, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_search_citations", exc)


@mcp.tool(
    name="uniprot_resolve_pdb",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_resolve_pdb(accession: str, response_format: str = "markdown") -> str:
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
        return _safe_error("uniprot_resolve_pdb", exc)


@mcp.tool(
    name="uniprot_resolve_alphafold",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_resolve_alphafold(accession: str, response_format: str = "markdown") -> str:
    """Resolve the AlphaFoldDB cross-reference for a UniProt entry — typically
    one canonical model per accession. Includes a direct EBI viewer link."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        return fmt_alphafold(data, accession, response_format, provenance=client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_resolve_alphafold", exc)


@mcp.tool(
    name="uniprot_resolve_interpro",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_resolve_interpro(accession: str, response_format: str = "markdown") -> str:
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
        return _safe_error("uniprot_resolve_interpro", exc)


@mcp.tool(
    name="uniprot_resolve_chembl",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_resolve_chembl(accession: str, response_format: str = "markdown") -> str:
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
        return _safe_error("uniprot_resolve_chembl", exc)


@mcp.tool(
    name="uniprot_get_evidence_summary",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_get_evidence_summary(accession: str, response_format: str = "markdown") -> str:
    """Summarise the ECO (Evidence and Conclusion Ontology) codes attached to
    a UniProt entry's annotations. Counts how many features and comments cite
    each evidence code, distinguishing experimental from inferred annotations.
    Critical for distinguishing 'wet-lab confirmed' annotations from 'inferred
    by similarity' for any downstream agent that cares about evidence quality."""
    try:
        _check_accession(accession)
        _check_format(response_format)
        client = _client()
        data = await client.get_entry(accession)
        return _format_evidence_summary(data, accession, response_format, client.last_provenance)
    except Exception as exc:
        return _safe_error("uniprot_get_evidence_summary", exc)


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

    if fmt == "json":
        from uniprot_mcp.formatters import _json_envelope

        return _json_envelope({"accession": accession, "evidence_counts": counts}, provenance)  # type: ignore[arg-type]

    from uniprot_mcp.formatters import _provenance_md_footer  # local import — cheap

    lines: list[str] = [f"## Evidence summary: {accession} ({len(counts)} distinct ECO codes)", ""]
    if not counts:
        lines.append("_No evidence annotations on this entry._")
    else:
        for code, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            description = _ECO_HUMAN_LABELS.get(code, "")
            suffix = f"  —  {description}" if description else ""
            lines.append(f"- **{code}**: {n} occurrence(s){suffix}")
    if provenance is not None:
        lines.extend(_provenance_md_footer(provenance))  # type: ignore[arg-type]
    return "\n".join(lines)


# Human-readable labels for the most common ECO codes UniProt uses. The
# ECO ontology has thousands of terms; this curated subset covers the
# overwhelming majority of UniProt usage. Source:
# https://www.evidenceontology.org/ — ECO term labels.
_ECO_HUMAN_LABELS: Final[dict[str, str]] = {
    "ECO:0000269": "experimental evidence used in manual assertion",
    "ECO:0000250": "sequence similarity evidence used in manual assertion",
    "ECO:0000305": "curator inference used in manual assertion",
    "ECO:0000244": "combinatorial evidence used in manual assertion",
    "ECO:0000255": "match to InterPro member signature evidence used in manual assertion",
    "ECO:0000256": "match to sequence model evidence used in automatic assertion",
    "ECO:0000259": "match to InterPro member signature used in automatic assertion",
    "ECO:0000303": "non-traceable author statement used in manual assertion",
    "ECO:0000304": "traceable author statement used in manual assertion",
    "ECO:0000312": "imported information used in manual assertion",
    "ECO:0007744": "combinatorial evidence used in automatic assertion",
    "ECO:0000501": "evidence used in automatic assertion",
}


@mcp.tool(
    name="uniprot_provenance_verify",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True),
)
async def uniprot_provenance_verify(
    url: str,
    release: str = "",
    response_sha256: str = "",
    response_format: str = "markdown",
) -> str:
    """Re-fetch a previously recorded UniProt URL and verify it still
    returns the same release identifier and the same canonical response
    body (SHA-256). Pass the values from a prior response's provenance
    footer (`url`, `release`, `response_sha256`); empty optional fields
    skip the corresponding check. Returns a verification report with
    explicit pass / drift / unreachable verdicts per check.

    This is the single tool that converts every prior uniprot-mcp
    response into an independently auditable artefact — a year from
    now, a third party can take the recorded provenance footer and
    confirm the upstream still serves the exact same bytes."""
    try:
        _check_len("url", url, MAX_PROVENANCE_URL_LEN)
        _check_len("release", release, MAX_RELEASE_TAG_LEN)
        _check_len("response_sha256", response_sha256, 64)
        _check_format(response_format)
        if not url.startswith("https://rest.uniprot.org/"):
            raise _InputError(
                "url must begin with https://rest.uniprot.org/ — only UniProt REST "
                "URLs are verifiable through this tool."
            )
        return await _provenance_verify_impl(
            url=url,
            recorded_release=release or None,
            recorded_sha256=response_sha256 or None,
            response_format=response_format,
        )
    except Exception as exc:
        return _safe_error("uniprot_provenance_verify", exc)


async def _provenance_verify_impl(
    *,
    url: str,
    recorded_release: str | None,
    recorded_sha256: str | None,
    response_format: str,
) -> str:
    """Worker for ``uniprot_provenance_verify``. Re-fetches ``url`` with
    a fresh httpx client (bypasses the singleton's pin-release config)
    and produces a structured verdict.
    """
    report: dict[str, object] = {
        "url": url,
        "recorded_release": recorded_release,
        "recorded_sha256": recorded_sha256,
    }
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        headers={"User-Agent": UA, "Accept": "application/json"},
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
    advice = _verify_advice(str(status))
    if advice:
        lines.extend(["", f"**Advice:** {advice}"])
    return "\n".join(lines)


def _verify_advice(status: str) -> str:
    return {
        "verified": (
            "Both checks passed. The recorded provenance is reproducible against the "
            "live UniProt API."
        ),
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
        "uniprot_provenance_verify",
    }

    tools = getattr(mcp, "_tool_manager", None)
    registered: set[str] = set()
    if tools is not None and hasattr(tools, "_tools"):
        registered = set(tools._tools.keys())

    missing = expected - registered
    extra = registered - expected
    print(f"[tools] registered: {len(registered)}/{len(expected)}", file=sys.stderr)
    if missing:
        print(f"[FAIL] missing tools: {sorted(missing)}", file=sys.stderr)
        return 1
    if extra:
        print(f"[WARN] unexpected tools: {sorted(extra)}", file=sys.stderr)

    async def _live() -> int:
        try:
            data = await _client().get_entry("P04637")
            gene = data.get("genes", [{}])[0].get("geneName", {}).get("value")
            if gene != "TP53":
                print(f"[FAIL] P04637 gene is {gene!r}, expected TP53", file=sys.stderr)
                return 2
            print("[live] P04637 -> TP53 OK", file=sys.stderr)
            return 0
        finally:
            await _client().close()

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
