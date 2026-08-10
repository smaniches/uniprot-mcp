#!/usr/bin/env bash
set -euo pipefail

# Security boundary: this installer runs immediately before GitHub OIDC is used
# to publish to the MCP Registry. Both the release version and expected digest
# are repository-controlled constants. Updating the publisher therefore
# requires an explicit reviewed commit that changes the trust anchor.
MCP_PUBLISHER_VERSION="1.8.0"
MCP_PUBLISHER_SHA256="1370446bbe74d562608e8005a6ccce02d146a661fbd78674e11cc70b9618d6cf"
ARCHIVE_NAME="mcp-publisher_linux_amd64.tar.gz"
URL="https://github.com/modelcontextprotocol/registry/releases/download/v${MCP_PUBLISHER_VERSION}/${ARCHIVE_NAME}"

usage() {
  echo "usage: $0 [--archive <local-archive>]" >&2
}

archive_override=""
if [[ $# -gt 0 ]]; then
  if [[ $# -ne 2 || "$1" != "--archive" || -z "$2" ]]; then
    usage
    exit 64
  fi
  archive_override="$2"
fi

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

actual_sha256="$(sha256sum "$archive" | awk '{print $1}')"
if [[ "$actual_sha256" != "$MCP_PUBLISHER_SHA256" ]]; then
  echo "mcp-publisher SHA-256 mismatch" >&2
  echo "expected: $MCP_PUBLISHER_SHA256" >&2
  echo "actual:   $actual_sha256" >&2
  exit 65
fi

# Extract only the expected executable after the archive has been authenticated.
tar -xzf "$archive" -C "$tmpdir" mcp-publisher
if [[ ! -f "$tmpdir/mcp-publisher" ]]; then
  echo "authenticated archive does not contain mcp-publisher" >&2
  exit 66
fi
install -m 0755 "$tmpdir/mcp-publisher" ./mcp-publisher

echo "installed mcp-publisher v${MCP_PUBLISHER_VERSION} (SHA-256 verified)"
