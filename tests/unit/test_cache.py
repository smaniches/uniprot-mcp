"""Tests for the local provenance cache (A3).

Two layers:

  - ``src/uniprot_mcp/cache.py``         — atomic file-system cache
  - ``server.uniprot_replay_from_cache`` — MCP tool reading the cache

Cache writing is opt-in via the ``UNIPROT_MCP_CACHE_DIR`` env var —
the test suite uses ``tmp_path`` so no real filesystem state leaks
between tests.
"""

from __future__ import annotations

import json

import pytest

from uniprot_mcp.cache import (
    CACHE_DIR_ENV,
    ProvenanceCache,
    cache_dir_from_env,
    key_for,
)
from uniprot_mcp.server import uniprot_replay_from_cache

# ---------------------------------------------------------------------------
# Pure-Python cache layer
# ---------------------------------------------------------------------------


def test_key_for_is_deterministic_sha256() -> None:
    a = key_for("https://rest.uniprot.org/uniprotkb/P04637")
    b = key_for("https://rest.uniprot.org/uniprotkb/P04637")
    c = key_for("https://rest.uniprot.org/uniprotkb/P38398")
    assert a == b
    assert a != c
    # SHA-256 is 64 lowercase hex chars
    assert len(a) == 64
    assert all(ch in "0123456789abcdef" for ch in a)


def test_cache_write_then_read_roundtrip(tmp_path) -> None:
    cache = ProvenanceCache(tmp_path)
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-25T12:00:00Z",
        "url": "https://rest.uniprot.org/uniprotkb/P04637",
        "response_sha256": "0" * 64,
    }
    body = '{"primaryAccession": "P04637"}'
    target = cache.write(prov["url"], body, prov)  # type: ignore[arg-type]
    assert target.exists()
    payload = cache.read(prov["url"])
    assert payload is not None
    assert payload["url"] == prov["url"]
    assert payload["body_text"] == body
    assert payload["provenance"]["release"] == "2026_01"


def test_cache_write_overwrites_atomically(tmp_path) -> None:
    """Two writes to the same URL leave only the latest payload —
    no stray .tmp files."""
    cache = ProvenanceCache(tmp_path)
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-25T12:00:00Z",
        "url": "https://rest.uniprot.org/uniprotkb/P04637",
        "response_sha256": "0" * 64,
    }
    cache.write(prov["url"], "old body", prov)  # type: ignore[arg-type]
    cache.write(prov["url"], "new body", prov)  # type: ignore[arg-type]
    payload = cache.read(prov["url"])
    assert payload is not None
    assert payload["body_text"] == "new body"
    # No leftover .tmp files in the cache directory.
    leftovers = [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == [], f"atomic write leaked: {leftovers}"


def test_cache_read_returns_none_when_absent(tmp_path) -> None:
    cache = ProvenanceCache(tmp_path)
    assert cache.read("https://rest.uniprot.org/uniprotkb/P00000") is None


def test_cache_read_returns_none_on_corrupted_file(tmp_path) -> None:
    """A truncated or malformed JSON file is treated as a cache miss
    rather than raising."""
    cache = ProvenanceCache(tmp_path)
    bad_path = tmp_path / f"{key_for('https://x')}.json"
    tmp_path.mkdir(parents=True, exist_ok=True)
    bad_path.write_text("{not valid json", encoding="utf-8")
    assert cache.read("https://x") is None


def test_cache_dir_from_env_disabled_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(CACHE_DIR_ENV, raising=False)
    assert cache_dir_from_env() is None


def test_cache_dir_from_env_enabled_when_set(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CACHE_DIR_ENV, str(tmp_path))
    resolved = cache_dir_from_env()
    assert resolved is not None
    assert resolved == tmp_path.resolve()


def test_cache_dir_from_env_blank_means_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(CACHE_DIR_ENV, "   ")
    assert cache_dir_from_env() is None


# ---------------------------------------------------------------------------
# Server tool — uniprot_replay_from_cache
# ---------------------------------------------------------------------------


async def test_replay_reports_disabled_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(CACHE_DIR_ENV, raising=False)
    out = await uniprot_replay_from_cache("https://rest.uniprot.org/uniprotkb/P04637", "markdown")
    assert "Provenance cache is disabled" in out
    assert CACHE_DIR_ENV in out


async def test_replay_reports_miss_when_url_not_cached(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(CACHE_DIR_ENV, str(tmp_path))
    out = await uniprot_replay_from_cache("https://rest.uniprot.org/uniprotkb/P04637", "markdown")
    assert "No cache entry" in out
    assert "P04637" in out


async def test_replay_returns_cached_body_and_provenance(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(CACHE_DIR_ENV, str(tmp_path))
    cache = ProvenanceCache(tmp_path)
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": "2026-01-28",
        "retrieved_at": "2026-04-25T12:00:00Z",
        "url": "https://rest.uniprot.org/uniprotkb/P04637",
        "response_sha256": "abc" * 21 + "a",  # 64 chars
    }
    body = '{"primaryAccession": "P04637", "genes": [{"geneName": {"value": "TP53"}}]}'
    cache.write(prov["url"], body, prov)  # type: ignore[arg-type]

    out = await uniprot_replay_from_cache(prov["url"], "markdown")
    assert "Cache replay" in out
    assert "P04637" in out
    assert "TP53" in out
    assert "release" in out  # provenance JSON included
    assert "2026_01" in out


async def test_replay_json_format_returns_full_entry(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(CACHE_DIR_ENV, str(tmp_path))
    cache = ProvenanceCache(tmp_path)
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-25T12:00:00Z",
        "url": "https://rest.uniprot.org/uniprotkb/P04637",
        "response_sha256": "x" * 64,
    }
    body = '{"primaryAccession": "P04637"}'
    cache.write(prov["url"], body, prov)  # type: ignore[arg-type]

    out = await uniprot_replay_from_cache(prov["url"], "json")
    payload = json.loads(out)
    assert payload["url"] == prov["url"]
    assert payload["body_text"] == body
    assert payload["provenance"]["release"] == "2026_01"


async def test_replay_rejects_oversize_url(monkeypatch: pytest.MonkeyPatch) -> None:
    out = await uniprot_replay_from_cache("https://x.example/" + "y" * 2000)
    assert "Input error" in out


async def test_replay_truncates_long_body_in_markdown(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(CACHE_DIR_ENV, str(tmp_path))
    cache = ProvenanceCache(tmp_path)
    big_body = "A" * 10_000
    prov = {
        "source": "UniProt",
        "release": "2026_01",
        "release_date": None,
        "retrieved_at": "2026-04-25T12:00:00Z",
        "url": "https://rest.uniprot.org/uniprotkb/P04637",
        "response_sha256": "y" * 64,
    }
    cache.write(prov["url"], big_body, prov)  # type: ignore[arg-type]
    out = await uniprot_replay_from_cache(prov["url"], "markdown")
    assert "truncated" in out
    assert "10000 bytes" in out
