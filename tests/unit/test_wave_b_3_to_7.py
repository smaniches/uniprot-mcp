"""Tests for Wave B/3-7: UniParc, Proteomes, Citations, structured cross-DB
resolvers (PDB / AlphaFold / InterPro / ChEMBL), and the evidence-code summary.

Each tool is exercised at three layers:

1. Identifier-regex shape (where applicable).
2. Validation rejection — bad input rejected before any HTTP call.
3. Happy-path rendering — mocked UniProt response produces well-formed
   Markdown / JSON envelope including the provenance footer.
"""

from __future__ import annotations

import json

import httpx
import respx

from uniprot_mcp.client import (
    CITATION_ID_RE,
    PROTEOME_ID_RE,
    UNIPARC_ID_RE,
)
from uniprot_mcp.server import (
    uniprot_get_citation,
    uniprot_get_evidence_summary,
    uniprot_get_proteome,
    uniprot_get_uniparc,
    uniprot_resolve_alphafold,
    uniprot_resolve_chembl,
    uniprot_resolve_interpro,
    uniprot_resolve_pdb,
    uniprot_search_citations,
    uniprot_search_proteomes,
    uniprot_search_uniparc,
)

# ---------------------------------------------------------------------------
# Identifier regexes
# ---------------------------------------------------------------------------


def test_uniparc_id_regex() -> None:
    assert UNIPARC_ID_RE.match("UPI000002ED67")
    assert UNIPARC_ID_RE.match("UPI0000000000")
    for bad in ("upi0000000000", "UPI", "UPI0000000ABG", "UPI0000000000A", "P04637"):
        assert not UNIPARC_ID_RE.match(bad), f"should reject {bad!r}"


def test_proteome_id_regex() -> None:
    assert PROTEOME_ID_RE.match("UP000005640")
    assert PROTEOME_ID_RE.match("UP000000001")
    for bad in ("up000005640", "UP12345", "UP00000564000000", "5640"):
        assert not PROTEOME_ID_RE.match(bad), f"should reject {bad!r}"


def test_citation_id_regex() -> None:
    assert CITATION_ID_RE.match("12345678")
    assert CITATION_ID_RE.match("1")
    for bad in ("12345678abc", "PMID:1234", "../etc/passwd", "1234567890123"):
        assert not CITATION_ID_RE.match(bad), f"should reject {bad!r}"


# ---------------------------------------------------------------------------
# Validation rejection (no network)
# ---------------------------------------------------------------------------


async def test_get_uniparc_rejects_bad_upi_without_network() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_get_uniparc("not-a-upi", "markdown")
    assert "Input error" in out and "UPI" in out
    assert not router.calls


async def test_get_proteome_rejects_bad_upid_without_network() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_get_proteome("UP12345", "markdown")
    assert "Input error" in out and "UP" in out
    assert not router.calls


async def test_get_citation_rejects_non_numeric() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_get_citation("PMID:1234", "markdown")
    assert "Input error" in out
    assert not router.calls


async def test_resolve_pdb_rejects_bad_accession() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_resolve_pdb("not-real", "markdown")
    assert "Input error" in out
    assert not router.calls


# ---------------------------------------------------------------------------
# UniParc happy paths
# ---------------------------------------------------------------------------

_UNIPARC_FIXTURE = {
    "uniParcId": "UPI000002ED67",
    "sequence": {
        "length": 393,
        "molWeight": 43653,
        "md5": "abc123def456",
        "crc64": "AABBCCDDEEFF0011",
        "value": "MEEPQSDPSV...",
    },
    "crossReferenceCount": 47,
    "oldestCrossRefCreated": "1992-04-01",
    "mostRecentCrossRefUpdated": "2026-01-15",
    "uniProtKBAccessions": ["P04637", "Q15086"],
    "commonTaxons": [{"scientificName": "Homo sapiens"}],
}


async def test_get_uniparc_happy_path_markdown() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniparc/UPI000002ED67").mock(
            return_value=httpx.Response(
                200, json=_UNIPARC_FIXTURE, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_get_uniparc("UPI000002ED67", "markdown")
    assert "## UPI000002ED67" in out
    assert "**Length:** 393 aa" in out
    assert "md5 `abc123def456`" in out
    assert "**Cross-reference records:** 47" in out
    assert "P04637, Q15086" in out
    assert "Homo sapiens" in out
    assert "release 2026_01" in out


async def test_search_uniparc_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniparc/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "uniParcId": "UPI000002ED67",
                            "sequence": {"length": 393},
                            "crossReferenceCount": 47,
                        }
                    ]
                },
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_search_uniparc("accession:P04637")
    assert "**1 UniParc records**" in out
    assert "UPI000002ED67" in out


# ---------------------------------------------------------------------------
# Proteome happy paths
# ---------------------------------------------------------------------------

_PROTEOME_FIXTURE = {
    "id": "UP000005640",
    "description": "Homo sapiens (modern humans).",
    "proteomeType": "Reference and representative proteome",
    "superkingdom": "Eukaryota",
    "taxonomy": {"scientificName": "Homo sapiens", "taxonId": 9606},
    "proteinCount": 83526,
    "geneCount": 23128,
    "annotationScore": 5,
    "components": [{"name": "Chromosome 1"}, {"name": "Chromosome 2"}],
    "modified": "2026-01-15",
    "proteomeCompletenessReport": {"buscoReport": {"score": 99.7}},
}


async def test_get_proteome_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/proteomes/UP000005640").mock(
            return_value=httpx.Response(
                200,
                json=_PROTEOME_FIXTURE,
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_get_proteome("UP000005640", "markdown")
    assert "## UP000005640: Homo sapiens" in out
    assert "**Type:** Reference and representative proteome" in out
    assert "**Organism:** Homo sapiens (taxId 9606)" in out
    assert "**Superkingdom:** Eukaryota" in out
    assert "**Protein count:** 83526" in out
    assert "**Gene count:** 23128" in out
    assert "**BUSCO completeness:** 99.7" in out
    assert "Chromosome 1, Chromosome 2" in out


async def test_search_proteomes_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/proteomes/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": "UP000005640",
                            "taxonomy": {"scientificName": "Homo sapiens"},
                            "proteinCount": 83526,
                            "proteomeType": "Reference and representative proteome",
                        }
                    ]
                },
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_search_proteomes("organism_id:9606", size=5)
    assert "**1 proteomes**" in out
    assert "UP000005640" in out
    assert "83526 proteins" in out


# ---------------------------------------------------------------------------
# Citation happy paths
# ---------------------------------------------------------------------------

_CITATION_FIXTURE = {
    "citation": {
        "id": "7649814",
        "title": "Hereditary breast and ovarian cancer due to mutations in BRCA1 and BRCA2.",
        "authors": ["Couch FJ", "Weber BL"],
        "journal": "Hum Mutat",
        "publicationDate": "1996",
        "volume": "8",
        "firstPage": "8",
        "lastPage": "18",
        "citationCrossReferences": [{"database": "PubMed", "id": "7649814"}],
    }
}


async def test_get_citation_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/citations/7649814").mock(
            return_value=httpx.Response(
                200, json=_CITATION_FIXTURE, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_get_citation("7649814", "markdown")
    assert "## Citation 7649814" in out
    assert "Hereditary breast and ovarian cancer" in out
    assert "Couch FJ, Weber BL" in out
    assert "Hum Mutat, 1996" in out


async def test_search_citations_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/citations/search").mock(
            return_value=httpx.Response(
                200,
                json={"results": [_CITATION_FIXTURE]},
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_search_citations("BRCA1 cancer", size=3)
    assert "**1 citations**" in out
    assert "7649814" in out
    assert "Hereditary breast and ovarian cancer" in out


# ---------------------------------------------------------------------------
# Cross-DB resolver happy paths
# ---------------------------------------------------------------------------

_ENTRY_WITH_XREFS = {
    "primaryAccession": "P04637",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "uniProtKBCrossReferences": [
        {
            "database": "PDB",
            "id": "1A1U",
            "properties": [
                {"key": "Method", "value": "X-ray"},
                {"key": "Resolution", "value": "2.30 A"},
                {"key": "Chains", "value": "A=94-312"},
            ],
        },
        {
            "database": "PDB",
            "id": "2OCJ",
            "properties": [
                {"key": "Method", "value": "X-ray"},
                {"key": "Resolution", "value": "1.80 A"},
                {"key": "Chains", "value": "A/B=94-312"},
            ],
        },
        {"database": "AlphaFoldDB", "id": "P04637"},
        {
            "database": "InterPro",
            "id": "IPR011615",
            "properties": [{"key": "EntryName", "value": "p53_DNA-bd"}],
        },
        {"database": "ChEMBL", "id": "CHEMBL3712"},
    ],
}


async def _mock_entry(router):
    router.get("/uniprotkb/P04637").mock(
        return_value=httpx.Response(
            200, json=_ENTRY_WITH_XREFS, headers={"X-UniProt-Release": "2026_01"}
        )
    )


async def test_resolve_pdb_returns_structured_records() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        await _mock_entry(router)
        out = await uniprot_resolve_pdb("P04637", "markdown")
    assert "## PDB structures for P04637 (2)" in out
    assert "**1A1U**" in out and "X-ray" in out and "2.30 A" in out
    assert "**2OCJ**" in out and "1.80 A" in out


async def test_resolve_pdb_json_shape() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        await _mock_entry(router)
        out = await uniprot_resolve_pdb("P04637", "json")
    payload = json.loads(out)
    assert payload["data"]["accession"] == "P04637"
    pdbs = payload["data"]["pdb"]
    assert len(pdbs) == 2
    assert pdbs[0]["pdb_id"] == "1A1U"
    assert pdbs[0]["method"] == "X-ray"
    assert pdbs[0]["resolution"] == "2.30 A"
    assert "chains" in pdbs[0]


async def test_resolve_alphafold_returns_canonical_model() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        await _mock_entry(router)
        out = await uniprot_resolve_alphafold("P04637", "markdown")
    assert "P04637" in out
    assert "alphafold.ebi.ac.uk/entry/P04637" in out


async def test_resolve_alphafold_handles_no_match() -> None:
    """Some entries lack an AlphaFoldDB cross-reference; render gracefully."""
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P04637", "uniProtKBCrossReferences": []},
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_resolve_alphafold("P04637", "markdown")
    assert "## AlphaFold models for P04637 (0)" in out
    assert "No AlphaFold cross-reference" in out


async def test_resolve_interpro_returns_structured_signatures() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        await _mock_entry(router)
        out = await uniprot_resolve_interpro("P04637", "markdown")
    assert "## InterPro signatures for P04637 (1)" in out
    assert "IPR011615" in out
    assert "p53_DNA-bd" in out


async def test_resolve_chembl_returns_target_card_link() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        await _mock_entry(router)
        out = await uniprot_resolve_chembl("P04637", "markdown")
    assert "CHEMBL3712" in out
    assert "ebi.ac.uk/chembl/target_report_card/CHEMBL3712" in out


async def test_resolve_chembl_handles_no_target() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P04637", "uniProtKBCrossReferences": []},
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_resolve_chembl("P04637", "markdown")
    assert "No ChEMBL cross-reference" in out


# ---------------------------------------------------------------------------
# Evidence summary
# ---------------------------------------------------------------------------

_ENTRY_WITH_EVIDENCES = {
    "primaryAccession": "P04637",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "features": [
        {
            "type": "Domain",
            "evidences": [
                {"evidenceCode": "ECO:0000269", "source": "PubMed"},
                {"evidenceCode": "ECO:0000305"},
            ],
        },
        {
            "type": "Modified residue",
            "evidences": [{"evidenceCode": "ECO:0000269", "source": "PubMed"}],
        },
    ],
    "comments": [
        {
            "commentType": "FUNCTION",
            "evidences": [{"evidenceCode": "ECO:0000250"}],
        }
    ],
}


async def test_evidence_summary_groups_eco_codes_by_count() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200, json=_ENTRY_WITH_EVIDENCES, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_get_evidence_summary("P04637", "markdown")
    assert "Evidence summary: P04637 (3 distinct ECO codes)" in out
    assert "**ECO:0000269**: 2 occurrence(s)" in out  # most-common first
    assert "experimental evidence" in out
    assert "**ECO:0000250**: 1 occurrence(s)" in out
    assert "**ECO:0000305**: 1 occurrence(s)" in out


async def test_evidence_summary_json_shape() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200, json=_ENTRY_WITH_EVIDENCES, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_get_evidence_summary("P04637", "json")
    payload = json.loads(out)
    assert payload["data"]["accession"] == "P04637"
    counts = payload["data"]["evidence_counts"]
    assert counts["ECO:0000269"] == 2
    assert counts["ECO:0000250"] == 1
    assert counts["ECO:0000305"] == 1


async def test_evidence_summary_handles_no_evidences() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P04637"},
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_get_evidence_summary("P04637", "markdown")
    assert "0 distinct ECO codes" in out
    assert "No evidence annotations" in out
