$ErrorActionPreference = "Stop"

# End-to-end container smoke test using the labeled synthetic fixture.
# Requires: activated venv (compliance-intelligence on PATH) and Docker running.
# Same two contracts as scripts/smoke_docker.sh, which CI runs:
#   1. fail closed - with no allowed snapshot loaded, /v1/screen returns 503
#   2. provenance  - with the synthetic fixture allowed, a known entity returns
#                    an exact-tier hit carrying dataset snapshot IDs

# An isolated, gitignored snapshot directory under the read-only ./data mount, so
# the container sees exactly one snapshot (the synthetic fixture) even on a host
# that has ingested real OFAC/UN snapshots into the default location.
$hostSnapshots = "data/processed/smoke-snapshots"
if (Test-Path $hostSnapshots) { Remove-Item -Recurse -Force $hostSnapshots }
$env:SNAPSHOT_DIRECTORY = $hostSnapshots
$env:ALLOW_SYNTHETIC_DATASET = "true"
compliance-intelligence ingest --source synthetic
# From here on the variable is read by compose.yml, so it takes the container path.
$env:SNAPSHOT_DIRECTORY = "/app/data/processed/smoke-snapshots"

# docker compose reports progress on stderr. Under $ErrorActionPreference = "Stop"
# PowerShell 5.1 turns that into a terminating error whenever a caller merges the
# streams, so docker runs with errors set to Continue and the exit code is checked.
function Invoke-Docker([string[]]$Arguments) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & docker @Arguments 2>&1 | ForEach-Object { Write-Host "$_" }
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Wait-ForHealth([bool]$expectedLoaded) {
    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-RestMethod http://127.0.0.1:8000/health -TimeoutSec 2
            if ($health.datasets_loaded -eq $expectedLoaded) { return }
        } catch { }
        Start-Sleep -Milliseconds 500
    }
    throw "Health endpoint never reported datasets_loaded=$expectedLoaded"
}

$body = '{"name":"Acme Galactic Holdings"}'
try {
    Write-Host "== 1/2 fail closed: synthetic snapshot present but not allowed"
    $env:ALLOW_SYNTHETIC_DATASET = "false"
    Invoke-Docker @("compose", "up", "--build", "-d")
    Wait-ForHealth $false
    $status = 0
    try {
        Invoke-WebRequest -Method Post http://127.0.0.1:8000/v1/screen `
            -ContentType "application/json" -Body $body -UseBasicParsing | Out-Null
        $status = 200
    } catch {
        $status = [int]$_.Exception.Response.StatusCode
    }
    if ($status -ne 503) { throw "Expected 503 without an allowed snapshot, got $status" }
    Invoke-Docker @("compose", "down")

    Write-Host "== 2/2 provenance: synthetic fixture allowed"
    $env:ALLOW_SYNTHETIC_DATASET = "true"
    Invoke-Docker @("compose", "up", "-d")
    Wait-ForHealth $true
    $screen = Invoke-RestMethod -Method Post http://127.0.0.1:8000/v1/screen `
        -ContentType "application/json" -Body $body
    if (-not $screen.review_required) { throw "Expected the synthetic entity to be flagged" }
    if ($screen.hits[0].risk_tier -ne "exact") {
        throw "Expected an exact-tier hit, got $($screen.hits[0].risk_tier)"
    }
    if (@($screen.dataset_snapshot_ids) -ne @("synthetic-fixture-4a9ccd33f11a")) {
        throw "Expected only the synthetic snapshot in the response, got $($screen.dataset_snapshot_ids)"
    }

    Write-Host "SMOKE TEST PASSED: 503 without an allowed snapshot; exact hit with snapshot provenance with one."
} finally {
    Invoke-Docker @("compose", "down")
    if (Test-Path $hostSnapshots) { Remove-Item -Recurse -Force $hostSnapshots }
}
