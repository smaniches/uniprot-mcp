# Privacy — `uniprot-mcp`

This document describes what data flows through `uniprot-mcp` when you run it, what it stores, and who else sees it. It exists because the [Anthropic Connectors Directory](https://support.claude.com/en/articles/12922490-remote-mcp-server-submission-guide) requires a privacy notice, and because users running biomedical software in regulated contexts deserve a precise answer.

**Last reviewed:** 2026-04-24. This document tracks the released version of the project; the authoritative copy lives at the commit SHA your installed package was built from.

---

## The short version

`uniprot-mcp` is a **stateless** MCP server. It does not collect, store, or transmit personal data anywhere. It calls one external service: the public [UniProt REST API](https://rest.uniprot.org). It writes one log file: standard error on the host that runs it. That is the entire privacy surface.

If you are evaluating this for HIPAA, GDPR, or institutional IRB review: there is no PII / PHI handling, no analytics, no telemetry, no third-party SDK, no remote write. The risk surface is identical to running `curl https://rest.uniprot.org/...` on the same machine.

---

## Data flows

```
┌──────────────────────┐   1. tool call (stdio)   ┌─────────────────┐
│  MCP client          │ ───────────────────────► │  uniprot-mcp    │
│  (Claude Desktop,    │                          │  (this process) │
│   Cline, …)          │ ◄─────────────────────── │                 │
└──────────────────────┘   4. tool result          └────────┬────────┘
                                                            │
                                       2. HTTPS GET / POST  │
                                       (public API, no key) │
                                                            ▼
                                                   ┌─────────────────┐
                                                   │ rest.uniprot.org│
                                                   └────────┬────────┘
                                                            │
                                                  3. JSON / FASTA
                                                            │
                                                            └────────►
```

1. **MCP client → uniprot-mcp**: tool name + arguments arrive over stdio. The client decides what arguments to send; this server does not log them outside the local stderr stream.
2. **uniprot-mcp → UniProt**: a standard HTTPS request to `rest.uniprot.org` carrying a `User-Agent` (`uniprot-mcp/<version> (+repo URL)`) and `Accept` header. **No API key, no cookie, no session, no IP-tracking signature beyond what every HTTPS client sends.**
3. **UniProt → uniprot-mcp**: JSON or FASTA response. We extract release headers (`X-UniProt-Release`, `X-UniProt-Release-Date`) for the provenance footer.
4. **uniprot-mcp → MCP client**: formatted Markdown / JSON / FASTA, including the provenance footer (release, retrieved-at timestamp, query URL).

Nothing else leaves the process.

---

## What is stored

- **In memory, transiently**: the most recent successful response's `Provenance` record (release, URL, timestamp). Discarded on next request or process exit.
- **On disk**: nothing, by default. The server has no database, no cache directory, no configuration file beyond what the Python interpreter loads at startup.
- **In logs (stderr)**: the tool name, exception class on failure, and at debug level the request URL. **Tool arguments are not logged at INFO level by default.** Stderr is captured by whatever supervisor runs the process (Claude Desktop, systemd, Docker), not by this project.

---

## Third parties

| Third party | What they see | Why |
|---|---|---|
| **UniProt** ([uniprot.org](https://www.uniprot.org), [rest.uniprot.org](https://rest.uniprot.org)) | Source IP, User-Agent, the request path / query string. UniProt's privacy policy: https://www.uniprot.org/help/privacy. | Required: this server's job is to query UniProt. |
| **AlphaFold-DB** ([alphafold.ebi.ac.uk](https://alphafold.ebi.ac.uk)) | Source IP, User-Agent, the UniProt accession appearing in the request path. EBI privacy policy: https://www.ebi.ac.uk/data-protection/privacy-notice/embl-ebi-public-website. | Used **only** by `uniprot_get_alphafold_confidence` to retrieve the public per-model pLDDT confidence summary (no structure download, no per-residue trace at this time). Other tools never call this origin. |

There are **no** other third parties — no Google Analytics, no Sentry, no CloudFlare front-end, no Anthropic / OpenAI / any-LLM-vendor integrations beyond the MCP protocol itself.

---

## Cookies, tracking, telemetry

None. The server is invoked as a subprocess; there is no browser context, no persistent session, no analytics SDK.

---

## Your rights under GDPR / CCPA

This software does not process personal data within the meaning of GDPR Art. 4(1) or CCPA §1798.140(o). Therefore there is no data subject access request to file with this project. If you have queried UniProt about *yourself* (e.g. you are a named author of a UniProt entry), you are interacting with UniProt directly — see UniProt's privacy policy linked above.

If you believe `uniprot-mcp` itself is mishandling data, contact `santiago.maniches@gmail.com` with subject `[uniprot-mcp privacy]`.

---

## Children

This software is not directed to children under 13 (US: COPPA) or under 16 (EU: GDPR). It also does not collect any personal data, so the question is largely moot.

---

## Changes to this notice

Material changes to data handling are recorded in `CHANGELOG.md` under the matching version. Cosmetic changes (typo fixes, link updates) are not announced.

---

## Contact

Privacy questions: `santiago.maniches@gmail.com` · subject `[uniprot-mcp privacy]`. Encrypted contact on request.

Maintainer: Santiago Maniches · ORCID [0009-0005-6480-1987](https://orcid.org/0009-0005-6480-1987) · TOPOLOGICA LLC.
