"""TOPOLOGICA UniProt MCP Server. 10 tools. FastMCP. stdio transport.

Fixed: removed lifespan context injection. Uses module-level lazy client.
Lifespan pattern breaks when FastMCP doesn't inject ctx properly (the
"Failed to connect" issue). Lazy client is reliable across all transports.

TOPOLOGICA LLC - Santiago Maniches
"""
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp.server.fastmcp import FastMCP
from client import UniProtClient
from formatters import (
    fmt_entry, fmt_search, fmt_features, fmt_go,
    fmt_crossrefs, fmt_variants, fmt_idmapping, fmt_taxonomy,
)

logger = logging.getLogger("topologica.uniprot")
logger.addHandler(logging.StreamHandler(sys.stderr))
logger.setLevel(logging.INFO)

mcp = FastMCP("topologica_uniprot_mcp")

# Module-level lazy client. No lifespan. No ctx injection. Just works.
_uniprot: UniProtClient | None = None

def _client() -> UniProtClient:
    global _uniprot
    if _uniprot is None:
        _uniprot = UniProtClient()
    return _uniprot


@mcp.tool(name="uniprot_get_entry", annotations={"readOnlyHint": True, "openWorldHint": True})
async def uniprot_get_entry(accession: str, response_format: str = "markdown") -> str:
    """Fetch a UniProt protein entry by accession (e.g. P04637 for p53, P38398 for BRCA1).
    Returns function, gene, organism, disease associations, cross-references."""
    try:
        data = await _client().get_entry(accession)
        return fmt_entry(data, response_format)
    except Exception as e:
        return f"Error fetching {accession}: {e}"


@mcp.tool(name="uniprot_search", annotations={"readOnlyHint": True, "openWorldHint": True})
async def uniprot_search(query: str, size: int = 10, reviewed_only: bool = False,
                         organism: str = "", response_format: str = "markdown") -> str:
    """Search UniProtKB. Examples: '(gene:TP53) AND (organism_id:9606)', 'kinase AND reviewed:true'.
    Set reviewed_only=true for Swiss-Prot only. Set organism to taxonomy ID or name."""
    try:
        q = query
        if reviewed_only and "reviewed:" not in q.lower():
            q = f"({q}) AND reviewed:true"
        if organism:
            if organism.isdigit():
                q = f"({q}) AND (organism_id:{organism})"
            else:
                q = f"({q}) AND (organism_name:{organism})"
        data = await _client().search(q, size=size)
        return fmt_search(data, response_format)
    except Exception as e:
        return f"Error searching: {e}"


@mcp.tool(name="uniprot_get_sequence", annotations={"readOnlyHint": True, "openWorldHint": True})
async def uniprot_get_sequence(accession: str) -> str:
    """Get protein sequence in FASTA format for a UniProt accession."""
    try:
        return await _client().get_fasta(accession)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(name="uniprot_get_features", annotations={"readOnlyHint": True, "openWorldHint": True})
async def uniprot_get_features(accession: str, feature_types: str = "",
                                response_format: str = "markdown") -> str:
    """Get protein features: domains, binding sites, PTMs, signal peptides.
    Optional filter (comma-separated): 'Domain,Active site,Binding site,Modified residue'."""
    try:
        data = await _client().get_entry(accession)
        features = data.get("features", [])
        if feature_types:
            types = {t.strip().lower() for t in feature_types.split(",")}
            features = [f for f in features if f.get("type", "").lower() in types]
        return fmt_features(features, accession, response_format)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(name="uniprot_get_go_terms", annotations={"readOnlyHint": True, "openWorldHint": True})
async def uniprot_get_go_terms(accession: str, aspect: str = "",
                                response_format: str = "markdown") -> str:
    """Get GO annotations grouped by aspect. Optional filter: 'F' (function), 'P' (process), 'C' (component)."""
    try:
        data = await _client().get_entry(accession)
        xrefs = data.get("uniProtKBCrossReferences", [])
        return fmt_go(xrefs, accession, aspect or None, response_format)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(name="uniprot_get_cross_refs", annotations={"readOnlyHint": True, "openWorldHint": True})
async def uniprot_get_cross_refs(accession: str, database: str = "",
                                  response_format: str = "markdown") -> str:
    """Get cross-references to PDB, Pfam, ENSEMBL, Reactome, KEGG, STRING, etc. Optional database filter."""
    try:
        data = await _client().get_entry(accession)
        xrefs = data.get("uniProtKBCrossReferences", [])
        return fmt_crossrefs(xrefs, accession, database or None, response_format)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(name="uniprot_get_variants", annotations={"readOnlyHint": True, "openWorldHint": True})
async def uniprot_get_variants(accession: str, response_format: str = "markdown") -> str:
    """Get known natural variants and disease mutations for a protein."""
    try:
        data = await _client().get_entry(accession)
        features = data.get("features", [])
        return fmt_variants(features, accession, response_format)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(name="uniprot_id_mapping", annotations={"readOnlyHint": True, "openWorldHint": True})
async def uniprot_id_mapping(ids: str, from_db: str, to_db: str,
                              response_format: str = "markdown") -> str:
    """Map between ID types. ids=comma-separated. Common db codes: UniProtKB_AC-ID, PDB, Ensembl, GeneID, Gene_Name."""
    try:
        id_list = [i.strip() for i in ids.split(",") if i.strip()][:100]
        job_id = await _client().id_mapping_submit(from_db, to_db, id_list)
        data = await _client().id_mapping_results(job_id)
        return fmt_idmapping(data, response_format)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(name="uniprot_batch_entries", annotations={"readOnlyHint": True, "openWorldHint": True})
async def uniprot_batch_entries(accessions: str, response_format: str = "markdown") -> str:
    """Fetch multiple entries. accessions=comma-separated UniProt IDs (max 100)."""
    try:
        acc_list = [a.strip() for a in accessions.split(",") if a.strip()][:100]
        data = await _client().batch_entries(acc_list)
        out = fmt_search({"results": data["results"]}, response_format)
        if data.get("invalid"):
            out += f"\n\n_Skipped {len(data['invalid'])} invalid accession(s): {', '.join(data['invalid'])}_"
        return out
    except Exception as e:
        return f"Error: {e}"


@mcp.tool(name="uniprot_taxonomy_search", annotations={"readOnlyHint": True, "openWorldHint": True})
async def uniprot_taxonomy_search(query: str, size: int = 5,
                                   response_format: str = "markdown") -> str:
    """Search UniProt taxonomy by organism name. Returns taxonomy IDs."""
    try:
        data = await _client().taxonomy_search(query, size)
        return fmt_taxonomy(data, response_format)
    except Exception as e:
        return f"Error: {e}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
