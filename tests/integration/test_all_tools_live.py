"""Live UniProt REST API smoke tests for every MCP tool.

Marked `integration` — skipped unless `pytest --integration` is passed.
These are the nightly drift detectors.
"""

from __future__ import annotations

import pytest

from uniprot_mcp.client import UniProtClient

pytestmark = pytest.mark.integration


@pytest.fixture
async def client():
    c = UniProtClient()
    yield c
    await c.close()


async def test_get_entry_p53(client: UniProtClient) -> None:
    data = await client.get_entry("P04637")
    assert data["primaryAccession"] == "P04637"
    assert data["genes"][0]["geneName"]["value"] == "TP53"


async def test_search_brca1(client: UniProtClient) -> None:
    data = await client.search("(gene:BRCA1) AND (organism_id:9606)", size=1)
    assert data["results"]
    assert data["results"][0]["primaryAccession"] == "P38398"


async def test_fasta_roundtrip(client: UniProtClient) -> None:
    fasta = await client.get_fasta("P38398")
    assert fasta.startswith(">sp|P38398|BRCA1_HUMAN")
    assert "MDLSALRVEEVQNVINAMQKILECPICLELIKEPVSTKCDHIFCKFCMLKLLNQKKGPSQ" in fasta


async def test_batch_mixed_valid_invalid(client: UniProtClient) -> None:
    """The bug that motivated this whole suite."""
    out = await client.batch_entries(["P04637", "INVALIDXYZ", "P38398"])
    assert {r["primaryAccession"] for r in out["results"]} == {"P04637", "P38398"}
    assert out["invalid"] == ["INVALIDXYZ"]


async def test_taxonomy_search_human(client: UniProtClient) -> None:
    data = await client.taxonomy_search("Homo sapiens", size=3)
    ids = {r["taxonId"] for r in data["results"]}
    assert 9606 in ids


async def test_id_mapping_gene_to_uniprot(client: UniProtClient) -> None:
    job = await client.id_mapping_submit("Gene_Name", "UniProtKB", ["BRCA1"])
    data = await client.id_mapping_results(job)
    assert data.get("results"), "expected at least one mapping"
