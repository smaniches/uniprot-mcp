"""uniprot-mcp — Model Context Protocol server for UniProt.

Author: Santiago Maniches <santiago.maniches@gmail.com>
        ORCID https://orcid.org/0009-0005-6480-1987
        TOPOLOGICA LLC
License: Apache-2.0
"""

from __future__ import annotations

from uniprot_mcp.client import ACCESSION_RE, UniProtClient

__version__ = "0.1.0"
__all__ = ["ACCESSION_RE", "UniProtClient", "__version__"]
