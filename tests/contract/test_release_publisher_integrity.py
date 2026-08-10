from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "scripts" / "install_mcp_publisher.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def _bash_executable() -> str:
    """Locate a bash that can actually run the installer.

    On Windows runners the PATH-resolved ``bash`` is the WSL launcher, which
    exits with an error (and an empty stderr) when no distribution is
    installed, so prefer the Git Bash that ships with Git for Windows.
    """
    if sys.platform == "win32":
        for base in (os.environ.get("PROGRAMFILES"), r"C:\Program Files"):
            if base:
                git_bash = Path(base) / "Git" / "bin" / "bash.exe"
                if git_bash.exists():
                    return str(git_bash)
    bash = shutil.which("bash")
    assert bash is not None, "bash is required for the installer contract tests"
    return bash


def _run_installer(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_bash_executable(), str(INSTALLER), *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def test_installer_fails_closed_on_wrong_digest(tmp_path: Path) -> None:
    fake_archive = tmp_path / "mcp-publisher_linux_amd64.tar.gz"
    fake_archive.write_bytes(b"not the approved publisher archive")

    result = _run_installer(tmp_path, "--platform", "linux_amd64", "--archive", str(fake_archive))

    assert result.returncode != 0
    assert "SHA-256 mismatch" in result.stderr
    assert not (tmp_path / "mcp-publisher").exists()


def test_installer_fails_closed_on_unpinned_platform(tmp_path: Path) -> None:
    fake_archive = tmp_path / "archive.tar.gz"
    fake_archive.write_bytes(b"irrelevant bytes")

    result = _run_installer(tmp_path, "--platform", "plan9_386", "--archive", str(fake_archive))

    assert result.returncode != 0
    assert "no pinned mcp-publisher" in result.stderr
    assert not (tmp_path / "mcp-publisher").exists()


def test_installer_pins_version_and_repository_controlled_digests() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")

    assert 'MCP_PUBLISHER_VERSION="1.8.0"' in installer
    digests = re.findall(r'expected_sha256="([0-9a-f]{64})"', installer)
    assert len(digests) == 4
    assert len(set(digests)) == 4


def test_installer_never_authenticates_or_publishes() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")

    assert "mcp-publisher login" not in installer
    assert "mcp-publisher publish" not in installer


def test_release_workflow_does_not_execute_mutable_latest_publisher() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "registry/releases/latest" not in workflow
    assert "bash scripts/install_mcp_publisher.sh" in workflow


def test_release_workflow_keeps_auth_and_publish_after_authenticated_install() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    install = workflow.index("bash scripts/install_mcp_publisher.sh")
    login = workflow.index("./mcp-publisher login github-oidc")
    publish = workflow.index("./mcp-publisher publish")
    assert install < login < publish
