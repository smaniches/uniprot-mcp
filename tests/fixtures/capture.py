"""Re-record fixtures from the live UniProt REST API.

Run manually when the UniProt schema changes or a new fixture is needed:

    python -m tests.fixtures.capture

Each fixture is written with a `_meta` block carrying source URL,
capture timestamp (UTC, ISO-8601), and UniProt release (from the
`x-uniprot-release` response header when present).

This script is *not* invoked during CI. CI must stay offline.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

BASE_URL = "https://rest.uniprot.org"
FIXTURE_DIR = Path(__file__).resolve().parent

FIXTURES = {
    "p04637_full": ("GET", "/uniprotkb/P04637", None),
    "brca1_search_full": (
        "GET",
        "/uniprotkb/search",
        {"query": "(gene:BRCA1) AND (organism_id:9606)", "size": 1},
    ),
    "taxonomy_human": ("GET", "/taxonomy/search", {"query": "Homo sapiens", "size": 3}),
}


def _meta(resp: httpx.Response) -> dict[str, str]:
    return {
        "source": str(resp.request.url),
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "uniprot_release": resp.headers.get("x-uniprot-release", "unknown"),
        "http_status": str(resp.status_code),
    }


def main() -> int:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        for stem, (method, path, params) in FIXTURES.items():
            print(f"-> {stem}: {method} {path}", file=sys.stderr)
            resp = client.request(method, path, params=params)
            resp.raise_for_status()
            payload = resp.json()
            payload = {"_meta": _meta(resp), **payload}
            out_path = FIXTURE_DIR / f"{stem}.json"
            out_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print(f"   wrote {out_path.name}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
