# Release runbook

How a `uniprot-mcp` release ships, link by link, and what to check
when something looks wrong. The chain is designed to be re-runnable
and auditable years after the fact — every artefact carries a
provenance attestation, an SBOM, and a Zenodo DOI.

## The chain

```
git tag v1.1.6  ──►  release.yml (Actions)  ──►  PyPI (Trusted Publishing, OIDC)
       │                       │
       │                       ├──►  GitHub Release (assets: dist/*, sbom.cdx.json, *.sigstore.json)
       │                       │            │
       │                       │            ├──►  release-verify.yml (this PR)
       │                       │            │            ├── pip index versions uniprot-mcp-server
       │                       │            │            ├── gh release view (asset presence)
       │                       │            │            ├── gh attestation verify (SLSA)
       │                       │            │            └── Zenodo records API (concept DOI lookup)
       │                       │            │
       │                       │            └──►  Zenodo webhook  ──►  version DOI minted
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
| `sign-and-release` | Sigstore signatures (`*.sigstore.json`); GitHub Release created with all assets |

If any job fails: read the failure, fix on a follow-up commit, push
a *new* tag (`v1.1.6.post1` or `v1.1.7`). Do not delete and re-push
the original tag — Zenodo treats the original as a separate version
and the duplicate DOI is forever.

### 4. Zenodo webhook (passive)

The Zenodo–GitHub integration is enabled per-account. Once flipped
on for the repo, every new GitHub Release triggers Zenodo to read
`.zenodo.json` and mint a new version DOI under the concept DOI
`10.5281/zenodo.20109942`. Typical latency: 30 s – 5 min.

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

`release-verify.yml` fires on `release: [published]`. It re-runs
each link in the chain and opens a `release-drift` issue if any
link's artifact is missing after a generous timeout. Greenable in
~5 min on a healthy release.

To re-trigger verification manually for an older tag:

```
gh workflow run release-verify.yml --field tag=v1.1.6
```

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
| `publish-pypi` fails with `Token request error` | OIDC publisher entry missing on PyPI | re-add at `pypi.org/manage/account/publishing/` |
| `release-verify` opens an issue saying "Zenodo: no record" | Webhook never enabled or deposit took >5 min | check Zenodo dashboard; if record exists, the verify timeout is too tight — bump the loop |
| `release-verify` says "missing sigstore bundle" | `sign-and-release` job was skipped (likely a permissions regression) | re-grant `id-token: write` on the job, re-run the workflow |
| `pip install uniprot-mcp-server==X` says version not found | PyPI CDN lag, usually clears in 60 s | wait, retry; if persistent, check `pypi.org/project/uniprot-mcp-server/#history` |

## Rolling forward, not back

**Never delete or re-push a release tag.** PyPI rejects re-uploads
of the same `(name, version)`. Zenodo treats the second push as a
separate version. GitHub renders both as duplicate releases. If a
release goes wrong, ship a `.postN` or a `Z+1` patch — fast forward
only.
