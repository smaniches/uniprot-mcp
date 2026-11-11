"""``uniprot_lookup_variant`` checks the stated reference against the sequence.

A lookup such as ``K175H`` on an entry whose residue 175 is Arg, or
``R999H`` on a 393-residue entry, used to come back as an empty match with
the same advisory as a real change that UniProt simply does not annotate.
The tool now compares the stated residue and position with the canonical
sequence carried in the entry and reports which of the cases applies.

The entry used here is the first 20 residues of human p53 with one natural
variant, so every expected value can be read off the sequence below.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx

from uniprot_mcp import server
from uniprot_mcp.formatters import fmt_variant_lookup
from uniprot_mcp.server import uniprot_lookup_variant

# position    12345678901234567890
_SEQUENCE = "MEEPQSDPSVEPPLSQETFS"
_VARIANT = {
    "type": "Natural variant",
    "description": "in a test family",
    "location": {"start": {"value": 4}, "end": {"value": 4}},
    "alternativeSequence": {"originalSequence": "P", "alternativeSequences": ["L"]},
}


def _entry(sequence: Any = None) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "primaryAccession": "P04637",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "features": [_VARIANT],
    }
    if sequence is not None:
        entry["sequence"] = sequence
    return entry


_WITH_SEQUENCE = _entry({"value": _SEQUENCE, "length": len(_SEQUENCE)})
_ADVISORY = "No UniProt natural-variant feature matches"


async def _lookup(entry: dict[str, Any], change: str, fmt: str = "markdown") -> str:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(200, json=entry, headers={"X-UniProt-Release": "2026_04"})
        )
        out = await uniprot_lookup_variant("P04637", change, fmt)
        assert len(router.calls) == 1  # the check costs no extra request
    return out


# ---------------------------------------------------------------------------
# The four outcomes, through the tool
# ---------------------------------------------------------------------------


async def test_confirmed_reference_with_an_annotated_change() -> None:
    md = await _lookup(_WITH_SEQUENCE, "P4L")
    assert "## Variant lookup: P04637 P4L (1 match(es))" in md
    assert (
        "**Reference residue confirmed:** the canonical sequence of P04637 has P at position 4."
        in md
    )
    assert "### P4L" in md
    assert "in a test family" in md
    assert _ADVISORY not in md

    data = json.loads(await _lookup(_WITH_SEQUENCE, "P4L", "json"))["data"]
    assert data["accession"] == "P04637"
    assert data["change"] == "P4L"
    assert data["matches"] == [_VARIANT]
    assert data["reference_check"] == {
        "status": "reference_confirmed",
        "position": 4,
        "stated_residue": "P",
        "sequence_length": 20,
        "sequence_residue": "P",
    }


async def test_confirmed_reference_without_annotation_is_the_only_true_absence() -> None:
    """Glu 2 exists, and UniProt has no variant for E2K: the advisory about
    absent annotations applies here and only here."""
    md = await _lookup(_WITH_SEQUENCE, "E2K")
    assert "(0 match(es))" in md
    assert (
        "**Reference residue confirmed:** the canonical sequence of P04637 has E at position 2."
        in md
    )
    assert f"_{_ADVISORY} `E2K`." in md
    assert "This does not mean the variant is benign" in md
    assert "ClinVar" in md

    data = json.loads(await _lookup(_WITH_SEQUENCE, "E2K", "json"))["data"]
    assert data["matches"] == []
    assert data["reference_check"]["status"] == "reference_confirmed"
    assert data["reference_check"]["sequence_residue"] == "E"


async def test_wrong_reference_residue_is_reported_as_a_mismatch() -> None:
    md = await _lookup(_WITH_SEQUENCE, "K4L")
    assert "## Variant lookup: P04637 K4L (0 match(es))" in md
    assert (
        "**Reference residue mismatch:** the canonical sequence of P04637 has P at "
        "position 4, not K." in md
    )
    assert "`K4L` does not describe a change to this sequence" in md
    assert "isoform, mature-chain and legacy numbering" in md
    # Not presented as a change that merely lacks an annotation.
    assert _ADVISORY not in md
    assert "benign" not in md
    assert "confirmed" not in md

    data = json.loads(await _lookup(_WITH_SEQUENCE, "K4L", "json"))["data"]
    assert data["matches"] == []
    assert data["reference_check"] == {
        "status": "reference_mismatch",
        "position": 4,
        "stated_residue": "K",
        "sequence_length": 20,
        "sequence_residue": "P",
    }


async def test_position_beyond_the_sequence_is_reported_as_out_of_range() -> None:
    md = await _lookup(_WITH_SEQUENCE, "R999H")
    assert "## Variant lookup: P04637 R999H (0 match(es))" in md
    assert (
        "**Position out of range:** the canonical sequence of P04637 has 20 residues, "
        "so position 999 does not exist." in md
    )
    assert "`R999H` cannot be looked up on this sequence" in md
    assert _ADVISORY not in md
    assert "benign" not in md

    data = json.loads(await _lookup(_WITH_SEQUENCE, "R999H", "json"))["data"]
    assert data["matches"] == []
    assert data["reference_check"] == {
        "status": "position_out_of_range",
        "position": 999,
        "stated_residue": "R",
        "sequence_length": 20,
    }


async def test_last_residue_is_in_range_and_the_next_position_is_not() -> None:
    last = json.loads(await _lookup(_WITH_SEQUENCE, "S20A", "json"))["data"]["reference_check"]
    assert last["status"] == "reference_confirmed"
    assert last["sequence_residue"] == "S"
    beyond = json.loads(await _lookup(_WITH_SEQUENCE, "S21A", "json"))["data"]["reference_check"]
    assert beyond["status"] == "position_out_of_range"
    first = json.loads(await _lookup(_WITH_SEQUENCE, "M1V", "json"))["data"]["reference_check"]
    assert first["status"] == "reference_confirmed"
    assert first["sequence_residue"] == "M"


@pytest.mark.parametrize("sequence", [None, {}, {"value": ""}, {"value": None}, "MEEPQSDPSV"])
async def test_entry_without_a_usable_sequence_says_the_check_was_not_made(sequence: Any) -> None:
    """No sequence, no verdict: the result must not claim a confirmation,
    and the annotation lookup itself still works."""
    entry = _entry(sequence)
    md = await _lookup(entry, "E2K")
    assert "**Reference residue not checked:** the entry carried no sequence" in md
    assert "confirmed" not in md
    assert f"_{_ADVISORY} `E2K`." in md

    data = json.loads(await _lookup(entry, "P4L", "json"))["data"]
    assert data["matches"] == [_VARIANT]
    assert data["reference_check"] == {
        "status": "not_checked",
        "position": 4,
        "stated_residue": "P",
    }


async def test_sequence_case_does_not_matter() -> None:
    entry = _entry({"value": _SEQUENCE.lower()})
    data = json.loads(await _lookup(entry, "E2K", "json"))["data"]
    assert data["reference_check"]["status"] == "reference_confirmed"
    assert data["reference_check"]["sequence_residue"] == "E"


# ---------------------------------------------------------------------------
# The comparison itself
# ---------------------------------------------------------------------------


def test_check_variant_reference_statuses() -> None:
    entry = {"sequence": {"value": "MEEP"}}
    assert server._check_variant_reference(entry, "M", 1)["status"] == "reference_confirmed"
    assert server._check_variant_reference(entry, "P", 4)["status"] == "reference_confirmed"
    assert server._check_variant_reference(entry, "E", 4) == {
        "status": "reference_mismatch",
        "position": 4,
        "stated_residue": "E",
        "sequence_length": 4,
        "sequence_residue": "P",
    }
    assert server._check_variant_reference(entry, "P", 5) == {
        "status": "position_out_of_range",
        "position": 5,
        "stated_residue": "P",
        "sequence_length": 4,
    }
    assert server._check_variant_reference({}, "P", 4) == {
        "status": "not_checked",
        "position": 4,
        "stated_residue": "P",
    }


# ---------------------------------------------------------------------------
# Formatter: the argument is optional and changes nothing when absent
# ---------------------------------------------------------------------------


def test_formatter_without_a_check_keeps_its_previous_output() -> None:
    assert fmt_variant_lookup([], "P04637", "E2K") == (
        "## Variant lookup: P04637 E2K (0 match(es))\n"
        "\n"
        "_No UniProt natural-variant feature matches `E2K`. "
        "This does not mean the variant is benign — UniProt only annotates "
        "variants from the literature. See ClinVar / dbSNP for population data._"
    )
    assert json.loads(fmt_variant_lookup([], "P04637", "E2K", "json")) == {
        "accession": "P04637",
        "change": "E2K",
        "matches": [],
    }


def test_formatter_shows_matches_even_under_a_mismatch_notice() -> None:
    """Upstream data that contradict each other are shown, not reconciled:
    the notice and the annotated feature both appear."""
    check = {
        "status": "reference_mismatch",
        "position": 4,
        "stated_residue": "P",
        "sequence_length": 20,
        "sequence_residue": "A",
    }
    md = fmt_variant_lookup([_VARIANT], "P04637", "P4L", reference_check=check)
    assert "**Reference residue mismatch:**" in md
    assert "### P4L" in md
    assert _ADVISORY not in md


# ---------------------------------------------------------------------------
# What a client is told about the tool
# ---------------------------------------------------------------------------


async def test_tool_description_and_schema_describe_the_check() -> None:
    tools = {tool.name: tool for tool in await server.mcp.list_tools()}
    tool = tools["uniprot_lookup_variant"]
    description = " ".join((tool.description or "").split())
    assert "checked against the entry's canonical sequence" in description
    for status in (
        "reference_confirmed",
        "reference_mismatch",
        "position_out_of_range",
        "not_checked",
    ):
        assert f"``{status}``" in description
    assert "``reference_check.status`` in JSON" in description
    assert "does NOT mean a variant is benign" in description
    change = tool.inputSchema["properties"]["change"]
    assert "numbered on the UniProt canonical sequence" in change["description"]
    assert tool.inputSchema["required"] == ["accession", "change"]
    assert tool.inputSchema["properties"]["response_format"]["default"] == "markdown"
