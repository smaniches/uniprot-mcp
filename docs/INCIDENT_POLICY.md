# Incident policy

> Plain-English commitment, enforceable through review. Applies to every
> release on `main` from `v1.0.1` onward.

## What triggers a postmortem

A postmortem is required (not optional) when **any** of the following occur:

1. **Nightly `integration.yml` goes red** and the failing run is *not* a transient network blip resolved by the next run. The dedicated `integration-drift` GitHub label and auto-filed issue make this case unambiguous.
2. **A user files an issue that is reproducibly an incorrect tool answer** (S0 or S1 severity). Includes any case where the JSON envelope's `data` does not match what the upstream UniProt response actually said.
3. **A `Provenance` record turns out to be non-reproducible** — the recorded URL no longer returns the expected response and we cannot explain why from the recorded release/release_date.
4. **A security report** is received that confirms a real vulnerability (per `SECURITY.md`). Postmortem may be private until the vulnerability is patched and a CVE assigned, then merged to public.

A postmortem is **not** required for:

- Caught-in-development bugs (those live in `AUDIT.md`, commit messages, and CI history).
- Build-system flakes that don't reach a tagged release.
- Cosmetic regressions caught by snapshot tests during a PR.

## What the postmortem must contain

Use [`POSTMORTEM_TEMPLATE.md`](POSTMORTEM_TEMPLATE.md). Every required section must be filled in before the fix PR is merged. Sections that read "n/a" must explain why.

The fix PR and the postmortem land **together**, in the same commit if practical:

```
git checkout -b fix/<slug>
# … fix, tests, docs ...
cp docs/POSTMORTEM_TEMPLATE.md docs/incidents/$(date -u +%Y-%m-%d)-<slug>.md
# fill in the template
echo "- $(date -u +%Y-%m-%d) · S<n> · <summary> ([postmortem](incidents/<slug>.md))" >> docs/INCIDENT_LOG.md
git add -A && git commit
gh pr create
```

The contract test in `tests/contract/test_incident_policy.py` (added below) checks that `docs/incidents/` contents and `docs/INCIDENT_LOG.md` agree on which incidents exist — drift between the two breaks CI.

## Blameless discipline

Postmortems describe systems that failed, not people. Reviewers reject any phrasing that names a contributor as the cause. Patterns we standardise on:

- "The release workflow's pin to `actions/upload-artifact@v4` resolved to a SHA that …" — fine.
- "X forgot to bump the SHA pin" — rewrite as "the SHA-pin update was not landed before the workflow ran."

The audit trail (Git log) already names contributors; the postmortem's job is to record what we *learned*, which is a property of the system, not the author.

## Sunset

A postmortem is **never** edited to retract its findings. Append corrections at the bottom under a `## Correction (YYYY-MM-DD)` heading. The Git history is the audit trail.

## Compliance officer view

A 2030 compliance officer auditing `uniprot-mcp` will look for: (a) a non-empty incident log on a project of any age, (b) postmortems that name systems and timestamps, (c) a fix-PR linked from each entry, (d) follow-up actions marked `[x]` rather than orphaned. This policy exists to keep all four green by default — they would otherwise need active maintenance, which entropy resists.
