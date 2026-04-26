# Incident log

> One line per incident, newest first. Each line links to a full
> postmortem in `docs/incidents/<YYYY-MM-DD>-<slug>.md`. Format:
>
> ```
> - YYYY-MM-DD · S<n> · <one-line summary> ([postmortem](incidents/...))
> ```
>
> Severity scale matches `POSTMORTEM_TEMPLATE.md`:
>
> - **S0** — silent data corruption (highest; tool answered with the *wrong* data without the agent or user noticing).
> - **S1** — tool returned a wrong answer that the agent could detect by reading our own provenance / error envelope.
> - **S2** — tool failed loudly; agent retried or surfaced an error; no incorrect data delivered.
> - **S3** — cosmetic / log-only / non-impacting.

## Open

_None._

## Closed

_None yet._ This project's incident log starts at v0.1.0 and will accumulate entries as upstream UniProt schema changes are observed by the nightly `integration.yml` workflow. The absence of entries here does **not** imply the project has had no failures during development — bugs caught before a release are tracked through CI / commits / `AUDIT.md`. This file specifically records **post-release** incidents that affected, or could have affected, users.

---

## Compliance officer view

A reader auditing this project in 2030 should expect to find this file populated rather than empty. An empty incident log is one of three things: (a) the project is too young to have failed yet, (b) the project does not detect its own failures, or (c) the project hides them. Topologica Bio commits to (a) being temporary and (b)/(c) being detectable: every release of `uniprot-mcp` carries a nightly live-API drift workflow that auto-files `integration-drift` issues, and the fix-PR-with-postmortem policy below is enforced through review.
