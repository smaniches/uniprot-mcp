"""Tests for the ClinVar resolver (R2.3 — second cross-origin tool).

Two-step flow:

  1. Fetch the UniProt entry to extract the canonical gene symbol.
  2. Query NCBI eutils ClinVar by gene (and optional HGVS-shorthand
     protein-change filter); aggregate the esummary records.

Mocked end-to-end via ``respx`` so CI stays offline.
"""

from __future__ import annotations

import json

import httpx
import respx

from uniprot_mcp.client import NCBI_EUTILS_BASE
from uniprot_mcp.server import uniprot_resolve_clinvar

_BRCA1_ENTRY = {
    "primaryAccession": "P38398",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "genes": [{"geneName": {"value": "BRCA1"}}],
}

_BRCA1_ESEARCH = {
    "header": {"type": "esearch"},
    "esearchresult": {"count": "15839", "idlist": ["4818740", "4813451"]},
}

_BRCA1_ESUMMARY = {
    "result": {
        "uids": ["4818740", "4813451"],
        "4818740": {
            "uid": "4818740",
            "accession": "VCV004818740",
            "title": "NM_007294.4(BRCA1):c.3896_3912delinsTGC (p.Gln1299fs)",
            "germline_classification": {
                "description": "Pathogenic",
                "review_status": "criteria provided, single submitter",
            },
            "trait_set": [{"trait_name": "Hereditary breast and ovarian cancer syndrome"}],
            "molecular_consequence_list": ["frameshift variant"],
            "protein_change": "Q1299fs",
            "genes": [{"symbol": "BRCA1"}],
        },
        "4813451": {
            "uid": "4813451",
            "accession": "VCV004813451",
            "title": "NM_007294.4(BRCA1):c.5266dup (p.Gln1756fs)",
            "germline_classification": {
                "description": "Pathogenic",
                "review_status": "reviewed by expert panel",
            },
            "trait_set": [{"trait_name": "Hereditary breast and ovarian cancer syndrome"}],
            "molecular_consequence_list": ["frameshift variant"],
            "protein_change": "Q1756fs",
        },
    }
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


async def test_clinvar_rejects_bad_accession() -> None:
    out = await uniprot_resolve_clinvar("not-real")
    assert "Input error" in out


async def test_clinvar_rejects_bad_change() -> None:
    out = await uniprot_resolve_clinvar("P38398", change="p.R175H")
    assert "Input error" in out


# ---------------------------------------------------------------------------
# Happy path — gene-only query
# ---------------------------------------------------------------------------


async def test_clinvar_gene_only_query_renders_records() -> None:
    with (
        respx.mock(base_url="https://rest.uniprot.org") as up_router,
        respx.mock(base_url=NCBI_EUTILS_BASE) as ncbi_router,
    ):
        up_router.get("/uniprotkb/P38398").mock(
            return_value=httpx.Response(
                200, json=_BRCA1_ENTRY, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        ncbi_router.get("/esearch.fcgi").mock(return_value=httpx.Response(200, json=_BRCA1_ESEARCH))
        ncbi_router.get("/esummary.fcgi").mock(
            return_value=httpx.Response(200, json=_BRCA1_ESUMMARY)
        )
        out = await uniprot_resolve_clinvar("P38398", size=2, response_format="markdown")
    assert "ClinVar records for P38398 (gene BRCA1)" in out
    assert "Showing 2 of 15839 matching records" in out
    assert "VCV004818740" in out
    assert "Pathogenic" in out
    assert "Hereditary breast and ovarian cancer syndrome" in out
    assert "frameshift variant" in out
    assert "Q1299fs" in out
    assert "reviewed by expert panel" in out


async def test_clinvar_with_change_filter_renders_query() -> None:
    captured_term: dict[str, str] = {}

    def _esearch_handler(req: httpx.Request) -> httpx.Response:
        captured_term["term"] = req.url.params.get("term", "")
        return httpx.Response(200, json=_BRCA1_ESEARCH)

    with (
        respx.mock(base_url="https://rest.uniprot.org") as up_router,
        respx.mock(base_url=NCBI_EUTILS_BASE) as ncbi_router,
    ):
        up_router.get("/uniprotkb/P38398").mock(
            return_value=httpx.Response(
                200, json=_BRCA1_ENTRY, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        ncbi_router.get("/esearch.fcgi").mock(side_effect=_esearch_handler)
        ncbi_router.get("/esummary.fcgi").mock(
            return_value=httpx.Response(200, json=_BRCA1_ESUMMARY)
        )
        out = await uniprot_resolve_clinvar(
            "P38398", change="R175H", size=2, response_format="markdown"
        )
    assert "change `R175H`" in out
    # The eutils term must contain both the gene filter and the HGVS-shorthand
    # variant filter, separated by AND.
    assert "BRCA1[Gene]" in captured_term["term"]
    assert "R175H" in captured_term["term"]


async def test_clinvar_no_matches_renders_advice() -> None:
    with (
        respx.mock(base_url="https://rest.uniprot.org") as up_router,
        respx.mock(base_url=NCBI_EUTILS_BASE) as ncbi_router,
    ):
        up_router.get("/uniprotkb/P38398").mock(
            return_value=httpx.Response(
                200, json=_BRCA1_ENTRY, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        ncbi_router.get("/esearch.fcgi").mock(
            return_value=httpx.Response(
                200,
                json={"esearchresult": {"count": "0", "idlist": []}},
            )
        )
        out = await uniprot_resolve_clinvar("P38398", change="R999H", response_format="markdown")
    assert "Showing 0 of 0 matching records" in out
    assert "No ClinVar records matched" in out


async def test_clinvar_handles_entry_without_gene_name() -> None:
    """An entry without a canonical gene name cannot be resolved through
    ClinVar — surface that as an Input error rather than crashing."""
    entry_no_gene = {
        "primaryAccession": "P00000",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "genes": [],
    }
    with respx.mock(base_url="https://rest.uniprot.org") as up_router:
        up_router.get("/uniprotkb/P00000").mock(
            return_value=httpx.Response(
                200, json=entry_no_gene, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_resolve_clinvar("P00000")
    assert "Input error" in out
    assert "no canonical gene name" in out


async def test_clinvar_json_envelope() -> None:
    with (
        respx.mock(base_url="https://rest.uniprot.org") as up_router,
        respx.mock(base_url=NCBI_EUTILS_BASE) as ncbi_router,
    ):
        up_router.get("/uniprotkb/P38398").mock(
            return_value=httpx.Response(
                200, json=_BRCA1_ENTRY, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        ncbi_router.get("/esearch.fcgi").mock(return_value=httpx.Response(200, json=_BRCA1_ESEARCH))
        ncbi_router.get("/esummary.fcgi").mock(
            return_value=httpx.Response(200, json=_BRCA1_ESUMMARY)
        )
        out = await uniprot_resolve_clinvar("P38398", response_format="json")
    payload = json.loads(out)
    assert payload["data"]["accession"] == "P38398"
    assert payload["data"]["gene"] == "BRCA1"
    assert payload["data"]["clinvar"]["total"] == 15839
    assert len(payload["data"]["clinvar"]["records"]) == 2
    assert payload["provenance"]["source"] == "NCBI ClinVar (eutils)"
