"""The chemistry tools say what they measured and how.

Two statements have to travel with every set of derived properties:

* **Which sequence.** ``uniprot_compute_properties`` and the chemistry
  section of ``uniprot_target_dossier`` use the canonical FASTA record as
  it comes, signal peptide and propeptides included. For human insulin
  that is the 110-residue precursor (11,981 Da), not the two mature chains.
* **Which pK values.** The theoretical pI and the net charge depend on the
  pK table, so the output names the table and the terminal values applied.

The properties expected below for the insulin precursor are the ExPASy
ProtParam values recorded in ``test_proteinchem_pi_reference.py``.
"""

from __future__ import annotations

import json

import httpx
import respx

from uniprot_mcp import formatters, server
from uniprot_mcp.formatters import fmt_properties, fmt_target_dossier
from uniprot_mcp.proteinchem import compute_protein_properties
from uniprot_mcp.server import (
    uniprot_compute_properties,
    uniprot_get_processing_features,
    uniprot_target_dossier,
)

_INS_FASTA = (
    ">sp|P01308|INS_HUMAN Insulin OS=Homo sapiens OX=9606 GN=INS PE=1 SV=1\n"
    "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDL\n"
    "QVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN\n"
)
_INS_ENTRY = {
    "primaryAccession": "P01308",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "proteinDescription": {"recommendedName": {"fullName": {"value": "Insulin"}}},
    "genes": [{"geneName": {"value": "INS"}}],
    "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
    "sequence": {"length": 110},
}
_MODEL_TEXT = (
    "Bjellqvist pK set (N-terminus 7.00 for M, C-terminus 3.55; side chains "
    "C 9.00, D 4.05, E 4.45, H 5.98, K 10.00, R 12.00, Y 10.00). Estimated from the "
    "sequence alone: post-translational modifications, disulfide bonds and folding "
    "are not considered."
)


def _fasta_response() -> httpx.Response:
    return httpx.Response(200, text=_INS_FASTA, headers={"X-UniProt-Release": "2026_04"})


# ---------------------------------------------------------------------------
# The statement itself
# ---------------------------------------------------------------------------


def test_scope_statement_names_what_is_included_and_where_to_look() -> None:
    scope = server._CANONICAL_SEQUENCE_SCOPE
    assert scope.startswith("Full canonical sequence of the UniProt FASTA record")
    assert "no processing applied" in scope
    for feature in ("signal peptide", "propeptide", "transit peptide", "initiator methionine"):
        assert feature in scope
    assert "the precursor and not the mature chain" in scope
    assert "uniprot_get_processing_features" in scope


def test_chemistry_helper_labels_the_record_and_ignores_fasta_comments() -> None:
    """The header and PIR-style ``;`` comment lines are not residues, and
    the scope comes first so a reader meets it before the numbers."""
    record = server._canonical_sequence_chemistry(
        ">sp|P01308|INS_HUMAN\n;Source: UniProt\nMALW\nMRL\n"
    )
    assert next(iter(record)) == "sequence_scope"
    assert record["sequence_scope"] == server._CANONICAL_SEQUENCE_SCOPE
    assert record["length"] == 7
    assert {k: v for k, v in record.items() if k != "sequence_scope"} == dict(
        compute_protein_properties("MALWMRL")
    )


# ---------------------------------------------------------------------------
# uniprot_compute_properties
# ---------------------------------------------------------------------------


async def test_properties_markdown_states_the_sequence_basis_and_the_pk_model() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P01308").mock(return_value=_fasta_response())
        out = await uniprot_compute_properties("P01308", "markdown")
        assert len(router.calls) == 1  # still one upstream request
    lines = out.splitlines()
    assert lines[0] == "## Sequence properties: P01308"
    assert lines[2] == f"**Sequence basis:** {server._CANONICAL_SEQUENCE_SCOPE}"
    assert lines[3] == "**Length:** 110 residues"
    assert "**Molecular weight:** 11980.9 Da" in lines
    assert "**Theoretical pI:** 5.22" in lines
    assert "**Net charge at pH 7:** -3.4 (positive = basic, negative = acidic)" in lines
    assert f"**pI and charge model:** {_MODEL_TEXT}" in lines
    assert lines.index(f"**pI and charge model:** {_MODEL_TEXT}") == (
        lines.index("**Net charge at pH 7:** -3.4 (positive = basic, negative = acidic)") + 1
    )
    assert any(line.startswith("**Extinction coefficient at 280 nm:** 16960 ") for line in lines)
    assert "Lehninger" not in out


async def test_properties_json_adds_scope_and_model_and_keeps_every_earlier_key() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P01308").mock(return_value=_fasta_response())
        payload = json.loads(await uniprot_compute_properties("P01308", "json"))
    assert set(payload) == {"data", "provenance"}
    assert set(payload["data"]) == {"accession", "properties"}
    props = payload["data"]["properties"]
    assert set(props) == {
        # present before this change, names and meaning unchanged
        "length",
        "molecular_weight",
        "theoretical_pi",
        "net_charge_pH7",
        "gravy",
        "aromaticity",
        "extinction_coefficient_280nm",
        "amino_acid_counts",
        # added
        "sequence_scope",
        "charge_model",
    }
    assert props["sequence_scope"] == server._CANONICAL_SEQUENCE_SCOPE
    assert props["length"] == 110
    assert props["molecular_weight"] == 11980.9086
    assert props["theoretical_pi"] == 5.22
    assert props["net_charge_pH7"] == -3.366
    assert props["extinction_coefficient_280nm"] == 16960
    assert props["charge_model"] == {
        "pk_set": "Bjellqvist",
        "n_terminal_residue": "M",
        "n_terminus_pk": 7.0,
        "c_terminus_pk": 3.55,
        "side_chain_pk": {
            "C": 9.0,
            "D": 4.05,
            "E": 4.45,
            "H": 5.98,
            "K": 10.0,
            "R": 12.0,
            "Y": 10.0,
        },
    }


# ---------------------------------------------------------------------------
# uniprot_target_dossier
# ---------------------------------------------------------------------------


def _dossier_router(router: respx.MockRouter) -> None:
    responses = iter(
        [
            httpx.Response(200, json=_INS_ENTRY, headers={"X-UniProt-Release": "2026_04"}),
            _fasta_response(),
        ]
    )
    router.get("/uniprotkb/P01308").mock(side_effect=lambda request: next(responses))


async def test_dossier_markdown_states_the_sequence_basis_and_the_pk_model() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        _dossier_router(router)
        out = await uniprot_target_dossier("P01308", "markdown")
    lines = out.splitlines()
    start = lines.index("## Sequence chemistry (derived)")
    assert lines[start + 1] == f"- Sequence basis: {server._CANONICAL_SEQUENCE_SCOPE}"
    assert lines[start + 2] == "- Molecular weight: 11980.9 Da"
    assert "- Theoretical pI: 5.22" in lines
    assert "- Net charge at pH 7: -3.4" in lines
    assert f"- pI and charge model: {_MODEL_TEXT}" in lines


async def test_dossier_json_carries_scope_and_model_in_the_chemistry_section() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        _dossier_router(router)
        payload = json.loads(await uniprot_target_dossier("P01308", "json"))
    dossier = payload["data"]["dossier"]
    assert dossier["chemistry_status"] == "available"
    chemistry = dossier["chemistry"]
    assert chemistry["sequence_scope"] == server._CANONICAL_SEQUENCE_SCOPE
    assert chemistry["charge_model"]["pk_set"] == "Bjellqvist"
    assert chemistry["charge_model"]["n_terminus_pk"] == 7.0
    assert chemistry["theoretical_pi"] == 5.22
    assert "amino_acid_counts" not in chemistry  # still left out of the dossier


# ---------------------------------------------------------------------------
# Formatters: nothing is claimed about data that carries no statement
# ---------------------------------------------------------------------------

_BARE = {
    "length": 10,
    "molecular_weight": 1000.0,
    "theoretical_pi": 7.0,
    "net_charge_pH7": 0.0,
    "gravy": 0.1,
    "aromaticity": 0.0,
}


def test_formatters_print_no_basis_or_model_for_a_record_without_them() -> None:
    properties = fmt_properties(_BARE, "P04637")
    assert "Sequence basis" not in properties
    assert "pI and charge model" not in properties
    dossier = fmt_target_dossier({"identity": {}, "chemistry": dict(_BARE)}, "P04637")
    assert "- Theoretical pI: 7.00" in dossier
    assert "Sequence basis" not in dossier
    assert "pI and charge model" not in dossier


def test_charge_model_text_for_absent_and_empty_sequence_records() -> None:
    assert formatters._charge_model_text(None) == ""
    empty = formatters._charge_model_text(compute_protein_properties("")["charge_model"])
    assert empty.startswith(
        "Bjellqvist pK set (N-terminus 7.50, C-terminus 3.55; side chains C 9.00"
    )
    assert " for " not in empty.split(";")[0]
    assert formatters._charge_model_text(
        compute_protein_properties("PGK")["charge_model"]
    ).startswith("Bjellqvist pK set (N-terminus 8.36 for P, C-terminus 3.55;")


# ---------------------------------------------------------------------------
# The tool the statement points to
# ---------------------------------------------------------------------------

# Processing features of P01308 as UniProt release 2026_04 returns them.
# The REST JSON calls a signal peptide feature "Signal".
_INS_PROCESSING_FEATURES = [
    {"type": "Signal", "location": {"start": {"value": 1}, "end": {"value": 24}}},
    {
        "type": "Peptide",
        "location": {"start": {"value": 25}, "end": {"value": 54}},
        "description": "Insulin B chain",
    },
    {
        "type": "Propeptide",
        "location": {"start": {"value": 57}, "end": {"value": 87}},
        "description": "C peptide",
    },
    {
        "type": "Peptide",
        "location": {"start": {"value": 90}, "end": {"value": 110}},
        "description": "Insulin A chain",
    },
    {"type": "Helix", "location": {"start": {"value": 35}, "end": {"value": 43}}},
]


async def test_processing_features_list_the_signal_peptide_under_its_rest_name() -> None:
    """The scope statement sends the reader to this tool for the
    boundaries, so the signal peptide has to be in its answer."""
    entry = {**_INS_ENTRY, "features": _INS_PROCESSING_FEATURES}
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P01308").mock(
            return_value=httpx.Response(200, json=entry, headers={"X-UniProt-Release": "2026_04"})
        )
        md = await uniprot_get_processing_features("P01308", "markdown")
        payload = json.loads(await uniprot_get_processing_features("P01308", "json"))
    assert "## Processing and maturation: P01308 (4 feature(s))" in md
    lines = md.splitlines()
    assert lines[lines.index("### Signal (1)") + 1] == "- **1-24**"
    assert "- **25-54**  Insulin B chain" in lines
    assert "- **57-87**  C peptide" in lines
    assert "- **90-110**  Insulin A chain" in lines
    assert "Helix" not in md
    assert [f["type"] for f in payload["data"]["features"]] == [
        "Signal",
        "Peptide",
        "Propeptide",
        "Peptide",
    ]


# ---------------------------------------------------------------------------
# What a client is told about the tools
# ---------------------------------------------------------------------------


async def test_tool_descriptions_state_the_sequence_basis_and_the_pk_set() -> None:
    tools = {tool.name: tool for tool in await server.mcp.list_tools()}
    properties = " ".join((tools["uniprot_compute_properties"].description or "").split())
    assert "full canonical sequence, unprocessed" in properties
    assert "the precursor, not the mature chain" in properties
    assert "uniprot_get_processing_features" in properties
    assert "Bjellqvist pK set" in properties
    assert "Lehninger" not in properties
    dossier = " ".join((tools["uniprot_target_dossier"].description or "").split())
    assert "full canonical sequence, unprocessed" in dossier
    # The interface itself is unchanged.
    schema = tools["uniprot_compute_properties"].inputSchema
    assert schema["required"] == ["accession"]
    assert set(schema["properties"]) == {"accession", "response_format"}
    assert schema["properties"]["response_format"]["default"] == "markdown"
