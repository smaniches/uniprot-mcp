"""Live capture of the TP53 R175H walkthrough through the candidate tools.

Records every upstream HTTP response the tools receive (raw bytes, headers,
URL, receive time) and every tool output, so each footer SHA-256 can be
recomputed from stored bytes with uniprot_mcp.client.canonical_response_hash.
"""

import asyncio
import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

import uniprot_mcp
from uniprot_mcp import server
from uniprot_mcp.client import canonical_response_hash

out = Path(sys.argv[1])
(out / "upstream").mkdir(parents=True, exist_ok=True)
records = []
_orig = httpx.AsyncClient.send


async def send(self, request, **kw):
    resp = await _orig(self, request, **kw)
    await resp.aread()
    i = len(records)
    name = f"upstream/{i:02d}.body"
    (out / name).write_bytes(resp.content)
    records.append(
        {
            "index": i,
            "url": str(resp.request.url),
            "status": resp.status_code,
            "received_at": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "headers": {
                k: v
                for k, v in resp.headers.items()
                if k.lower()
                in (
                    "content-type",
                    "x-uniprot-release",
                    "x-uniprot-release-date",
                    "x-api-deployment-date",
                    "date",
                )
            },
            "body_file": name,
            "raw_sha256": hashlib.sha256(resp.content).hexdigest(),
            "canonical_sha256": canonical_response_hash(resp),
        }
    )
    return resp


httpx.AsyncClient.send = send

CALLS = [
    (
        "uniprot_search",
        dict(query="gene_exact:TP53 AND organism_id:9606 AND reviewed:true", size=1),
    ),
    ("uniprot_features_at_position", dict(accession="P04637", position=175)),
    ("uniprot_lookup_variant", dict(accession="P04637", change="R175H")),
    ("uniprot_resolve_clinvar", dict(accession="P04637", change="R175H", size=5)),
    ("uniprot_get_alphafold_confidence", dict(accession="P04637")),
]


async def main():
    transcript = []
    for name, args in CALLS:
        start = len(records)
        text = await getattr(server, name)(**args)
        transcript.append(
            {
                "tool": name,
                "arguments": args,
                "output": text,
                "upstream_records": list(range(start, len(records))),
            }
        )
    meta = {
        "captured_at_utc_start": transcript and records[0]["received_at"],
        "uniprot_mcp_version": uniprot_mcp.__version__,
        "python": platform.python_version(),
        "httpx": httpx.__version__,
        "digest_method": (
            "SHA-256; JSON bodies re-serialized with sort_keys=True, "
            "separators=(',',':'), ensure_ascii=False "
            "(uniprot_mcp.client.canonical_response_hash); non-JSON raw bytes"
        ),
        "upstream": records,
    }
    (out / "capture_manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    (out / "tool_outputs.json").write_text(
        json.dumps(transcript, indent=2, ensure_ascii=False) + "\n"
    )


asyncio.run(main())
