"""TOPOLOGICA UniProt MCP Server. 16 tools. FastMCP. stdio transport.

Hardened against the common class of MCP-server defects:

- Inputs are length-capped before reaching httpx (DoS / abuse mitigation).
- ``response_format`` is validated against an allow-list.
- Error envelopes do not leak raw exception text back to the LLM; we
  emit a stable, agent-safe message and log detail server-side.
- Every successful tool response carries a machine-verifiable
  :class:`~uniprot_mcp.client.Provenance` record — UniProt release
  number, release date, retrieval timestamp, and the resolved query
  URL — rendered inline as a Markdown footer, a JSON envelope, or a
  PIR-style comment block depending on the output format.
- Module-level lazy client avoids the FastMCP lifespan ctx-injection
  race that broke ``Failed to connect`` in the first implementation.

Author: Santiago Maniches <santiago.maniches@gmail.com>
        ORCID https://orcid.org/0009-0005-6480-1987
        TOPOLOGICA LLC
License: Apache-2.0
"""

from __future__ import annotations

import logging
import sys
from typing import Final

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from uniprot_mcp.client import (
    ACCESSION_RE,
    KEYWORD_ID_RE,
    SUBCELLULAR_LOCATION_ID_RE,
    UNIREF_ID_RE,
    UNIREF_IDENTITY_TIERS,
    UniProtClient,
)
from uniprot_mcp.formatters import (
    fmt_crossrefs,
    fmt_entry,
    fmt_fasta,
    fmt_features,
    fmt_go,
    fmt_idmapping,
    fmt_keyword,
    fmt_keyword_search,
    fmt_search,
    fmt_subcellular_location,
    fmt_subcellular_location_search,
    fmt_taxonomy,
    fmt_uniref,
    fmt_uniref_search,
    fmt_variants,
)

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


def _safe_error(tool: str, exc: BaseException) -> str:
    """Format an agent-safe error. Detail goes to stderr log, not the LLM."""
    logger.exception("tool=%s failed", tool)
    if isinstance(exc, _InputError):
        return f"Input error in {tool}: {exc}"
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
    if "--self-test" in sys.argv[1:]:
        sys.exit(_self_test())
    mcp.run()


if __name__ == "__main__":
    main()
