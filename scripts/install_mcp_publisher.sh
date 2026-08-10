#!/usr/bin/env bash
#
# install_mcp_publisher.sh - install a pinned, digest-verified mcp-publisher.
#
# Usage:
#   scripts/install_mcp_publisher.sh [--platform <os_arch>] [--archive <file>]
#
# Security boundary: this installer runs immediately before GitHub OIDC is
# used to publish to the MCP Registry, so the bytes it installs execute with
# publish authority. The release version and every per-platform digest are
# repository-controlled constants; updating the publisher therefore requires
# an explicit reviewed commit that changes the trust anchor recorded here.
#
# The script fetches one exact release asset from the official
# modelcontextprotocol/registry releases over HTTPS, verifies its SHA-256
# against the pinned digest, verifies the archive contains exactly the
# expected members, extracts only the binary, and asserts the binary reports
# the pinned version before installing it. It never authenticates and never
# publishes; those stay visible as separate steps in the calling workflow.
#
# --platform and --archive exist for hermetic tests: --platform selects which
# pinned digest row applies and --archive substitutes a local file for the
# download. Neither can weaken the anchor - the supplied bytes must still
# match a digest recorded in this file.
#
# Upgrading: bump MCP_PUBLISHER_VERSION, download each release asset, and
# replace every digest below with the value recomputed from the published
# asset (sha256sum mcp-publisher_<platform>.tar.gz). A digest that is not
# derived from the published asset defeats the check.
set -euo pipefail

MCP_PUBLISHER_VERSION="1.8.0"

usage() {
  echo "usage: $0 [--platform <os_arch>] [--archive <local-archive>]" >&2
}

archive_override=""
platform_override=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --archive)
      if [[ $# -lt 2 || -z "$2" ]]; then
        usage
        exit 64
      fi
      archive_override="$2"
      shift 2
      ;;
    --platform)
      if [[ $# -lt 2 || -z "$2" ]]; then
        usage
        exit 64
      fi
      platform_override="$2"
      shift 2
      ;;
    *)
      usage
      exit 64
      ;;
  esac
done

if [[ -n "$platform_override" ]]; then
  platform="$platform_override"
else
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch="$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')"
  platform="${os}_${arch}"
fi

# One digest per supported release asset, each recomputed from the published
# v1.8.0 asset itself. Any other platform fails closed.
case "$platform" in
  linux_amd64)  expected_sha256="1370446bbe74d562608e8005a6ccce02d146a661fbd78674e11cc70b9618d6cf" ;;
  linux_arm64)  expected_sha256="c978982c60e1b4903a976de090f04dc4fac4a320daa50704fcad2dbc93433d62" ;;
  darwin_amd64) expected_sha256="5350f756e8408d0e22802b7f384af941448358b503eb1e1772979a61b9b99fde" ;;
  darwin_arm64) expected_sha256="e74f8846c3b5d0428cfeae3f9f520bbf9031d18e68224108c3760d60b6aaf2e0" ;;
  *)
    echo "no pinned mcp-publisher ${MCP_PUBLISHER_VERSION} digest for platform ${platform}" >&2
    exit 65
    ;;
esac

ARCHIVE_NAME="mcp-publisher_${platform}.tar.gz"
URL="https://github.com/modelcontextprotocol/registry/releases/download/v${MCP_PUBLISHER_VERSION}/${ARCHIVE_NAME}"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
archive="$tmpdir/$ARCHIVE_NAME"

if [[ -n "$archive_override" ]]; then
  cp -- "$archive_override" "$archive"
else
  curl --fail --show-error --silent --location \
    --proto '=https' --tlsv1.2 \
    --output "$archive" \
    "$URL"
fi

actual_sha256="$(
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$archive" | cut -d' ' -f1
  else
    # macOS ships shasum rather than GNU coreutils sha256sum.
    shasum -a 256 "$archive" | cut -d' ' -f1
  fi
)"
if [[ "$actual_sha256" != "$expected_sha256" ]]; then
  echo "mcp-publisher SHA-256 mismatch for ${platform}" >&2
  echo "expected: $expected_sha256" >&2
  echo "actual:   $actual_sha256" >&2
  exit 66
fi

# The digest gate above authenticates the bytes; the member check additionally
# rejects an archive that carries anything beyond the three reviewed files.
expected_members="LICENSE
README.md
mcp-publisher"
actual_members="$(tar tzf "$archive" | LC_ALL=C sort)"
if [[ "$actual_members" != "$(printf '%s' "$expected_members" | LC_ALL=C sort)" ]]; then
  echo "unexpected members in authenticated archive ${ARCHIVE_NAME}:" >&2
  printf '%s\n' "$actual_members" >&2
  exit 67
fi

tar -xzf "$archive" -C "$tmpdir" mcp-publisher
if [[ ! -f "$tmpdir/mcp-publisher" ]]; then
  echo "authenticated archive does not contain mcp-publisher" >&2
  exit 67
fi
chmod +x "$tmpdir/mcp-publisher"

# Assert the authenticated binary self-reports the pinned version before it
# lands at the destination. mcp-publisher writes --version to stderr through
# Go's log package with a timestamp prefix, so match a substring of the
# merged stream.
version_output="$("$tmpdir/mcp-publisher" --version 2>&1)"
if [[ "$version_output" != *"mcp-publisher ${MCP_PUBLISHER_VERSION}"* ]]; then
  echo "mcp-publisher reported an unexpected version:" >&2
  printf '%s\n' "$version_output" >&2
  exit 68
fi

install -m 0755 "$tmpdir/mcp-publisher" ./mcp-publisher
echo "installed mcp-publisher v${MCP_PUBLISHER_VERSION} (digest, members and version verified for ${platform})"
