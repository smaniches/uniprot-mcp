"""uniprot-mcp — Model Context Protocol server for UniProt.

Author: Santiago Maniches <santiago.maniches@gmail.com>
        ORCID https://orcid.org/0009-0005-6480-1987
        TOPOLOGICA LLC
License: Apache-2.0

The PyPI distribution name is ``uniprot-mcp-server``; the installed
console script and MCP server identity are both ``uniprot-mcp``.
``__version__`` is sourced from the installed wheel's metadata so it
cannot drift from ``pyproject.toml``.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from uniprot_mcp.client import ACCESSION_RE, UniProtClient

try:
    __version__ = version("uniprot-mcp-server")
except PackageNotFoundError:  # pragma: no cover — only when running from a checkout without install
    __version__ = "0.0.0+unknown"

__all__ = ["ACCESSION_RE", "UniProtClient", "__version__"]
