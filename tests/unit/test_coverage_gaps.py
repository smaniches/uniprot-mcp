"""Targeted tests that lift coverage to 99%.

Each test here is pinned to a specific uncovered line reported by
pytest-cov. Do not delete a test without verifying that its target line
is reachable from some other test first.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from typing import ClassVar
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx

from uniprot_mcp import server
from uniprot_mcp.client import (
    MAX_RETRY_AFTER_SECONDS,
    UniProtClient,
    parse_retry_after,
)
from uniprot_mcp.formatters import (
    fmt_crossrefs,
    fmt_entry,
    fmt_features,
    fmt_go,
    fmt_idmapping,
    fmt_search,
    fmt_taxonomy,
    fmt_variants,
    is_swissprot,
)
from uniprot_mcp.server import (
    _check_accession,
    _InputError,
    uniprot_batch_entries,
    uniprot_get_cross_refs,
    uniprot_get_features,
    uniprot_get_go_terms,
    uniprot_get_sequence,
    uniprot_get_variants,
    uniprot_id_mapping,
    uniprot_search,
    uniprot_taxonomy_search,
)

# ---------------------------------------------------------------------------
# parse_retry_after edge cases (client.py:65, 67)
# ---------------------------------------------------------------------------


def test_retry_after_empty_string_returns_backoff() -> None:
    """Empty string is falsy -> fallback path."""
    assert parse_retry_after("", 0) > 0


def test_retry_after_naive_http_date_is_treated_as_utc() -> None:
    """HTTP-date without explicit tz gets UTC applied (line 67)."""
    future = datetime.now(tz=UTC) + timedelta(seconds=30)
    # Strip TZ to force the `dt.tzinfo is None` branch.
    header = future.replace(tzinfo=None).strftime("%a, %d %b %Y %H:%M:%S")
    delay = parse_retry_after(header, 0)
    assert 0 <= delay <= MAX_RETRY_AFTER_SECONDS


def test_retry_after_parsedate_returns_none() -> None:
    """Header that passes parsedate_to_datetime but yields None (line 65)."""
    # email.utils.parsedate_to_datetime returns a datetime; to hit the None
    # branch we patch it to return None.
    with patch("uniprot_mcp.client.parsedate_to_datetime", return_value=None):
        assert parse_retry_after("Anything goes", 0) > 0


# ---------------------------------------------------------------------------
# client._req TimeoutException branch (client.py:113)
# ---------------------------------------------------------------------------


async def test_req_retries_on_timeout_then_succeeds() -> None:
    timeouts_then_ok = [
        httpx.TimeoutException("slow"),
        httpx.Response(200, json={"primaryAccession": "P04637"}),
    ]

    def _side(req):  # type: ignore[no-untyped-def]
        reply = timeouts_then_ok.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(side_effect=_side)
        client = UniProtClient()
        try:
            data = await client.get_entry("P04637")
        finally:
            await client.close()
    assert data["primaryAccession"] == "P04637"


async def test_req_gives_up_after_persistent_timeouts() -> None:
    def _always_timeout(req):  # type: ignore[no-untyped-def]
        raise httpx.TimeoutException("persistent")

    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(side_effect=_always_timeout)
        client = UniProtClient()
        try:
            with pytest.raises(RuntimeError, match="Request failed"):
                await client.get_entry("P04637")
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# client.search with `fields` parameter (client.py:125)
# ---------------------------------------------------------------------------


async def test_search_passes_fields_parameter() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        client = UniProtClient()
        try:
            await client.search("p53", size=5, fields=["accession", "gene_names"])
        finally:
            await client.close()
    sent = route.calls[0].request.url
    assert "fields=accession%2Cgene_names" in str(sent) or "fields=accession,gene_names" in str(
        sent
    )


# ---------------------------------------------------------------------------
# id_mapping_submit retry branches (client.py:143-144, 146-147, 151-153)
# ---------------------------------------------------------------------------


async def test_id_mapping_submit_retries_on_429() -> None:
    replies = iter(
        [
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"jobId": "J1"}),
        ]
    )
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.post("/idmapping/run").mock(side_effect=lambda req: next(replies))
        client = UniProtClient()
        try:
            jid = await client.id_mapping_submit("Gene_Name", "UniProtKB", ["BRCA1"])
        finally:
            await client.close()
    assert jid == "J1"


async def test_id_mapping_submit_retries_on_5xx() -> None:
    replies = iter(
        [
            httpx.Response(503),
            httpx.Response(200, json={"jobId": "J2"}),
        ]
    )
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.post("/idmapping/run").mock(side_effect=lambda req: next(replies))
        client = UniProtClient()
        try:
            jid = await client.id_mapping_submit("Gene_Name", "UniProtKB", ["BRCA1"])
        finally:
            await client.close()
    assert jid == "J2"


async def test_id_mapping_submit_retries_on_timeout() -> None:
    def _side(req):  # type: ignore[no-untyped-def]
        raise httpx.TimeoutException("slow")

    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.post("/idmapping/run").mock(side_effect=_side)
        client = UniProtClient()
        try:
            with pytest.raises(RuntimeError, match="id_mapping_submit failed"):
                await client.id_mapping_submit("Gene_Name", "UniProtKB", ["BRCA1"])
        finally:
            await client.close()


# ---------------------------------------------------------------------------
# id_mapping_results redirectURL + fall-through branches (client.py:163-167)
# ---------------------------------------------------------------------------


async def test_id_mapping_results_follows_redirect() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/idmapping/status/JOBR").mock(
            return_value=httpx.Response(200, json={"redirectURL": "/idmapping/results/JOBR"})
        )
        router.get("/idmapping/results/JOBR").mock(
            return_value=httpx.Response(200, json={"results": [{"from": "X", "to": "Y"}]})
        )
        client = UniProtClient()
        try:
            out = await client.id_mapping_results("JOBR")
        finally:
            await client.close()
    assert out["results"][0]["from"] == "X"


async def test_id_mapping_results_raises_on_timeout() -> None:
    # 30 polls of "something else" -> never returns, raises TimeoutError.
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/idmapping/status/JOBT").mock(
            return_value=httpx.Response(200, json={"jobStatus": "NEW"})
        )
        client = UniProtClient()
        # Patch asyncio.sleep to return immediately to keep the test fast.
        with patch("uniprot_mcp.client.asyncio.sleep", new=AsyncMock(return_value=None)):
            try:
                with pytest.raises(TimeoutError, match="did not complete"):
                    await client.id_mapping_results("JOBT")
            finally:
                await client.close()


# ---------------------------------------------------------------------------
# batch_entries caps at 100 (client.py:188)
# ---------------------------------------------------------------------------


async def test_batch_entries_caps_valid_at_100() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        # 150 valid accessions (P00000..P00149).
        many = [f"P{i:05d}" for i in range(150)]
        client = UniProtClient()
        try:
            await client.batch_entries(many)
        finally:
            await client.close()
    sent = int(route.calls[0].request.url.params["size"])
    assert sent == 100


# ---------------------------------------------------------------------------
# Formatter empty / fallback paths (formatters.py: 38-41, 47, 111, 130, 144, 157, 194 etc)
# ---------------------------------------------------------------------------


def test_fmt_entry_falls_back_to_submission_name() -> None:
    entry = {
        "primaryAccession": "Q99999",
        "entryType": "UniProtKB unreviewed (TrEMBL)",
        "proteinDescription": {"submissionNames": [{"fullName": {"value": "Putative protein"}}]},
        "genes": [],
        "organism": {"scientificName": "Unknown"},
    }
    out = fmt_entry(entry)
    assert "Q99999" in out
    assert "Putative protein" in out
    assert "TrEMBL" in out


def test_fmt_entry_unknown_name_when_nothing_provided() -> None:
    entry = {
        "primaryAccession": "X00000",
        "entryType": "UniProtKB unreviewed (TrEMBL)",
        "proteinDescription": {},
        "organism": {},
    }
    out = fmt_entry(entry)
    assert "Unknown" in out


def test_fmt_entry_no_gene_section() -> None:
    entry = {
        "primaryAccession": "P01234",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "X"}}},
        "genes": [],
        "organism": {"scientificName": "Mus musculus"},
    }
    out = fmt_entry(entry)
    assert "**Gene:**" not in out


def test_is_swissprot_false_for_trembl() -> None:
    assert is_swissprot({"entryType": "UniProtKB unreviewed (TrEMBL)"}) is False


def test_fmt_search_empty() -> None:
    assert "0 results" in fmt_search({"results": []})


def test_fmt_search_json() -> None:
    out = fmt_search({"results": []}, "json")
    assert out.startswith("{")


def test_fmt_features_json() -> None:
    out = fmt_features([], "P01234", "json")
    assert out == "[]"


def test_fmt_features_truncates_over_twenty() -> None:
    feats = [
        {
            "type": "Domain",
            "description": f"d{i}",
            "location": {"start": {"value": i}, "end": {"value": i + 1}},
        }
        for i in range(25)
    ]
    out = fmt_features(feats, "P01234", "markdown")
    assert "+5 more" in out


def test_fmt_go_json() -> None:
    assert fmt_go([], "P01234", None, "json") == "[]"


def test_fmt_crossrefs_json_with_filter() -> None:
    xrefs = [{"database": "PDB", "id": "1ABC"}, {"database": "GO", "id": "GO:0000"}]
    out = fmt_crossrefs(xrefs, "P01234", "PDB", "json")
    assert "1ABC" in out
    assert "GO" not in out


def test_fmt_variants_truncates_over_fifty() -> None:
    variants = [
        {
            "type": "Natural variant",
            "location": {"start": {"value": i}},
            "alternativeSequence": {"originalSequence": "A", "alternativeSequences": ["V"]},
        }
        for i in range(55)
    ]
    out = fmt_variants(variants, "P01234")
    assert "+5 more" in out


def test_fmt_variants_json() -> None:
    assert fmt_variants([], "P01234", "json") == "[]"


def test_fmt_idmapping_truncates_and_json() -> None:
    data = {
        "results": [{"from": f"g{i}", "to": {"primaryAccession": f"P{i:05d}"}} for i in range(55)],
        "failedIds": [f"f{i}" for i in range(25)],
    }
    md = fmt_idmapping(data)
    assert "+5 more" in md
    assert "Failed:" in md
    js = fmt_idmapping(data, "json")
    assert js.startswith("{")


def test_fmt_idmapping_scalar_to() -> None:
    data = {"results": [{"from": "X", "to": "plain-scalar"}], "failedIds": []}
    out = fmt_idmapping(data)
    assert "plain-scalar" in out


def test_fmt_taxonomy_json() -> None:
    out = fmt_taxonomy({"results": []}, "json")
    assert out.startswith("{")


# ---------------------------------------------------------------------------
# Server tool exception paths (server.py 150-151, 193-194, 212-213, 228-229,
# 253-254, 275-276, 293-294)
# ---------------------------------------------------------------------------


async def test_get_sequence_masks_runtime_error() -> None:
    """Upstream 4xx -> httpx.HTTPStatusError -> caught + masked."""
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(400))
        out = await uniprot_get_sequence("P04637")
    assert "Error in uniprot_get_sequence" in out


async def test_get_go_terms_rejects_bad_aspect() -> None:
    out = await uniprot_get_go_terms("P04637", "X")
    assert "aspect must be" in out


async def test_get_go_terms_masks_upstream_error() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(400))
        out = await uniprot_get_go_terms("P04637")
    assert "Error in uniprot_get_go_terms" in out


async def test_get_cross_refs_masks_upstream_error() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(400))
        out = await uniprot_get_cross_refs("P04637")
    assert "Error in uniprot_get_cross_refs" in out


async def test_get_variants_masks_upstream_error() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(400))
        out = await uniprot_get_variants("P04637")
    assert "Error in uniprot_get_variants" in out


async def test_id_mapping_rejects_empty_ids() -> None:
    out = await uniprot_id_mapping("", "Gene_Name", "UniProtKB")
    assert "ids must contain at least one" in out


async def test_id_mapping_rejects_over_100_ids() -> None:
    ids = ",".join(f"G{i}" for i in range(101))
    out = await uniprot_id_mapping(ids, "Gene_Name", "UniProtKB")
    assert "cannot exceed 100" in out


async def test_id_mapping_masks_upstream_error() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.post("/idmapping/run").mock(return_value=httpx.Response(400))
        out = await uniprot_id_mapping("BRCA1", "Gene_Name", "UniProtKB")
    assert "Error in uniprot_id_mapping" in out


async def test_batch_entries_oversize_input() -> None:
    huge = ",".join(["P04637"] * 2000)  # 12k chars, exceeds MAX_IDS_LEN
    out = await uniprot_batch_entries(huge)
    assert "Input error" in out


async def test_taxonomy_search_masks_upstream_error() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/taxonomy/search").mock(return_value=httpx.Response(400))
        out = await uniprot_taxonomy_search("Homo sapiens")
    assert "Error in uniprot_taxonomy_search" in out


async def test_search_masks_upstream_error() -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/search").mock(return_value=httpx.Response(400))
        out = await uniprot_search("kinase")
    assert "Error in uniprot_search" in out


async def test_get_features_with_filter_happy_path() -> None:
    entry = {
        "primaryAccession": "P04637",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "p53"}}},
        "genes": [{"geneName": {"value": "TP53"}}],
        "organism": {"scientificName": "Homo sapiens"},
        "features": [
            {
                "type": "Domain",
                "description": "A",
                "location": {"start": {"value": 1}, "end": {"value": 5}},
            },
            {
                "type": "Other",
                "description": "B",
                "location": {"start": {"value": 10}, "end": {"value": 12}},
            },
        ],
    }
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=entry))
        out = await uniprot_get_features("P04637", "Domain")
    assert "Domain" in out


# ---------------------------------------------------------------------------
# server._check_accession success path still enforced via _safe_error (server.py 316->319)
# ---------------------------------------------------------------------------


def test_self_test_no_tool_manager(monkeypatch, capsys) -> None:
    """Branch: _tool_manager absent -> registered stays empty."""
    monkeypatch.setattr(server.mcp, "_tool_manager", None, raising=False)
    rc = server._self_test()
    # Missing tools -> rc == 1
    assert rc == 1
    captured = capsys.readouterr()
    assert "missing tools" in captured.err


def test_self_test_extra_tool_warning(monkeypatch, capsys) -> None:
    """Branch: extra tools registered -> WARN logged but still PASS."""

    class _FakeMgr:
        _tools: ClassVar[dict[str, None]] = {
            "uniprot_get_entry": None,
            "uniprot_search": None,
            "uniprot_get_sequence": None,
            "uniprot_get_features": None,
            "uniprot_get_variants": None,
            "uniprot_get_go_terms": None,
            "uniprot_get_cross_refs": None,
            "uniprot_id_mapping": None,
            "uniprot_batch_entries": None,
            "uniprot_taxonomy_search": None,
            "uniprot_get_keyword": None,
            "uniprot_search_keywords": None,
            "uniprot_get_subcellular_location": None,
            "uniprot_search_subcellular_locations": None,
            "uniprot_get_uniref": None,
            "uniprot_search_uniref": None,
            "uniprot_provenance_verify": None,
            "unexpected_extra_tool": None,
        }

    monkeypatch.setattr(server.mcp, "_tool_manager", _FakeMgr(), raising=False)
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={"primaryAccession": "P04637", "genes": [{"geneName": {"value": "TP53"}}]},
            )
        )
        rc = server._self_test()
    assert rc == 0
    captured = capsys.readouterr()
    assert "unexpected_extra_tool" in captured.err


# ---------------------------------------------------------------------------
# server.main() CLI entry (server.py 346-348)
# ---------------------------------------------------------------------------


def test_main_runs_mcp(monkeypatch) -> None:
    called: list[bool] = []

    def _fake_run() -> None:
        called.append(True)

    monkeypatch.setattr(server.mcp, "run", _fake_run)
    monkeypatch.setattr(sys, "argv", ["uniprot-mcp"])
    server.main()
    assert called == [True]


def test_main_self_test_dispatches(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["uniprot-mcp", "--self-test"])
    monkeypatch.setattr(server, "_self_test", lambda: 0)
    with pytest.raises(SystemExit) as exc_info:
        server.main()
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# Helper-function edge cases (server.py)
# ---------------------------------------------------------------------------


def test_check_accession_accepts_lowercase_via_upper() -> None:
    _check_accession("p04637")  # must not raise


def test_check_accession_empty_rejected() -> None:
    with pytest.raises(_InputError):
        _check_accession("")


# ---------------------------------------------------------------------------
# Final branch-coverage trims to reach 99% (client.py:188, server.py:270,
# formatters.py:78->74, 86->74, 88->74, 90->74, 102->106)
# ---------------------------------------------------------------------------


async def test_batch_entries_client_fields_param() -> None:
    """Covers client.py:188 (if fields: branch)."""
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        client = UniProtClient()
        try:
            await client.batch_entries(["P04637"], fields=["accession", "gene_names"])
        finally:
            await client.close()
    assert "fields" in str(route.calls[0].request.url)


async def test_batch_entries_server_appends_invalid_suffix() -> None:
    """Covers server.py:270 (invalid-accessions suffix)."""
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": [{"primaryAccession": "P04637"}]})
        )
        out = await uniprot_batch_entries("P04637,BADTOK")
    assert "Skipped 1 invalid" in out


def test_fmt_entry_function_with_empty_texts() -> None:
    """Covers formatters.py:78->74 (FUNCTION comment with empty texts)."""
    entry = {
        "primaryAccession": "P01234",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "X"}}},
        "genes": [{"geneName": {"value": "G"}}],
        "organism": {"scientificName": "Homo sapiens"},
        "comments": [{"commentType": "FUNCTION", "texts": []}],
    }
    out = fmt_entry(entry)
    assert "**Function:**" not in out


def test_fmt_entry_subcellular_without_locations() -> None:
    """Covers formatters.py:86->74 (SUBCELLULAR LOCATION with no usable locs)."""
    entry = {
        "primaryAccession": "P01234",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "X"}}},
        "genes": [{"geneName": {"value": "G"}}],
        "organism": {"scientificName": "Homo sapiens"},
        "comments": [{"commentType": "SUBCELLULAR LOCATION", "subcellularLocations": []}],
    }
    out = fmt_entry(entry)
    assert "**Localization:**" not in out


def test_fmt_entry_ignores_unknown_comment_types() -> None:
    """Covers formatters.py:88->74 (elif chain falls through for unknown type)."""
    entry = {
        "primaryAccession": "P01234",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "X"}}},
        "genes": [{"geneName": {"value": "G"}}],
        "organism": {"scientificName": "Homo sapiens"},
        "comments": [{"commentType": "COFACTOR"}],  # not FUNCTION/SUBCELL/DISEASE
    }
    out = fmt_entry(entry)
    # No crash, no special block emitted for unknown type.
    assert "**Gene:** G" in out


def test_fmt_entry_disease_with_empty_dict() -> None:
    """Covers formatters.py:90->74 (DISEASE comment with empty disease dict)."""
    entry = {
        "primaryAccession": "P01234",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "X"}}},
        "genes": [{"geneName": {"value": "G"}}],
        "organism": {"scientificName": "Homo sapiens"},
        "comments": [{"commentType": "DISEASE", "disease": {}}],
    }
    out = fmt_entry(entry)
    assert "**Disease:**" not in out


def test_fmt_entry_crossrefs_without_pdb_entries() -> None:
    """Covers formatters.py:102->106 (crossrefs present but no PDB rows)."""
    entry = {
        "primaryAccession": "P01234",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "X"}}},
        "genes": [{"geneName": {"value": "G"}}],
        "organism": {"scientificName": "Homo sapiens"},
        "uniProtKBCrossReferences": [{"database": "GO", "id": "GO:0005634"}],
    }
    out = fmt_entry(entry)
    assert "Cross-refs" in out
    assert "**PDB:**" not in out


async def test_get_features_branch_when_feature_types_empty_string() -> None:
    """Covers server.py:169->172 (feature_types is '' -> skip filter)."""
    entry = {
        "primaryAccession": "P04637",
        "entryType": "UniProtKB reviewed (Swiss-Prot)",
        "proteinDescription": {"recommendedName": {"fullName": {"value": "p53"}}},
        "genes": [{"geneName": {"value": "TP53"}}],
        "organism": {"scientificName": "Homo sapiens"},
        "features": [
            {
                "type": "Domain",
                "description": "A",
                "location": {"start": {"value": 1}, "end": {"value": 5}},
            }
        ],
    }
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(return_value=httpx.Response(200, json=entry))
        out = await uniprot_get_features("P04637", "")  # empty feature_types -> no filter
    assert "Domain" in out
