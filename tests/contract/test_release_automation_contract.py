"""Guard the release workflow and runbook against known release-gate regressions.

These checks are deliberately static: GitHub's approval gate is an external
platform behavior and is verified on the live release PR, not simulated here.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _release_job(name: str) -> str:
    """Extract one top-level job without requiring a YAML parser dependency."""
    jobs = _text(".github/workflows/release.yml").split("\njobs:\n", maxsplit=1)[1]
    match = re.search(rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [a-z][a-z0-9-]*:\s*$|\Z)", jobs)
    assert match is not None, f"release.yml is missing job {name!r}"
    return match.group(1)


def _needs(job: str) -> set[str]:
    match = re.search(r"(?m)^    needs:\s*(\[[^\n]+\]|[a-z][a-z0-9-]*)\s*$", job)
    assert match is not None, "release job is missing an explicit needs dependency"
    return {name.strip() for name in match.group(1).strip("[]").split(",")}


def test_release_please_dispatches_publishing_only_after_creating_a_release() -> None:
    workflow = _text(".github/workflows/release-please.yml")
    assert "token: ${{ secrets.GITHUB_TOKEN }}" in workflow
    assert "if: ${{ steps.release.outputs.release_created }}" in workflow
    assert "gh workflow run release.yml" in workflow
    assert '--field tag="${{ steps.release.outputs.tag_name }}"' in workflow


def test_generated_release_pr_requires_real_pr_checks_and_approval_guidance() -> None:
    for workflow in ("ci.yml", "docs.yml"):
        source = _text(f".github/workflows/{workflow}")
        assert re.search(r"(?m)^  pull_request:\s*$", source)

    runbook = " ".join(_text("docs/RELEASE.md").split())
    assert "action_required" in runbook
    assert "Approve workflows to run" in runbook
    assert "current release PR head" in runbook
    assert "Do not substitute `workflow_dispatch` runs" in runbook
    assert "Never bypass the required checks" in runbook


def test_release_verification_requires_successful_signing_and_pypi() -> None:
    assert _needs(_release_job("publish-pypi")) == {"build", "attest-sbom"}
    assert _needs(_release_job("sign-and-release")) == {"build", "attest-sbom"}
    assert _needs(_release_job("publish-mcp-registry")) == {"publish-pypi"}
    assert _needs(_release_job("dispatch-verify")) == {
        "publish-pypi",
        "sign-and-release",
    }
    dispatch = _release_job("dispatch-verify")
    assert "gh workflow run release-verify.yml" in dispatch
    assert '--field tag="$VERIFY_TAG"' in dispatch
    assert "if: always()" not in dispatch


def test_missing_sigstore_bundle_guidance_checks_assets_not_oidc_permissions() -> None:
    runbook = _text("docs/RELEASE.md")
    matching_rows = [
        line
        for line in runbook.splitlines()
        if line.startswith("| `release-verify` says `missing sigstore bundle`")
    ]
    assert len(matching_rows) == 1
    row = matching_rows[0]
    assert "sign-and-release" in row
    assert "attached GitHub Release assets" in row
    assert "rerunning PyPI publication" in row
    assert "permissions regression" not in row
    assert "re-grant" not in row


def test_release_review_feedback_requires_explicit_disposition() -> None:
    runbook = " ".join(_text("docs/RELEASE.md").split())
    assert "Codex" in runbook
    assert "Dependabot" in runbook
    assert "explain non-applicability" in runbook
    assert "resolve actionable threads" in runbook
