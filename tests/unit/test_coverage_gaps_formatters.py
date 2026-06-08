"""Targeted tests closing the remaining branch/line gaps in formatters.py.

Every formatter here is fed a richly-populated input (and, where the gap is
a JSON-output or provenance-footer arc, the matching ``fmt="json"`` /
``provenance=`` call) so that the optional Markdown sections and the JSON
serialization paths are actually exercised. Assertions check the rendered
content, not just that the call returned a string.

Arc references are to the ``--cov-branch`` ``term-missing`` report taken on
branch chore/coverage-100 (formatters.py at 90%).
"""

from __future__ import annotations

from uniprot_mcp.client import Provenance
from uniprot_mcp.formatters import (
    _kw_id,
    _provenance_fasta_header,
    _provenance_md_footer,
    _uniref_representative,
    fmt_alphafold,
    fmt_alphafold_confidence,
    fmt_chembl,
    fmt_citation,
    fmt_citation_search,
    fmt_clinvar,
    fmt_disease_associations,
    fmt_features_at_position,
    fmt_interpro,
    fmt_keyword,
    fmt_keyword_search,
    fmt_orthology,
    fmt_pdb,
    fmt_properties,
    fmt_proteome,
    fmt_proteome_search,
    fmt_publications,
    fmt_subcellular_location,
    fmt_subcellular_location_search,
    fmt_target_dossier,
    fmt_uniparc,
    fmt_uniparc_search,
    fmt_uniref,
    fmt_uniref_search,
    fmt_variant_lookup,
)

# A provenance with a SHA, full release info.
_PROV: Provenance = {
    "source": "UniProt",
    "release": "2026_02",
    "release_date": "2026-03-05",
    "retrieved_at": "2026-04-24T12:00:00Z",
    "url": "https://rest.uniprot.org/uniprotkb/P04637",
    "response_sha256": "a" * 64,
    "accept_header": "application/json",
}


# ---------------------------------------------------------------------------
# Provenance helpers: missing-SHA and release-without-date arcs
# (193->195, 213->214, 217->219)
# ---------------------------------------------------------------------------


def test_md_footer_without_sha_omits_sha_line() -> None:
    """193->195: empty response_sha256 -> no SHA-256 line, still Accept line."""
    prov: Provenance = {**_PROV, "response_sha256": ""}
    lines = _provenance_md_footer(prov)
    assert not any(line.startswith("_SHA-256:") for line in lines)
    assert any(line.startswith("_Accept:") for line in lines)


def test_fasta_header_release_without_date() -> None:
    """213->214: release present but release_date missing -> bare release."""
    prov: Provenance = {**_PROV, "release_date": None}
    lines = _provenance_fasta_header(prov)
    assert ";Release: 2026_02" in lines
    assert ";Release: 2026_02 (2026-03-05)" not in lines


def test_fasta_header_without_sha_omits_sha_line() -> None:
    """217->219: empty response_sha256 -> no ;SHA-256 line in FASTA header."""
    prov: Provenance = {**_PROV, "response_sha256": ""}
    lines = _provenance_fasta_header(prov)
    assert not any(line.startswith(";SHA-256:") for line in lines)
    assert any(line.startswith(";Accept:") for line in lines)


# ---------------------------------------------------------------------------
# _kw_id fall-through (486->488) and _uniref_representative non-dict (657->658)
# ---------------------------------------------------------------------------


def test_kw_id_falls_back_to_flat_id() -> None:
    """486->488: 'keyword' absent (neither dict nor non-empty str) -> flat id."""
    assert _kw_id({"id": "KW-9999"}) == "KW-9999"


def test_kw_id_empty_keyword_string_falls_back() -> None:
    """486->488: keyword is empty string (falsy) -> flat id fallback."""
    assert _kw_id({"keyword": "", "id": "KW-1234"}) == "KW-1234"


def test_uniref_representative_non_dict_returns_empty() -> None:
    """657->658: representativeMember that is not a dict -> ''."""
    assert _uniref_representative({"representativeMember": "P04637"}) == ""


# ---------------------------------------------------------------------------
# fmt_keyword — full markdown + json + provenance (525->526, 529->531, 534->536,
# 544->545)
# ---------------------------------------------------------------------------


def test_fmt_keyword_full_markdown_hits_all_sections() -> None:
    data = {
        "keyword": {"id": "KW-0007", "name": "Acetylation"},
        "category": "PTM",
        "definition": "Protein acetylation.",
        "synonyms": [f"syn{i}" for i in range(10)],
        "parents": [{"keyword": {"name": "Parent KW"}}],
        "children": [{"id": "KW-0001"}, {"id": "KW-0002"}],
        "geneOntologies": [{"id": "GO:0006473"}],
        "statistics": {"reviewedProteinCount": 100, "unreviewedProteinCount": 50},
    }
    out = fmt_keyword(data, provenance=_PROV)
    assert "**Category:** PTM" in out
    assert "**Children:** 2 narrower keyword(s)" in out
    assert "**GO:** GO:0006473" in out
    assert "**Proteins annotated:** 100 reviewed, 50 unreviewed" in out
    assert "(+2 more)" in out  # synonyms truncated at 8
    assert "_Source:" in out  # provenance footer


def test_fmt_keyword_json() -> None:
    out = fmt_keyword({"keyword": {"id": "KW-0007"}}, "json", provenance=_PROV)
    assert out.startswith("{")
    assert '"provenance"' in out


def test_fmt_keyword_search_json() -> None:
    out = fmt_keyword_search({"results": []}, "json")
    assert out.startswith("{")


# ---------------------------------------------------------------------------
# fmt_subcellular_location — full markdown + json (566->567, 592-599, 602->604,
# 607->609, 617->618)
# ---------------------------------------------------------------------------


def test_fmt_subcellular_location_full_markdown() -> None:
    data = {
        "id": "SL-0191",
        "name": "Nucleus",
        "category": "Cellular component",
        "definition": "The nucleus.",
        "synonyms": ["nuclear"],
        "keyword": {"id": "KW-0539", "name": "Nucleus"},
        "isA": [{"name": "Intracellular"}],
        "isPartOf": [{"name": "Cell"}],
        "parts": [{"name": "Nucleolus"}],
        "geneOntologies": [{"id": "GO:0005634"}],
        "statistics": {"reviewedProteinCount": 10, "unreviewedProteinCount": 5},
    }
    out = fmt_subcellular_location(data, provenance=_PROV)
    assert "**Keyword:** KW-0539" in out
    assert "**Is-a:** Intracellular" in out
    assert "**Part of:** Cell" in out
    assert "**Has parts:** 1" in out
    assert "**GO:** GO:0005634" in out
    assert "**Proteins annotated:** 10 reviewed, 5 unreviewed" in out
    assert "_Source:" in out


def test_fmt_subcellular_location_json() -> None:
    out = fmt_subcellular_location({"id": "SL-0191"}, "json")
    assert out.startswith("{")


def test_fmt_subcellular_location_search_json() -> None:
    out = fmt_subcellular_location_search({"results": []}, "json")
    assert out.startswith("{")


# ---------------------------------------------------------------------------
# fmt_uniref — full markdown + json (683->685, 699->697, 701->705, 713->714,
# 724->726, 731->733)
# ---------------------------------------------------------------------------


def test_fmt_uniref_full_markdown() -> None:
    data = {
        "id": "UniRef50_P04637",
        "name": "Cluster: Cellular tumor antigen p53",
        "entryType": "UniRef50",
        "representativeMember": {"memberId": "P04637", "uniprotKBId": "TP53_HUMAN"},
        "memberCount": 25,
        "commonTaxon": {"scientificName": "Homo sapiens", "taxonId": 9606},
        "updated": "2026-01-15",
        "members": [{"memberId": f"P{i:05d}"} for i in range(25)],
    }
    out = fmt_uniref(data, provenance=_PROV)
    assert "**Identity tier:** 50%" in out
    assert "**Representative:** P04637 (TP53_HUMAN)" in out
    assert "**Member count:** 25" in out
    assert "**Common taxon:** Homo sapiens (taxId 9606)" in out
    assert "**Last updated:** 2026-01-15" in out
    assert "(+5 more)" in out  # 25 members, only 20 shown
    assert "_Source:" in out


def test_fmt_uniref_json() -> None:
    out = fmt_uniref({"id": "UniRef50_P04637"}, "json")
    assert out.startswith("{")


def test_fmt_uniref_search_full_markdown() -> None:
    data = {
        "results": [
            {
                "id": "UniRef90_P04637",
                "name": "p53 cluster",
                "entryType": "UniRef90",
                "memberCount": 12,
                "representativeMember": {"memberId": "P04637", "uniprotKBId": "TP53_HUMAN"},
            }
        ]
    }
    out = fmt_uniref_search(data, provenance=_PROV)
    assert "90%" in out
    assert "12 members" in out
    assert "rep P04637 (TP53_HUMAN)" in out
    assert "p53 cluster" in out


def test_fmt_uniref_search_json() -> None:
    out = fmt_uniref_search({"results": []}, "json")
    assert out.startswith("{")


# ---------------------------------------------------------------------------
# fmt_uniparc — full markdown + json + >50 results (745->746, 761-783, 791->792,
# 800->801, 802->804, 811->812)
# ---------------------------------------------------------------------------


def test_fmt_uniparc_full_markdown() -> None:
    data = {
        "uniParcId": "UPI000002ED67",
        "sequence": {"length": 393, "molWeight": 43653, "md5": "abc", "crc64": "def"},
        "crossReferenceCount": 12,
        "oldestCrossRefCreated": "2000-01-01",
        "mostRecentCrossRefUpdated": "2026-01-01",
        "uniProtKBAccessions": [f"P{i:05d}" for i in range(15)],
        "commonTaxons": [{"commonTaxon": "Homo sapiens"}],
    }
    out = fmt_uniparc(data, provenance=_PROV)
    assert "md5 `abc`" in out
    assert "crc64 `def`" in out
    assert "**Cross-reference records:** 12" in out
    assert "**Oldest cross-ref:** 2000-01-01" in out
    assert "**Most recent cross-ref:** 2026-01-01" in out
    assert "(+5 more)" in out  # 15 accessions, 10 shown
    assert "_Source:" in out


def test_fmt_uniparc_json() -> None:
    out = fmt_uniparc({"uniParcId": "UPI000002ED67"}, "json")
    assert out.startswith("{")


def test_fmt_uniparc_search_truncates_and_json() -> None:
    data = {"results": [{"uniParcId": f"UPI{i:09d}"} for i in range(55)]}
    md = fmt_uniparc_search(data, provenance=_PROV)
    assert "(+5 more)" in md
    assert "_Source:" in md
    js = fmt_uniparc_search({"results": []}, "json")
    assert js.startswith("{")


# ---------------------------------------------------------------------------
# fmt_proteome — full markdown + json + search (811->812, 830-854, 862->863,
# 873-884, 893->894)
# ---------------------------------------------------------------------------


def test_fmt_proteome_full_markdown() -> None:
    data = {
        "id": "UP000005640",
        "description": "Homo sapiens reference proteome",
        "proteomeType": "Reference",
        "superkingdom": "Eukaryota",
        "taxonomy": {"scientificName": "Homo sapiens", "taxonId": 9606},
        "proteinCount": 20000,
        "geneCount": 19000,
        "annotationScore": 5,
        "components": [{"name": f"Chromosome {i}"} for i in range(12)],
        "modified": "2026-01-01",
        "proteomeCompletenessReport": {"buscoReport": {"score": 99}},
    }
    out = fmt_proteome(data, provenance=_PROV)
    assert "**Type:** Reference" in out
    assert "**Organism:** Homo sapiens (taxId 9606)" in out
    assert "**Superkingdom:** Eukaryota" in out
    assert "**Gene count:** 19000" in out
    assert "**Annotation score:** 5 / 5" in out
    assert "**BUSCO completeness:** 99 %" in out
    assert "**Components:** 12" in out
    assert "(+2 more)" in out  # 12 components, 10 names shown
    assert "**Last modified:** 2026-01-01" in out
    assert "_Source:" in out


def test_fmt_proteome_json() -> None:
    out = fmt_proteome({"id": "UP000005640"}, "json")
    assert out.startswith("{")


def test_fmt_proteome_search_full_markdown() -> None:
    data = {
        "results": [
            {
                "id": "UP000005640",
                "taxonomy": {"scientificName": "Homo sapiens"},
                "proteinCount": 20000,
                "proteomeType": "Reference",
            }
        ]
    }
    out = fmt_proteome_search(data, provenance=_PROV)
    assert "20000 proteins" in out
    assert "Reference" in out
    assert "Homo sapiens" in out
    assert "_Source:" in out


def test_fmt_proteome_search_truncates_over_50() -> None:
    """883: more than 50 proteomes -> '... (+N more)' footer."""
    data = {"results": [{"id": f"UP{i:09d}"} for i in range(55)]}
    out = fmt_proteome_search(data)
    assert "... (+5 more)" in out


def test_fmt_proteome_search_json() -> None:
    out = fmt_proteome_search({"results": []}, "json")
    assert out.startswith("{")


# ---------------------------------------------------------------------------
# fmt_citation — full markdown + json + search (893->894, 912-926, 938->939,
# 952->954, 955->956)
# ---------------------------------------------------------------------------


def test_fmt_citation_full_markdown() -> None:
    data = {
        "citation": {
            "id": "12345",
            "title": "A study of p53",
            "authors": [f"Author{i}" for i in range(8)],
            "journal": "Nature",
            "publicationDate": "2020",
            "volume": "100",
            "firstPage": "1",
            "lastPage": "10",
            "citationCrossReferences": [{"database": "PubMed", "id": "12345"}],
        }
    }
    out = fmt_citation(data, provenance=_PROV)
    assert "**Title:** A study of p53" in out
    assert "(+2 more)" in out  # 8 authors, 6 shown
    assert "**Source:** Nature, 2020, vol. 100, 1-10" in out
    assert "**Cross-refs:** PubMed:12345" in out
    assert "_Source:" in out


def test_fmt_citation_json() -> None:
    out = fmt_citation({"citation": {"id": "12345"}}, "json")
    assert out.startswith("{")


def test_fmt_citation_search_truncates_and_titles() -> None:
    data = {
        "results": [
            {"citation": {"id": str(i), "title": f"Paper {i}", "publicationDate": "2020"}}
            for i in range(55)
        ]
    }
    md = fmt_citation_search(data, provenance=_PROV)
    assert "(+5 more)" in md
    assert "Paper 0" in md
    assert "(2020)" in md
    assert "_Source:" in md


def test_fmt_citation_search_json() -> None:
    out = fmt_citation_search({"results": []}, "json")
    assert out.startswith("{")


# ---------------------------------------------------------------------------
# fmt_pdb / fmt_alphafold / fmt_interpro / fmt_chembl — json + rich markdown
# (1000->1002, 1002->1004, 1005->1006, 1007->1009, 1022->1023, 1031->1033,
# 1046->1047, 1060->1061, 1062->1064, 1076->1077, 1089->1091)
# ---------------------------------------------------------------------------


def _entry_with_xrefs(database: str, n: int, *, props: list[dict] | None = None) -> dict:
    return {
        "uniProtKBCrossReferences": [
            {
                "database": database,
                "id": f"{database}{i:04d}",
                "properties": props or [],
            }
            for i in range(n)
        ]
    }


def test_fmt_pdb_markdown_with_resolution_and_chains() -> None:
    entry = {
        "uniProtKBCrossReferences": [
            {
                "database": "PDB",
                "id": "1ABC",
                "properties": [
                    {"key": "Method", "value": "X-ray"},
                    {"key": "Resolution", "value": "2.0 A"},
                    {"key": "Chains", "value": "A/B"},
                ],
            }
        ]
    }
    out = fmt_pdb(entry, "P04637", provenance=_PROV)
    assert "1ABC" in out
    assert "2.0 A" in out
    assert "chains A/B" in out
    assert "_Source:" in out


def test_fmt_pdb_truncates_over_50() -> None:
    entry = _entry_with_xrefs("PDB", 55, props=[{"key": "Method", "value": "X-ray"}])
    out = fmt_pdb(entry, "P04637")
    assert "(+5 more)" in out


def test_fmt_pdb_json() -> None:
    out = fmt_pdb(_entry_with_xrefs("PDB", 1), "P04637", "json", provenance=_PROV)
    assert out.startswith("{")
    assert '"provenance"' in out


def test_fmt_alphafold_json_and_markdown_provenance() -> None:
    entry = _entry_with_xrefs("AlphaFoldDB", 1)
    md = fmt_alphafold(entry, "P04637", provenance=_PROV)
    assert "AlphaFoldDB0000" in md
    assert "_Source:" in md
    js = fmt_alphafold(entry, "P04637", "json", provenance=_PROV)
    assert js.startswith("{")


def test_fmt_interpro_json_and_truncation() -> None:
    entry = _entry_with_xrefs("InterPro", 55, props=[{"key": "EntryName", "value": "p53 domain"}])
    md = fmt_interpro(entry, "P04637", provenance=_PROV)
    assert "p53 domain" in md
    assert "(+5 more)" in md
    assert "_Source:" in md
    js = fmt_interpro(entry, "P04637", "json")
    assert js.startswith("{")


def test_fmt_chembl_json_and_markdown_provenance() -> None:
    entry = _entry_with_xrefs("ChEMBL", 1)
    md = fmt_chembl(entry, "P04637", provenance=_PROV)
    assert "ChEMBL0000" in md
    assert "_Source:" in md
    js = fmt_chembl(entry, "P04637", "json", provenance=_PROV)
    assert js.startswith("{")


# ---------------------------------------------------------------------------
# fmt_orthology — provenance footer (1147->1149)
# ---------------------------------------------------------------------------


def test_fmt_orthology_with_provenance_footer() -> None:
    out = fmt_orthology({"KEGG": ["hsa:7157"]}, "P04637", provenance=_PROV)
    assert "KEGG Orthology" in out
    assert "_Source:" in out


# ---------------------------------------------------------------------------
# fmt_target_dossier — fully populated dossier hits every section
# (1183-1195, 1199->1205, 1206-1226, 1227-1257, 1258-1272, 1273-1285,
# 1286->1293, 1294-1312, 1313-1325)
# ---------------------------------------------------------------------------


def test_fmt_target_dossier_full_markdown() -> None:
    dossier = {
        "identity": {
            "name": "Cellular tumor antigen p53",
            "gene": "TP53",
            "organism": "Homo sapiens",
            "length": 393,
            "reviewed": "Swiss-Prot (reviewed)",
            "entry_id": "TP53_HUMAN",
        },
        "function": "Acts as a tumor suppressor.",
        "chemistry": {
            "molecular_weight": 43653.0,
            "theoretical_pi": 6.33,
            "gravy": -0.756,
            "aromaticity": 0.07,
            "net_charge_pH7": -3.2,
            "extinction_coefficient_280nm": 35000,
        },
        "structure": {
            "pdb_count": 200,
            "best_pdb": {"id": "1TUP", "method": "X-ray", "resolution": "2.2 A"},
            "alphafold_model_id": "AF-P04637-F1",
            "interpro_count": 4,
        },
        "drug_target": {"chembl_ids": [f"CHEMBL{i}" for i in range(7)], "drugbank_count": 3},
        "diseases": [{"name": f"Disease {i}", "mim_id": f"{i:06d}"} for i in range(12)],
        "variants": {"count": 500},
        "functional_annotations": {
            "go_molecular_function": ["DNA binding"],
            "subcellular_locations": ["Nucleus"],
            "evidence_distinct_codes": 8,
        },
        "cross_reference_summary": {
            "total": 300,
            "database_count": 40,
            "top_databases": ["PDB", "GO", "InterPro"],
        },
    }
    out = fmt_target_dossier(dossier, "P04637", provenance=_PROV)
    assert "**Protein:** Cellular tumor antigen p53" in out
    assert "**Gene:** TP53" in out
    assert "**Organism:** Homo sapiens" in out
    assert "**Length:** 393 aa" in out
    assert "**Curation:** Swiss-Prot (reviewed)" in out
    assert "**Entry ID:** TP53_HUMAN" in out
    assert "## Function" in out
    assert "Molecular weight: 43653.0 Da" in out
    assert "Theoretical pI: 6.33" in out
    assert "GRAVY: -0.756" in out
    assert "Net charge at pH 7: -3.2" in out
    assert "Extinction coefficient" in out
    assert "PDB structures: 200 (best: 1TUP, X-ray, 2.2 A)" in out
    assert "AlphaFold model: `AF-P04637-F1`" in out
    assert "InterPro signatures: 4" in out
    assert "ChEMBL targets: CHEMBL0" in out
    assert "(+2 more)" in out  # 7 chembl ids, 5 shown
    assert "DrugBank cross-references: 3" in out
    assert "## Disease associations (12)" in out
    assert "(MIM:000000)" in out
    assert "(+2 more)" in out  # 12 diseases, 10 shown
    assert "Natural variants annotated: 500" in out
    assert "**GO Molecular Function:**" in out
    assert "**Subcellular locations:**" in out
    assert "distinct ECO codes" in out
    assert "300 cross-references across 40 databases" in out
    assert "Top databases: PDB, GO, InterPro" in out
    assert "_Source:" in out


def test_fmt_target_dossier_empty_structure_and_drug_sections() -> None:
    """Hits the else-branches: pdb_count 0, no alphafold, empty chembl."""
    dossier = {
        "identity": {},
        "structure": {"pdb_count": 0},
        "drug_target": {"chembl_ids": []},
    }
    out = fmt_target_dossier(dossier, "P04637")
    assert "PDB structures: 0 (no experimental structure on file)" in out
    assert "AlphaFold model: not cross-referenced from UniProt" in out
    assert "ChEMBL targets: none" in out


def test_fmt_target_dossier_json() -> None:
    out = fmt_target_dossier({"identity": {}}, "P04637", "json", provenance=_PROV)
    assert out.startswith("{")
    assert '"dossier"' in out


# ---------------------------------------------------------------------------
# fmt_clinvar — germline + clinical_significance fallback + full fields
# (1376->1380, 1382-1383, 1386->1385, 1392-1409, 1410->1412)
# ---------------------------------------------------------------------------


def test_fmt_clinvar_germline_classification_full() -> None:
    payload = {
        "total": 5,
        "records": [
            {
                "title": "NM_007294.4(BRCA1):c.5266dup",
                "accession": "VCV004813451",
                "germline_classification": {
                    "description": "Pathogenic",
                    "review_status": "reviewed by expert panel",
                },
                "trait_set": [
                    {"trait_name": "Breast cancer"},
                    "not-a-dict-skip",  # 1386->1385 loop-back
                ],
                "molecular_consequence_list": ["frameshift variant"],
                "protein_change": "Q1756fs",
            }
        ],
    }
    out = fmt_clinvar(payload, "P38398", "BRCA1", "", provenance=_PROV)
    assert "**ClinVar accession:** VCV004813451" in out
    assert "**Classification:** Pathogenic  (reviewed by expert panel)" in out
    assert "**Conditions:** Breast cancer" in out
    assert "**Molecular consequence(s):** frameshift variant" in out
    assert "**Protein change(s):** Q1756fs" in out
    assert "_Source:" in out


def test_fmt_clinvar_clinical_significance_fallback() -> None:
    """1382-1383: no germline block, older clinical_significance is used."""
    payload = {
        "total": 1,
        "records": [
            {
                "title": "Old-style record",
                "clinical_significance": {
                    "description": "Likely benign",
                    "review_status": "single submitter",
                },
            }
        ],
    }
    out = fmt_clinvar(payload, "P38398", "BRCA1", "p.Q1756fs")
    assert "change `p.Q1756fs`" in out
    assert "**Classification:** Likely benign  (single submitter)" in out


def test_fmt_clinvar_json() -> None:
    out = fmt_clinvar({"records": [], "total": 0}, "P38398", "BRCA1", "", "json")
    assert out.startswith("{")
    assert '"clinvar"' in out


# ---------------------------------------------------------------------------
# fmt_alphafold_confidence — non-numeric global mean + non-numeric fraction
# (1471-1472, 1490-1491)
# ---------------------------------------------------------------------------


def test_fmt_alphafold_confidence_non_numeric_global_and_fraction() -> None:
    record = {
        "entryId": "AF-P04637-F1",
        "globalMetricValue": "n/a",  # not a float -> ValueError -> band '?'
        "fractionPlddtVeryHigh": "0.8",  # str, not numeric -> elif frac branch
    }
    out = fmt_alphafold_confidence(record, "P04637", provenance=_PROV)
    assert "**Global pLDDT (mean):** n/a" in out
    assert "Very high (≥ 90): 0.8" in out
    assert "_Source:" in out


def test_fmt_alphafold_confidence_numeric_full() -> None:
    record = {
        "entryId": "AF-P04637-F1",
        "organismScientificName": "Homo sapiens",
        "gene": "TP53",
        "uniprotEnd": 393,
        "latestVersion": 4,
        "globalMetricValue": 85.5,
        "fractionPlddtVeryHigh": 0.5,
        "fractionPlddtConfident": 0.3,
        "fractionPlddtLow": 0.15,
        "fractionPlddtVeryLow": 0.05,
        "cifUrl": "https://x/model.cif",
        "pdbUrl": "https://x/model.pdb",
        "paeImageUrl": "https://x/pae.png",
    }
    out = fmt_alphafold_confidence(record, "P04637")
    assert "**Gene:** TP53" in out
    assert "**Residues modelled:** 1-393" in out
    assert "**Model version:** v4" in out
    assert "**Global pLDDT (mean):** 85.5" in out
    assert "Very high (≥ 90):  50.0%" in out
    assert "**CIF:** https://x/model.cif" in out
    assert "**PDB:** https://x/model.pdb" in out
    assert "**PAE image:** https://x/pae.png" in out


# ---------------------------------------------------------------------------
# fmt_publications — full markdown + json + truncation (1542->1544, 1546->1548,
# 1550->1556, 1556->1558, 1559->1561, 1562->1563, 1564->1566, 1525 json)
# ---------------------------------------------------------------------------


def test_fmt_publications_full_markdown_and_truncation() -> None:
    pubs = [
        {
            "title": f"Paper {i}",
            "authors": [f"A{j}" for j in range(8)],
            "year": 2020 + i,
            "journal": "Nature",
            "pubmed_id": f"{1000 + i}",
            "doi": f"10.1/{i}",
            "reference_positions": ["FUNCTION", "INTERACTION"],
        }
        for i in range(55)
    ]
    out = fmt_publications(pubs, "P04637", provenance=_PROV)
    assert "PMID:1000" in out
    assert "doi:10.1/0" in out
    assert "_Paper 0_" in out
    assert "(+2 more)" in out  # authors truncated
    assert "**Cited for:**" in out
    assert "... (+5 more)" in out  # publications truncated at 50
    assert "_Source:" in out


def test_fmt_publications_no_identifier_head() -> None:
    """1548: head with no pmid/doi/year -> '(no identifier)'."""
    out = fmt_publications([{"title": "Untitled ref"}], "P04637")
    assert "(no identifier)" in out


def test_fmt_publications_json() -> None:
    out = fmt_publications([], "P04637", "json", provenance=_PROV)
    assert out.startswith("{")


# ---------------------------------------------------------------------------
# fmt_properties — extinction coeff + composition + json (1594->1599, 1600->1604,
# 1604->1606, 1578 json)
# ---------------------------------------------------------------------------


def test_fmt_properties_full_markdown() -> None:
    data = {
        "length": 393,
        "molecular_weight": 43653.0,
        "theoretical_pi": 6.33,
        "net_charge_pH7": -3.2,
        "gravy": -0.756,
        "aromaticity": 0.07,
        "extinction_coefficient_280nm": 35000,
        "amino_acid_counts": {"A": 10, "C": 0, "G": 5},
    }
    out = fmt_properties(data, "P04637", provenance=_PROV)
    assert "Extinction coefficient at 280 nm:** 35000" in out
    assert "**Amino acid composition:** A:10, G:5" in out  # C:0 omitted
    assert "_Source:" in out


def test_fmt_properties_json() -> None:
    out = fmt_properties({"length": 0}, "P04637", "json")
    assert out.startswith("{")


# ---------------------------------------------------------------------------
# fmt_features_at_position — variant rendering + json (1618->1622, 1638->1640,
# 1645->1630)
# ---------------------------------------------------------------------------


def test_fmt_features_at_position_with_variant_and_no_desc() -> None:
    features = [
        {
            "type": "Natural variant",
            "location": {"start": {"value": 175}, "end": {"value": 175}},
            "description": "In cancer.",
            "alternativeSequence": {
                "originalSequence": "R",
                "alternativeSequences": ["H"],
            },
        },
        {
            # No description -> 1638->1640 skip; alt present but no alts list
            "type": "Domain",
            "location": {"start": {"value": 100}, "end": {"value": 200}},
            "alternativeSequence": {"originalSequence": "X", "alternativeSequences": []},
        },
    ]
    out = fmt_features_at_position(features, "P04637", 175, provenance=_PROV)
    assert "Variant: R → H" in out
    assert "**Domain** [100-200]" in out
    assert "_Source:" in out


def test_fmt_features_at_position_json() -> None:
    out = fmt_features_at_position([], "P04637", 1, "json", provenance=_PROV)
    assert out.startswith("{")


# ---------------------------------------------------------------------------
# fmt_variant_lookup — evidence rendering + json (1661->1665, 1685->1687,
# 1691->1692)
# ---------------------------------------------------------------------------


def test_fmt_variant_lookup_with_evidence_and_desc() -> None:
    matches = [
        {
            "location": {"start": {"value": 175}},
            "alternativeSequence": {
                "originalSequence": "R",
                "alternativeSequences": ["H"],
            },
            "description": "In Li-Fraumeni syndrome.",
            "evidences": [
                {"evidenceCode": "ECO:0000269"},
                {"evidenceCode": "ECO:0000269"},  # dedup
                {"evidenceCode": "ECO:0000305"},
            ],
        }
    ]
    out = fmt_variant_lookup(matches, "P04637", "R175H", provenance=_PROV)
    assert "### R175H" in out  # mutation = orig + pos + '/'.join(alts) = R175H
    assert "In Li-Fraumeni syndrome." in out
    assert "**Evidence:** ECO:0000269, ECO:0000305" in out
    assert "_Source:" in out


def test_fmt_variant_lookup_json() -> None:
    out = fmt_variant_lookup([], "P04637", "R175H", "json", provenance=_PROV)
    assert out.startswith("{")


# ---------------------------------------------------------------------------
# fmt_disease_associations — full markdown (1729->1731, 1731->1733, 1735->1737,
# 1738->1744, 1742->1744)
# ---------------------------------------------------------------------------


def test_fmt_disease_associations_full_markdown() -> None:
    associations = [
        {
            "name": "Li-Fraumeni syndrome",
            "disease_id": "DI-00001",
            "acronym": "LFS",
            "description": "A familial cancer syndrome.",
            "cross_references": [{"database": "MIM", "id": "151623"}],
            "note": "Caused by germline mutations.",
        },
        {
            # cross_references present but no usable id -> bits empty (1742->1744)
            "name": "Other condition",
            "cross_references": [{"database": "MIM"}],
        },
    ]
    out = fmt_disease_associations(associations, "P04637", provenance=_PROV)
    assert "### Li-Fraumeni syndrome  (acronym LFS, id DI-00001)" in out
    assert "A familial cancer syndrome." in out
    assert "**Cross-refs:** MIM:151623" in out
    assert "**Note:** Caused by germline mutations." in out
    assert "### Other condition" in out
    assert "_Source:" in out


# ---------------------------------------------------------------------------
# MINIMAL-INPUT tests: every formatter called with all optional fields ABSENT
# and no provenance, so the FALSE arc of each optional-section condition (and
# the "no provenance footer" arc) is exercised. These complement the rich
# tests above, which only took the True arcs.
# ---------------------------------------------------------------------------


def test_fmt_keyword_minimal_skips_optional_sections() -> None:
    """529->531, 534->536: GO ids empty + stats with no protein counts skipped,
    no provenance footer."""
    data = {
        "keyword": {"id": "KW-0007", "name": "Acetylation"},
        "geneOntologies": [{"name": "no-id-here"}],  # no 'id' -> ids empty
        "statistics": {"otherField": 1},  # rev/unrev both None
    }
    out = fmt_keyword(data)
    assert "## KW-0007: Acetylation" in out
    assert "**GO:**" not in out
    assert "**Proteins annotated:**" not in out
    assert "_Source:" not in out


def test_fmt_subcellular_location_minimal_skips_optional_sections() -> None:
    """580->...: definition/synonyms/keyword/is_a/is_part_of/parts/go/stats all
    absent; provenance footer absent."""
    data = {
        "id": "SL-0191",
        "name": "Nucleus",
        "isA": [{"noname": 1}],  # 590->594 names empty
        "isPartOf": [{"noname": 1}],  # 594->598 names empty
        "geneOntologies": [{"noid": 1}],  # 600->604 ids empty
        "statistics": {"x": 1},  # 604->609 rev/unrev None
    }
    out = fmt_subcellular_location(data)
    assert "## SL-0191: Nucleus" in out
    assert "**Is-a:**" not in out
    assert "**Part of:**" not in out
    assert "**GO:**" not in out
    assert "_Source:" not in out


def test_fmt_uniref_minimal_skips_optional_sections() -> None:
    """683->685, 699->697, 701->705, 705->707: unknown tier, member dicts with
    no acc, no provenance."""
    data = {
        "id": "UnknownCluster",  # tier '?' -> 683->685 skip tier line
        "members": [{"noacc": 1}],  # acc empty -> 699->697 loop-back, sample empty
    }
    out = fmt_uniref(data)
    assert "## UnknownCluster" in out
    assert "**Identity tier:**" not in out
    assert "**Members:**" not in out  # sample empty -> 701->705 skip
    assert "_Source:" not in out


def test_fmt_uniref_search_minimal_skips_tier_and_name() -> None:
    """724->726, 731->733: unknown tier (no tier bit), no name (head unchanged)."""
    data = {"results": [{"id": "UnknownCluster", "memberCount": 3}]}
    out = fmt_uniref_search(data)
    assert "3 members" in out
    assert "**UnknownCluster**:" not in out  # no name -> head not suffixed


def test_fmt_uniparc_minimal_skips_optional_sections() -> None:
    """761->768, 769->771, 771->773, 773->777, 777->783, 783->785: no checksums,
    no dates, no accessions, no taxons, no provenance."""
    data = {"uniParcId": "UPI000002ED67", "sequence": {"length": 393, "molWeight": 43653}}
    out = fmt_uniparc(data)
    assert "## UPI000002ED67" in out
    assert "**Checksums:**" not in out
    assert "**Oldest cross-ref:**" not in out
    assert "**Most recent cross-ref:**" not in out
    assert "**Linked UniProtKB accessions:**" not in out
    assert "**Common taxa:**" not in out
    assert "_Source:" not in out


def test_fmt_uniparc_only_md5_checksum() -> None:
    """765->767: md5 present, crc64 absent -> only md5 bit."""
    data = {"uniParcId": "UPI1", "sequence": {"length": 1, "molWeight": 1, "md5": "abc"}}
    out = fmt_uniparc(data)
    assert "md5 `abc`" in out
    assert "crc64" not in out


def test_fmt_uniparc_only_crc64_checksum() -> None:
    """763->765: crc64 present, md5 absent -> enters block, skips md5 bit."""
    data = {"uniParcId": "UPI1", "sequence": {"length": 1, "molWeight": 1, "crc64": "def"}}
    out = fmt_uniparc(data)
    assert "crc64 `def`" in out
    assert "md5" not in out


def test_fmt_uniparc_common_taxons_with_names() -> None:
    """781->782: common_taxons entries with scientificName -> Common taxa line."""
    data = {
        "uniParcId": "UPI1",
        "sequence": {"length": 1, "molWeight": 1},
        "commonTaxons": [{"scientificName": "Homo sapiens"}],
    }
    out = fmt_uniparc(data)
    assert "**Common taxa:** Homo sapiens" in out


def test_fmt_uniparc_search_minimal_no_provenance() -> None:
    """802->804: no provenance footer on uniparc search."""
    out = fmt_uniparc_search({"results": [{"uniParcId": "UPI1"}]})
    assert "UPI1" in out
    assert "_Source:" not in out


def test_fmt_proteome_minimal_skips_optional_sections() -> None:
    """830->...854: description/type/organism/superkingdom/genecount/annotation/
    busco/components/modified all absent; no provenance footer."""
    data = {"id": "UP000005640", "proteinCount": 100}
    out = fmt_proteome(data)
    assert "## UP000005640" in out
    assert "**Description:**" not in out
    assert "**Type:**" not in out
    assert "**Organism:**" not in out
    assert "**Superkingdom:**" not in out
    assert "**Gene count:**" not in out
    assert "**Annotation score:**" not in out
    assert "**BUSCO completeness:**" not in out
    assert "**Components:**" not in out
    assert "**Last modified:**" not in out
    assert "_Source:" not in out


def test_fmt_proteome_components_without_names() -> None:
    """849->852: components present but none has a 'name' -> no name line."""
    data = {"id": "UP1", "proteinCount": 1, "components": [{"noname": 1}]}
    out = fmt_proteome(data)
    assert "**Components:** 1" in out


def test_fmt_proteome_search_minimal_skips_bits() -> None:
    """873->875, 875->877, 879->881, 882->883, 884->886: unknown protein count,
    no type, no organism, <=50 results, no provenance."""
    data = {"results": [{"id": "UP1"}]}
    out = fmt_proteome_search(data)
    assert "**UP1**" in out
    assert "proteins" not in out
    assert "_Source:" not in out


def test_fmt_citation_minimal_skips_optional_sections() -> None:
    """912->914, 920->922, 922->924, 924->926: no title, journal with no
    year/volume/pages -> bare Source line; no provenance."""
    data = {"citation": {"id": "1", "journal": "Nature"}}
    out = fmt_citation(data)
    assert "## Citation 1" in out
    assert "**Title:**" not in out
    assert "**Source:** Nature" in out
    assert "vol." not in out
    assert "_Source:" not in out


def test_fmt_citation_search_minimal_skips_title() -> None:
    """952->954: result with no title -> head not suffixed with title."""
    out = fmt_citation_search({"results": [{"citation": {"id": "1"}}]})
    assert "**1**" in out


def test_fmt_alphafold_chembl_no_provenance() -> None:
    """1031->1033, 1089->1091: alphafold/chembl markdown without provenance."""
    af = fmt_alphafold(_entry_with_xrefs("AlphaFoldDB", 1), "P04637")
    assert "_Source:" not in af
    ch = fmt_chembl(_entry_with_xrefs("ChEMBL", 1), "P04637")
    assert "_Source:" not in ch


def test_fmt_interpro_no_provenance() -> None:
    """1062->1064: interpro markdown without provenance."""
    out = fmt_interpro(_entry_with_xrefs("InterPro", 1), "P04637")
    assert "_Source:" not in out


def test_fmt_orthology_empty_no_provenance() -> None:
    """1126/1133/1147->1149: empty grouped -> no-orthology note, no provenance."""
    out = fmt_orthology({}, "P04637")
    assert "No orthology cross-references" in out
    assert "_Source:" not in out


def test_fmt_target_dossier_chemistry_fields_absent() -> None:
    """1208->...1218: a chemistry dict that is truthy but missing each numeric
    field -> every inner 'if ... is not None' takes its False arc."""
    dossier = {"identity": {}, "chemistry": {"placeholder": "x"}}
    out = fmt_target_dossier(dossier, "P04637")
    assert "## Sequence chemistry (derived)" in out
    assert "Molecular weight:" not in out
    assert "Theoretical pI:" not in out


def test_fmt_target_dossier_structure_with_best_pdb_no_id() -> None:
    """1233->1240: best_pdb present but without an 'id' -> no detail tail."""
    dossier = {"identity": {}, "structure": {"pdb_count": 3, "best_pdb": {"method": "X-ray"}}}
    out = fmt_target_dossier(dossier, "P04637")
    assert "- PDB structures: 3" in out
    assert "(best:" not in out


def test_fmt_target_dossier_func_partial_sections() -> None:
    """1296->1300, 1300->1304, 1304->1309: functional_annotations truthy but each
    sub-field absent."""
    dossier = {"identity": {}, "functional_annotations": {"placeholder": "x"}}
    out = fmt_target_dossier(dossier, "P04637")
    assert "## Functional annotations" in out
    assert "**GO Molecular Function:**" not in out
    assert "**Subcellular locations:**" not in out
    assert "**Evidence codes:**" not in out


def test_fmt_target_dossier_xref_without_top_databases() -> None:
    """1319->1321: cross_reference_summary present but no top_databases."""
    dossier = {"identity": {}, "cross_reference_summary": {"total": 10, "database_count": 2}}
    out = fmt_target_dossier(dossier, "P04637")
    assert "10 cross-references across 2 databases" in out
    assert "Top databases:" not in out


def test_fmt_target_dossier_skips_absent_top_sections() -> None:
    """1227->1257, 1258->1272: no structure and no drug_target sections."""
    dossier = {"identity": {"name": "x"}}
    out = fmt_target_dossier(dossier, "P04637")
    assert "## Structural evidence" not in out
    assert "## Drug-target context" not in out


def test_fmt_clinvar_germline_not_a_dict_uses_clinical_significance() -> None:
    """1376->1380: germline_classification that is not a dict -> classification
    stays empty, falls through to clinical_significance."""
    payload = {
        "total": 1,
        "records": [
            {
                "title": "Weird record",
                "germline_classification": "string-not-dict",
                "clinical_significance": {"description": "Uncertain significance"},
            }
        ],
    }
    out = fmt_clinvar(payload, "P38398", "BRCA1", "")
    assert "**Classification:** Uncertain significance" in out


def test_fmt_clinvar_record_without_classification() -> None:
    """1394->1397: record with traits but no classification -> Conditions line
    rendered, Classification line skipped."""
    payload = {
        "total": 1,
        "records": [{"title": "T", "trait_set": [{"trait_name": "Cancer"}]}],
    }
    out = fmt_clinvar(payload, "P38398", "BRCA1", "")
    assert "**Conditions:** Cancer" in out
    assert "**Classification:**" not in out


def test_fmt_alphafold_confidence_empty_record_no_provenance() -> None:
    """1441->1443: empty record -> no-model message, no provenance footer."""
    out = fmt_alphafold_confidence({}, "P04637")
    assert "No AlphaFold model found" in out
    assert "_Source:" not in out


def test_fmt_publications_journal_no_title() -> None:
    """1550->1552: publication with journal but no title -> title line skipped."""
    out = fmt_publications([{"pubmed_id": "1", "journal": "Nature"}], "P04637")
    assert "Nature" in out
    assert "PMID:1" in out


def test_fmt_properties_minimal_no_e280_no_counts_no_prov() -> None:
    """1594->1599, 1600->1604, 1604->1606: no extinction coeff, empty counts,
    no provenance."""
    data = {
        "length": 10,
        "molecular_weight": 1000.0,
        "theoretical_pi": 7.0,
        "net_charge_pH7": 0.0,
        "gravy": 0.1,
        "aromaticity": 0.0,
    }
    out = fmt_properties(data, "P04637")
    assert "Extinction coefficient" not in out
    assert "**Amino acid composition:**" not in out
    assert "_Source:" not in out


def test_fmt_variant_lookup_match_without_description() -> None:
    """1685->1687: match with no description -> desc line skipped, still renders
    the mutation header."""
    matches = [
        {
            "location": {"start": {"value": 175}},
            "alternativeSequence": {"originalSequence": "R", "alternativeSequences": ["H"]},
        }
    ]
    out = fmt_variant_lookup(matches, "P04637", "R175H")
    assert "### R175H" in out


def test_fmt_disease_associations_xrefs_without_ids() -> None:
    """cross_references present but no usable id -> bits empty, no Cross-refs."""
    associations = [{"name": "D", "cross_references": [{"database": "MIM"}]}]
    out = fmt_disease_associations(associations, "P04637")
    assert "### D" in out
    assert "**Cross-refs:**" not in out


def test_fmt_disease_associations_no_xrefs_key() -> None:
    """1738->1744: a record with no cross_references at all -> False arc of
    ``if xrefs`` straight to the note check."""
    associations = [{"name": "D", "note": "some note"}]
    out = fmt_disease_associations(associations, "P04637")
    assert "### D" in out
    assert "**Cross-refs:**" not in out
    assert "**Note:** some note" in out
