"""Tests for Round 1 clinical-bioinformatics tools.

Four tools added to close the most-asked clinical / wet-lab questions
that pure UniProt REST cannot answer on its own:

  uniprot_compute_properties        — derived sequence chemistry
  uniprot_features_at_position      — what is at residue N?
  uniprot_lookup_variant            — is this HGVS change in UniProt?
  uniprot_get_disease_associations  — which diseases is this implicated in?

All four are pure-Python compositions over existing client methods —
no new third-party origin, no expansion of the threat model.
"""

from __future__ import annotations

import json
import math

import httpx
import pytest
import respx

from uniprot_mcp.proteinchem import (
    aromaticity,
    compute_protein_properties,
    extinction_coefficient_280nm,
    gravy_index,
    isoelectric_point,
    molecular_weight,
    net_charge_at_pH,
)
from uniprot_mcp.server import (
    _InputError,
    _parse_variant_change,
    uniprot_compute_properties,
    uniprot_features_at_position,
    uniprot_get_disease_associations,
    uniprot_lookup_variant,
)

# ---------------------------------------------------------------------------
# proteinchem — pure-math sanity
# ---------------------------------------------------------------------------


def test_glycine_monomer_has_known_residue_mass() -> None:
    """Single glycine: residue (57.0519) + water (18.01528) = 75.06718 Da
    rounded to 4 dp = 75.0672. Tight tolerance kills _RESIDUE_MASS["G"]
    or _WATER constant mutations (any single-digit flip shifts MW by
    >= 1e-4)."""
    p = compute_protein_properties("G")
    assert math.isclose(p["molecular_weight"], 75.0672, abs_tol=1e-6)
    assert p["length"] == 1


def test_di_alanine_has_known_mass() -> None:
    """2 * 71.0788 + 18.01528 = 160.17288 → 160.1729 (4 dp).
    Tight tolerance kills _RESIDUE_MASS["A"] mutations."""
    p = compute_protein_properties("AA")
    assert math.isclose(p["molecular_weight"], 160.1729, abs_tol=1e-6)


def test_aromaticity_is_fyw_fraction() -> None:
    p = compute_protein_properties("AAFFFAAA")  # 3 F in 8 residues
    assert math.isclose(p["aromaticity"], 3 / 8, abs_tol=1e-9)


def test_extinction_coefficient_pace_formula() -> None:
    """Pace 1995: ε = 1490·#Trp + 5500·#Tyr (reduced cysteines)."""
    # 5 W + 3 Y = 1490*5 + 5500*3 = 7450 + 16500 = 23950
    p = compute_protein_properties("WWWWWYYYAAAA")
    assert p["extinction_coefficient_280nm"] == 23950


def test_gravy_for_pure_isoleucine() -> None:
    """KD value for I is +4.5; pure-I sequence GRAVY = +4.5.
    Tight tolerance kills _KYTE_DOOLITTLE["I"] mutations."""
    p = compute_protein_properties("IIIII")
    assert math.isclose(p["gravy"], 4.5, abs_tol=1e-6)


def test_gravy_for_pure_arginine_is_most_hydrophilic() -> None:
    """KD value for R is -4.5; the lowest possible GRAVY for any
    homopolymer. Tight tolerance kills _KYTE_DOOLITTLE["R"] mutations."""
    p = compute_protein_properties("RRRRR")
    assert math.isclose(p["gravy"], -4.5, abs_tol=1e-6)


def test_pi_is_basic_for_arginine_rich_protein() -> None:
    """A heavily basic (Arg-rich) protein must have a basic pI > 7."""
    p = compute_protein_properties("RRRRRRRR")
    assert p["theoretical_pi"] > 10.0


def test_pi_is_acidic_for_aspartate_rich_protein() -> None:
    """A heavily acidic protein must have an acidic pI < 7."""
    p = compute_protein_properties("DDDDDDDDDD")
    assert p["theoretical_pi"] < 5.0


def test_net_charge_at_pH7_signs_match_expectation() -> None:
    """Arg-rich at pH 7 → positive; Glu-rich at pH 7 → negative."""
    arg_charge = net_charge_at_pH({"R": 5}, 7.0)
    glu_charge = net_charge_at_pH({"E": 5}, 7.0)
    assert arg_charge > 0
    assert glu_charge < 0


def test_pi_is_zero_for_empty_sequence() -> None:
    """Empty sequence: defined-but-undefined behaviour. Library returns
    0.0 length and pI rather than raising — caller can detect."""
    p = compute_protein_properties("")
    assert p["length"] == 0
    assert p["theoretical_pi"] == 0.0


def test_unknown_letters_go_into_other_bucket() -> None:
    """X / B / Z / U / O / gaps are not standard amino acids — count
    them under 'other' so the user can detect a non-canonical input."""
    p = compute_protein_properties("AAAXBZ-")
    assert p["amino_acid_counts"]["A"] == 3
    assert p["amino_acid_counts"]["other"] == 3
    assert p["length"] == 3  # length excludes 'other'


def test_helper_functions_work_independently() -> None:
    counts = {"A": 2, "F": 1, "Y": 1, "W": 1, "K": 1, "D": 1}
    assert molecular_weight(counts) > 0
    assert isinstance(gravy_index(counts, sum(counts.values())), float)
    assert 0 <= aromaticity(counts, sum(counts.values())) <= 1
    assert net_charge_at_pH(counts, 1.0) > 0  # very acidic → all amines protonated → positive
    assert net_charge_at_pH(counts, 13.0) < 0  # very basic → all carboxyls deprotonated → negative
    assert extinction_coefficient_280nm(counts) > 0
    pi = isoelectric_point(counts)
    assert 0.0 <= pi <= 14.0


# ---------------------------------------------------------------------------
# uniprot_compute_properties — server tool wiring
# ---------------------------------------------------------------------------


async def test_compute_properties_rejects_bad_accession() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_compute_properties("not-real")
    assert "Input error" in out
    assert not router.calls


async def test_compute_properties_happy_path_against_mocked_fasta() -> None:
    fasta = ">sp|P04637|P53_HUMAN\nMEEPQSDPSV\n"
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                text=fasta,
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_compute_properties("P04637", "markdown")
    assert "## Sequence properties: P04637" in out
    assert "**Length:** 10 residues" in out
    assert "Molecular weight" in out
    assert "Theoretical pI" in out
    assert "GRAVY" in out
    assert "release 2026_01" in out


async def test_compute_properties_json_envelope() -> None:
    fasta = ">sp|P04637|P53_HUMAN\nMEEPQSDPSV\n"
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                text=fasta,
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_compute_properties("P04637", "json")
    payload = json.loads(out)
    assert payload["data"]["accession"] == "P04637"
    props = payload["data"]["properties"]
    assert props["length"] == 10
    assert "molecular_weight" in props
    assert "theoretical_pi" in props


# ---------------------------------------------------------------------------
# uniprot_features_at_position — server tool wiring
# ---------------------------------------------------------------------------


_TP53_ENTRY_WITH_FEATURES = {
    "primaryAccession": "P04637",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "features": [
        {
            "type": "Chain",
            "description": "Cellular tumor antigen p53",
            "location": {"start": {"value": 1}, "end": {"value": 393}},
        },
        {
            "type": "DNA binding",
            "description": "DNA-binding domain",
            "location": {"start": {"value": 102}, "end": {"value": 292}},
        },
        {
            "type": "Modified residue",
            "description": "Phosphoserine",
            "location": {"start": {"value": 175}, "end": {"value": 175}},
        },
        {
            "type": "Natural variant",
            "description": "in a sporadic cancer; loss of DNA binding",
            "location": {"start": {"value": 175}, "end": {"value": 175}},
            "alternativeSequence": {
                "originalSequence": "R",
                "alternativeSequences": ["H"],
            },
        },
    ],
}


async def test_features_at_position_finds_overlapping_features() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200, json=_TP53_ENTRY_WITH_FEATURES, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_features_at_position("P04637", 175, "markdown")
    # At position 175: Chain (1-393), DNA binding (102-292), Modified residue (175),
    # Natural variant (175) — four features.
    assert "Features at residue 175 of P04637 (4 feature(s))" in out
    assert "Chain" in out
    assert "DNA binding" in out
    assert "Modified residue" in out and "Phosphoserine" in out
    assert "Natural variant" in out
    assert "R → H" in out  # alternativeSequence rendering


async def test_features_at_position_finds_no_features_outside_chain() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200, json=_TP53_ENTRY_WITH_FEATURES, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_features_at_position("P04637", 500, "markdown")
    # Position 500 is outside the protein (length 393); only Chain (1-393)
    # would not match. 0 features.
    assert "0 feature(s)" in out
    assert "No annotated features overlap position 500" in out


async def test_features_at_position_rejects_negative_position() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_features_at_position("P04637", -5, "markdown")
    assert "Input error" in out
    assert not router.calls


async def test_features_at_position_rejects_oversize_position() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_features_at_position("P04637", 999_999, "markdown")
    assert "Input error" in out
    assert not router.calls


# ---------------------------------------------------------------------------
# uniprot_lookup_variant — HGVS-style change parsing + matching
# ---------------------------------------------------------------------------


def test_parse_variant_change_accepts_canonical() -> None:
    assert _parse_variant_change("R175H") == ("R", 175, "H")
    assert _parse_variant_change("V600E") == ("V", 600, "E")
    assert _parse_variant_change("R248*") == ("R", 248, "*")  # nonsense / stop


def test_parse_variant_change_rejects_non_canonical() -> None:
    for bad in ("p.R175H", "R175del", "r175h", "175H", "RH175", "R0H", "R-5H"):
        with pytest.raises(_InputError):
            _parse_variant_change(bad)


async def test_lookup_variant_finds_match() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200, json=_TP53_ENTRY_WITH_FEATURES, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_lookup_variant("P04637", "R175H", "markdown")
    assert "1 match(es)" in out
    assert "R175H" in out
    assert "loss of DNA binding" in out


async def test_lookup_variant_finds_no_match_for_unknown_change() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200, json=_TP53_ENTRY_WITH_FEATURES, headers={"X-UniProt-Release": "2026_01"}
            )
        )
        out = await uniprot_lookup_variant("P04637", "A1V", "markdown")
    assert "0 match(es)" in out
    assert "ClinVar" in out  # advice points at clinical-grade alternatives


async def test_lookup_variant_rejects_bad_change() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        out = await uniprot_lookup_variant("P04637", "p.R175H", "markdown")
    assert "Input error" in out
    assert not router.calls


# ---------------------------------------------------------------------------
# uniprot_get_disease_associations
# ---------------------------------------------------------------------------


_BRCA1_ENTRY_WITH_DISEASES = {
    "primaryAccession": "P38398",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "comments": [
        {
            "commentType": "DISEASE",
            "disease": {
                "diseaseId": "Breast cancer",
                "diseaseAccession": "DI-00255",
                "acronym": "BC",
                "description": "A common cancer of the breast tissue.",
                "diseaseCrossReference": {"database": "MIM", "id": "114480"},
            },
            "note": {"texts": [{"value": "BRCA1 germline mutations confer high lifetime risk."}]},
        },
        {
            "commentType": "FUNCTION",
            "texts": [{"value": "DNA-damage repair role."}],
        },
        {
            "commentType": "DISEASE",
            "disease": {
                "diseaseId": "Pancreatic cancer 4",
                "diseaseAccession": "DI-04200",
                "description": "A malignant neoplasm of the pancreas.",
                "diseaseCrossReference": {"database": "MIM", "id": "614320"},
            },
        },
    ],
}


async def test_disease_associations_extracts_structured_records() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P38398").mock(
            return_value=httpx.Response(
                200,
                json=_BRCA1_ENTRY_WITH_DISEASES,
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_get_disease_associations("P38398", "markdown")
    assert "Disease associations: P38398 (2 record(s))" in out
    assert "Breast cancer" in out and "BC" in out and "DI-00255" in out
    assert "MIM:114480" in out
    assert "Pancreatic cancer 4" in out and "MIM:614320" in out


async def test_disease_associations_renders_empty() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P12345").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P12345", "comments": []},
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_get_disease_associations("P12345", "markdown")
    assert "0 record(s)" in out
    assert "No DISEASE-type annotations" in out
    assert "Open Targets" in out  # advice points at adjacent sources


async def test_disease_associations_json_envelope() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P38398").mock(
            return_value=httpx.Response(
                200,
                json=_BRCA1_ENTRY_WITH_DISEASES,
                headers={"X-UniProt-Release": "2026_01"},
            )
        )
        out = await uniprot_get_disease_associations("P38398", "json")
    payload = json.loads(out)
    assert payload["data"]["accession"] == "P38398"
    assert len(payload["data"]["diseases"]) == 2
    assert payload["data"]["diseases"][0]["name"] == "Breast cancer"
    assert payload["data"]["diseases"][0]["cross_references"][0]["id"] == "114480"
