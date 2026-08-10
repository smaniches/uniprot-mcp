from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "bind_release_sbom.py"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
RELEASE_VERIFY_WORKFLOW = ROOT / ".github" / "workflows" / "release-verify.yml"
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
    assert data["metadata"]["component"]["hashes"] == [{"alg": "SHA-256", "content": digest}]
    assert MODULE.verify(sbom, wheel) == digest


def test_verify_rejects_artifact_substitution(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    sbom = _sbom(tmp_path)
    MODULE.bind(sbom, wheel)

    with zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("tampered.txt", "different published bytes")

    with pytest.raises(MODULE.BindingError, match="does not equal wheel SHA-256"):
        MODULE.verify(sbom, wheel)


def test_verify_rejects_unbound_sbom(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    sbom = _sbom(tmp_path)

    with pytest.raises(MODULE.BindingError, match="does not equal wheel SHA-256"):
        MODULE.verify(sbom, wheel)


def test_bind_rejects_root_identity_mismatch(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    sbom = _sbom(tmp_path, name="different-package")

    with pytest.raises(MODULE.BindingError, match="does not match wheel name"):
        MODULE.bind(sbom, wheel)


def test_bind_rejects_root_version_mismatch(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    sbom = _sbom(tmp_path, version="9.9.9")

    with pytest.raises(MODULE.BindingError, match="does not match wheel version"):
        MODULE.bind(sbom, wheel)


def test_bind_rejects_conflicting_existing_digest_and_leaves_sbom_unchanged(
    tmp_path: Path,
) -> None:
    wheel = _wheel(tmp_path)
    sbom = _sbom(tmp_path)
    data = json.loads(sbom.read_text(encoding="utf-8"))
    data["metadata"]["component"]["hashes"] = [{"alg": "SHA-256", "content": "0" * 64}]
    sbom.write_text(json.dumps(data), encoding="utf-8")
    before = sbom.read_bytes()

    with pytest.raises(MODULE.BindingError, match="conflicting SHA-256"):
        MODULE.bind(sbom, wheel)

    assert sbom.read_bytes() == before


def test_bind_rejects_multiple_existing_sha256_entries(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    sbom = _sbom(tmp_path)
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    data = json.loads(sbom.read_text(encoding="utf-8"))
    data["metadata"]["component"]["hashes"] = [
        {"alg": "SHA-256", "content": digest},
        {"alg": "SHA256", "content": digest},
    ]
    sbom.write_text(json.dumps(data), encoding="utf-8")
    before = sbom.read_bytes()

    with pytest.raises(MODULE.BindingError, match="multiple SHA-256"):
        MODULE.bind(sbom, wheel)

    assert sbom.read_bytes() == before


def test_verify_rejects_duplicate_sha256_entries(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    sbom = _sbom(tmp_path)
    digest = MODULE.bind(sbom, wheel)
    data = json.loads(sbom.read_text(encoding="utf-8"))
    data["metadata"]["component"]["hashes"].append({"alg": "SHA-256", "content": digest})
    sbom.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(MODULE.BindingError, match="multiple SHA-256"):
        MODULE.verify(sbom, wheel)


def _job(workflow: str, name: str) -> str:
    """Return one job's block from a workflow file (2-space-indented keys)."""
    lines = workflow.splitlines()
    start = lines.index(f"  {name}:")
    block = [lines[start]]
    for line in lines[start + 1 :]:
        if re.match(r"^  [A-Za-z0-9_-]+:", line):
            break
        block.append(line)
    return "\n".join(block)


def _permissions(job_block: str) -> dict[str, str]:
    """Return a job's permissions map, ignoring trailing comments."""
    match = re.search(r"^    permissions:\n((?:      \S+: \S+.*\n?)+)", job_block, flags=re.M)
    assert match is not None
    permissions: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, _, value = line.strip().partition(":")
        permissions[key] = value.split("#")[0].strip()
    return permissions


def test_release_workflow_binds_sbom_to_the_exact_wheel() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    # The SBOM must be generated from the installed exact wheel, not from the
    # incidental CI environment, and its root must be bound then re-verified.
    assert "cyclonedx-py requirements" not in workflow
    assert "cyclonedx-py environment" in workflow
    assert "scripts/bind_release_sbom.py --sbom" in workflow
    assert "scripts/bind_release_sbom.py --verify-only" in workflow
    # The SBOM attestation subject is the wheel the SBOM describes.
    assert 'subject-path: "dist/*.whl"' in workflow


def test_privileged_build_job_performs_no_runtime_resolution_or_sbom_work() -> None:
    build = _job(RELEASE_WORKFLOW.read_text(encoding="utf-8"), "build")

    assert _permissions(build) == {
        "contents": "read",
        "id-token": "write",
        "attestations": "write",
    }
    assert ".sbom-runtime" not in build
    assert "cyclonedx-py" not in build
    assert "bind_release_sbom.py" not in build
    assert "attest-sbom" not in build
    assert "actions/attest-build-provenance" in build


def test_sbom_job_is_unprivileged_and_generates_from_the_exact_wheel() -> None:
    sbom = _job(RELEASE_WORKFLOW.read_text(encoding="utf-8"), "sbom")

    assert "needs: build" in sbom
    assert _permissions(sbom) == {"contents": "read"}
    assert "name: release-artifacts" in sbom
    assert ".sbom-runtime" in sbom
    assert 'python -m pip --python .sbom-runtime install "$wheel"' in sbom
    assert "cyclonedx-py environment" in sbom
    assert "scripts/bind_release_sbom.py --sbom" in sbom
    assert "scripts/bind_release_sbom.py --verify-only" in sbom
    assert "name: release-sbom" in sbom


def test_attest_sbom_job_has_only_attestation_authority() -> None:
    attest = _job(RELEASE_WORKFLOW.read_text(encoding="utf-8"), "attest-sbom")

    assert "needs: [build, sbom]" in attest
    assert _permissions(attest) == {
        "contents": "read",
        "id-token": "write",
        "attestations": "write",
    }
    assert "actions/checkout" not in attest
    assert "pip install" not in attest
    assert "python -m venv" not in attest
    assert "name: release-artifacts" in attest
    assert "name: release-sbom" in attest
    assert 'subject-path: "dist/*.whl"' in attest
    assert 'subject-path: "dist/*"' not in attest
    assert 'sbom-path: "sbom.cdx.json"' in attest


def test_publication_waits_for_the_completed_integrity_chain() -> None:
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    pypi = _job(workflow, "publish-pypi")
    sign = _job(workflow, "sign-and-release")
    registry = _job(workflow, "publish-mcp-registry")
    verify = _job(workflow, "dispatch-verify")

    assert "needs: [build, attest-sbom]" in pypi
    assert "needs: [build, attest-sbom]" in sign
    assert "needs: publish-pypi" in registry
    assert "needs: [publish-pypi, sign-and-release]" in verify
    # The GitHub Release still ships wheel, sdist, SBOM and Sigstore bundles.
    assert "name: release-artifacts" in sign
    assert "name: release-sbom" in sign
    assert "sbom.cdx.json" in sign
    assert "*.sigstore.json" in sign


def test_release_verify_workflow_reverifies_sbom_binding_post_release() -> None:
    workflow = RELEASE_VERIFY_WORKFLOW.read_text(encoding="utf-8")

    assert "bind_release_sbom.py" in workflow
    assert "--verify-only" in workflow
