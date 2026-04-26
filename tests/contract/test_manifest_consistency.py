"""Manifest-consistency contract tests.

The repository ships three machine-readable descriptions of itself:

- ``.well-known/mcp.json`` — for MCP-aware clients that auto-discover.
- ``server.json`` — for the MCP Registry (registry.modelcontextprotocol.io).
- ``smithery.yaml`` — for the Smithery marketplace.

If those descriptions drift from the real tool surface (the
``@mcp.tool`` decorators in ``server.py``), client integrations
quietly break. These tests pin the truth: the *only* source of
authority is the registered tool set on the live ``mcp`` instance,
and the static manifests must agree with it exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uniprot_mcp import server

REPO_ROOT = Path(__file__).resolve().parents[2]


def _registered_tools() -> set[str]:
    """Return the tool names registered on the FastMCP instance."""
    tool_manager = getattr(server.mcp, "_tool_manager", None)
    if tool_manager is None or not hasattr(tool_manager, "_tools"):
        pytest.skip("FastMCP internals changed; rewrite the introspection helper.")
    return set(tool_manager._tools.keys())


def test_well_known_mcp_json_matches_registered_tools() -> None:
    manifest_path = REPO_ROOT / ".well-known" / "mcp.json"
    assert manifest_path.exists(), f"missing {manifest_path}"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = set(manifest.get("tools", []))
    registered = _registered_tools()
    missing = registered - declared
    extra = declared - registered
    assert not missing, f".well-known/mcp.json is missing tools: {sorted(missing)}"
    assert not extra, f".well-known/mcp.json declares tools that don't exist: {sorted(extra)}"


def test_well_known_mcp_json_carries_required_metadata() -> None:
    manifest_path = REPO_ROOT / ".well-known" / "mcp.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Anthropic Connectors Directory + MCP Registry minimums.
    for key in ("name", "version", "description", "license", "transports", "entry"):
        assert key in manifest, f".well-known/mcp.json missing required field: {key!r}"
    assert manifest["transports"] == ["stdio"], "this server is stdio-only"
    assert manifest["entry"]["stdio"]["command"] == "uniprot-mcp"
    assert manifest["license"] == "Apache-2.0"


def test_server_json_matches_well_known_version() -> None:
    """The MCP Registry manifest and the .well-known descriptor must
    declare the same version — they describe the same release."""
    well_known = json.loads((REPO_ROOT / ".well-known" / "mcp.json").read_text(encoding="utf-8"))
    server_json_path = REPO_ROOT / "server.json"
    if not server_json_path.exists():
        pytest.skip("server.json absent; pre-1.0.1 repos may lack the registry manifest.")
    server_json = json.loads(server_json_path.read_text(encoding="utf-8"))
    assert server_json["version_detail"]["version"] == well_known["version"], (
        "server.json and .well-known/mcp.json must declare the same version"
    )
    # Names follow different conventions (registry uses reverse-DNS,
    # well-known uses the bare slug); just sanity-check both are present.
    assert server_json.get("name", "").endswith("/uniprot-mcp")
    assert well_known["name"] == "uniprot-mcp"


def test_pyproject_version_matches_well_known() -> None:
    """The wheel's metadata version must equal the manifest's. Otherwise
    a `pip install` produces a package whose self-reported version
    disagrees with what the registries advertise."""
    pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    # Strict-tomllib parse since the file is small and the location of
    # the version field is well-known.
    import tomllib

    pyproject = tomllib.loads(pyproject_text)
    pyproject_version = pyproject["project"]["version"]
    well_known = json.loads((REPO_ROOT / ".well-known" / "mcp.json").read_text(encoding="utf-8"))
    assert pyproject_version == well_known["version"], (
        f"pyproject.toml version ({pyproject_version}) and .well-known/mcp.json "
        f"version ({well_known['version']}) disagree."
    )


def test_runtime_version_matches_well_known() -> None:
    """``uniprot_mcp.__version__`` must match the manifest. The package's
    ``__version__`` is sourced from importlib.metadata so the only way it
    can drift is if the installed distribution disagrees with pyproject —
    which is exactly the failure mode this test catches."""
    import uniprot_mcp

    well_known = json.loads((REPO_ROOT / ".well-known" / "mcp.json").read_text(encoding="utf-8"))
    runtime = uniprot_mcp.__version__
    assert runtime == well_known["version"], (
        f"uniprot_mcp.__version__ ({runtime}) and .well-known/mcp.json "
        f"version ({well_known['version']}) disagree. The installed wheel's "
        f"metadata is the source of truth — rebuild after a version bump."
    )


def test_server_json_pypi_distribution_name() -> None:
    """``server.json`` declares the PyPI distribution name in
    ``packages[0].name``. It must match ``pyproject.toml.project.name`` —
    otherwise the MCP Registry tells clients to install a wrong package."""
    import tomllib

    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pyproject_name = pyproject["project"]["name"]
    server_json_path = REPO_ROOT / "server.json"
    if not server_json_path.exists():
        pytest.skip("server.json absent")
    server_json = json.loads(server_json_path.read_text(encoding="utf-8"))
    pypi_pkg = next(
        (p for p in server_json.get("packages", []) if p.get("registry_name") == "pypi"),
        None,
    )
    assert pypi_pkg is not None, "server.json declares no pypi package"
    assert pypi_pkg["name"] == pyproject_name, (
        f"server.json packages[pypi].name ({pypi_pkg['name']!r}) and "
        f"pyproject.toml project.name ({pyproject_name!r}) disagree. "
        f"Clients following the MCP Registry would install the wrong package."
    )
