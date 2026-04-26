"""Surgical tests targeting the operator-level mutations that the
existing cache test suite does not catch.

The first matrix mutmut run on `src/uniprot_mcp/cache.py` reported
7 mutants generated, 0 killed (cache: 0% kill rate at v1.1.0
baseline). The mutants that survive standard API-surface tests are
typically operator flips (``==`` → ``!=``), boolean negations
(``not x`` → ``x``), constant changes (``"utf-8"`` → ``"utf-9"``),
and isinstance-check removals.

Each test below names the *specific class of mutation* it kills.
The combined effect: the seven cache mutants should now be killed
by behavioural assertions, not just API-shape assertions.

Why this matters: the user's "radioactive material" framing —
a wrong cache implementation that *passes* the existing tests but
produces a different SHA-256 (mutated encoding) or returns
arbitrary cached objects (mutated isinstance check) is exactly
the kind of silent correctness defect a bio-pharma reviewer
would flag. These tests close that gap.
"""

from __future__ import annotations

import hashlib
import json

from uniprot_mcp.cache import ProvenanceCache, key_for

# ---------------------------------------------------------------------------
# key_for — SHA-256 of the URL bytes
# ---------------------------------------------------------------------------


def test_key_for_uses_utf8_encoding_specifically() -> None:
    """If the encoding argument were mutated (utf-8 → utf-16, latin-1, etc.),
    the resulting hash would differ. Pin the exact expected hash for an
    ASCII URL — any mutation of the encoding flips the digest."""
    url = "https://rest.uniprot.org/uniprotkb/P04637"
    expected = hashlib.sha256(url.encode("utf-8")).hexdigest()
    assert key_for(url) == expected
    # And confirm the alternative encoding produces a different digest
    # (so the test is not trivially satisfied by any encoding).
    different = hashlib.sha256(url.encode("utf-16")).hexdigest()
    assert key_for(url) != different


def test_key_for_handles_unicode_urls_consistently() -> None:
    """A non-ASCII URL must produce a stable SHA-256. Mutating the
    encoding argument would either crash or change the digest."""
    url = "https://example.org/protein/proté"  # Latin-1-incompatible char
    h = key_for(url)
    expected = hashlib.sha256(url.encode("utf-8")).hexdigest()
    assert h == expected
    assert len(h) == 64


def test_key_for_changes_when_url_byte_changes() -> None:
    """One-byte difference → fully-different hash (avalanche). Catches
    any mutation that truncates the URL or hashes a substring."""
    a = key_for("https://example.org/a")
    b = key_for("https://example.org/b")
    assert a != b
    # Hamming distance over the hex digest should be high (typical
    # avalanche). A bug that hashed only a prefix would produce two
    # identical hashes here.
    diff = sum(1 for x, y in zip(a, b, strict=False) if x != y)
    assert diff > 30, f"too few differing chars ({diff}) — suspect prefix-only hash"


# ---------------------------------------------------------------------------
# ProvenanceCache.read — guards against malformed cache contents
# ---------------------------------------------------------------------------


def test_read_returns_none_when_cached_json_is_a_list_not_a_dict(tmp_path) -> None:
    """The defensive ``if not isinstance(decoded, dict): return None``
    branch is the cache's guard against corrupted-but-parseable JSON.
    A mutation that removes the `not` would let a list pass through
    and break downstream callers. This test forces the branch."""
    cache = ProvenanceCache(tmp_path)
    bad = tmp_path / f"{key_for('https://x')}.json"
    bad.write_text("[1, 2, 3]", encoding="utf-8")
    assert cache.read("https://x") is None


def test_read_returns_none_when_cached_json_is_a_string(tmp_path) -> None:
    """Same defensive branch, with a different non-dict type."""
    cache = ProvenanceCache(tmp_path)
    bad = tmp_path / f"{key_for('https://x')}.json"
    bad.write_text('"not a dict"', encoding="utf-8")
    assert cache.read("https://x") is None


def test_read_returns_none_when_cached_json_is_a_number(tmp_path) -> None:
    cache = ProvenanceCache(tmp_path)
    bad = tmp_path / f"{key_for('https://x')}.json"
    bad.write_text("42", encoding="utf-8")
    assert cache.read("https://x") is None


def test_read_returns_dict_when_cached_json_is_a_dict(tmp_path) -> None:
    """The positive case: a real dict must pass through. Without this
    test, a mutation that returned None even for valid dicts would
    not be caught by the "cache returns None when corrupt" tests."""
    cache = ProvenanceCache(tmp_path)
    good = tmp_path / f"{key_for('https://y')}.json"
    good.write_text(json.dumps({"url": "https://y", "body_text": ""}), encoding="utf-8")
    payload = cache.read("https://y")
    assert payload is not None
    assert isinstance(payload, dict)
    assert payload["url"] == "https://y"


# ---------------------------------------------------------------------------
# ProvenanceCache.has — boolean correctness
# ---------------------------------------------------------------------------


def test_has_returns_true_when_entry_exists(tmp_path) -> None:
    """Catches a mutation that flips the boolean (``has`` returning the
    opposite of presence)."""
    cache = ProvenanceCache(tmp_path)
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-26T12:00:00Z",
        "url": "https://rest.uniprot.org/uniprotkb/P04637",
        "response_sha256": "0" * 64,
    }
    cache.write(prov["url"], '{"a": 1}', prov)  # type: ignore[arg-type]
    assert cache.has(prov["url"]) is True


def test_has_returns_false_when_entry_absent(tmp_path) -> None:
    cache = ProvenanceCache(tmp_path)
    assert cache.has("https://rest.uniprot.org/uniprotkb/P00000") is False


def test_has_distinguishes_two_different_urls(tmp_path) -> None:
    """A mutation that uses a fixed (constant) cache key would return
    True for any URL once the first is cached. Defends the URL-keyed
    behaviour."""
    cache = ProvenanceCache(tmp_path)
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-26T12:00:00Z",
        "url": "https://rest.uniprot.org/uniprotkb/P04637",
        "response_sha256": "0" * 64,
    }
    cache.write(prov["url"], '{"a": 1}', prov)  # type: ignore[arg-type]
    assert cache.has("https://rest.uniprot.org/uniprotkb/P04637") is True
    assert cache.has("https://rest.uniprot.org/uniprotkb/P38398") is False


# ---------------------------------------------------------------------------
# ProvenanceCache.write — atomic, content-addressed
# ---------------------------------------------------------------------------


def test_write_creates_base_directory_if_absent(tmp_path) -> None:
    """The ``self.base_dir.mkdir(parents=True, exist_ok=True)`` call
    must succeed when the directory does not exist. A mutation that
    drops `parents=True` or changes `exist_ok` would crash here."""
    nested = tmp_path / "deep" / "nested" / "cache"
    cache = ProvenanceCache(nested)
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-26T12:00:00Z",
        "url": "https://x",
        "response_sha256": "0" * 64,
    }
    target = cache.write("https://x", '{"a": 1}', prov)  # type: ignore[arg-type]
    assert target.exists()
    assert nested.exists() and nested.is_dir()


def test_write_filename_is_sha256_hex_of_url(tmp_path) -> None:
    """The cache file's stem must equal SHA-256(url) — content
    addressing. A mutation that swapped to MD5 or a substring would
    produce a different filename."""
    cache = ProvenanceCache(tmp_path)
    url = "https://rest.uniprot.org/uniprotkb/P04637"
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-26T12:00:00Z",
        "url": url,
        "response_sha256": "0" * 64,
    }
    target = cache.write(url, "{}", prov)  # type: ignore[arg-type]
    expected_stem = hashlib.sha256(url.encode("utf-8")).hexdigest()
    assert target.name == f"{expected_stem}.json"
    assert target.suffix == ".json"


def test_write_payload_contains_url_body_and_provenance(tmp_path) -> None:
    """A mutation that dropped one of the three top-level keys
    (url / body_text / provenance) would silently corrupt every
    cached entry. Defend the payload schema."""
    cache = ProvenanceCache(tmp_path)
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-26T12:00:00Z",
        "url": "https://x",
        "response_sha256": "0" * 64,
    }
    target = cache.write("https://x", "BODY-CONTENT", prov)  # type: ignore[arg-type]
    raw = json.loads(target.read_text(encoding="utf-8"))
    assert raw["url"] == "https://x"
    assert raw["body_text"] == "BODY-CONTENT"
    assert raw["provenance"]["release"] == "2026_01"
    # All three fields must be present — mutation that emits two of three breaks downstream.
    assert set(raw.keys()) == {"url", "body_text", "provenance"}


def test_write_payload_is_valid_utf8_json(tmp_path) -> None:
    """A mutation of the encoding argument (``encode("utf-8")`` →
    something else) would produce bytes that don't decode. Defend
    the encoding."""
    cache = ProvenanceCache(tmp_path)
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-26T12:00:00Z",
        "url": "https://uniprot.example.org/é",  # non-ASCII char in URL
        "response_sha256": "0" * 64,
    }
    target = cache.write(prov["url"], "BODY", prov)  # type: ignore[arg-type]
    # Read as UTF-8; must parse successfully.
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["url"] == prov["url"]


def test_write_returns_path_pointing_at_real_file(tmp_path) -> None:
    """The return value must be the actual file. A mutation that
    returned ``None`` or the temp-file path (instead of the final
    path after os.replace) would break callers."""
    cache = ProvenanceCache(tmp_path)
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-26T12:00:00Z",
        "url": "https://x",
        "response_sha256": "0" * 64,
    }
    target = cache.write("https://x", "{}", prov)  # type: ignore[arg-type]
    assert target.exists()
    assert target.is_file()
    assert target.suffix == ".json"
    # The returned path must be inside the configured cache dir.
    assert target.parent == tmp_path.resolve()


def test_write_then_read_preserves_body_byte_for_byte(tmp_path) -> None:
    """A round-trip on a body containing every printable ASCII byte
    plus newlines plus non-ASCII characters must preserve every byte.
    Catches any mutation that dropped, replaced, or re-encoded the body."""
    cache = ProvenanceCache(tmp_path)
    body = "".join(chr(c) for c in range(32, 127)) + "\n" + "héllo wörld 🧬"
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-26T12:00:00Z",
        "url": "https://x",
        "response_sha256": "0" * 64,
    }
    cache.write("https://x", body, prov)  # type: ignore[arg-type]
    payload = cache.read("https://x")
    assert payload is not None
    assert payload["body_text"] == body
