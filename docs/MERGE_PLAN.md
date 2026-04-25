# Merge & flip plan — `hardening-v2` → `main` → public

**Status date:** 2026-04-24. Tracks the path from the current
`hardening-v2` working branch to the first public-listed `v1.0.1`
release. Authoritative companion to `docs/PENDING_V1.md`.

---

## Branch graph (current)

```
main           6b73e02  feat: initial release of uniprot-mcp 0.1.0     [v0.1.0 — private baseline]
                  │
                  └──► hardening-v2 (active)
                        a365dae  raise the bar — supply-chain, snapshots
                        d6fef42  audit remediation — src layout, …
                        f9a6c1b  ruff auto-fixes
                        8de1ffe  ci: mypy src-path; bump tool coverage
                        6c368cb  ruff format
                        e646595  mypy: explicit dict types
                        1401845  remove CodeQL + Scorecard (private-repo)
                        6f9b737  audit remediation (#1)
                        020c2a8  raise coverage gate to 99 %
                        ──── (4 commits in this session) ────
                        549d259  PENDING_V1.md
                        843ace5  SHA-pin Actions + SBOM attestation
                        4e441f7  search fuzz + Retry-After delay tests
                        eab93ef  provenance on every response (§3a.3)
                        ──── (Wave A docs commits, Wave B, Wave D, Wave E ahead)
audit-remediation     ← legacy branch, contained in hardening-v2 — delete after merge
```

`hardening-v2` is therefore strictly ahead of both `main` and
`audit-remediation`; no rebase or back-merge is required.

---

## Merge order of operations

### Phase 0 — keep `hardening-v2` healthy as it grows

Every commit on `hardening-v2` lands with:

- `pytest` green on the offline suite (unit + property + client + contract).
- `mypy src/uniprot_mcp` clean.
- `ruff check src tests` clean.
- `ruff format --check src tests` clean.
- `bandit -r src/uniprot_mcp` clean.
- `pip-audit --strict` clean *(when network is available — billing-blocked CI cannot run this; we run locally before each push)*.

Pushes happen after each coherent batch — never accumulate a multi-commit unpushed state. The session that pushed two commits late hit the boundary of acceptable; the rule going forward is *push within the same turn the commit lands*.

### Phase 1 — close every PENDING_V1.md item on `hardening-v2`

Wave A → Wave B → Wave D in order, with Wave E (mutation, 3×3 matrix, docs.yml, branch protection) deferred until **after** the GitHub Actions billing reset (~2026-05-01). Every closure recorded in PENDING_V1.md §6.

**Checkpoint:** `hardening-v2` cannot ship to `main` until §1, §2, §3 are all green or explicitly waived in PENDING_V1.md §4 with a documented reason.

### Phase 2 — pre-merge dry run on `hardening-v2`

Before opening the PR:

1. Local clean clone test — `git clone . /tmp/uniprot-mcp-clean && cd /tmp/... && pip install -e ".[test,dev]" && pytest`. Catches anything that depends on the developer's working-tree state (cached wheels, editable installs, env vars).
2. `--self-test` against live UniProt. Should print `[live] P04637 -> TP53 OK [PASS]`.
3. `python -m build` produces a wheel and sdist; both inspect cleanly with `tarfile.open` / `zipfile.ZipFile` for unexpected files (no `__pycache__`, no `.pyc`, no editable-install metadata).
4. `gh pr create --draft` with the merge description below — keep it draft so reviewers can comment without it being mergeable yet.

### Phase 3 — open the PR, request review, merge

PR title: `Release uniprot-mcp v1.0.1 — public-flip readiness`.

PR body: a structured summary keyed off PENDING_V1.md sections, plus a **changelog summary** that becomes the body of the GitHub Release notes. Use the heredoc-form below.

```
## Summary
First public release of uniprot-mcp. Closes the AUDIT.md follow-up
list, raises every formatter to provenance-aware output, expands the
tool surface from 10 to N, ships a pre-registered benchmark, and
flips the repository visibility on the same day this PR merges.

## Closes (PENDING_V1.md)
- §1.1 …  – §1.7  AUDIT-driven follow-ups (six items)
- §2.1 …  – §2.8  Launch-plan gates (eight items)
- §3a.* / §3b.* / §3c.* / §3d.* Raise-the-bar additions

## Test plan
- [x] Offline suite green: `pytest tests/unit tests/property tests/client tests/contract`
- [x] Live integration green: `pytest --integration tests/integration`
- [x] mypy: `mypy src/uniprot_mcp`
- [x] ruff: `ruff check src tests && ruff format --check src tests`
- [x] Bandit: `bandit -r src/uniprot_mcp`
- [x] pip-audit: `pip-audit --strict`
- [x] Mutation: ≥ 95 % kill on every source module — see `MUTATION_SCORES.md`
- [x] Benchmark run: `tests/benchmark/run-2026-MM-DD/` on disk
- [x] `python -m build` produces clean wheel + sdist
- [x] `--self-test` green against live UniProt
- [x] Independent reviewer ran the suite locally
- [x] Beta cohort ≥ 3 successful replications (RESULTS.md)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

**Merge strategy:** preserve commit history. Use a **merge commit** (not squash) so each closure is independently `git blame`-able. Public scientific software benefits from a granular history; reviewers and citers should be able to point at the exact commit a feature landed.

If branch protection on `main` requires linear history (recommended for OSS hygiene), use **rebase merge** instead. Both preserve commit-level detail; squash erases it.

### Phase 4 — tag and the flip itself

Immediately after merge:

```bash
git checkout main
git pull --ff-only
git tag -a v1.0.1 -m "Release v1.0.1 — first public uniprot-mcp"
git push origin v1.0.1
```

Pushing the tag fires `release.yml`, which:

1. Builds the wheel + sdist.
2. Generates the CycloneDX SBOM.
3. Attests SLSA build provenance + SBOM (added in `843ace5`).
4. Publishes to PyPI via Trusted Publishing (must be configured in pending-publisher mode beforehand — PENDING_V1.md §1.5).
5. Signs artefacts with Sigstore.
6. Creates a GitHub Release with auto-generated notes + attached artefacts.

While the release workflow runs (~6 min), perform the **visibility flip**:

```bash
gh repo edit smaniches/uniprot-mcp --visibility public --accept-visibility-change-consequences
```

The flip is irreversible without GitHub Support intervention. **Do not flip until** the release workflow has finished green and the tag is signed-off in the PyPI dashboard.

After flip:

1. Re-add `codeql.yml` and `scorecard.yml` workflows (they were removed for private-repo billing reasons in commit `1401845`). Push to `main`. Both workflows activate on the next event.
2. Verify the GitHub Pages docs build (Phase 1 §2.4 docs.yml) and the URL is reachable.
3. Verify Dependabot, Secret Scanning, Push Protection, and CodeQL alerts are all enabled in the repo settings (private repos do not all surface these).
4. Submit MCP Registry PR, Smithery listing, Anthropic Connectors form, Glama listing — drafts for all four already on disk per PENDING_V1.md §3c.3.

### Phase 5 — post-flip validation

Within 24 h of the flip, verify:

| Check | How |
|---|---|
| PyPI page renders correctly | https://pypi.org/project/uniprot-mcp/1.0.1/ |
| `pip install uniprot-mcp` from a clean venv works | `python -m venv /tmp/v && /tmp/v/bin/pip install uniprot-mcp && /tmp/v/bin/uniprot-mcp --self-test` |
| Sigstore signature verifies | `python -m sigstore verify identity --cert-identity 'https://github.com/smaniches/uniprot-mcp/.github/workflows/release.yml@refs/tags/v1.0.1' dist/*.whl` |
| SLSA attestation verifies | `gh attestation verify dist/*.whl --repo smaniches/uniprot-mcp` |
| SBOM attestation verifies | `gh attestation verify dist/*.whl --repo smaniches/uniprot-mcp --predicate-type https://cyclonedx.org/bom` |
| CodeQL ran and is green | https://github.com/smaniches/uniprot-mcp/security/code-scanning |
| Scorecard score is published | https://securityscorecards.dev/viewer/?uri=github.com/smaniches/uniprot-mcp |
| Zenodo DOI minted | https://zenodo.org/account/settings/github/ — auto-creates one per tag once the integration is enabled |

If any of the above fail, do **not** announce. Open a `release-defect` issue, fix forward with `v1.0.2`. Do not retract the tag — that breaks SLSA/Sigstore guarantees for any consumer that has already pinned to it.

---

## Rollback

The release pipeline is idempotent up to PyPI's "no-overwrite" policy: a published `v1.0.1` cannot be re-uploaded. Therefore:

- **Bug discovered before flip**: amend on `hardening-v2`, force-push, no public exposure.
- **Bug discovered after PyPI publish but before MCP-Registry submission**: yank from PyPI (`uniprot-mcp==1.0.1` becomes uninstallable by name; older versions remain). Ship `v1.0.2`. Do not delete the GitHub Release — write a `Yanked due to <issue>` line in its notes.
- **Bug discovered after directories listed**: same as above plus update the directory listings to point at the new version. The MCP Registry has a versioning model; Smithery and Anthropic do not retract listings.
- **Catastrophic security defect post-flip**: file a CVE; advise users to pin to a fixed version; ship a patched release immediately. Repository visibility cannot be reverted to private without losing CodeQL/Scorecard history; do not attempt.

---

## Branch hygiene after merge

- Delete `audit-remediation` (already subsumed): `git push origin --delete audit-remediation`.
- Keep `hardening-v2` on origin until v1.1 work begins; then either delete it or rename to `hardening-v2-archive`.
- Enable branch protection on `main`: required reviewers ≥ 1, required status checks (CI matrix + integration), no force pushes, no direct commits, signed commits required.

---

## What this plan deliberately does not do

- **No rebase of `main` onto `hardening-v2`.** `main` is the stable public reference; we merge into it, we don't rewrite it.
- **No squash merge.** Granular history is more valuable than a tidy log entry.
- **No surprise visibility flip.** The flip is gated on every Phase 5 verification passing. If they don't pass, the repo stays private and we ship `v1.0.2` first.
- **No simultaneous orchestrator (`topologica-bio`) flip.** That repo has its own merge plan; this one is independent. `uniprot-mcp` flips on its own evidence.
