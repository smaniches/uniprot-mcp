#!/usr/bin/env python3
"""Bind and verify a CycloneDX root component against an exact wheel artifact.

The CycloneDX environment generator describes the installed runtime graph and
uses pyproject.toml for the root component. This script closes the remaining
artifact-identity gap by reading Name/Version from the wheel itself and adding
its SHA-256 to metadata.component. Verification fails closed if the SBOM root
and wheel identity diverge or the recorded digest is absent/wrong.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from typing import Any

_SHA256_ALGS = {"SHA-256", "SHA256", "SHA_256"}


class BindingError(RuntimeError):
    """Raised when the SBOM cannot be proven to describe the supplied wheel."""


def _normalized_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _wheel_identity(wheel: Path) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(wheel) as archive:
            metadata_members = [
                name
                for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_members) != 1:
                raise BindingError(
                    f"expected exactly one .dist-info/METADATA in {wheel}, "
                    f"found {len(metadata_members)}"
                )
            message = BytesParser(policy=default).parsebytes(
                archive.read(metadata_members[0])
            )
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        raise BindingError(f"cannot read wheel metadata from {wheel}: {exc}") from exc

    name = message.get("Name")
    version = message.get("Version")
    if not name or not version:
        raise BindingError(f"wheel METADATA in {wheel} lacks Name or Version")
    return str(name), str(version)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise BindingError(f"cannot hash wheel {path}: {exc}") from exc
    return digest.hexdigest()


def _load_sbom(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BindingError(f"cannot read CycloneDX JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BindingError("CycloneDX document root must be a JSON object")
    return data


def _root_component(data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        raise BindingError("CycloneDX metadata object is missing")
    component = metadata.get("component")
    if not isinstance(component, dict):
        raise BindingError(
            "CycloneDX metadata.component is missing; generate with "
            "--pyproject pyproject.toml --mc-type library"
        )
    return component


def _assert_identity(component: dict[str, Any], wheel_name: str, wheel_version: str) -> None:
    root_name = component.get("name")
    root_version = component.get("version")
    if not isinstance(root_name, str) or _normalized_name(root_name) != _normalized_name(wheel_name):
        raise BindingError(
            f"SBOM root name {root_name!r} does not match wheel name {wheel_name!r}"
        )
    if str(root_version) != wheel_version:
        raise BindingError(
            f"SBOM root version {root_version!r} does not match wheel version {wheel_version!r}"
        )


def _sha256_entries(component: dict[str, Any]) -> list[str]:
    hashes = component.get("hashes", [])
    if not isinstance(hashes, list):
        raise BindingError("CycloneDX metadata.component.hashes must be a list")

    values: list[str] = []
    for entry in hashes:
        if not isinstance(entry, dict):
            raise BindingError("CycloneDX hash entries must be objects")
        alg = str(entry.get("alg", "")).upper()
        if alg in _SHA256_ALGS:
            content = entry.get("content")
            if not isinstance(content, str):
                raise BindingError("CycloneDX SHA-256 hash content must be a string")
            values.append(content.lower())
    return values


def bind(sbom: Path, wheel: Path) -> str:
    data = _load_sbom(sbom)
    component = _root_component(data)
    wheel_name, wheel_version = _wheel_identity(wheel)
    digest = _sha256(wheel)
    _assert_identity(component, wheel_name, wheel_version)

    existing = _sha256_entries(component)
    if existing and any(value != digest for value in existing):
        raise BindingError(
            "SBOM already contains a conflicting SHA-256 for the root component"
        )

    hashes = component.get("hashes", [])
    component["hashes"] = [
        entry
        for entry in hashes
        if str(entry.get("alg", "")).upper() not in _SHA256_ALGS
    ] + [{"alg": "SHA-256", "content": digest}]

    temporary = sbom.with_suffix(sbom.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(sbom)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise BindingError(f"cannot write bound SBOM {sbom}: {exc}") from exc

    verify(sbom, wheel)
    return digest


def verify(sbom: Path, wheel: Path) -> str:
    data = _load_sbom(sbom)
    component = _root_component(data)
    wheel_name, wheel_version = _wheel_identity(wheel)
    digest = _sha256(wheel)
    _assert_identity(component, wheel_name, wheel_version)

    recorded = _sha256_entries(component)
    if recorded != [digest]:
        raise BindingError(
            f"SBOM root SHA-256 {recorded!r} does not equal wheel SHA-256 {digest}"
        )
    return digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bind/verify a CycloneDX root component against an exact wheel."
    )
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="verify an existing binding without modifying the SBOM",
    )
    args = parser.parse_args(argv)

    try:
        digest = verify(args.sbom, args.wheel) if args.verify_only else bind(args.sbom, args.wheel)
    except BindingError as exc:
        print(f"SBOM binding error: {exc}", file=sys.stderr)
        return 1

    action = "verified" if args.verify_only else "bound"
    print(f"SBOM root {action} to wheel SHA-256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
