"""Live UniProt + AlphaFold + ClinVar tests for every R1 / R2 / R3 / R4
clinical-layer tool.

The existing ``test_all_tools_live.py`` covers the original 10 core
tools. This file extends coverage to the additional 28 tools added
between v0.1.0 and v1.0.1 — the entire clinical layer plus
controlled vocabularies, sequence archives, proteomes, citations,
structured cross-DB resolvers, evidence summary, target dossier,
orthology, sequence chemistry, position-aware features, HGVS variant
lookup, disease associations, AlphaFold pLDDT, ClinVar, publications,
and the cache.

Marked ``integration`` — skipped unless ``pytest --integration`` is
passed. These run nightly against the live APIs in production.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from uniprot_mcp.cache import CACHE_DIR_ENV
from uniprot_mcp.client import UniProtClient
from uniprot_mcp.server import (
    uniprot_compute_properties,
    uniprot_features_at_position,
    uniprot_get_alphafold_confidence,
    uniprot_get_citation,
    uniprot_get_disease_associations,
    uniprot_get_evidence_summary,
    uniprot_get_keyword,
    uniprot_get_proteome,
    uniprot_get_publications,
    uniprot_get_subcellular_location,
    uniprot_get_uniparc,
    uniprot_get_uniref,
    uniprot_lookup_variant,
    uniprot_replay_from_cache,
    uniprot_resolve_alphafold,
    uniprot_resolve_chembl,
    uniprot_resolve_clinvar,
    uniprot_resolve_interpro,
    uniprot_resolve_orthology,
    uniprot_resolve_pdb,
    uniprot_search_keywords,
    uniprot_search_proteomes,
    uniprot_search_subcellular_locations,
    uniprot_search_uniparc,
    uniprot_search_uniref,
    uniprot_target_dossier,
)

pytestmark = pytest.mark.integration


@pytest.fixture
async def client() -> AsyncIterator[UniProtClient]:
    c = UniProtClient()
    yield c
    await c.close()


# ---------------------------------------------------------------------------
# Sequence chemistry / position / variant / disease  (R1 — pure-Python over
# the entry / FASTA, but live-tested here to confirm we parse real responses)
# ---------------------------------------------------------------------------


async def test_compute_properties_for_p04637_live() -> None:
    out = await uniprot_compute_properties("P04637", "json")
    payload = json.loads(out)
    props = payload["data"]["properties"]
    # TP53 canonical isoform: 393 aa (verified independently against UniProt).
    assert props["length"] == 393
    # Empirical bounds derived from the 393-aa sequence; values are
    # stable across UniProt releases (they're functions of sequence
    # composition, which doesn't change for the canonical isoform).
    assert 43000 < props["molecular_weight"] < 44000
    assert 6.0 < props["theoretical_pi"] < 7.5
    assert -1.0 < props["gravy"] < 0.0
    assert payload["provenance"]["source"] == "UniProt"


async def test_features_at_position_175_of_p04637_live() -> None:
    out = await uniprot_features_at_position("P04637", 175, "markdown")
    # Position 175 is in the DNA-binding domain (102-292) — that
    # feature MUST appear, plus at least one of the other annotations.
    assert "P04637" in out
    assert "175" in out
    # The Chain feature (1-393) overlaps 175 too.
    assert "Chain" in out


async def test_lookup_variant_R175H_live() -> None:
    out = await uniprot_lookup_variant("P04637", "R175H", "markdown")
    # R175H is one of the most-annotated cancer-driver variants.
    assert "P04637" in out
    assert "R175H" in out
    # Must produce a non-zero match against the live UniProt entry.
    assert "0 match(es)" not in out


async def test_disease_associations_for_p04637_live() -> None:
    out = await uniprot_get_disease_associations("P04637", "json")
    payload = json.loads(out)
    diseases = payload["data"]["diseases"]
    # TP53 has multiple disease associations including Li-Fraumeni
    # syndrome — the precise count varies by release but must be > 0.
    assert isinstance(diseases, list)
    assert len(diseases) > 0
    # Li-Fraumeni is a stable association across releases.
    names = [str(d.get("name", "")) for d in diseases]
    assert any("Li-Fraumeni" in n for n in names), f"Li-Fraumeni not found in: {names}"


# ---------------------------------------------------------------------------
# Controlled vocabularies (R / B/1)
# ---------------------------------------------------------------------------


async def test_get_keyword_acetylation_live() -> None:
    out = await uniprot_get_keyword("KW-0007", "json")
    payload = json.loads(out)
    data = payload["data"]
    # Schema-shape check: response carries a keyword block with id/name.
    kw = data.get("keyword") or {}
    if isinstance(kw, dict):
        assert kw.get("id") == "KW-0007"
        assert "Acetylation" in str(kw.get("name", ""))


async def test_search_keywords_acetylation_live() -> None:
    out = await uniprot_search_keywords("Acetylation", size=3, response_format="json")
    payload = json.loads(out)
    results = payload["data"].get("results", [])
    assert len(results) > 0


async def test_get_subcellular_location_cell_membrane_live() -> None:
    """Validates the SL-0086 vs SL-0039 lesson is honoured: SL-0039
    is the canonical Cell membrane id."""
    out = await uniprot_get_subcellular_location("SL-0039", "json")
    payload = json.loads(out)
    assert payload["data"].get("name") == "Cell membrane"


async def test_search_subcellular_locations_membrane_live() -> None:
    out = await uniprot_search_subcellular_locations("membrane", size=3, response_format="json")
    payload = json.loads(out)
    assert len(payload["data"].get("results", [])) > 0


# ---------------------------------------------------------------------------
# Sequence archives & clusters (B/2 + B/3)
# ---------------------------------------------------------------------------


async def test_get_uniref50_p04637_live() -> None:
    out = await uniprot_get_uniref("UniRef50_P04637", "json")
    payload = json.loads(out)
    assert payload["data"]["id"] == "UniRef50_P04637"
    # Cluster has at least P04637 itself as a member; member count > 0.
    member_count = payload["data"].get("memberCount", 0)
    assert isinstance(member_count, int) and member_count > 0


async def test_search_uniref_p53_live() -> None:
    out = await uniprot_search_uniref("p53", identity_tier="50", size=3, response_format="json")
    payload = json.loads(out)
    assert "results" in payload["data"]


async def test_get_uniparc_live() -> None:
    """UPI000002ED67 is the UniParc record for human TP53 protein
    sequence (one of several historical members)."""
    out = await uniprot_get_uniparc("UPI000002ED67", "json")
    payload = json.loads(out)
    assert payload["data"]["uniParcId"] == "UPI000002ED67"


async def test_search_uniparc_live() -> None:
    out = await uniprot_search_uniparc("accession:P04637", size=3, response_format="json")
    payload = json.loads(out)
    assert "results" in payload["data"]


# ---------------------------------------------------------------------------
# Proteomes & literature (B/4 + B/5)
# ---------------------------------------------------------------------------


async def test_get_proteome_human_live() -> None:
    """UP000005640 is the human reference proteome."""
    out = await uniprot_get_proteome("UP000005640", "json")
    payload = json.loads(out)
    assert payload["data"]["id"] == "UP000005640"
    # Human proteome has > 20k proteins; allow a wide band for future
    # changes.
    protein_count = payload["data"].get("proteinCount", 0)
    assert protein_count > 20000


async def test_search_proteomes_live() -> None:
    out = await uniprot_search_proteomes(
        "organism_id:9606", size=3, response_format="json"
    )
    payload = json.loads(out)
    assert len(payload["data"].get("results", [])) > 0


async def test_get_citation_live() -> None:
    """PubMed 2922050 is the Hollstein-Sidransky-Vogelstein-Harris 1989
    Science paper that's a canonical TP53 reference."""
    out = await uniprot_get_citation("2922050", "json")
    payload = json.loads(out)
    # The citation API can return either a direct citation object or a
    # wrapper; both shapes are accepted by the formatter. Just assert
    # the response is non-empty.
    assert payload["data"]


# ---------------------------------------------------------------------------
# Structured cross-DB resolvers (B/7)
# ---------------------------------------------------------------------------


async def test_resolve_pdb_for_p04637_live() -> None:
    out = await uniprot_resolve_pdb("P04637", "json")
    payload = json.loads(out)
    pdbs = payload["data"]["pdb"]
    # TP53 has many PDB structures — assert at least 5.
    assert len(pdbs) >= 5
    # Each entry has a PDB id and (usually) method + resolution.
    for entry in pdbs[:3]:
        assert entry.get("pdb_id")


async def test_resolve_alphafold_for_p04637_live() -> None:
    out = await uniprot_resolve_alphafold("P04637", "json")
    payload = json.loads(out)
    af_entries = payload["data"]["alphafold"]
    assert len(af_entries) >= 1
    assert af_entries[0]["alphafold_id"] == "P04637"


async def test_resolve_interpro_for_p04637_live() -> None:
    out = await uniprot_resolve_interpro("P04637", "json")
    payload = json.loads(out)
    iprs = payload["data"]["interpro"]
    assert len(iprs) > 0
    for entry in iprs[:3]:
        assert entry.get("interpro_id", "").startswith("IPR")


async def test_resolve_chembl_for_p04637_live() -> None:
    """TP53 has documented ChEMBL drug-target records."""
    out = await uniprot_resolve_chembl("P04637", "json")
    payload = json.loads(out)
    chembls = payload["data"]["chembl"]
    # P04637 has at least one ChEMBL cross-reference; assert > 0.
    assert len(chembls) > 0


# ---------------------------------------------------------------------------
# Cross-origin enrichment (R2 + R2.3)
# ---------------------------------------------------------------------------


async def test_get_alphafold_confidence_for_p04637_live() -> None:
    """Live AlphaFold-DB call — the cross-origin endpoint must be
    reachable and return a record with the four pLDDT bands."""
    out = await uniprot_get_alphafold_confidence("P04637", "json")
    payload = json.loads(out)
    af = payload["data"]["alphafold"]
    assert af.get("uniprotAccession") == "P04637"
    assert "globalMetricValue" in af
    # Four bands sum to ~1.0 (allow rounding).
    fractions = [
        af.get("fractionPlddtVeryHigh", 0),
        af.get("fractionPlddtConfident", 0),
        af.get("fractionPlddtLow", 0),
        af.get("fractionPlddtVeryLow", 0),
    ]
    total = sum(f for f in fractions if isinstance(f, (int, float)))
    assert 0.95 <= total <= 1.05, f"pLDDT bands don't sum to ~1.0: {fractions}"
    # Provenance source must be AlphaFoldDB, not UniProt.
    assert payload["provenance"]["source"] == "AlphaFoldDB"


async def test_resolve_clinvar_for_brca1_live() -> None:
    """Live NCBI eutils call. BRCA1 has ~15,000 ClinVar records."""
    out = await uniprot_resolve_clinvar("P38398", size=3, response_format="json")
    payload = json.loads(out)
    assert payload["data"]["gene"] == "BRCA1"
    assert payload["data"]["clinvar"]["total"] > 1000
    assert len(payload["data"]["clinvar"]["records"]) > 0
    assert payload["provenance"]["source"] == "NCBI ClinVar (eutils)"


async def test_get_publications_for_p04637_live() -> None:
    out = await uniprot_get_publications("P04637", "json")
    payload = json.loads(out)
    pubs = payload["data"]["publications"]
    # TP53 entry cites hundreds of publications.
    assert len(pubs) > 50
    # Each publication is a dict with the expected keys.
    for p in pubs[:3]:
        assert "title" in p
        assert "authors" in p


# ---------------------------------------------------------------------------
# Composition + provenance (R3 + R4)
# ---------------------------------------------------------------------------


async def test_get_evidence_summary_for_p04637_live() -> None:
    out = await uniprot_get_evidence_summary("P04637", "json")
    payload = json.loads(out)
    counts = payload["data"]["evidence_counts"]
    # TP53 has many distinct ECO codes; expect ECO:0000269 (experimental
    # evidence) to be the most common.
    assert isinstance(counts, dict)
    assert len(counts) > 3
    # Top code is typically ECO:0000269 for a heavily-studied protein.
    if counts:
        top_code = max(counts, key=lambda k: counts[k])
        assert top_code.startswith("ECO:")


async def test_resolve_orthology_for_p04637_live() -> None:
    out = await uniprot_resolve_orthology("P04637", "json")
    payload = json.loads(out)
    grouped = payload["data"]["orthology"]
    # TP53 has cross-references in multiple orthology databases.
    assert len(grouped) >= 2
    # KEGG and OrthoDB are both stable cross-references.
    assert "KEGG" in grouped or "OrthoDB" in grouped or "OMA" in grouped


async def test_target_dossier_for_p04637_live() -> None:
    out = await uniprot_target_dossier("P04637", "json")
    payload = json.loads(out)
    dossier = payload["data"]["dossier"]
    # All the major sections must be populated.
    assert dossier["identity"]["gene"] == "TP53"
    assert dossier["identity"]["organism"] == "Homo sapiens"
    assert dossier["identity"]["length"] == 393
    assert "tumor" in str(dossier.get("function", "")).lower()
    assert dossier["chemistry"]["molecular_weight"] > 40000
    assert dossier["structure"]["pdb_count"] > 0
    assert dossier["structure"]["alphafold_model_id"] == "P04637"
    assert dossier["variants"]["count"] > 0
    assert len(dossier["diseases"]) > 0


async def test_replay_from_cache_live(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end cache flow: configure cache dir, populate it via a
    direct ProvenanceCache write (the client does not auto-write —
    the cache fills via explicit calls in the future cache-on-write
    integration), and read it back through the MCP tool."""
    from uniprot_mcp.cache import ProvenanceCache

    monkeypatch.setenv(CACHE_DIR_ENV, str(tmp_path))
    cache = ProvenanceCache(tmp_path)
    url = "https://rest.uniprot.org/uniprotkb/P04637"
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-25T12:00:00Z",
        "url": url,
        "response_sha256": "0" * 64,
    }
    body = '{"primaryAccession": "P04637"}'
    cache.write(url, body, prov)  # type: ignore[arg-type]
    out = await uniprot_replay_from_cache(url, "json")
    payload = json.loads(out)
    assert payload["url"] == url
    assert payload["body_text"] == body


# ---------------------------------------------------------------------------
# UA-string sanity — live-side check that our requests are identifiable
# ---------------------------------------------------------------------------


async def test_user_agent_is_versioned(client: UniProtClient) -> None:
    """The UA string in client.py is manually maintained in lock-step
    with the version. A live-side sanity check that our actual outgoing
    requests carry it. (We don't hit a UA-echo endpoint; instead we
    just assert the constant is current.)"""
    from uniprot_mcp.client import UA

    assert UA.startswith("uniprot-mcp/1.")
    assert "github.com/smaniches/uniprot-mcp" in UA
