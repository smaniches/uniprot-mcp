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
# That guarantee only holds if the PEP 517 build backend is covered too.
# constraints/build.in exists for exactly that reason: see the comment
# above the compile calls below.
#
# Both .github/workflows/ci.yml (the `lock` gate) and
# .github/workflows/dev-lock-maintenance.yml (the monthly refresh) call
# this script, so the compile flags cannot drift between the job that
# verifies the locks and the job that regenerates them.
#
# SCOPE: this script regenerates every lock whose graph resolves purely
# from wheels — dev, test, docs, release, mutation-build, uv-bootstrap.
# It does NOT regenerate constraints/mutation.lock, whose graph is
# sdist-only and therefore requires executing third-party build code.
# That one has its own deliberate entry point:
#     scripts/regenerate-mutation-lock.sh
# Because of that split, running this script executes no third-party
# code, which is what lets the maintenance workflow upload the refreshed
# locks before any untrusted toolchain runs.
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
# --no-build is a SECURITY control, not an optimisation, and must not be
# dropped. It forbids uv from building any source distribution during
# resolution. Building an sdist means executing its setup.py / build
# backend, and this script runs on every pull request via the ci.yml
# `lock` gate. With --no-build, resolution reads wheel metadata only, so
# no third-party code executes on the routine path at all.
#
# Every input compiled below resolves cleanly under it. If adding a
# dependency makes this fail, that dependency is sdist-only: either find
# a wheel-publishing alternative, or give it its own deliberate,
# reviewed lock the way constraints/mutation.lock is handled.
PYTHON_TARGET=3.11
COMMON=(--universal --generate-hashes --no-emit-package pip
        --python-version "$PYTHON_TARGET" --no-build)

# constraints/build.in carries the PEP 517 build backend (hatchling and
# the editables hook requirement). It is compiled into every lock whose
# workflow installs or builds the local project, because --no-deps does
# NOT suppress build isolation: without the backend already present and
# hash-verified, `pip install -e .` downloads hatchling from the index
# outside --require-hashes. With it, those workflows pass
# --no-build-isolation and touch the index for nothing.
BUILD=constraints/build.in

# Toolchains resolved from pyproject.toml extras.
uv pip compile pyproject.toml "$BUILD" --extra test --extra dev "${COMMON[@]}" \
  "${UPGRADE[@]}" --output-file constraints/dev.lock
uv pip compile pyproject.toml "$BUILD" --extra test "${COMMON[@]}" \
  "${UPGRADE[@]}" --output-file constraints/test.lock
uv pip compile pyproject.toml "$BUILD" --extra docs "${COMMON[@]}" \
  "${UPGRADE[@]}" --output-file constraints/docs.lock

# Toolchains that are not pyproject extras because they are never
# installed alongside the project: each one runs in its own job.
# release.lock also carries the build backend so `python -m build` can
# run with --no-isolation.
uv pip compile constraints/release.in "$BUILD" "${COMMON[@]}" \
  "${UPGRADE[@]}" --output-file constraints/release.lock

# Backend used to build third-party sdists. Only the mutation toolchain
# needs it, but the input itself resolves entirely from wheels, so it is
# safe to regenerate on the routine path. mutation.yml installs this and
# then installs mutation.lock with --no-build-isolation.
uv pip compile constraints/mutation-build.in "${COMMON[@]}" \
  "${UPGRADE[@]}" --output-file constraints/mutation-build.lock

# constraints/mutation.lock is deliberately NOT regenerated here. mutmut
# and glob2 publish no wheels, so resolving that graph makes uv BUILD
# their sdists, executing third-party setup.py code. This script runs on
# every pull request (the ci.yml `lock` gate) and in the monthly refresh,
# and neither is an appropriate place to execute arbitrary build code.
# Regenerating it is a deliberate, reviewed operation:
#     scripts/regenerate-mutation-lock.sh

# The uv bootstrap lock is intentionally NOT upgraded: uv is the tool
# generating every lock above, so its version is what makes the output
# byte-reproducible. Bump constraints/uv.in deliberately, in its own
# reviewable commit.
uv pip compile constraints/uv.in "${COMMON[@]}" \
  --output-file constraints/uv-bootstrap.lock
