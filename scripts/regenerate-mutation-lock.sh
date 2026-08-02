#!/usr/bin/env bash
# Regenerates constraints/mutation.lock. DELIBERATE, MANUAL OPERATION.
#
# WHY THIS IS NOT IN scripts/regenerate-locks.sh
#
# mutmut==2.5.1 and glob2==0.7 publish no wheels — only sdists — and
# neither ships a pyproject.toml. Resolving that graph therefore forces
# uv to BUILD both source distributions to read their metadata, which
# executes their setup.py under the implicit setuptools backend.
#
# scripts/regenerate-locks.sh runs on EVERY pull request (the ci.yml
# `lock` gate) and in the monthly maintenance refresh. Neither is an
# appropriate place to execute arbitrary third-party build code, and
# regenerating there would break the maintenance workflow's
# upload-before-execution property. So that script compiles with
# --no-build, which forbids source builds outright, and mutation.lock is
# regenerated here instead: rarely, on purpose, by a human who then
# reviews the diff.
#
# WHEN TO RUN IT
#
#   * a CVE in mutmut's dependency graph needs picking up; or
#   * constraints/mutation.in changed.
#
# The second case is enforced, not left to memory:
# scripts/check_mutation_lock_sync.py compares the pins in mutation.in
# against mutation.lock without resolving anything, and runs in the
# ci.yml `lock` job, a pre-commit hook, and a contract test. Editing the
# input without running this script fails CI.
#
# Not on a schedule. mutmut is pinned to 2.5.1 exactly because
# scripts/mutmut_shard.py monkeypatches its internal
# `parse_run_argument` seam, so there is nothing to gain from routine
# churn here, and the mutation workflow is a weekly probe rather than a
# merge gate.
#
# WHAT TO CHECK IN THE DIFF
#
# Every changed line should be a version bump or a hash change for a
# package you recognise from mutmut's dependency graph. Because this
# resolution runs untrusted build code, review it as you would review a
# dependency bump from an unfamiliar source, and prefer running it in a
# throwaway environment.
#
# Usage:
#   python -m pip install --require-hashes -r constraints/uv-bootstrap.lock
#   scripts/regenerate-mutation-lock.sh              # reuse committed pins
#   scripts/regenerate-mutation-lock.sh --upgrade    # advance transitives

set -euo pipefail

cd "$(dirname "$0")/.."

UPGRADE=()
if [ "${1:-}" = "--upgrade" ]; then
  UPGRADE=(--upgrade)
fi

# Same flags as scripts/regenerate-locks.sh, minus --no-build: this
# graph cannot resolve without building its sdists. See the header for
# why that is confined to this script. --python-version must stay at the
# project's requires-python floor so the output is byte-identical on any
# interpreter.
uv pip compile constraints/mutation.in \
  --universal --generate-hashes --no-emit-package pip \
  --python-version 3.11 \
  "${UPGRADE[@]}" --output-file constraints/mutation.lock

cat <<'NOTE'

constraints/mutation.lock regenerated.

This resolution built mutmut and glob2 from source, executing their
setup.py. Review the diff before committing, and remember that the
mutation workflow installs this lock with --no-build-isolation on top of
constraints/mutation-build.lock, so the build tools it uses at INSTALL
time are hash-verified even though this RESOLUTION was not sandboxed.
NOTE
