"""Local provenance cache for offline replay.

Opt-in via the ``UNIPROT_MCP_CACHE_DIR`` environment variable. When
set, every successful UniProt response is written to disk under the
specified directory, keyed by the SHA-256 of the request URL. The
:func:`uniprot_replay_from_cache` MCP tool then lets agents (or human
auditors) re-read a previously-recorded response *without* hitting the
upstream — useful for:

  - Reproducing a year-old answer from a sealed cache snapshot.
  - Working offline / behind air-gaps.
  - Reducing UniProt's load when running a benchmark twice.

Each cache entry is a single JSON file with the schema::

    {
      "url": "https://rest.uniprot.org/uniprotkb/P04637",
      "body_text": "<raw response body>",
      "provenance": {
        "source": "UniProt",
        "release": "2026_01",
        ...
      }
    }

The cache is content-addressed: the entry's filename is
``<sha256(url)>.json``. Writing is atomic (temp-file + rename) so a
crashed process never leaves a half-written entry behind.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uniprot_mcp.client import Provenance

CACHE_DIR_ENV = "UNIPROT_MCP_CACHE_DIR"


def cache_dir_from_env() -> Path | None:
    """Return the configured cache directory, or ``None`` when caching
    is disabled (env var unset or empty)."""
    raw = os.environ.get(CACHE_DIR_ENV, "").strip()
    return Path(raw).expanduser().resolve() if raw else None


def key_for(url: str) -> str:
    """SHA-256 of the request URL — the cache file's stem."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


class ProvenanceCache:
    """Atomic, content-addressed file-system cache.

    The cache is intentionally simple: one JSON file per URL, no
    expiry policy, no compression, no hot in-memory layer. The opt-in
    env var means there is zero default-on disk activity; users who
    explicitly turn it on accept the file-system implications.
    """

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir.expanduser().resolve()

    def _path_for(self, url: str) -> Path:
        return self.base_dir / f"{key_for(url)}.json"

    def write(self, url: str, body_text: str, provenance: Provenance) -> Path:
        """Persist a (URL, body, provenance) triple atomically.

        Creates ``base_dir`` if absent. Writes to a temp file in the
        same directory, then ``os.replace``s — guarantees readers
        either see the previous version or the new one, never a
        truncated file.
        """
        self.base_dir.mkdir(parents=True, exist_ok=True)
        target = self._path_for(url)
        payload = {
            "url": url,
            "body_text": body_text,
            "provenance": dict(provenance),
        }
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        # Use a NamedTemporaryFile in the same directory so os.replace
        # is guaranteed atomic on the same filesystem.
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=self.base_dir,
            prefix=f"{key_for(url)}.",
            suffix=".tmp",
            delete=False,
        ) as tf:
            tf.write(encoded)
            tmp_path = Path(tf.name)
        os.replace(tmp_path, target)
        return target

    def read(self, url: str) -> dict[str, object] | None:
        """Return the cached payload for ``url`` if present, else ``None``."""
        path = self._path_for(url)
        if not path.exists():
            return None
        try:
            decoded: object = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        # Defensive: a corrupted JSON file that decodes to a non-dict
        # (e.g. an array) is treated as a cache miss rather than crashing.
        if not isinstance(decoded, dict):
            return None
        return decoded

    def has(self, url: str) -> bool:
        return self._path_for(url).exists()


__all__ = [
    "CACHE_DIR_ENV",
    "ProvenanceCache",
    "cache_dir_from_env",
    "key_for",
]
