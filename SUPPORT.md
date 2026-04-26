# Support — `uniprot-mcp`

`uniprot-mcp` is open-source software released under Apache-2.0. Support is community-driven; the maintainer (Santiago Maniches, TOPOLOGICA LLC) responds to issues on a best-effort basis.

This document exists because the [Anthropic Connectors Directory](https://support.claude.com/en/articles/12922490-remote-mcp-server-submission-guide) requires a clear support contact for every listed MCP server.

---

## Where to ask

| Question | Channel |
|---|---|
| **"How do I install / run / configure this?"** | Open a [GitHub Discussion](https://github.com/smaniches/uniprot-mcp/discussions) or an issue with the `question` label. |
| **"I think this is a bug."** | Open a [GitHub Issue](https://github.com/smaniches/uniprot-mcp/issues/new) using the bug template. Include the version (`uniprot-mcp --version`), Python version, OS, and the smallest input that reproduces. |
| **"This is a security vulnerability."** | **Do not open a public issue.** See [`SECURITY.md`](SECURITY.md). |
| **"I'd like to contribute."** | See [`CONTRIBUTING.md`](CONTRIBUTING.md). PRs welcome; small PRs land faster than large ones. |
| **"Commercial / enterprise / regulated-environment support."** | Email `santiago.maniches@gmail.com` with subject `[uniprot-mcp commercial]`. The orchestrator tier (`topologica-bio`) is the commercial product; commercial licensing of `uniprot-mcp` itself is not necessary because the project is permissively Apache-2.0. |

---

## Response expectations

- **Bug reports**: triaged within 7 days. Critical correctness bugs (wrong UniProt data, security implications, broken release artefacts) are prioritised over polish.
- **Feature requests**: read within 7 days; not all are accepted. Scope is bounded by the [project goals](README.md#design-goals): a reference-quality, narrow-and-deep MCP for UniProt. Cross-database orchestration belongs in `topologica-bio`, not here.
- **Pull requests**: reviewed within 14 days. Squash-merge to keep `main` history readable.
- **Security reports**: see `SECURITY.md` for the dedicated SLA.

These are best-effort targets, not contractual commitments. The maintainer is one person; please be patient.

---

## What this project will not help with

- **UniProt itself.** If a UniProt accession is missing or incorrect, that is a UniProt data issue. Direct contact: `https://www.uniprot.org/contact`.
- **MCP protocol questions** unrelated to this server. See https://modelcontextprotocol.io.
- **General Python / async / packaging help.** Stack Overflow is the right venue.

---

## Maintainer

Santiago Maniches · ORCID [0009-0005-6480-1987](https://orcid.org/0009-0005-6480-1987) · TOPOLOGICA LLC · `santiago.maniches@gmail.com`
