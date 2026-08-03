# Release runbook

How a `uniprot-mcp` release ships, link by link, and what to check
when something looks wrong. The chain is designed to be re-runnable
and auditable years after the fact — every artefact carries a
provenance attestation, an SBOM, and a Zenodo DOI.

## Release policy — releases are deliberate

release-please opens a release PR **only** for `feat:` (minor) and
`fix:` (patch) commits. Housekeeping types — `ci`, `docs`, `test`,
`refactor`, `perf`, `deps` — are marked `hidden: true` in
`release-please-config.json`, so merging them lands silently on `main`
**without** proposing a version bump. This stops a steady stream of
`ci:`/`docs:` merges from each cutting their own patch release. A
housekeeping change that genuinely warrants a release (e.g. a
security-relevant dependency bump) should be committed as `fix:` so it
triggers one. Past releases are immutable on PyPI/Zenodo regardless;
this only governs what gets cut going forward.

## The chain

```
git tag v1.1.6  ──►  release.yml (Actions)  ──►  PyPI (Trusted Publishing, OIDC)
       │                       │                       │
       │                       │                       └──►  MCP Registry (registry.modelcontextprotocol.io, GitHub OIDC)
       │                       │
       │                       ├──►  GitHub Release (assets: dist/*, sbom.cdx.json, *.sigstore.json)
       │                       │            │
       │                       │            ├──►  release-verify.yml (immediate)
       │                       │            │            ├── pip index versions uniprot-mcp-server
       │                       │            │            ├── gh release view (asset presence)
       │                       │            │            └── gh attestation verify (SLSA)
       │                       │            │
       │                       │            └──►  Zenodo webhook  ──►  version DOI minted
       │                       │                                      │
       │                       │                                      └──►  zenodo-verify.yml
       │                       │                                             (scheduled, delayed)
       │                       │
       │                       └──►  Sigstore signing (gh-action-sigstore-python)
       │
       └──►  release-drafter.yml (next-release draft updated on every push to main)
```

## Step-by-step

### 1. Pre-tag (on the release branch)

- [ ] `python scripts/check_versions.py` exits 0
      (every version-bearing file agrees with `pyproject.toml`).
- [ ] `pytest tests/unit tests/property tests/client tests/contract`
      green (includes `test_version_consistency` and
      `test_changelog_has_current_version`).
- [ ] `CHANGELOG.md` has a `## [X.Y.Z] - YYYY-MM-DD` entry.
- [ ] PR is merged into `main`; CI on the merge commit is green.

### 2. Tag push

```sh
git checkout main && git pull
git tag -a v1.1.6 -m "v1.1.6"
git push origin v1.1.6
```

The tag triggers `.github/workflows/release.yml`. Watch the run at
`https://github.com/smaniches/uniprot-mcp/actions/workflows/release.yml`.

### 3. `release.yml` jobs

| Job | Output |
|---|---|
| `build` | sdist + wheel; CycloneDX SBOM (`sbom.cdx.json`); SLSA build-provenance attestation; SBOM attestation; uploads as `release-artifacts` |
| `publish-pypi` | PyPI upload via OIDC Trusted Publishing (no token) |
| `publish-mcp-registry` | `server.json` published to the official MCP Registry (`registry.modelcontextprotocol.io`); runs after `publish-pypi`; GitHub OIDC auth, no secret |
| `sign-and-release` | Sigstore signatures (`*.sigstore.json`); GitHub Release created with all assets |

The `publish-mcp-registry` job authenticates to the registry with GitHub
OIDC for the `io.github.smaniches` namespace, and the registry verifies
control of the PyPI package via the `mcp-name: io.github.smaniches/uniprot-mcp`
marker in `README.md` (the PyPI long description). Both must stay intact for
the publish to validate. `server.json`'s version is bumped by release-please
(an `extra-files` target), so it always matches the released PyPI version.

If any job fails: read the failure, fix on a follow-up commit, push
a *new* tag (`v1.1.6.post1` or `v1.1.7`). Do not delete and re-push
the original tag — Zenodo treats the original as a separate version
and the duplicate DOI is forever.

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

`release-verify.yml` fires immediately on `release: [published]`. It verifies
PyPI, the complete GitHub Release asset set, and SLSA provenance. A failure in
one of those links opens `Release verification failed for <tag>` with the
`release-drift` label. Zenodo is deliberately excluded from this immediate
gate.

`zenodo-verify.yml` runs every six hours. For scheduled runs it checks the
latest stable GitHub Release only after that release is at least six hours old.
It compares the release tag with `metadata.version` on Zenodo concept record
`19817710`. Only a mismatch after that delayed threshold opens
`Zenodo verification failed for <tag>`. When a later delayed run observes the
expected version, it records the successful run on that Zenodo-specific issue
and closes it. A transient inability to read the Zenodo API fails the workflow
without claiming that the deposit itself is missing.

To re-trigger immediate verification manually for an older tag:

```
gh workflow run release-verify.yml --field tag=v1.1.6
```

To verify Zenodo immediately for the latest stable tag, bypassing the scheduled
age gate explicitly:

```
gh workflow run zenodo-verify.yml --field tag=v1.3.2
```

The manual Zenodo workflow rejects older tags because the concept-record API
exposes only the latest-version pointer. Historical version records must be
verified by their immutable version DOI rather than compared with that pointer.

### 7. CITATION.cff version-DOI append (next cycle)

Each release mints a Zenodo version DOI that is only known *after*
the deposit lands. The convention: the v1.1.6 release adds the
v1.1.6 changelog entry; the *following* release cycle (v1.1.7)
appends the v1.1.6 version DOI to `CITATION.cff` `identifiers:`.
This is why the file currently lists DOIs for v1.1.1 and v1.1.2
but not v1.1.5 — that entry will be added with v1.1.6's polish
work.

## When a release goes wrong

| Symptom | Probable cause | Fix |
|---|---|---|
| Immediate `release-verify` fails | PyPI, GitHub assets, or SLSA provenance is incomplete | inspect the named failed step and repair the release chain; Zenodo is not part of this result |
| Delayed `zenodo-verify` opens an issue | Zenodo still does not expose the release after the six-hour threshold | inspect the GitHub-Zenodo integration delivery and the existing concept record; do not mint manually or change the DOI badge |
| `zenodo-verify` cannot read the API | Zenodo or the network is temporarily unavailable | retry later; this condition does not assert that a deposit is missing |
| `publish-pypi` fails with `Token request error` | OIDC publisher entry missing on PyPI | re-add at `pypi.org/manage/account/publishing/` |
| `release-verify` says `missing sigstore bundle` | `sign-and-release` job was skipped (likely a permissions regression) | re-grant `id-token: write` on the job, re-run the workflow |
| `pip install uniprot-mcp-server==X` says version not found | PyPI CDN lag, usually clears in 60 s | wait, retry; if persistent, check `pypi.org/project/uniprot-mcp-server/#history` |

## Rolling forward, not back

**Never delete or re-push a release tag.** PyPI rejects re-uploads
of the same `(name, version)`. Zenodo treats the second push as a
separate version. GitHub renders both as duplicate releases. If a
release goes wrong, ship a `.postN` or a `Z+1` patch — fast forward
only.
