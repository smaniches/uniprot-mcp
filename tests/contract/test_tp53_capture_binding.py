"""Contract: the TP53 worked transcript is bound to stored source bytes.

``examples/01_clinical_variant_interpretation.jsonl`` was recorded live
on 2026-10-15 and its upstream response bodies are stored under
``examples/captures/2026-10-15_tp53_r175h/``. These offline checks
recompute every digest from the stored bytes with the same canonical
method the tools use, and require each tool output in the transcript to
be the verbatim captured output whose footer digest matches its bytes.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path

import httpx
import pytest

from uniprot_mcp.client import canonical_response_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPTURE = REPO_ROOT / "examples" / "captures" / "2026-10-15_tp53_r175h"
TRANSCRIPT = REPO_ROOT / "examples" / "01_clinical_variant_interpretation.jsonl"
_SHA_LINE = re.compile(r"^_SHA-256: ([0-9a-f]{64})_$", re.MULTILINE)
_QUERY_LINE = re.compile(r"^_Query: (\S+)_$", re.MULTILINE)

# The sdist ships only README files from examples/, not the capture data
# (same situation as the atlas contract tests); run wherever the data exists.
pytestmark = pytest.mark.skipif(
    not (CAPTURE / "capture_manifest.json").exists(), reason="capture data not present"
)


def _manifest() -> dict:
    return json.loads((CAPTURE / "capture_manifest.json").read_text(encoding="utf-8"))


def _body(record: dict) -> bytes:
    return gzip.decompress((CAPTURE / record["body_file"]).read_bytes())


def test_stored_bytes_reproduce_recorded_digests() -> None:
    for rec in _manifest()["upstream"]:
        body = _body(rec)
        assert hashlib.sha256(body).hexdigest() == rec["raw_sha256"], rec["url"]
        response = httpx.Response(
            rec["status"], content=body, headers={"content-type": rec["headers"]["content-type"]}
        )
        assert canonical_response_hash(response) == rec["canonical_sha256"], rec["url"]


def test_transcript_tool_outputs_are_the_captured_outputs() -> None:
    captured = json.loads((CAPTURE / "tool_outputs.json").read_text(encoding="utf-8"))
    lines = [json.loads(ln) for ln in TRANSCRIPT.read_text(encoding="utf-8").splitlines()]
    tool_msgs = [ln for ln in lines if ln.get("role") == "tool"]
    calls = [ln["tool_call"] for ln in lines if "tool_call" in ln]
    assert [m["name"] for m in tool_msgs] == [c["tool"] for c in captured]
    assert [c["arguments"] for c in calls] == [c["arguments"] for c in captured]
    assert [m["content"] for m in tool_msgs] == [c["output"] for c in captured]


def test_every_footer_digest_matches_stored_bytes_for_its_query() -> None:
    upstream = _manifest()["upstream"]
    captured = json.loads((CAPTURE / "tool_outputs.json").read_text(encoding="utf-8"))
    for call in captured:
        digests = _SHA_LINE.findall(call["output"])
        queries = _QUERY_LINE.findall(call["output"])
        assert len(digests) == 1 and len(queries) == 1, call["tool"]
        own = [upstream[i] for i in call["upstream_records"]]
        # The footer describes the last upstream response the tool received.
        assert own[-1]["url"] == queries[0], call["tool"]
        assert own[-1]["canonical_sha256"] == digests[0], call["tool"]
