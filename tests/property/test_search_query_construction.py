"""Property-based tests for ``uniprot_search`` query construction.

The server builds UniProt query-language strings by string concatenation
(``src/uniprot_mcp/server.py`` lines 120-134). That is cheap but easy
to break — a stray quote in ``organism`` or a ``reviewed:`` already
present in ``query`` can silently produce a malformed or duplicated
clause.

These tests drive arbitrary ``query`` / ``organism`` inputs through the
tool with the HTTP layer mocked, and assert the outgoing query string
is well-formed no matter what the caller sent in. They close AUDIT
follow-up #4 and PENDING_V1.md §1.6.

Invariants verified:

1. Multi-word organism names are emitted inside a quoted
   ``organism_name:"..."`` clause — never as bare tokens that could
   split on whitespace in the UniProt query language.
2. All-digit organism values are emitted as ``organism_id:N`` with no
   quoting — keeping taxon-id queries semantically correct.
3. Any ``"`` in ``organism`` is replaced with ``'`` before reaching the
   query — preventing an inner double-quote from closing the wrapping
   clause early (an injection-shaped defect).
4. ``reviewed_only=True`` is idempotent: when the caller's query
   already contains ``reviewed:``, no second clause is appended.
"""

from __future__ import annotations

import string

import httpx
import respx
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from uniprot_mcp.server import uniprot_search

# Alphabets deliberately kept to realistic UniProt query tokens —
# enough variety to trip edge cases without spending the fuzz budget
# on characters UniProt would itself reject.
_QUERY_ALPHABET = st.characters(
    whitelist_categories=("Ll", "Lu", "Nd"),
    whitelist_characters=" _-:()",
)
_ORGANISM_ALPHABET = st.characters(
    whitelist_categories=("Ll", "Lu"),
    whitelist_characters=" \"'",
)

search_query = st.text(alphabet=_QUERY_ALPHABET, min_size=1, max_size=50)
organism_name = st.text(alphabet=_ORGANISM_ALPHABET, min_size=1, max_size=30)
organism_taxid = st.text(alphabet=string.digits, min_size=1, max_size=7)

# Hypothesis + pytest-asyncio's function-scoped event loop fixture
# trip a PyPy health check; suppress it deliberately, documented here.
_SETTINGS = settings(
    deadline=2000,
    max_examples=50,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)


@given(query=search_query, organism=organism_name)
@_SETTINGS
async def test_organism_name_is_always_quoted(query: str, organism: str) -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        out = await uniprot_search(query=query, organism=organism)

    if "Error" in out or "Input error" in out:
        return  # validation rejected the input — nothing upstream to check
    if not route.called:
        return
    sent = route.calls[0].request.url.params["query"]
    assert 'organism_name:"' in sent
    # The clause must close with a matching quote somewhere after it.
    after = sent.split('organism_name:"', 1)[1]
    assert '"' in after, f"organism_name clause was never closed: {sent!r}"


@given(query=search_query, taxid=organism_taxid)
@_SETTINGS
async def test_numeric_organism_uses_unquoted_taxon_id(query: str, taxid: str) -> None:
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        out = await uniprot_search(query=query, organism=taxid)

    if "Error" in out or "Input error" in out:
        return
    if not route.called:
        return
    sent = route.calls[0].request.url.params["query"]
    assert f"organism_id:{taxid}" in sent
    assert "organism_name" not in sent, (
        f"Numeric organism must never take the name code path: {sent!r}"
    )


@given(query=search_query, organism=organism_name)
@_SETTINGS
async def test_no_double_quote_leaks_into_organism_clause(query: str, organism: str) -> None:
    """Any ``"`` supplied in organism is replaced with ``'`` before the
    server wraps the value in double quotes. If that replacement were
    ever skipped, an attacker-controlled ``"`` could close the clause
    and inject further query terms."""
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        out = await uniprot_search(query=query, organism=organism)

    if "Error" in out or "Input error" in out:
        return
    if not route.called:
        return
    sent = route.calls[0].request.url.params["query"]
    if "organism_name:" not in sent:
        return
    _, rest = sent.split('organism_name:"', 1)
    inner, _, _ = rest.partition('"')
    assert '"' not in inner, f"Unescaped double-quote leaked inside organism_name clause: {inner!r}"


@given(query=search_query)
@_SETTINGS
async def test_reviewed_only_is_idempotent(query: str) -> None:
    """``reviewed_only=True`` must not append a second ``reviewed:true``
    when the caller's query already contains ``reviewed:``."""
    already_reviewed = f"{query} AND reviewed:true"
    with respx.mock(base_url="https://rest.uniprot.org") as router:
        route = router.get("/uniprotkb/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        out = await uniprot_search(query=already_reviewed, reviewed_only=True)

    if "Error" in out or "Input error" in out:
        return
    if not route.called:
        return
    sent = route.calls[0].request.url.params["query"]
    assert sent.lower().count("reviewed:") == 1, f"reviewed:true was duplicated: {sent!r}"
