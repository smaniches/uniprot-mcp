"""Tests for Round 2 (AlphaFold pLDDT confidence + per-entry publications).

AlphaFold confidence is a **cross-origin** call to ``alphafold.ebi.ac.uk``;
publications is a pure-Python composition over the entry's ``references``
block. Both are exercised against ``respx``-mocked HTTP for offline CI.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from mcp.server.fastmcp.exceptions import ToolError

from uniprot_mcp.client import ALPHAFOLD_API_BASE
from uniprot_mcp.formatters import _plddt_band, fmt_alphafold_confidence
from uniprot_mcp.server import (
    _extract_publications,
    uniprot_get_alphafold_confidence,
    uniprot_get_publications,
)

# ---------------------------------------------------------------------------
# AlphaFold pLDDT — cross-origin
# ---------------------------------------------------------------------------

_ALPHAFOLD_FIXTURE = [
    {
        "entryId": "AF-P04637-F1",
        "uniprotAccession": "P04637",
        "uniprotEnd": 393,
        "latestVersion": 6,
        "modelCreatedDate": "2024-09-01",
        "globalMetricValue": 76.4,
        "fractionPlddtVeryHigh": 0.32,
        "fractionPlddtConfident": 0.40,
        "fractionPlddtLow": 0.20,
        "fractionPlddtVeryLow": 0.08,
        "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v6.cif",
        "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v6.pdb",
        "paeImageUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-predicted_aligned_error_v6.png",
        "gene": "TP53",
        "organismScientificName": "Homo sapiens",
    }
]


async def test_alphafold_confidence_rejects_bad_accession() -> None:
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router, pytest.raises(ToolError) as exc_info:
        await uniprot_get_alphafold_confidence("not-real")
    assert "Input error" in str(exc_info.value)
    assert not router.calls


async def test_alphafold_confidence_happy_path_markdown() -> None:
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(
            return_value=httpx.Response(200, json=_ALPHAFOLD_FIXTURE)
        )
        out = await uniprot_get_alphafold_confidence("P04637", "markdown")
    assert "AlphaFold confidence — AF-P04637-F1" in out
    assert "TP53" in out
    assert "Homo sapiens" in out
    assert "Residues modelled:** 1-393" in out
    assert "Model version:** v6" in out
    assert "Global pLDDT (mean):** 76.4" in out
    assert "confident" in out
    # Bands rendered with percentages.
    assert "32.0%" in out
    assert "40.0%" in out
    assert "20.0%" in out
    assert " 8.0%" in out


async def test_alphafold_confidence_json_envelope() -> None:
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(
            return_value=httpx.Response(200, json=_ALPHAFOLD_FIXTURE)
        )
        out = await uniprot_get_alphafold_confidence("P04637", "json")
    payload = json.loads(out)
    assert payload["data"]["accession"] == "P04637"
    assert payload["data"]["alphafold"]["entryId"] == "AF-P04637-F1"
    assert payload["provenance"]["source"] == "AlphaFoldDB"
    assert payload["provenance"]["release"] == "v6"


async def test_alphafold_confidence_handles_missing_model() -> None:
    """Some accessions have no AlphaFold prediction; the API returns ``[]``.
    The tool must render this as a recognisable empty result, not crash."""
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P99999").mock(return_value=httpx.Response(200, json=[]))
        out = await uniprot_get_alphafold_confidence("P99999", "markdown")
    assert "## AlphaFold confidence: P99999" in out
    assert "No AlphaFold model" in out


def test_plddt_band_thresholds() -> None:
    """Band edges per AlphaFold-DB FAQ: 90, 70, 50."""
    assert _plddt_band(95.0) == "very high"
    assert _plddt_band(90.0) == "very high"
    assert _plddt_band(89.99) == "confident"
    assert _plddt_band(70.0) == "confident"
    assert _plddt_band(69.99) == "low"
    assert _plddt_band(50.0) == "low"
    assert _plddt_band(49.99) == "very low"
    assert _plddt_band(0.0) == "very low"


def test_fmt_alphafold_confidence_minimal_record() -> None:
    """A record with only the entryId still renders without crashing."""
    out = fmt_alphafold_confidence({"entryId": "AF-X-F1"}, "X", "markdown")
    assert "AlphaFold confidence — AF-X-F1" in out


# ---------------------------------------------------------------------------
# Post-2026-06-25 AlphaFold DB metadata contract and protein identity
# ---------------------------------------------------------------------------


async def test_alphafold_current_schema_model_id_and_coordinates() -> None:
    """New-only fields must work when the legacy keys disappear."""
    model = {
        "modelEntityId": "AF-P04637-F2",
        "uniprotAccession": "P04637",
        "sequenceStart": 201,
        "sequenceEnd": 393,
        "latestVersion": 6,
        "globalMetricValue": 85.0,
    }
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(return_value=httpx.Response(200, json=[model]))
        markdown = await uniprot_get_alphafold_confidence("P04637", "markdown")
    assert "AlphaFold confidence — AF-P04637-F2" in markdown
    assert "Residues modelled:** 201-393" in markdown
    assert "not per-residue confidence" in markdown


async def test_alphafold_does_not_conflate_canonical_and_isoform_models() -> None:
    """The live TP53 endpoint returns canonical and isoform predictions."""
    isoform = {
        "modelEntityId": "AF-P04637-2-F1",
        "uniprotAccession": "P04637-2",
        "latestVersion": 99,
    }
    canonical = {
        "modelEntityId": "AF-P04637-F1",
        "uniprotAccession": "P04637",
        "sequenceStart": 1,
        "sequenceEnd": 393,
        "latestVersion": 6,
    }
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(
            return_value=httpx.Response(200, json=[isoform, canonical])
        )
        payload = json.loads(await uniprot_get_alphafold_confidence("P04637", "json"))
    assert payload["data"]["alphafold"]["modelEntityId"] == "AF-P04637-F1"
    assert payload["provenance"]["release"] == "v6"
    assert "additionalModelSummaries" not in payload["data"]["alphafold"]


async def test_alphafold_multiple_fragments_of_same_accession() -> None:
    """Do not silently discard same-accession model fragments."""
    canonical = {
        "modelEntityId": "AF-P04637-F1",
        "uniprotAccession": "P04637",
        "sequenceStart": 1,
        "sequenceEnd": 200,
        "latestVersion": 6,
    }
    second = {
        "modelEntityId": "AF-P04637-F2",
        "uniprotAccession": "P04637",
        "sequenceStart": 151,
        "sequenceEnd": 393,
        "latestVersion": 6,
    }
    legacy = {
        "entryId": "AF-P04637-F3",
        "uniprotAccession": "P04637",
        "uniprotStart": 350,
        "uniprotEnd": 393,
    }
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(
            return_value=httpx.Response(
                200, json=[canonical, second, legacy, {"uniprotAccession": "P04637-3"}]
            )
        )
        payload = json.loads(await uniprot_get_alphafold_confidence("P04637", "json"))
    extras = payload["data"]["alphafold"]["additionalModelSummaries"]
    assert len(extras) == 2
    assert extras[0]["modelEntityId"] == "AF-P04637-F2"
    assert extras[0]["sequenceStart"] == 151
    assert extras[1]["modelEntityId"] == "AF-P04637-F3"
    assert extras[1]["sequenceStart"] == 350

    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(
            return_value=httpx.Response(200, json=[canonical, second, legacy])
        )
        markdown = await uniprot_get_alphafold_confidence("P04637", "markdown")
    assert "Additional predictions for this accession:** 2" in markdown
    assert "AF-P04637-F2 (residues 151-393)" in markdown
    assert "AF-P04637-F3 (residues 350-393)" in markdown


async def test_alphafold_rejects_prediction_for_wrong_accession() -> None:
    """A plausible-looking model for a different isoform is not evidence."""
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(
            return_value=httpx.Response(
                200, json=[{"modelEntityId": "AF-P04637-2-F1", "uniprotAccession": "P04637-2"}]
            )
        )
        with pytest.raises(ToolError) as exc_info:
            await uniprot_get_alphafold_confidence("P04637", "markdown")
    assert "upstream request failed" in str(exc_info.value)
    assert "P04637-2" not in str(exc_info.value)


@pytest.mark.parametrize("bad_payload", [{"modelEntityId": "bad"}, ["not-an-object"]])
async def test_alphafold_rejects_invalid_upstream_payload(bad_payload: object) -> None:
    with respx.mock(base_url=ALPHAFOLD_API_BASE) as router:
        router.get("/api/prediction/P04637").mock(
            return_value=httpx.Response(200, json=bad_payload)
        )
        with pytest.raises(ToolError) as exc_info:
            await uniprot_get_alphafold_confidence("P04637")
    assert "upstream request failed" in str(exc_info.value)


def test_alphafold_legacy_fragment_start_is_retained() -> None:
    legacy = {"entryId": "AF-LEGACY-F2", "uniprotStart": 101, "uniprotEnd": 200}
    markdown = fmt_alphafold_confidence(legacy, "P04637")
    assert "AlphaFold confidence — AF-LEGACY-F2" in markdown
    assert "Residues modelled:** 101-200" in markdown


def test_alphafold_additional_prediction_with_missing_metadata() -> None:
    record = {"entryId": "AF-OLD-F1", "additionalModelSummaries": [{"modelEntityId": None}]}
    markdown = fmt_alphafold_confidence(record, "P04637")
    assert "- unknown" in markdown


# ---------------------------------------------------------------------------
# Per-entry publications — pure Python over the entry's references field
# ---------------------------------------------------------------------------

_TP53_ENTRY_WITH_REFERENCES = {
    "primaryAccession": "P04637",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "references": [
        {
            "referencePositions": ["NUCLEOTIDE SEQUENCE [MRNA]", "TISSUE=Mammary tumor"],
            "citation": {
                "id": "CI-XXXX",
                "citationCrossReferences": [
                    {"database": "PubMed", "id": "2922050"},
                    {"database": "DOI", "id": "10.1126/science.2922050"},
                ],
                "title": "Different p53 mutations in human tumours.",
                "authors": ["Hollstein M.", "Sidransky D.", "Vogelstein B.", "Harris C.C."],
                "journal": "Science",
                "publicationDate": "1989",
            },
        },
        {
            "referencePositions": ["INVOLVEMENT IN LI-FRAUMENI SYNDROME"],
            "citation": {
                "citationCrossReferences": [{"database": "PubMed", "id": "1978757"}],
                "title": "Germ line p53 mutations in a family syndrome.",
                "authors": ["Malkin D.", "Friend S.H."],
                "journal": "Science",
                "publicationDate": "1990",
            },
        },
    ],
}


def test_extract_publications_parses_pubmed_doi_and_positions() -> None:
    pubs = _extract_publications(_TP53_ENTRY_WITH_REFERENCES)
    assert len(pubs) == 2
    p0 = pubs[0]
    assert p0["pubmed_id"] == "2922050"
    assert p0["doi"] == "10.1126/science.2922050"
    assert p0["title"].startswith("Different p53")
    assert p0["year"] == "1989"
    assert "Hollstein M." in p0["authors"]
    assert "INVOLVEMENT" not in p0["reference_positions"][0]  # exact strings
    assert p0["reference_positions"][0] == "NUCLEOTIDE SEQUENCE [MRNA]"


def test_extract_publications_handles_missing_xrefs() -> None:
    """Some references have no PubMed / DOI cross-references — render
    them with ``(no identifier)`` rather than crashing."""
    entry = {"references": [{"citation": {"title": "Untitled", "authors": ["Anon"]}}]}
    pubs = _extract_publications(entry)
    assert len(pubs) == 1
    assert pubs[0]["pubmed_id"] is None
    assert pubs[0]["doi"] is None


def test_extract_publications_empty_when_no_references() -> None:
    assert _extract_publications({"primaryAccession": "P00000"}) == []


async def test_get_publications_rejects_bad_accession() -> None:
    with (
        respx.mock(base_url="https://rest.uniprot.org") as router,
        pytest.raises(ToolError) as exc_info,
    ):
        await uniprot_get_publications("not-real")
    assert "Input error" in str(exc_info.value)
    assert not router.calls


async def test_get_publications_happy_path_markdown() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json=_TP53_ENTRY_WITH_REFERENCES,
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_get_publications("P04637", "markdown")
    assert "Publications cited by P04637 (2 reference(s))" in out
    assert "PMID:2922050" in out
    assert "doi:10.1126/science.2922050" in out
    assert "Different p53" in out
    assert "Hollstein M., Sidransky D., Vogelstein B., Harris C.C." in out
    assert "Cited for:" in out
    assert "INVOLVEMENT IN LI-FRAUMENI SYNDROME" in out


async def test_get_publications_renders_empty() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P00000").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P00000"},
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_get_publications("P00000", "markdown")
    assert "0 reference(s)" in out
    assert "No publications listed" in out


async def test_get_publications_json_envelope() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json=_TP53_ENTRY_WITH_REFERENCES,
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_get_publications("P04637", "json")
    payload = json.loads(out)
    assert payload["data"]["accession"] == "P04637"
    pubs = payload["data"]["publications"]
    assert len(pubs) == 2
    assert pubs[0]["pubmed_id"] == "2922050"
