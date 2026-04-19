# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

Please do **not** open a public GitHub issue for security reports.

Email security reports to **santiago.maniches@gmail.com** with the subject
line `[uniprot-mcp security]`. Include:

- A description of the issue and its impact
- Steps to reproduce (proof-of-concept welcome)
- Affected version(s) and environment
- Any suggested mitigation

You will receive an acknowledgement within **72 hours**. We aim to triage
and provide a remediation plan within **7 days** for high-severity issues.

## Scope

In scope:
- Code in this repository
- Supply-chain concerns (dependency confusion, typosquatting of this
  package on PyPI, tampered release artifacts)

Out of scope (but please still tell us):
- Vulnerabilities in the UniProt REST API itself — report those to
  [UniProt Help](https://www.uniprot.org/contact).
- Vulnerabilities in the upstream `mcp` or `httpx` packages — please
  report to those projects directly.

## Disclosure

We coordinate responsible disclosure: fixed release first, public
advisory with CVE second. Researchers are credited in the advisory
unless they prefer anonymity.
