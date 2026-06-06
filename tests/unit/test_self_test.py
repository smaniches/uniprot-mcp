"""Cover the `_self_test` helper end-to-end with a mocked upstream."""

from __future__ import annotations

import httpx
import respx

from uniprot_mcp import server


def test_self_test_passes_with_mocked_upstream(capsys) -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={
                    "primaryAccession": "P04637",
                    "genes": [{"geneName": {"value": "TP53"}}],
                },
            )
        )
        rc = server._self_test()
    assert rc == 0
    captured = capsys.readouterr()
    assert "[PASS]" in captured.err
    # The self-test must emit a real per-response provenance footer
    # (claim C2): the Source/Query/SHA-256 block, not just smoke status.
    assert "[provenance]" in captured.err
    assert "_Source:" in captured.err
    assert "_SHA-256:" in captured.err


def test_self_test_fails_when_upstream_returns_wrong_gene(capsys) -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        router.get("/uniprotkb/P04637").mock(
            return_value=httpx.Response(
                200,
                json={
                    "primaryAccession": "P04637",
                    "genes": [{"geneName": {"value": "NOT_TP53"}}],
                },
            )
        )
        rc = server._self_test()
    assert rc == 2
    captured = capsys.readouterr()
    assert "[FAIL]" in captured.err
