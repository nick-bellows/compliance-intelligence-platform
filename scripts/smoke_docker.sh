#!/usr/bin/env bash
# End-to-end container smoke test using the labeled synthetic fixture.
# POSIX counterpart of scripts/smoke_docker.ps1; CI runs this one.
#
# Proves two contracts against the real image, not the unit-test app factory:
#   1. fail closed  - with no allowed snapshot loaded, /v1/screen returns 503
#   2. provenance   - with the synthetic fixture allowed, a known entity returns
#                     an exact-tier hit carrying dataset snapshot IDs
#
# Requires: the package installed (compliance-intelligence on PATH), Docker with
# the compose plugin, curl, and python.
set -euo pipefail
cd "$(dirname "$0")/.."

HEALTH_URL="http://127.0.0.1:8000/health"
SCREEN_URL="http://127.0.0.1:8000/v1/screen"
# An isolated, gitignored snapshot directory under the read-only ./data mount, so
# the container sees exactly one snapshot (the synthetic fixture) even on a host
# that has ingested real OFAC/UN snapshots into the default location.
HOST_SNAPSHOTS="data/processed/smoke-snapshots"
CONTAINER_SNAPSHOTS="/app/data/processed/smoke-snapshots"

cleanup() {
  docker compose down --timeout 5 >/dev/null 2>&1 || true
  rm -rf "$HOST_SNAPSHOTS"
}
trap cleanup EXIT

wait_for_health() {
  # $1 = expected value of datasets_loaded ("true" or "false")
  local expected="$1" attempt body
  for attempt in $(seq 1 90); do
    if body=$(curl -fsS "$HEALTH_URL" 2>/dev/null) \
      && python -c 'import json,sys; sys.exit(0 if str(json.loads(sys.argv[1])["datasets_loaded"]).lower()==sys.argv[2] else 1)' "$body" "$expected"; then
      return 0
    fi
    sleep 1
  done
  echo "health endpoint never reported datasets_loaded=$expected" >&2
  docker compose logs --no-color | tail -40 >&2
  return 1
}

rm -rf "$HOST_SNAPSHOTS"
SNAPSHOT_DIRECTORY="$HOST_SNAPSHOTS" ALLOW_SYNTHETIC_DATASET=true \
  compliance-intelligence ingest --source synthetic
# From here on the variable is read by compose.yml, so it takes the container path.
export SNAPSHOT_DIRECTORY="$CONTAINER_SNAPSHOTS"

echo "== 1/2 fail closed: synthetic snapshot present but not allowed"
ALLOW_SYNTHETIC_DATASET=false docker compose up --build -d --quiet-pull
wait_for_health false
# The body is followed by the status code; the last three bytes are the code.
# (No -o /dev/null: it is not portable to Git Bash with path conversion off.)
status=$(curl -sS -w '%{http_code}' -X POST "$SCREEN_URL" -H 'Content-Type: application/json' -d '{"name":"Acme Galactic Holdings"}' | tail -c 3)
if [ "$status" != "503" ]; then
  echo "expected 503 without an allowed snapshot, got $status" >&2
  exit 1
fi
docker compose down --timeout 5

echo "== 2/2 provenance: synthetic fixture allowed"
ALLOW_SYNTHETIC_DATASET=true docker compose up -d --quiet-pull
wait_for_health true
response=$(curl -fsS -X POST "$SCREEN_URL" \
  -H 'Content-Type: application/json' -d '{"name":"Acme Galactic Holdings"}')
python - "$response" <<'PY'
import json
import sys

body = json.loads(sys.argv[1])
assert body["review_required"], body
assert body["hits"], body
assert body["hits"][0]["risk_tier"] == "exact", body["hits"][0]
assert body["dataset_snapshot_ids"] == ["synthetic-fixture-4a9ccd33f11a"], body["dataset_snapshot_ids"]
print("SMOKE TEST PASSED: 503 without an allowed snapshot; exact hit with snapshot provenance with one.")
PY
