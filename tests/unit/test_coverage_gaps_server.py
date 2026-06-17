"""Targeted tests closing the remaining branch/line gaps in server.py.

Three groups:

  1. Pure module-level helpers (_assemble_target_dossier, _extract_publications,
     _format_evidence_summary, _format_verify_report, _verify_advice) — called
     directly with crafted (often deliberately malformed) inputs so every
     defensive ``isinstance`` / fall-through arc is exercised AND its observable
     outcome asserted.
  2. In-tool guards (features_at_position, lookup_variant,
     disease_associations) — exercised through the tool with a respx-mocked
     entry, asserting the rendered Markdown reflects the skip.
  3. Tool exception handlers — a single upstream 400 per still-uncovered tool
     drives the ``except Exception -> _safe_error`` path.

Arc references are to the ``--cov-branch`` ``term-missing`` report on branch
chore/coverage-100 (server.py at 94%).
"""

from __future__ import annotations

import os
import sys

import httpx
import pytest
import respx
from mcp.server.fastmcp.exceptions import ToolError

from uniprot_mcp import server
from uniprot_mcp.server import (
    PIN_RELEASE_ENV,
    _assemble_target_dossier,
    _extract_publications,
    _format_evidence_summary,
    _format_verify_report,
    _verify_advice,
    uniprot_features_at_position,
    uniprot_get_disease_associations,
    uniprot_get_evidence_summary,
    uniprot_get_processing_features,
    uniprot_get_ptms,
    uniprot_lookup_variant,
    uniprot_resolve_alphafold,
    uniprot_resolve_chembl,
    uniprot_resolve_clinvar,
    uniprot_resolve_interpro,
    uniprot_resolve_orthology,
    uniprot_search_citations,
    uniprot_search_proteomes,
    uniprot_search_uniparc,
)

_BASE = "https://rest.uniprot.org"


# ===========================================================================
# _assemble_target_dossier — defensive parsing arcs
# ===========================================================================


def test_assemble_dossier_protein_description_not_dict() -> None:
    """744->748: proteinDescription that is not a dict -> full_name ''."""
    dossier = _assemble_target_dossier({"proteinDescription": "not-a-dict"}, {})
    assert dossier["identity"]["name"] is None


def test_assemble_dossier_genes_empty_list() -> None:
    """751->755: genes empty -> gene stays None (outer guard False)."""
    dossier = _assemble_target_dossier({"genes": []}, {})
    assert dossier["identity"]["gene"] is None


def test_assemble_dossier_gene_name_not_dict() -> None:
    """753->755: genes[0] is a dict but its geneName is not -> gene None."""
    dossier = _assemble_target_dossier({"genes": [{"geneName": "flat-string"}]}, {})
    assert dossier["identity"]["gene"] is None


def test_assemble_dossier_organism_not_dict() -> None:
    """757->759: organism not a dict -> organism_name '' -> None."""
    dossier = _assemble_target_dossier({"organism": "flat-string"}, {})
    assert dossier["identity"]["organism"] is None


def test_assemble_dossier_function_comment_non_dict_and_empty_texts() -> None:
    """772->782, 773->772, 774->778, 775->774, 778->772: comments containing a
    non-dict entry, a FUNCTION comment whose texts are non-dict / value-less,
    and a non-FUNCTION comment -> no function extracted."""
    entry = {
        "comments": [
            "not-a-dict",  # 773 guard False
            {"commentType": "MISC"},  # FUNCTION check False -> 773->772
            {"commentType": "FUNCTION", "texts": ["flat", {"novalue": 1}]},  # 775 False
        ]
    }
    dossier = _assemble_target_dossier(entry, {})
    assert dossier["function"] == ""  # no FUNCTION text extracted


def test_assemble_dossier_function_extracted_when_present() -> None:
    """778->772 True side: a FUNCTION comment with a value -> function set,
    confirms the break path is reachable too."""
    entry = {
        "comments": [
            {"commentType": "FUNCTION", "texts": [{"value": "Tumor suppressor."}]},
            {"commentType": "FUNCTION", "texts": [{"value": "second ignored"}]},
        ]
    }
    dossier = _assemble_target_dossier(entry, {})
    assert dossier["function"] == "Tumor suppressor."


def test_assemble_dossier_xrefs_not_a_list() -> None:
    """783->784: uniProtKBCrossReferences not a list -> coerced to []."""
    dossier = _assemble_target_dossier({"uniProtKBCrossReferences": {"bad": 1}}, {})
    assert dossier["structure"]["pdb_count"] == 0


def test_assemble_dossier_pdb_resolution_unparseable() -> None:
    """804-805: a PDB xref whose Resolution does not parse -> skipped, no
    best_pdb chosen."""
    entry = {
        "uniProtKBCrossReferences": [
            {
                "database": "PDB",
                "id": "1ABC",
                "properties": [{"key": "Resolution", "value": "not-a-number"}],
            }
        ]
    }
    dossier = _assemble_target_dossier(entry, {})
    assert dossier["structure"]["pdb_count"] == 1
    assert dossier["structure"]["best_pdb"] == {}


def test_assemble_dossier_disease_comment_empty_disease_and_non_mim_xref() -> None:
    """827->828, 831->833: a DISEASE comment with an empty disease dict is
    skipped; another with a non-MIM cross-reference still recorded with mim
    None."""
    entry = {
        "comments": [
            {"commentType": "DISEASE", "disease": {}},  # 827->828 skip
            {
                "commentType": "DISEASE",
                "disease": {
                    "diseaseId": "Some disease",
                    "diseaseCrossReference": {"database": "MeSH", "id": "D000"},
                },
            },
        ]
    }
    dossier = _assemble_target_dossier(entry, {})
    assert len(dossier["diseases"]) == 1
    assert dossier["diseases"][0]["name"] == "Some disease"
    assert dossier["diseases"][0]["mim_id"] is None


def test_assemble_dossier_go_mf_caps_at_five() -> None:
    """851->852: more than five GO molecular-function terms -> break at 5."""
    entry = {
        "uniProtKBCrossReferences": [
            {
                "database": "GO",
                "id": f"GO:{i:07d}",
                "properties": [{"key": "GoTerm", "value": f"F:func{i}"}],
            }
            for i in range(8)
        ]
    }
    dossier = _assemble_target_dossier(entry, {})
    assert len(dossier["functional_annotations"]["go_molecular_function"]) == 5


def test_assemble_dossier_subcell_loc_non_dict_and_no_name() -> None:
    """858->... 859->858, 861->858: subcellularLocations with a non-dict entry
    and a dict with no location value -> no locations collected."""
    entry = {
        "comments": [
            {
                "commentType": "SUBCELLULAR LOCATION",
                "subcellularLocations": ["flat", {"location": {}}],
            }
        ]
    }
    dossier = _assemble_target_dossier(entry, {})
    assert dossier["functional_annotations"]["subcellular_locations"] == []


def test_assemble_dossier_eco_walk_non_dict_evidence() -> None:
    """872->871, 874->871: evidences list containing a non-dict and a dict with
    no evidenceCode -> not counted."""
    entry = {
        "features": [
            {"type": "X", "evidences": ["flat", {"noCode": 1}]},
        ]
    }
    dossier = _assemble_target_dossier(entry, {})
    assert dossier["functional_annotations"]["evidence_distinct_codes"] == 0


def test_assemble_dossier_xref_summary_non_dict_entry() -> None:
    """887->886: a cross-reference list entry that is not a dict is skipped by
    the db-count loop, so database_count reflects only the real dict entry."""
    entry = {
        "uniProtKBCrossReferences": [
            "flat-not-dict",
            {"database": "PDB", "id": "1ABC"},
        ]
    }
    dossier = _assemble_target_dossier(entry, {})
    # total counts the raw list (2); database_count only the dict entry (1).
    assert dossier["cross_reference_summary"]["total"] == 2
    assert dossier["cross_reference_summary"]["database_count"] == 1


# ===========================================================================
# _extract_publications — defensive parsing arcs (1109-1127)
# ===========================================================================


def test_extract_publications_references_not_a_list() -> None:
    """1109->1110: references is not a list -> empty result."""
    assert _extract_publications({"references": {"bad": 1}}) == []


def test_extract_publications_skips_malformed_refs_and_citations() -> None:
    """1112->1113, 1115->1116, 1121->1122: a non-dict ref, a ref whose citation
    is not a dict, and an xref entry that is not a dict are all skipped; a valid
    PubMed + DOI pair is extracted."""
    entry = {
        "references": [
            "not-a-dict",  # 1112->1113 skip
            {"citation": "flat-not-dict"},  # 1115->1116 skip
            {
                "citation": {
                    "title": "Real paper",
                    "citationCrossReferences": [
                        "flat",  # 1121->1122 skip
                        {"database": "PubMed", "id": "12345"},
                        {"database": "DOI", "id": "10.1/x"},  # 1127 elif
                    ],
                }
            },
        ]
    }
    out = _extract_publications(entry)
    assert len(out) == 1
    assert out[0]["pubmed_id"] == "12345"
    assert out[0]["doi"] == "10.1/x"


def test_extract_publications_xrefs_not_a_list() -> None:
    """1120 guard: citationCrossReferences not a list -> iterated as empty."""
    entry = {
        "references": [
            {"citation": {"title": "T", "citationCrossReferences": {"bad": 1}}},
        ]
    }
    out = _extract_publications(entry)
    assert len(out) == 1
    assert out[0]["pubmed_id"] is None


def test_extract_publications_xref_other_database_ignored() -> None:
    """1127->1120: a cross-reference whose database is neither PubMed nor DOI
    falls through both branches (loop-back) -> no pmid/doi recorded."""
    entry = {
        "references": [
            {
                "citation": {
                    "title": "T",
                    "citationCrossReferences": [{"database": "AGRICOLA", "id": "X1"}],
                }
            }
        ]
    }
    out = _extract_publications(entry)
    assert len(out) == 1
    assert out[0]["pubmed_id"] is None
    assert out[0]["doi"] is None


# ===========================================================================
# _format_evidence_summary — non-dict evidence arcs (1622->1621, 1624->1621)
# ===========================================================================


def test_format_evidence_summary_skips_non_dict_and_codeless_evidence() -> None:
    """1622->1621, 1624->1621: evidences with a non-dict entry and a dict with
    no evidenceCode -> zero distinct codes, empty-state message rendered."""
    data = {"features": [{"evidences": ["flat", {"noCode": 1}]}]}
    out = _format_evidence_summary(data, "P04637", "markdown", None)
    assert "0 distinct ECO codes" in out
    assert "_No evidence annotations on this entry._" in out


def test_format_evidence_summary_counts_real_codes_with_label() -> None:
    """Positive control: real ECO code is counted and labelled."""
    data = {"features": [{"evidences": [{"evidenceCode": "ECO:0000269"}]}]}
    out = _format_evidence_summary(data, "P04637", "markdown", None)
    assert "ECO:0000269" in out
    assert "1 occurrence(s)" in out


# ===========================================================================
# _format_verify_report — partial-report arcs (1794->1797, 1797->1803,
# 1810->1811, 1814->1816)
# ===========================================================================


def test_format_verify_report_minimal_report_omits_optional_lines() -> None:
    """1794->1797, 1797->1803, 1814->1816: a report carrying only a url (status
    defaults to '?') -> no url_resolves / release / hash lines and no advice."""
    out = _format_verify_report({"url": "https://x/entry"}, "markdown")
    assert "**Status:** ?" in out
    assert "URL resolves" not in out
    assert "Release:" not in out
    assert "Response SHA-256:" not in out
    assert "**Advice:**" not in out


def test_format_verify_report_with_error_line() -> None:
    """1810->1811: a report carrying an error -> Error line rendered."""
    out = _format_verify_report(
        {"url": "https://x", "status": "url_unreachable", "error": "ConnectError"},
        "markdown",
    )
    assert "**Error:** ConnectError" in out


def test_verify_advice_unknown_status_is_empty() -> None:
    """_verify_advice returns '' for an unknown status (the guard at 1814)."""
    assert _verify_advice("totally-unknown-status") == ""


# ===========================================================================
# In-tool guards exercised through the tool with a mocked entry
# ===========================================================================


def _entry(**extra: object) -> dict:
    base = {
        "primaryAccession": "P04637",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "genes": [{"geneName": {"value": "TP53"}}],
        "organism": {"scientificName": "Homo sapiens"},
    }
    base.update(extra)
    return base


async def test_features_at_position_skips_features_with_non_int_bounds() -> None:
    """1199->1200: a feature whose start/end are not ints is skipped; only the
    integer-bounded feature that overlaps the position is rendered."""
    entry = _entry(
        features=[
            {"type": "Region", "location": {"start": {"value": "x"}, "end": {"value": "y"}}},
            {
                "type": "Domain",
                "location": {"start": {"value": 100}, "end": {"value": 200}},
                "description": "real domain",
            },
        ]
    )
    with respx.mock(base_url=_BASE) as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=entry))
        out = await uniprot_features_at_position("P04637", 150)
    assert "real domain" in out
    assert "Region" not in out


async def test_lookup_variant_skips_non_matching_original() -> None:
    """1331->1321: a Natural variant at the right position but whose recorded
    original residue / alt does not match -> not a match (0 matches)."""
    entry = _entry(
        features=[
            {
                "type": "Natural variant",
                "location": {"start": {"value": 175}},
                "alternativeSequence": {
                    "originalSequence": "G",  # query asks for R175H -> mismatch
                    "alternativeSequences": ["A"],
                },
            }
        ]
    )
    with respx.mock(base_url=_BASE) as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=entry))
        out = await uniprot_lookup_variant("P04637", "R175H")
    assert "0 match(es)" in out


async def test_disease_associations_skips_empty_disease_and_non_id_xref() -> None:
    """1367->1368, 1371->1378: a DISEASE comment with an empty disease is
    skipped; another with a cross-reference lacking an id -> no cross_references
    recorded but the disease is still listed."""
    entry = _entry(
        comments=[
            {"commentType": "DISEASE", "disease": {}},  # 1367->1368 skip
            {
                "commentType": "DISEASE",
                "disease": {
                    "diseaseId": "Li-Fraumeni syndrome",
                    "diseaseCrossReference": {"database": "MIM"},  # no id -> 1371 False
                },
            },
        ]
    )
    with respx.mock(base_url=_BASE) as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=entry))
        out = await uniprot_get_disease_associations("P04637")
    assert "Li-Fraumeni syndrome" in out
    assert "**Cross-refs:**" not in out


async def test_resolve_orthology_skips_xref_with_empty_id() -> None:
    """683->679: an orthology-database cross-reference with an empty id is not
    appended (loop-back); a sibling with a real id is."""
    entry = _entry(
        uniProtKBCrossReferences=[
            {"database": "KEGG", "id": ""},  # empty id -> 683->679 loop-back
            {"database": "KEGG", "id": "hsa:7157"},
            {"database": "PDB", "id": "1ABC"},  # not an orthology db -> 681 False
        ]
    )
    with respx.mock(base_url=_BASE) as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=entry))
        out = await uniprot_resolve_orthology("P04637")
    assert "hsa:7157" in out
    assert "KEGG" in out


async def test_resolve_clinvar_gene_name_block_not_dict() -> None:
    """1026->1028: genes[0].geneName is a truthy non-dict -> gene stays empty,
    raising the 'no canonical gene name' input error."""
    entry = {
        "primaryAccession": "P04637",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "genes": [{"geneName": "flat-string-not-dict"}],
    }
    with respx.mock(base_url=_BASE) as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=entry))
        with pytest.raises(ToolError) as exc_info:
            await uniprot_resolve_clinvar("P04637")
    assert "no canonical gene name" in str(exc_info.value)


# ===========================================================================
# Tool exception handlers — one upstream 400 per still-uncovered tool
# ===========================================================================


@pytest.mark.parametrize(
    ("tool", "path"),
    [
        (uniprot_get_processing_features, "/uniprotkb/P04637"),
        (uniprot_get_ptms, "/uniprotkb/P04637"),
        (uniprot_get_disease_associations, "/uniprotkb/P04637"),
        (uniprot_resolve_alphafold, "/uniprotkb/P04637"),
        (uniprot_resolve_interpro, "/uniprotkb/P04637"),
        (uniprot_resolve_chembl, "/uniprotkb/P04637"),
        (uniprot_get_evidence_summary, "/uniprotkb/P04637"),
    ],
)
async def test_accession_tool_masks_upstream_error(tool, path: str) -> None:
    """Each accession-based tool's ``except Exception -> _safe_error`` arc."""
    with respx.mock(base_url=_BASE) as router:
        router.get(path).mock(return_value=httpx.Response(400))
        with pytest.raises(ToolError) as exc_info:
            await tool("P04637")
    assert str(exc_info.value).startswith("Error in ")


async def test_search_uniparc_masks_upstream_error() -> None:
    with respx.mock(base_url=_BASE) as router:
        router.get("/uniparc/search").mock(return_value=httpx.Response(400))
        with pytest.raises(ToolError) as exc_info:
            await uniprot_search_uniparc("taxonomy_id:9606")
    assert "Error in uniprot_search_uniparc" in str(exc_info.value)


async def test_search_proteomes_masks_upstream_error() -> None:
    with respx.mock(base_url=_BASE) as router:
        router.get("/proteomes/search").mock(return_value=httpx.Response(400))
        with pytest.raises(ToolError) as exc_info:
            await uniprot_search_proteomes("organism_id:9606")
    assert "Error in uniprot_search_proteomes" in str(exc_info.value)


async def test_search_citations_masks_upstream_error() -> None:
    with respx.mock(base_url=_BASE) as router:
        router.get("/citations/search").mock(return_value=httpx.Response(400))
        with pytest.raises(ToolError) as exc_info:
            await uniprot_search_citations("p53")
    assert "Error in uniprot_search_citations" in str(exc_info.value)


# ===========================================================================
# CLI --pin-release argument handling (1941->1942, 1942, 1943->1944, 1944-1948)
# ===========================================================================


def test_main_pin_release_with_value_sets_env(monkeypatch) -> None:
    """1942: --pin-release=<v> sets PIN_RELEASE_ENV then runs the server.

    main() writes os.environ directly, so we snapshot/restore the key to avoid
    leaking a pinned-release config into the autouse client-reset fixture.
    """
    ran: list[bool] = []
    monkeypatch.setattr(server.mcp, "run", lambda: ran.append(True))
    monkeypatch.setattr(sys, "argv", ["uniprot-mcp", "--pin-release=2026_02"])
    prior = os.environ.get(PIN_RELEASE_ENV)
    try:
        server.main()
        assert os.environ.get(PIN_RELEASE_ENV) == "2026_02"
        assert ran == [True]
    finally:
        if prior is None:
            os.environ.pop(PIN_RELEASE_ENV, None)
        else:
            os.environ[PIN_RELEASE_ENV] = prior


def test_main_pin_release_without_value_exits_2(monkeypatch, capsys) -> None:
    """1944-1948: bare --pin-release errors to stderr and exits with code 2."""
    monkeypatch.setattr(sys, "argv", ["uniprot-mcp", "--pin-release"])
    with pytest.raises(SystemExit) as exc_info:
        server.main()
    assert exc_info.value.code == 2
    assert "--pin-release requires a value" in capsys.readouterr().err
