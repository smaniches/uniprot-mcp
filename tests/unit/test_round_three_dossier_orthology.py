"""Tests for Round 3 (composition tools).

Two tools:

  uniprot_resolve_orthology   — group cross-refs by orthology DB
  uniprot_target_dossier       — one-call comprehensive characterisation

Both pure-Python compositions over a UniProt entry; no extra origin.
"""

from __future__ import annotations

import json

import httpx
import respx

from uniprot_mcp.server import (
    _ORTHOLOGY_DATABASES,
    _assemble_target_dossier,
    uniprot_resolve_orthology,
    uniprot_target_dossier,
)

# ---------------------------------------------------------------------------
# Orthology resolver
# ---------------------------------------------------------------------------

_ENTRY_WITH_ORTHOLOGY_XREFS = {
    "primaryAccession": "P04637",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "uniProtKBCrossReferences": [
        {"database": "KEGG", "id": "hsa:7157"},
        {"database": "OMA", "id": "GIPCAQH"},
        {"database": "OrthoDB", "id": "1067666at2759"},
        {"database": "eggNOG", "id": "KOG3068"},
        {"database": "TreeFam", "id": "TF106101"},
        {"database": "GeneTree", "id": "ENSGT00940000162033"},
        # Non-orthology xrefs that must NOT appear in the result.
        {"database": "PDB", "id": "1A1U"},
        {"database": "GO", "id": "GO:0003700"},
        {"database": "ChEMBL", "id": "CHEMBL3712"},
    ],
}


async def test_orthology_groups_known_databases() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200, json=_ENTRY_WITH_ORTHOLOGY_XREFS, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_resolve_orthology("P04637", "markdown")
    assert "Orthology: P04637 (6 database(s), 6 cross-ref(s))" in out
    # Every orthology DB rendered with its label.
    assert "KEGG" in out and "KEGG Orthology" in out
    assert "OMA" in out and "OMA Browser" in out
    assert "OrthoDB" in out
    assert "eggNOG" in out
    assert "TreeFam" in out
    assert "GeneTree" in out
    # Non-orthology cross-refs filtered out.
    assert "PDB" not in out
    assert "GO:0003700" not in out
    assert "ChEMBL" not in out or "ChEMBL targets" not in out  # the label contains ChEMBL


async def test_orthology_renders_empty_with_advice() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P12345").mock(
            return_value=httpx.Response(
                200,
                json={
                    "primaryAccession": "P12345",
                    "uniProtKBCrossReferences": [{"database": "PDB", "id": "1ABC"}],
                },
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_resolve_orthology("P12345", "markdown")
    assert "0 database(s), 0 cross-ref(s)" in out
    assert "No orthology cross-references" in out
    # Advice points at adjacent sources.
    assert "OMA / OrthoDB" in out


async def test_orthology_json_envelope() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200, json=_ENTRY_WITH_ORTHOLOGY_XREFS, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_resolve_orthology("P04637", "json")
    payload = json.loads(out)
    assert payload["data"]["accession"] == "P04637"
    grouped = payload["data"]["orthology"]
    assert "KEGG" in grouped
    assert grouped["KEGG"] == ["hsa:7157"]
    assert "PDB" not in grouped


async def test_orthology_rejects_bad_accession() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_resolve_orthology("not-real")
    assert "Input error" in out
    assert not router.calls


def test_orthology_database_set_known_terms() -> None:
    """Sanity-check that the registered orthology DB set covers the
    canonical list."""
    expected_subset = {
        "KEGG",
        "OMA",
        "OrthoDB",
        "eggNOG",
        "InParanoid",
        "TreeFam",
        "GeneTree",
    }
    assert expected_subset.issubset(_ORTHOLOGY_DATABASES)


# ---------------------------------------------------------------------------
# Target dossier
# ---------------------------------------------------------------------------

_TP53_RICH_ENTRY = {
    "primaryAccession": "P04637",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}
    },
    "genes": [{"geneName": {"value": "TP53"}}],
    "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
    "sequence": {"length": 393, "molWeight": 43653},
    "comments": [
        {
            "commentType": "FUNCTION",
            "texts": [
                {
                    "value": "Acts as a tumor suppressor in many tumor types; "
                    "induces growth arrest or apoptosis."
                }
            ],
        },
        {
            "commentType": "SUBCELLULAR LOCATION",
            "subcellularLocations": [
                {"location": {"value": "Nucleus"}},
                {"location": {"value": "Cytoplasm"}},
            ],
        },
        {
            "commentType": "DISEASE",
            "disease": {
                "diseaseId": "Li-Fraumeni syndrome 1",
                "diseaseAccession": "DI-XXX",
                "description": "An autosomal-dominant cancer-predisposition syndrome.",
                "diseaseCrossReference": {"database": "MIM", "id": "151623"},
            },
        },
    ],
    "uniProtKBCrossReferences": [
        {
            "database": "PDB",
            "id": "2OCJ",
            "properties": [
                {"key": "Method", "value": "X-ray"},
                {"key": "Resolution", "value": "1.80 A"},
            ],
        },
        {
            "database": "PDB",
            "id": "1A1U",
            "properties": [
                {"key": "Method", "value": "X-ray"},
                {"key": "Resolution", "value": "2.30 A"},
            ],
        },
        {"database": "AlphaFoldDB", "id": "P04637"},
        {"database": "InterPro", "id": "IPR011615"},
        {"database": "ChEMBL", "id": "CHEMBL3712"},
        {"database": "DrugBank", "id": "DB02123"},
        {
            "database": "GO",
            "id": "GO:0003700",
            "properties": [
                {"key": "GoTerm", "value": "F:DNA-binding transcription factor activity"}
            ],
        },
        {
            "database": "GO",
            "id": "GO:0006915",
            "properties": [{"key": "GoTerm", "value": "P:apoptotic process"}],
        },
    ],
    "features": [
        {
            "type": "Natural variant",
            "location": {"start": {"value": 175}, "end": {"value": 175}},
        },
        {
            "type": "Natural variant",
            "location": {"start": {"value": 248}, "end": {"value": 248}},
        },
        {
            "type": "Modified residue",
            "location": {"start": {"value": 15}, "end": {"value": 15}},
            "evidences": [{"evidenceCode": "ECO:0000269"}],
        },
    ],
}

_TP53_FASTA = (
    ">sp|P04637|P53_HUMAN Cellular tumor antigen p53 OS=Homo sapiens\nMEEPQSDPSVEPPLSQETFSDLWKL\n"
)


def test_assemble_target_dossier_pure_python() -> None:
    """The assembly logic is pure-data; no I/O. Verify the structured
    output covers all the headings the formatter expects."""
    dossier = _assemble_target_dossier(_TP53_RICH_ENTRY, {"molecular_weight": 43653.0})
    assert dossier["identity"]["name"] == "Cellular tumor antigen p53"
    assert dossier["identity"]["gene"] == "TP53"
    assert dossier["identity"]["organism"] == "Homo sapiens"
    assert dossier["identity"]["length"] == 393
    assert dossier["identity"]["reviewed"] == "Swiss-Prot (reviewed)"
    assert "tumor suppressor" in dossier["function"]
    assert dossier["chemistry"]["molecular_weight"] == 43653.0
    assert dossier["structure"]["pdb_count"] == 2
    # Best PDB by resolution is 2OCJ at 1.80 A (lower number = better).
    assert dossier["structure"]["best_pdb"]["id"] == "2OCJ"
    assert dossier["structure"]["alphafold_model_id"] == "P04637"
    assert dossier["structure"]["interpro_count"] == 1
    assert dossier["drug_target"]["chembl_ids"] == ["CHEMBL3712"]
    assert dossier["drug_target"]["drugbank_count"] == 1
    assert len(dossier["diseases"]) == 1
    assert dossier["diseases"][0]["mim_id"] == "151623"
    assert dossier["variants"]["count"] == 2
    assert (
        "DNA-binding transcription factor activity"
        in dossier["functional_annotations"]["go_molecular_function"]
    )
    assert "Nucleus" in dossier["functional_annotations"]["subcellular_locations"]
    assert dossier["functional_annotations"]["evidence_distinct_codes"] >= 1
    # Cross-reference summary
    assert dossier["cross_reference_summary"]["total"] == 8
    assert dossier["cross_reference_summary"]["database_count"] >= 6


async def test_target_dossier_renders_full_markdown() -> None:
    """The dossier tool issues two GETs to the same URL: one for the
    JSON entry, one for the FASTA. We use a side-effect handler that
    hands back JSON first and FASTA second."""
    json_resp = httpx.Response(200, json=_TP53_RICH_ENTRY, headers={"X-UniProt-Release": "2026_01"})
    fasta_resp = httpx.Response(200, text=_TP53_FASTA)
    seq = iter([json_resp, fasta_resp])

    def _handler(request: httpx.Request) -> httpx.Response:
        return next(seq)

    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(side_effect=_handler)
        out = await uniprot_target_dossier("P04637", "markdown")
    # All major section headings present.
    for heading in (
        "# Target dossier: P04637",
        "## Identity",
        "## Function",
        "## Sequence chemistry (derived)",
        "## Structural evidence",
        "## Drug-target context",
        "## Disease associations",
        "## Variants",
        "## Functional annotations",
        "## Cross-references",
    ):
        assert heading in out, f"missing heading: {heading}"
    # Specific values from the fixture.
    assert "TP53" in out
    assert "Homo sapiens" in out
    assert "393 aa" in out
    assert "tumor suppressor" in out
    assert "PDB structures: 2" in out
    assert "best: 2OCJ" in out
    assert "AlphaFold model: `P04637`" in out
    assert "ChEMBL targets: CHEMBL3712" in out
    assert "Li-Fraumeni syndrome 1" in out
    assert "MIM:151623" in out
    assert "Natural variants annotated: 2" in out
    assert "DNA-binding transcription factor activity" in out
    assert "Nucleus" in out


async def test_target_dossier_rejects_bad_accession() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_target_dossier("not-real")
    assert "Input error" in out
    assert not router.calls


async def test_target_dossier_json_shape() -> None:
    json_resp = httpx.Response(200, json=_TP53_RICH_ENTRY, headers={"X-UniProt-Release": "2026_01"})
    fasta_resp = httpx.Response(200, text=_TP53_FASTA)
    seq = iter([json_resp, fasta_resp])

    def _handler(request: httpx.Request) -> httpx.Response:
        return next(seq)

    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(side_effect=_handler)
        out = await uniprot_target_dossier("P04637", "json")
    payload = json.loads(out)
    assert payload["data"]["accession"] == "P04637"
    dossier = payload["data"]["dossier"]
    assert dossier["identity"]["gene"] == "TP53"
    assert dossier["structure"]["pdb_count"] == 2
    assert dossier["drug_target"]["chembl_ids"] == ["CHEMBL3712"]
