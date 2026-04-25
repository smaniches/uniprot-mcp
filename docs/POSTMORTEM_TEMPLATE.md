# Postmortem template

> Copy this file to `docs/incidents/<YYYY-MM-DD>-<slug>.md` and fill in. The slug is short kebab-case (e.g. `2026-04-30-uniprot-features-shape-drift`). Keep blameless-incident discipline: name systems, not people. Link the fix PR; never edit a landed postmortem to retract — append corrections instead.

## Header

- **Incident date / time (UTC):**
- **Detected by:** _(nightly `integration.yml`, user report, internal review, …)_
- **Severity:** _S0 (silent data corruption) · S1 (tool returns wrong answer) · S2 (tool fails-loudly, agent retries) · S3 (cosmetic / log-only)_
- **Status:** _open · mitigated · resolved · monitoring_
- **Maintainer on point:** Santiago Maniches (ORCID 0009-0005-6480-1987)
- **Fix PR:** _(URL)_
- **Affected versions:** _(e.g. v1.0.1 – v1.0.3, fixed in v1.0.4)_

## Summary

Two or three sentences. What broke, what the user-visible effect was, and how it was fixed. A reader who only reads this section should be able to decide whether their environment was affected.

## Timeline (UTC)

Bullet list of events in chronological order. Be specific — timestamps to the minute, log lines verbatim where useful.

- `YYYY-MM-DDTHH:MM` —
- `YYYY-MM-DDTHH:MM` —
- `YYYY-MM-DDTHH:MM` —

## Root cause

Single paragraph. The technical thing that failed — *what* changed, *why* it broke us, *not* who-changed-it. If multiple causes contributed, list them as a numbered chain (cause 1 ⇒ cause 2 ⇒ user-visible effect).

## Impact

| Dimension | Value |
|---|---|
| Tools affected | _(e.g. `uniprot_get_features`, `uniprot_get_variants`)_ |
| Users affected | _(installs / agents / pipelines)_ |
| Provenance integrity | _did any record become non-reproducible? Y/N_ |
| Window of impact | _from `<detected>` to `<fix landed>`, _ |
| Remediation required from users | _(none / re-run query / pin to fixed version)_ |

## Detection

- **What alerted us:** _(`integration.yml` opened a `integration-drift` issue / user filed report #N / internal `--self-test` failure)_
- **Time-to-detect:** _(from breakage to alert)_
- **Test that caught it / should have caught it:**
- **If not caught automatically:** what test would have caught it earlier? Add it in the same PR as the fix.

## Resolution

What was changed, in flat declarative prose. Reference commit SHAs, not commit messages. Include the diff summary if the fix was small.

```
src/uniprot_mcp/client.py    | <stat>
tests/contract/...           | <stat>
```

## Follow-up actions

- [ ] Test added: _(name + path)_
- [ ] Monitoring added: _(workflow / alert / metric)_
- [ ] Documentation updated: _(README / ARCHITECTURE / THREAT_MODEL)_
- [ ] `INCIDENT_LOG.md` entry appended
- [ ] Upstream report filed (if a UniProt-side fix is needed): _(link)_
- [ ] Compatibility shim status: _(temporary, with sunset commit; or permanent)_

## Lessons learned

Two or three bullets. What does future-us need to know? Examples:

- A response field we treated as required was actually optional in the spec — add `.get()` defaults across this category of fields.
- The integration suite ran nightly but only on one accession; widen the canary to N accessions across organism kingdoms.
- The `Provenance` record carries the upstream URL but not the response hash; if we add `response_sha256` we can detect this earlier.

## Compliance officer view

> Would a regulated bio-pharma compliance officer reading this postmortem in 2030 trust the project? Answer in one paragraph. If "no", what additional evidence is required? File those as **Follow-up actions** above.
