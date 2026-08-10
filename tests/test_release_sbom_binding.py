from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bind_release_sbom.py"
SPEC = importlib.util.spec_from_file_location("bind_release_sbom", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _wheel(tmp_path: Path, *, name: str = "uniprot-mcp-server", version: str = "1.3.2") -> Path:
    wheel = tmp_path / "package.whl"
    metadata = f"Metadata-Version: 2.3\nName: {name}\nVersion: {version}\n\n"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("package-1.3.2.dist-info/METADATA", metadata)
    return wheel


def _sbom(tmp_path: Path, *, name: str = "uniprot-mcp-server", version: str = "1.3.2") -> Path:
    path = tmp_path / "sbom.cdx.json"
    path.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "version": 1,
                "metadata": {
                    "component": {
                        "type": "library",
                        "name": name,
                        "version": version,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_bind_records_exact_wheel_sha256(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    sbom = _sbom(tmp_path)

    digest = MODULE.bind(sbom, wheel)
    data = json.loads(sbom.read_text(encoding="utf-8"))

    assert digest == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert data["metadata"]["component"]["hashes"] == [
        {"alg": "SHA-256", "content": digest}
    ]
    assert MODULE.verify(sbom, wheel) == digest


def test_verify_rejects_artifact_substitution(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    sbom = _sbom(tmp_path)
    MODULE.bind(sbom, wheel)

    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("tampered.txt", "different published bytes")

    with pytest.raises(MODULE.BindingError, match="does not equal wheel SHA-256"):
        MODULE.verify(sbom, wheel)


def test_bind_rejects_root_identity_mismatch(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    sbom = _sbom(tmp_path, name="different-package")

    with pytest.raises(MODULE.BindingError, match="does not match wheel name"):
        MODULE.bind(sbom, wheel)


def test_bind_rejects_conflicting_existing_digest(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    sbom = _sbom(tmp_path)
    data = json.loads(sbom.read_text(encoding="utf-8"))
    data["metadata"]["component"]["hashes"] = [
        {"alg": "SHA-256", "content": "0" * 64}
    ]
    sbom.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(MODULE.BindingError, match="conflicting SHA-256"):
        MODULE.bind(sbom, wheel)
