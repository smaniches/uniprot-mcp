# Release runbook

How a `uniprot-mcp` release ships and what to verify. Release Please
owns version bumps, tags and GitHub Releases; downstream workflows build,
attest and publish artifacts. Zenodo synchronization is asynchronous.

## Release policy — releases are deliberate

`release-please.yml` runs on pushes to `main` and maintains a release
PR based on Conventional Commits. `feat:` normally requests a minor
release; `fix:` and `security:` normally request a patch release.
Security changes appear in a dedicated changelog section.

For a deliberate version override, include `Release-As: X.Y.Z` in the
body of a commit merged into `main`. Release Please then updates its
existing release PR. Preserve the footer in the final merge or squash
commit. Do not edit the manifest, generated version files or the
bot-owned release branch to select the next version.

`hidden: true` in `release-please-config.json` controls changelog
visibility; it does **not** guarantee that a commit type cannot cause
a release. Release eligibility and version selection are separate
from changelog display.

## The chain

```text
approved commit on main (optional Release-As: X.Y.Z)
  -> release-please.yml -> updated Release Please PR (versions + changelog)
  -> review, required checks, merge of that PR
  -> release-please.yml -> tag vX.Y.Z + GitHub Release
       |-> release.yml (explicit workflow_dispatch)
       |     |-> build (sdist, wheel, SLSA attestation)
       |     |-> sbom -> attest-sbom
       |     |-> publish-pypi -> publish-mcp-registry
       |     |-> sign-and-release (Sigstore; attach GitHub Release assets)
       |     `-> dispatch-verify -> release-verify.yml
       `-> Zenodo webhook -> version DOI -> zenodo-verify.yml (delayed)
```

## Step-by-step

### 1. Request and review the release

- [ ] Merge a focused preparatory PR into `main`. To override the
      version, put `Release-As: X.Y.Z` in the final commit body and
      confirm it survives the chosen merge method.
- [ ] Confirm `release-please.yml` updates the existing release PR to
      the intended version and adds a `## [X.Y.Z]` entry to
      `CHANGELOG.md` in the bot-generated branch.
- [ ] Check that `pyproject.toml`, `.release-please-manifest.json`,
      `CITATION.cff`, `.zenodo.json`, `.well-known/mcp.json`,
      both versions in `server.json` and the user-agent test pin agree.
- [ ] On the generated release PR head, run
      `python scripts/check_versions.py` and the focused
      `tests/contract/test_version_consistency.py` and
      `tests/contract/test_changelog_has_current_version.py` checks.
      Confirm the required CI and strict docs checks are green.

- [ ] Triage every review finding from maintainers, Codex, Dependabot
      and security tooling. Reproduce or explain non-applicability, reply
      with evidence and resolve actionable threads before merging.

**Release Please PR checks.** Release Please creates or updates its PR
using `GITHUB_TOKEN`. GitHub may queue the resulting `pull_request`
workflows for approval (`action_required`) rather than running them
automatically. On the generated release PR, use **Approve workflows to
run** when prompted, then confirm that CI, CodeQL and strict docs
checks pass for the current release PR head. Recheck after any bot update.
Do not substitute `workflow_dispatch` runs: GitHub does not count
checks from those runs as required PR checks. Never bypass the required
checks merely to merge a release PR.

### 2. Merge the generated release PR

After explicit approval and passing required checks, merge the Release
Please PR. Its subsequent `main` run creates the tag `vX.Y.Z` and
GitHub Release, then dispatches `release.yml` with that tag via
`workflow_dispatch`. The `push: tags` trigger is a fallback, not the
normal procedure. **Do not create or push the tag manually.**

### 3. `release.yml` jobs

| Job | Output |
|---|---|
| `build` | Build sdist and wheel, attach SLSA build-provenance attestation, upload dist artifact. |
| `sbom` | Generate CycloneDX SBOM from the exact built wheel in an unprivileged job. |
| `attest-sbom` | Attest the SBOM against the released wheel. |
| `publish-pypi` | Publish to PyPI via OIDC Trusted Publishing after build and SBOM attestation. |
| `publish-mcp-registry` | Publish `server.json` to the official MCP Registry after PyPI succeeds, using GitHub OIDC. |
| `sign-and-release` | Sigstore-sign artifacts and attach them and the SBOM to the Release Please-created GitHub Release; create a Release only on the push-tag fallback. |
| `dispatch-verify` | Start immediate verification after PyPI publication and signing; does not wait for the MCP Registry job. |

The **source distribution** is an installable package archive, not a complete
research checkout. It includes the package, metadata, license, and core
documents; the repository-only tests, benchmark records, and source-capture
fixtures remain in the GitHub tag. Those tests must be run against the tagged
repository checkout, where their required source files are available.
The offline CI test suite verifies this actual sdist inventory before release.

The `publish-mcp-registry` job authenticates to the registry with GitHub
OIDC for the `io.github.smaniches` namespace, and the registry verifies
control of the PyPI package via the `mcp-name: io.github.smaniches/uniprot-mcp`
marker in `README.md` (the PyPI long description). Both must stay intact for
the publish to validate. `server.json`'s version is bumped by release-please
(an `extra-files` target), so it always matches the released PyPI version.

If a downstream job fails, inspect which uploads already completed before
retrying: a published PyPI file cannot be uploaded again under the same
name and version. Re-run only a safely incomplete step; if a new version
is needed, use a fresh Release Please cycle. Never move or re-push a
published tag.

### 4. Zenodo webhook (passive)

The Zenodo–GitHub integration is enabled per-account. Once flipped
on for the repo, every new GitHub Release triggers Zenodo to read
`.zenodo.json` and mint a new version DOI under the concept DOI
`10.5281/zenodo.19817710`.

The synchronization is asynchronous. It often completes within 30 seconds to
five minutes, but five minutes is not a failure boundary. Release v1.3.2 was
still represented as v1.3.1 when its original five-minute verification ended
and later advanced automatically to v1.3.2. Do not create a manual deposit,
change the concept DOI badge, or move the release tag to compensate for normal
propagation delay.

**Enabling the webhook (one-time):**

1. Visit `https://zenodo.org/account/settings/github/`.
2. Toggle the `smaniches/uniprot-mcp` repo to ON.
3. Confirm the GitHub-side webhook at
   `https://github.com/smaniches/uniprot-mcp/settings/hooks` shows a
   recent successful delivery to `zenodo.org/api/hooks/receivers/...`
   with HTTP 200.

The webhook is idempotent — re-enabling and re-disabling will not
mint duplicate DOIs.

### 5. PyPI Trusted Publishing (passive)

The publisher entry on
`https://pypi.org/manage/account/publishing/` binds:

- Project: `uniprot-mcp-server`
- Owner: `smaniches`
- Repository: `uniprot-mcp`
- Workflow: `release.yml`
- Environment: `pypi`

If the entry is missing (e.g. after a PyPI account migration), the
`publish-pypi` job will fail with `OIDC token verification`. Re-add
the publisher entry with the four fields above.

### 6. Post-tag verification (automatic)

Verification is split by expected consistency window.

`release-verify.yml` declares a `release: published` trigger, but
GitHub suppresses downstream workflows for Release Please events created
with `GITHUB_TOKEN`. The normal path is an explicit dispatch from the
end of `release.yml`, after PyPI publication and release-asset signing
complete. It verifies the PyPI version and downloaded hashes, GitHub
Release assets, SLSA provenance and SBOM-to-wheel binding. A failure
opens `Release verification failed for <tag>` with the `release-drift`
label. **This workflow does not verify MCP Registry publication or Zenodo.**
Check the official registry entry and its package version separately.

`zenodo-verify.yml` runs every six hours. On scheduled runs it checks
the latest stable GitHub Release only when it is at least six hours old.
It compares the release tag with `metadata.version` on Zenodo concept
record `19817710`. An observed mismatch past that threshold opens
`Zenodo verification failed for <tag>`; a later match closes that
issue. Transient Zenodo API failures are inconclusive on scheduled
runs (the workflow remains green and retries later); manual runs fail
without asserting that a deposit is missing.

To re-trigger immediate verification manually for an older tag:

```
gh workflow run release-verify.yml --ref v1.4.0 --field tag=v1.4.0
```

To verify Zenodo immediately for the latest stable tag, bypassing the scheduled
age gate explicitly:

```
gh workflow run zenodo-verify.yml --ref v1.4.0 --field tag=v1.4.0
```

The manual Zenodo workflow rejects older tags because the concept-record API
exposes only the latest-version pointer. Historical version records must be
verified by their immutable version DOI rather than compared with that pointer.

### 7. CITATION.cff version-DOI append (next cycle)

A version DOI becomes available only after Zenodo ingests the GitHub
Release. The following release cycle may add that verified DOI to
`CITATION.cff` `identifiers:`, without replacing the concept DOI or
altering existing attribution.

## When a release goes wrong

| Symptom | Probable cause | Fix |
|---|---|---|
| Immediate `release-verify` fails | PyPI, GitHub assets, or SLSA provenance is incomplete | inspect the named failed step and repair the release chain; Zenodo is not part of this result |
| Delayed `zenodo-verify` opens an issue | Zenodo still does not expose the release after the six-hour threshold | inspect the GitHub-Zenodo integration delivery and the existing concept record; do not mint manually or change the DOI badge |
| `zenodo-verify` cannot read the API | Zenodo or the network is temporarily unavailable | retry later; this condition does not assert that a deposit is missing |
| `publish-pypi` fails with `Token request error` | OIDC publisher entry missing on PyPI | re-add at `pypi.org/manage/account/publishing/` |
| `release-verify` says `missing sigstore bundle` | Missing release asset, incorrect attachment glob, deletion, or verification invoked separately before signing completed | Inspect the `sign-and-release` job logs, generated bundles and attached GitHub Release assets; repair the specific missing artifact without unnecessarily rerunning PyPI publication |
| `pip install uniprot-mcp-server==X` says version not found | PyPI CDN lag, usually clears in 60 s | wait, retry; if persistent, check `pypi.org/project/uniprot-mcp-server/#history` |

## Rolling forward, not back

**Never delete, overwrite or re-push a release tag.** PyPI rejects
re-uploads of the same name and version, and Zenodo release records
must not be rewritten. If a partial publication cannot be safely
completed, ship a new forward version through Release Please.
