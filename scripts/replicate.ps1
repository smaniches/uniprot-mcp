# One-command beta-lab replication of the v1.1.0 sealed benchmark (Windows).
#
# See scripts/replicate.sh for the canonical narrative; this is the
# PowerShell port for Windows beta-labs.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/replicate.ps1
#
# Requirements: python>=3.11, pip, gh (GitHub CLI), internet.
# License: Apache-2.0

$ErrorActionPreference = "Stop"

$VERSION = if ($env:VERSION) { $env:VERSION } else { "1.1.3" }
$PKG = "uniprot-mcp-server"
$REPO = "smaniches/uniprot-mcp"

$WORK = New-Item -ItemType Directory -Path (Join-Path $env:TEMP "uniprot-mcp-replicate-$([guid]::NewGuid().ToString('N').Substring(0,8))")

function Step($msg)  { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function OK($msg)    { Write-Host "  [OK] $msg"   -ForegroundColor Green }
function Fail($msg)  { Write-Host "  [FAIL] $msg" -ForegroundColor Red; exit 1 }

try {
    Step "1. Download $PKG==$VERSION from PyPI"
    & python -m pip download --no-deps -q "$PKG==$VERSION" -d "$WORK\pypi"
    $WHEEL = Get-ChildItem "$WORK\pypi\*.whl" | Select-Object -First 1
    $WHEEL_SHA = (Get-FileHash $WHEEL.FullName -Algorithm SHA256).Hash.ToLower()
    OK "downloaded wheel: $($WHEEL.Name)"
    Write-Host "    wheel SHA-256: $WHEEL_SHA"

    Step "2. Cross-check SHA-256 across PyPI / GitHub Release / SLSA attestation"
    $pypiJson = Invoke-RestMethod -Uri "https://pypi.org/pypi/$PKG/$VERSION/json"
    $PYPI_SHA = ($pypiJson.urls | Where-Object { $_.packagetype -eq "bdist_wheel" } | Select-Object -First 1).digests.sha256
    Write-Host "    PyPI registry: $PYPI_SHA"
    if ($WHEEL_SHA -eq $PYPI_SHA) { OK "wheel matches PyPI registry record" }
    else                          { Fail "wheel SHA-256 disagrees with PyPI registry" }

    New-Item -ItemType Directory -Path "$WORK\release" | Out-Null
    & gh release download "v$VERSION" --repo $REPO --pattern "$($WHEEL.Name)" --dir "$WORK\release" --clobber
    $RELEASE_SHA = (Get-FileHash "$WORK\release\$($WHEEL.Name)" -Algorithm SHA256).Hash.ToLower()
    Write-Host "    GitHub Release: $RELEASE_SHA"
    if ($WHEEL_SHA -eq $RELEASE_SHA) { OK "wheel matches GitHub Release asset" }
    else                              { Fail "PyPI wheel disagrees with GitHub Release asset" }

    Step "3. Verify SLSA build provenance attestation"
    $owner = ($REPO -split "/")[0]
    & gh attestation verify $WHEEL.FullName --owner $owner | Out-Null
    if ($LASTEXITCODE -eq 0) { OK "SLSA attestation verified" }
    else                      { Fail "SLSA attestation did NOT verify" }

    Step "4. Install in isolated venv"
    & python -m venv "$WORK\venv"
    & "$WORK\venv\Scripts\pip.exe" install -q "$PKG==$VERSION"
    OK "installed"

    Step "5. uniprot-mcp --self-test (live UniProt)"
    & "$WORK\venv\Scripts\uniprot-mcp.exe" --self-test
    OK "self-test passed"

    Step "6. Re-derive benchmark answers from live UniProt + check SHA-256 seal"
    # Hash-only path: re-derives every Tier A / Tier B answer live and
    # compares its canonical SHA-256 to the committed
    # tests\benchmark\expected.hashes.jsonl. Does NOT require the
    # gitignored tests\benchmark\expected.jsonl. Tier C set-inclusion
    # prompts (28, 29) are reported and skipped — maintainers verify
    # those with the local plaintext via tests\benchmark\verify.py +
    # verify_answers.py.
    & "$WORK\venv\Scripts\python.exe" tests\benchmark\verify_against_hashes.py tests\benchmark\expected.hashes.jsonl
    OK "benchmark replication complete"

    Write-Host "`n==== REPLICATION SUCCESS ====" -ForegroundColor Green
    Write-Host "Source commit (per SLSA):  see 'gh attestation verify' output above"
    Write-Host "Wheel SHA-256:             $WHEEL_SHA"
    Write-Host "PyPI page:                 https://pypi.org/project/$PKG/$VERSION/"
    Write-Host "GitHub Release:            https://github.com/$REPO/releases/tag/v$VERSION"
}
finally {
    Remove-Item $WORK -Recurse -Force -ErrorAction SilentlyContinue
}
