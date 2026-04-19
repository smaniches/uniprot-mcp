"""Happy-path coverage for every @mcp.tool wrapper.

Each tool is exercised end-to-end with a respx-mocked UniProt API.
Goal: ensure every tool's success branch is covered, not just the
input-validation rejection path.
"""
from __future__ import annotations

import httpx
import respx

from uniprot_mcp.server import (
    uniprot_batch_entries,
    uniprot_get_cross_refs,
    uniprot_get_entry,
    uniprot_get_features,
    uniprot_get_go_terms,
    uniprot_get_sequence,
    uniprot_get_variants,
    uniprot_id_mapping,
    uniprot_search,
    uniprot_taxonomy_search,
)

_MIN_ENTRY: dict = {
    "primaryAccession": "P04637",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}
    },
    "genes": [{"geneName": {"value": "TP53"}}],
    "organism": {"scientificName": "Homo sapiens"},
    "sequence": {"length": 393, "molWeight": 43653},
    "comments": [],
    "features": [
        {
            "type": "Domain",
            "description": "DNA-binding",
            "location": {"start": {"value": 102}, "end": {"value": 292}},
        },
        {
            "type": "Natural variant",
            "description": "in a sporadic cancer",
            "location": {"start": {"value": 175}, "end": {"value": 175}},
            "alternativeSequence": {"originalSequence": "R", "alternativeSequences": ["H"]},
        },
    ],
    "uniProtKBCrossReferences": [
        {"database": "PDB", "id": "1A1U"},
        {
            "database": "GO",
            "id": "GO:0003700",
            "properties": [
                {"key": "GoTerm", "value": "F:DNA-binding transcription factor activity"},
                {"key": "GoEvidenceType", "value": "IDA:UniProtKB"},
            ],
        },
    ],
}


async def test_get_entry_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=_MIN_ENTRY))
        out = await uniprot_get_entry("P04637", "markdown")
    assert "P04637" in out and "TP53" in out


async def test_get_entry_json_format() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=_MIN_ENTRY))
        out = await uniprot_get_entry("P04637", "json")
    assert '"primaryAccession": "P04637"' in out


async def test_get_sequence_happy_path() -> None:
    fasta = ">sp|P04637|P53_HUMAN\nMEEPQSD\n"
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, text=fasta))
        out = await uniprot_get_sequence("P04637")
    assert out.startswith(">sp|P04637")


async def test_get_features_with_filter() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=_MIN_ENTRY))
        out = await uniprot_get_features("P04637", "Domain", "markdown")
    assert "Domain" in out


async def test_get_variants_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=_MIN_ENTRY))
        out = await uniprot_get_variants("P04637", "markdown")
    assert "Variants" in out


async def test_get_go_terms_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=_MIN_ENTRY))
        out = await uniprot_get_go_terms("P04637", "F", "markdown")
    assert "GO" in out


async def test_get_cross_refs_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=_MIN_ENTRY))
        out = await uniprot_get_cross_refs("P04637", "PDB", "markdown")
    assert "PDB" in out


async def test_search_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": [_MIN_ENTRY]})
        )
        out = await uniprot_search("p53", size=5, reviewed_only=True)
    assert "results" in out


async def test_batch_entries_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": [_MIN_ENTRY]})
        )
        out = await uniprot_batch_entries("P04637,P38398", "markdown")
    assert "results" in out or "P04637" in out


async def test_id_mapping_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.post("/idmapping/run").mock(return_value=httpx.Response(200, json={"jobId": "J1"}))
        router.get("/idmapping/status/J1").mock(
            return_value=httpx.Response(
                200,
                json={"results": [{"from": "BRCA1", "to": {"primaryAccession": "P38398"}}]},
            )
        )
        out = await uniprot_id_mapping("BRCA1", "Gene_Name", "UniProtKB", "markdown")
    assert "P38398" in out


async def test_taxonomy_search_happy_path() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/taxonomy/search").mock(
            return_value=httpx.Response(
                200,
                json={"results": [{"taxonId": 9606, "scientificName": "Homo sapiens", "rank": "species"}]},
            )
        )
        out = await uniprot_taxonomy_search("Homo sapiens", 3, "markdown")
    assert "9606" in out or "Homo" in out
