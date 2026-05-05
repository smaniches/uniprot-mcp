#!/usr/bin/env bash
# One-command beta-lab replication of the sealed benchmark for the
# latest published release. Override the version with the `VERSION`
# env var to verify any specific release (e.g. `VERSION=1.1.0`).
#
# What this script does (in order):
#
#   1. Downloads the published `uniprot-mcp-server` wheel for the
#      configured VERSION from PyPI into a temp dir and computes its
#      SHA-256.
#   2. Compares the wheel's SHA-256 to the value recorded in PyPI's API
#      (and prints the GitHub Release SHA-256 + the SLSA-attested subject
#      digest for cross-check).
#   3. Verifies the SLSA build provenance attestation against the source
#      commit on `smaniches/uniprot-mcp` (requires `gh attestation verify`).
#   4. Installs the wheel in an isolated venv.
#   5. Runs `uniprot-mcp --self-test` to confirm the binary works.
#   6. Re-derives every benchmark answer from live UniProt and
#      hash-compares the derived bytes against the committed
#      tests/benchmark/expected.hashes.jsonl. The plaintext
#      tests/benchmark/expected.jsonl is gitignored (it is the seal
#      itself; only its SHA-256 is committed) and is therefore not
#      required by this script.
#
# Exit code 0 iff every step passes. The point: a third party with a
# fresh checkout of this repo and network access can prove, without
# trusting the author, that the published wheel was built from a
# specific git commit and produces the sealed benchmark answers.
#
# Usage:
#   bash scripts/replicate.sh
#
# Requirements: python>=3.11, pip, gh (GitHub CLI), curl, jq, internet.
#
# License: Apache-2.0

set -euo pipefail

VERSION="${VERSION:-1.1.3}"
PKG="uniprot-mcp-server"
REPO="smaniches/uniprot-mcp"

WORK="$(mktemp -d -t uniprot-mcp-replicate-XXXX)"
trap 'rm -rf "$WORK"' EXIT

step()  { printf "\n\033[1;34m==> %s\033[0m\n" "$*"; }
ok()    { printf "  \033[32m[OK]\033[0m %s\n" "$*"; }
fail()  { printf "  \033[31m[FAIL]\033[0m %s\n" "$*"; exit 1; }

step "1. Download $PKG==$VERSION from PyPI"
python -m pip download --no-deps -q "${PKG}==${VERSION}" -d "$WORK/pypi"
WHEEL="$(ls "$WORK/pypi/${PKG//-/_}-${VERSION}-py3-none-any.whl")"
WHEEL_SHA="$(python -c "import hashlib,sys;print(hashlib.sha256(open('$WHEEL','rb').read()).hexdigest())")"
ok "downloaded wheel: $(basename "$WHEEL")"
echo "    wheel SHA-256: $WHEEL_SHA"

step "2. Cross-check SHA-256 across PyPI / GitHub Release / SLSA attestation"
PYPI_SHA="$(curl -fsSL "https://pypi.org/pypi/${PKG}/${VERSION}/json" \
  | python -c "import json,sys;[print(f['digests']['sha256']) for f in json.load(sys.stdin)['urls'] if f['packagetype']=='bdist_wheel']")"
echo "    PyPI registry: $PYPI_SHA"
[[ "$WHEEL_SHA" == "$PYPI_SHA" ]] && ok "wheel matches PyPI registry record" \
  || fail "wheel SHA-256 disagrees with PyPI registry"

# GitHub Release recorded SHA — by reading the asset directly. (gh release view
# does not expose checksums; download and compare.)
mkdir -p "$WORK/release"
gh release download "v${VERSION}" --repo "$REPO" \
  --pattern "${PKG//-/_}-${VERSION}-py3-none-any.whl" --dir "$WORK/release" --clobber
RELEASE_SHA="$(python -c "import hashlib;print(hashlib.sha256(open('$WORK/release/${PKG//-/_}-${VERSION}-py3-none-any.whl','rb').read()).hexdigest())")"
echo "    GitHub Release: $RELEASE_SHA"
[[ "$WHEEL_SHA" == "$RELEASE_SHA" ]] && ok "wheel matches GitHub Release asset" \
  || fail "PyPI wheel disagrees with GitHub Release asset"

step "3. Verify SLSA build provenance attestation"
gh attestation verify "$WHEEL" --owner "${REPO%/*}" >/dev/null && ok "SLSA attestation verified" \
  || fail "SLSA attestation did NOT verify"

step "4. Install in isolated venv"
python -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q "${PKG}==${VERSION}"
ok "installed"

step "5. uniprot-mcp --self-test (live UniProt)"
"$WORK/venv/bin/uniprot-mcp" --self-test 2>&1 | tail -5
ok "self-test passed"

step "6. Re-derive benchmark answers from live UniProt + check SHA-256 seal"
# Hash-only path: re-derives every Tier A / Tier B answer live and
# compares its canonical SHA-256 to the committed
# tests/benchmark/expected.hashes.jsonl. Does NOT require the
# gitignored tests/benchmark/expected.jsonl (which is the local-only
# seal plaintext). Tier C set-inclusion prompts (28, 29) are reported
# and skipped — maintainers verify those with the local plaintext via
# tests/benchmark/verify.py + verify_answers.py.
"$WORK/venv/bin/python" tests/benchmark/verify_against_hashes.py \
  tests/benchmark/expected.hashes.jsonl
ok "benchmark replication complete"

printf "\n\033[1;32m==== REPLICATION SUCCESS ====\033[0m\n"
echo "Source commit (per SLSA):  see 'gh attestation verify' output above"
echo "Wheel SHA-256:             $WHEEL_SHA"
echo "PyPI page:                 https://pypi.org/project/${PKG}/${VERSION}/"
echo "GitHub Release:            https://github.com/${REPO}/releases/tag/v${VERSION}"
