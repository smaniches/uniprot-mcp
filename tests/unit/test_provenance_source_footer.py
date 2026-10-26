"""Markdown provenance footers name the provider that served the response.

Regression for UNI-02: ``_provenance_md_footer`` printed the UniProt
constant for every record, so ClinVar and AlphaFold DB responses were
attributed to UniProt, and an AlphaFold *model* version and model-creation
date were rendered as a "UniProt release". These tests drive the real tool
wrappers end-to-end against respx-mocked upstreams. Mocked bodies reuse
field values from responses captured on 2026-10-15 (AlphaFold DB
``/api/prediction/P04637``; ClinVar esearch/esummary for TP53 R175H,
UID 12374 / VCV000012374; UniProt release header ``2026_03``).
"""

from __future__ import annotations

import json

import httpx
import respx

from uniprot_mcp.client import ALPHAFOLD_API_BASE, NCBI_EUTILS_BASE, Provenance
from uniprot_mcp.formatters import _provenance_md_footer
from uniprot_mcp.server import (
    uniprot_get_alphafold_confidence,
    uniprot_get_entry,
    uniprot_resolve_clinvar,
)

_AF_P04637 = {
    "entryId": "AF-P04637-F1",
    "modelEntityId": "AF-P04637-F1",
    "uniprotAccession": "P04637",
    "uniprotStart": 1,
    "uniprotEnd": 393,
    "sequenceStart": 1,
    "sequenceEnd": 393,
    "latestVersion": 6,
    "modelCreatedDate": "2025-08-01T00:00:00Z",
    "globalMetricValue": 75.06,
    "fractionPlddtVeryLow": 0.298,
    "fractionPlddtLow": 0.104,
    "fractionPlddtConfident": 0.071,
    "fractionPlddtVeryHigh": 0.527,
    "toolUsed": "AlphaFold Monomer v2.0 pipeline",
}

_ENTRY = {
    "primaryAccession": "P04637",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}
    },
    "genes": [{"geneName": {"value": "TP53"}}],
    "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
    "sequence": {"length": 393, "molWeight": 43653},
    "comments": [],
    "features": [],
}

_UNIPROT_HEADERS = {
    "X-UniProt-Release": "2026_03",
    "X-UniProt-Release-Date": "02-September-2026",
}

_CV_SEARCH = {
    "header": {"type": "esearch", "version": "0.3"},
    "esearchresult": {"count": "1", "retmax": "1", "retstart": "0", "idlist": ["12374"]},
}
_CV_SUMMARY = {
    "header": {"type": "esummary", "version": "0.3"},
    "result": {
        "uids": ["12374"],
        "12374": {
            "uid": "12374",
            "accession": "VCV000012374",
            "title": "NM_000546.6(TP53):c.524G>A (p.Arg175His)",
            "germline_classification": {
                "description": "Pathogenic",
                "review_status": "reviewed by expert panel",
            },
        },
    },
}


def _footer_source(out: str) -> str:
    lines = [ln for ln in out.splitlines() if ln.startswith("_Source: ")]
    assert len(lines) == 1, out
    return lines[0]


async def test_alphafold_footer_names_alphafold_model_not_uniprot_release() -> None:
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(
            return_value=httpx.Response(200, json=[_AF_P04637])
        )
        out = await uniprot_get_alphafold_confidence("P04637", "markdown")
    src = _footer_source(out)
    assert src.startswith("_Source: AlphaFoldDB model v6 (created 2025-08-01T00:00:00Z) • ")
    assert "UniProt" not in src
    assert "release" not in src
    assert "_Query: https://alphafold.ebi.ac.uk/api/prediction/P04637_" in out


async def test_alphafold_no_model_footer_names_alphafold() -> None:
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(return_value=httpx.Response(404, json=[]))
        out = await uniprot_get_alphafold_confidence("P04637", "markdown")
    assert _footer_source(out).startswith("_Source: AlphaFoldDB • Retrieved ")


async def test_alphafold_json_provenance_unchanged() -> None:
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(
            return_value=httpx.Response(200, json=[_AF_P04637])
        )
        md = await uniprot_get_alphafold_confidence("P04637", "markdown")
        js = await uniprot_get_alphafold_confidence("P04637", "json")
    prov = json.loads(js)["provenance"]
    assert prov["source"] == "AlphaFoldDB"
    assert prov["release"] == "v6"
    assert prov["release_date"] == "2025-08-01T00:00:00Z"
    # The hash in the Markdown footer is the same canonical hash as in JSON.
    assert f"_SHA-256: {prov['response_sha256']}_" in md


async def test_clinvar_footer_names_ncbi_clinvar() -> None:
    with respx.mock(assert_all_called=False) as router:
        router.get("https://rest.uniprot.org/uniprotkb/P04637").mock(
            return_value=httpx.Response(200, json=_ENTRY, headers=_UNIPROT_HEADERS)
        )
        router.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi").mock(
            return_value=httpx.Response(200, json=_CV_SEARCH)
        )
        router.get(f"{NCBI_EUTILS_BASE}/esummary.fcgi").mock(
            return_value=httpx.Response(200, json=_CV_SUMMARY)
        )
        out = await uniprot_resolve_clinvar("P04637", "R175H", 1, "markdown")
        js = await uniprot_resolve_clinvar("P04637", "R175H", 1, "json")
    src = _footer_source(out)
    # ClinVar provenance carries no release; only the provider name is shown.
    assert src.startswith("_Source: NCBI ClinVar (eutils) • Retrieved ")
    assert "UniProt" not in src
    assert "esummary.fcgi" in out
    prov = json.loads(js)["provenance"]
    assert prov["source"] == "NCBI ClinVar (eutils)"
    assert f"_SHA-256: {prov['response_sha256']}_" in out


async def test_uniprot_footer_unchanged() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(200, json=_ENTRY, headers=_UNIPROT_HEADERS)
        )
        out = await uniprot_get_entry("P04637", "markdown")
    src = _footer_source(out)
    assert src.startswith("_Source: UniProt release 2026_03 (")
    assert "model" not in src


def test_legacy_record_without_source_defaults_to_uniprot() -> None:
    legacy = {
        "release": "2026_02",
        "release_date": "2026-03-05",
        "retrieved_at": "2026-04-01T00:00:00Z",
        "url": "https://rest.uniprot.org/uniprotkb/P04637",
        "response_sha256": "0" * 64,
    }
    lines = _provenance_md_footer(legacy)  # type: ignore[arg-type]
    assert lines[2] == (
        "_Source: UniProt release 2026_02 (2026-03-05) • Retrieved 2026-04-01T00:00:00Z_"
    )


def test_alphafold_version_without_date() -> None:
    prov = Provenance(
        source="AlphaFoldDB",
        release="v6",
        release_date=None,
        retrieved_at="2026-10-15T00:00:00Z",
        url="https://alphafold.ebi.ac.uk/api/prediction/P04637",
        response_sha256="",
        accept_header="application/json",
    )
    lines = _provenance_md_footer(prov)
    assert lines[2] == "_Source: AlphaFoldDB model v6 • Retrieved 2026-10-15T00:00:00Z_"
    assert not any(ln.startswith("_SHA-256") for ln in lines)
