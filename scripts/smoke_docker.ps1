$ErrorActionPreference = "Stop"

# End-to-end container smoke test using the labeled synthetic fixture.
# Requires: activated venv (compliance-intelligence on PATH) and Docker running.

$env:ALLOW_SYNTHETIC_DATASET = "true"
compliance-intelligence ingest --source synthetic

docker compose up --build -d
try {
    $deadline = (Get-Date).AddSeconds(45)
    $health = $null
    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-RestMethod http://127.0.0.1:8000/health -TimeoutSec 2
            if ($health.datasets_loaded) { break }
        } catch {
            Start-Sleep -Milliseconds 500
        }
        Start-Sleep -Milliseconds 500
    }
    if ($null -eq $health -or -not $health.datasets_loaded) {
        throw "Health endpoint never reported datasets_loaded=true"
    }

    $body = '{"name":"Acme Galactic Holdings"}'
    $screen = Invoke-RestMethod -Method Post http://127.0.0.1:8000/v1/screen `
        -ContentType "application/json" -Body $body
    if (-not $screen.review_required) { throw "Expected the synthetic entity to be flagged" }
    if ($screen.hits[0].risk_tier -ne "exact") {
        throw "Expected an exact-tier hit, got $($screen.hits[0].risk_tier)"
    }
    if (-not $screen.dataset_snapshot_ids) { throw "Expected snapshot provenance in the response" }

    Write-Host "SMOKE TEST PASSED: container served an exact hit with snapshot provenance."
} finally {
    docker compose down
}
