"""Negative controls for the exact-release PyPI read-back gate."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "pypi_verifier", Path(__file__).resolve().parents[2] / "scripts" / "verify_pypi_release.py"
)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def _metadata() -> dict:
    return {
        "info": {"name": "uniprot-mcp-server", "version": "1.3.13"},
        "urls": [
            {
                "packagetype": kind,
                "filename": filename,
                "url": f"https://files.pythonhosted.org/{filename}",
                "yanked": False,
                "size": 4,
                "digests": {"sha256": hashlib.sha256(b"test").hexdigest()},
            }
            for kind, filename in [("bdist_wheel", "package.whl"), ("sdist", "package.tar.gz")]
        ],
    }


def test_exact_release_and_normalized_name() -> None:
    assert len(VERIFIER.verify_metadata(_metadata(), "UniProt_MCP_Server", "1.3.13")) == 2


@pytest.mark.parametrize("field,value", [("name", "other"), ("version", "1.3.12")])
def test_wrong_identity_is_rejected(field: str, value: str) -> None:
    data = _metadata()
    data["info"][field] = value
    with pytest.raises(VERIFIER.VerificationError, match="does not match"):
        VERIFIER.verify_metadata(data, "uniprot-mcp-server", "1.3.13")


@pytest.mark.parametrize("formats", [[], ["sdist"], ["bdist_wheel"], ["sdist", "other"]])
def test_both_distribution_formats_are_required(formats: list[str]) -> None:
    data = _metadata()
    data["urls"] = [{"packagetype": kind} for kind in formats]
    with pytest.raises(VERIFIER.VerificationError, match="both a wheel and an sdist"):
        VERIFIER.verify_metadata(data, "uniprot-mcp-server", "1.3.13")


@pytest.mark.parametrize(
    "field,value",
    [
        ("yanked", True),
        ("digests", {"sha256": "bad"}),
        ("url", "https://example.org/package.whl"),
        ("url", "http://files.pythonhosted.org/package.whl"),
        ("size", 0),
        ("size", 50_000_001),
    ],
)
def test_invalid_artifact_is_rejected(field: str, value: object) -> None:
    data = _metadata()
    data["urls"][0][field] = value
    with pytest.raises(VERIFIER.VerificationError):
        VERIFIER.verify_metadata(data, "uniprot-mcp-server", "1.3.13")


@pytest.mark.parametrize("payload", [b"test", b"fake", b"truncated"])
def test_downloaded_artifact_bytes_are_verified(
    monkeypatch: pytest.MonkeyPatch, payload: bytes
) -> None:
    metadata = json.dumps(_metadata()).encode()
    monkeypatch.setattr(
        VERIFIER, "_download", lambda url, limit: metadata if url.endswith("/json") else payload
    )
    if payload == b"test":
        VERIFIER.verify_release("uniprot-mcp-server", "1.3.13")
    else:
        with pytest.raises(VERIFIER.VerificationError, match="integrity failure"):
            VERIFIER.verify_release("uniprot-mcp-server", "1.3.13")


def test_invalid_origin_is_rejected_before_network() -> None:
    with pytest.raises(VERIFIER.VerificationError, match="allowed HTTPS"):
        VERIFIER._download("file:///etc/passwd", 100)
