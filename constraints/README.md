# Hash-locked toolchain constraints

Every file in this directory is generated. Do not hand-edit a `.lock`.

## Why these exist

Workflows install their third-party toolchains with:

```
python -m pip install --require-hashes -r constraints/<name>.lock
```

Under `--require-hashes`, pip refuses to install any artifact whose SHA-256 is
not recorded in the lock. A substituted or backdoored wheel on the index
therefore cannot enter a CI, docs, release, or mutation-testing job, even if it
satisfies the version specifier.

The project itself is installed separately with `python -m pip install
--no-deps -e .`, which downloads nothing: all external dependencies are already
present from the hash-verified lock above.

## The files

| File | Generated from | Consumed by |
| --- | --- | --- |
| `dev.lock` | `pyproject.toml` extras `test` + `dev` | `ci.yml` lint, `dev-lock-maintenance.yml` validate, `mutation.yml` |
| `test.lock` | `pyproject.toml` extra `test` | `ci.yml` test matrix, `integration.yml` |
| `docs.lock` | `pyproject.toml` extra `docs` | `docs.yml` |
| `release.lock` | `release.in` (`build`, `cyclonedx-bom`) | `release.yml` |
| `mutation.lock` | `mutation.in` (`mutmut==2.5.1`) | `mutation.yml` |
| `uv-bootstrap.lock` | `uv.in` (`uv==0.11.20`) | `ci.yml` lock gate, `dev-lock-maintenance.yml` |

`uv-bootstrap.lock` is the root of trust: it installs the exact `uv` that
compiles every other lock, which is what makes regeneration byte-reproducible.
Bump `uv.in` deliberately, in its own reviewable commit.

## Regenerating

```
python -m pip install --require-hashes -r constraints/uv-bootstrap.lock
scripts/regenerate-locks.sh              # reuse committed pins as preferences
scripts/regenerate-locks.sh --upgrade    # advance to newest allowed by ranges
```

`--upgrade` is not recorded in the generated headers, so a refreshed lock stays
byte-identical to what the CI `lock` gate regenerates without it. That gate runs
`scripts/regenerate-locks.sh` and then `git diff --exit-code constraints/`, so
CI fails if a lock is stale relative to its inputs.

`.github/workflows/dev-lock-maintenance.yml` runs the `--upgrade` form monthly
and opens a single PR with the result.

## Dependabot

`.github/dependabot.yml` excludes `constraints/**`. Dependabot's pip parser
cannot tell a transitive pin from a direct dependency in a compiled lock, so it
would otherwise open PRs that bump transitives and break the sync gate.
Transitive updates arrive through the monthly maintenance workflow instead;
for an urgent CVE, dispatch that workflow manually.
