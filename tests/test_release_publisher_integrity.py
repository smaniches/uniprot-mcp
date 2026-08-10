from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_mcp_publisher.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def test_installer_fails_closed_on_wrong_digest(tmp_path: Path) -> None:
    fake_archive = tmp_path / "mcp-publisher_linux_amd64.tar.gz"
    fake_archive.write_bytes(b"not the approved publisher archive")

    result = subprocess.run(
        ["bash", str(INSTALLER), "--archive", str(fake_archive)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "SHA-256 mismatch" in result.stderr
    assert not (tmp_path / "mcp-publisher").exists()


def test_release_workflow_does_not_execute_mutable_latest_publisher() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "registry/releases/latest" not in workflow
    assert "bash scripts/install_mcp_publisher.sh" in workflow
