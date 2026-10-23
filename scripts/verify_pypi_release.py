#!/usr/bin/env python3
"""Verify canonical PyPI metadata and downloaded release artifact digests."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlsplit


class VerificationError(ValueError):
    """The public release cannot be verified without weakening the gate."""


def _download(url: str, limit: int) -> bytes:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {"pypi.org", "files.pythonhosted.org"}:
        raise VerificationError("release URL is not on an allowed HTTPS origin")
    # The preceding check rejects non-HTTPS schemes and unapproved origins.
    request = urllib.request.Request(  # noqa: S310
        url, headers={"User-Agent": "uniprot-release-verifier"}
    )
    with urllib.request.urlopen(request, timeout=45) as response:  # noqa: S310
        data = response.read(limit + 1)
    if len(data) > limit:
        raise VerificationError("release response exceeds the size limit")
    return data


def _normalize(name: object) -> str:
    return re.sub(r"[-_.]+", "-", str(name)).lower()


def verify_metadata(data: dict[str, Any], package: str, version: str) -> list[dict[str, Any]]:
    """Fail closed on wrong identity, missing formats, yanks, or bad digests."""
    info = data.get("info", {})
    if _normalize(info.get("name", "")) != _normalize(package) or info.get("version") != version:
        raise VerificationError("PyPI package/version does not match the requested release")
    files = data.get("urls", [])
    if not {"bdist_wheel", "sdist"}.issubset({item.get("packagetype") for item in files}):
        raise VerificationError("release must contain both a wheel and an sdist")
    for item in files:
        if item.get("yanked"):
            raise VerificationError("release contains a yanked artifact")
        if not re.fullmatch(r"[a-f0-9]{64}", item.get("digests", {}).get("sha256", "")):
            raise VerificationError("artifact lacks a valid SHA-256 digest")
        parsed = urlsplit(item.get("url", ""))
        if parsed.scheme != "https" or parsed.netloc != "files.pythonhosted.org":
            raise VerificationError("artifact URL is not on canonical PyPI file storage")
        if not isinstance(item.get("size"), int) or not 0 < item["size"] <= 50_000_000:
            raise VerificationError("artifact size is absent or outside the allowed bound")
    return files


def verify_release(package: str, version: str) -> None:
    """Read one exact release and verify its wheel and sdist bytes."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", package):
        raise VerificationError("invalid package name")
    if not re.fullmatch(r"[A-Za-z0-9_.+!-]+", version):
        raise VerificationError("invalid version")
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    metadata = json.loads(_download(url, 5_000_000))
    for item in verify_metadata(metadata, package, version):
        content = _download(item["url"], item["size"])
        digest = hashlib.sha256(content).hexdigest()
        if len(content) != item["size"] or digest != item["digests"]["sha256"]:
            raise VerificationError(f"artifact integrity failure: {item['filename']}")
        print(f"PyPI SHA-256 verified: {item['filename']} {digest}")
    print(f"PyPI release verified: {package} {version}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: verify_pypi_release.py PACKAGE VERSION", file=sys.stderr)
        return 2
    for attempt in range(1, 6):
        try:
            verify_release(*args)
            return 0
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"PyPI transport failure, attempt {attempt}/5: {exc}", file=sys.stderr)
            if attempt < 5:
                time.sleep(30)
        except (VerificationError, KeyError, TypeError, json.JSONDecodeError) as exc:
            print(f"PyPI verification failed: {exc}", file=sys.stderr)
            return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
