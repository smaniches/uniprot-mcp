#!/usr/bin/env bash
# Regenerates every hash-locked file under constraints/.
#
# The locks exist so that each workflow can install its third-party
# toolchain with `python -m pip install --require-hashes -r <lock>`.
# Under --require-hashes pip refuses to install any artifact whose
# SHA-256 is not recorded in the lock, which means a compromised or
# substituted wheel on the index cannot enter a CI, release, or
# mutation-testing job.
#
# Both .github/workflows/ci.yml (the `lock` gate) and
# .github/workflows/dev-lock-maintenance.yml (the monthly refresh) call
# this script, so the compile flags cannot drift between the job that
# verifies the locks and the job that regenerates them.
#
# Usage:
#   scripts/regenerate-locks.sh              # reuse committed pins as preferences
#   scripts/regenerate-locks.sh --upgrade    # advance to newest allowed by ranges
#
# Requires the uv version pinned in constraints/uv-bootstrap.lock:
#   python -m pip install --require-hashes -r constraints/uv-bootstrap.lock
#
# --upgrade is deliberately NOT recorded in the generated headers, so a
# refreshed lock stays byte-identical to what the CI gate regenerates
# without it.

set -euo pipefail

cd "$(dirname "$0")/.."

UPGRADE=()
if [ "${1:-}" = "--upgrade" ]; then
  UPGRADE=(--upgrade)
fi

# Shared flags. --universal resolves across every supported Python and
# platform in one file so the same lock serves the whole test matrix;
# --generate-hashes is what makes --require-hashes possible downstream;
# pip is excluded because it is a runner-provided bootstrap component,
# not a dependency of this project.
#
# --python-version is REQUIRED for reproducibility and must not be
# dropped. Without it uv resolves against whatever interpreter happens
# to be running, which overrides pyproject's requires-python: compiling
# on 3.12 emits a narrower wheel set than compiling on 3.11 (the cp311
# hashes disappear), so the CI sync gate fails against a lock generated
# on a different Python. Pinning it to the project's floor makes the
# output byte-identical on any runner and keeps the resolution as wide
# as requires-python allows.
PYTHON_TARGET=3.11
COMMON=(--universal --generate-hashes --no-emit-package pip
        --python-version "$PYTHON_TARGET")

# Toolchains resolved from pyproject.toml extras.
uv pip compile pyproject.toml --extra test --extra dev "${COMMON[@]}" \
  "${UPGRADE[@]}" --output-file constraints/dev.lock
uv pip compile pyproject.toml --extra test "${COMMON[@]}" \
  "${UPGRADE[@]}" --output-file constraints/test.lock
uv pip compile pyproject.toml --extra docs "${COMMON[@]}" \
  "${UPGRADE[@]}" --output-file constraints/docs.lock

# Toolchains that are not pyproject extras because they are never
# installed alongside the project: each one runs in its own job.
uv pip compile constraints/release.in "${COMMON[@]}" \
  "${UPGRADE[@]}" --output-file constraints/release.lock

# mutmut is version-locked in constraints/mutation.in (not a range),
# because scripts/mutmut_shard.py couples to a 2.5.1 internal seam.
# --upgrade therefore only advances its transitive dependencies.
uv pip compile constraints/mutation.in "${COMMON[@]}" \
  "${UPGRADE[@]}" --output-file constraints/mutation.lock

# The uv bootstrap lock is intentionally NOT upgraded: uv is the tool
# generating every lock above, so its version is what makes the output
# byte-reproducible. Bump constraints/uv.in deliberately, in its own
# reviewable commit.
uv pip compile constraints/uv.in "${COMMON[@]}" \
  --output-file constraints/uv-bootstrap.lock
