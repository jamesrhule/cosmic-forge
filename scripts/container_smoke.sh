#!/usr/bin/env bash
# Container smoke test for the qcompass-api and qcompass-worker images (P3-07).
#
#   DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/postgres \
#     scripts/container_smoke.sh qcompass-api:ci qcompass-worker:ci
#
# DATABASE_URL must be a THROWAWAY Postgres (CI's service container; R13).
# Containers run on the host network, exactly as configured for production
# (QCOMPASS_ENV=production, no anonymous access), and:
#   1. both images run as a non-root user and declare a HEALTHCHECK;
#   2. migrations apply from inside the api image (supabase/migrations);
#   3. the api answers /healthz and /readyz (database, storage, queue);
#   4. the worker starts, answers its /healthz, and connects to the queue;
#   5. a real job flows through both: an API key (issued in the api image)
#      submits an H2/STO-3G chemistry run, the worker container computes it,
#      and the API returns it completed with a classical-reference hash.
set -euo pipefail
API_IMAGE="${1:?api image}"
WORKER_IMAGE="${2:?worker image}"
: "${DATABASE_URL:?set DATABASE_URL to a throwaway Postgres}"
API_PORT="${SMOKE_API_PORT:-18080}"
WORKER_PORT="${SMOKE_WORKER_PORT:-18081}"
API="http://127.0.0.1:${API_PORT}"
NAME="qcsmoke-$$"

cleanup() {
  for c in "$NAME-api" "$NAME-worker"; do
    if docker inspect "$c" >/dev/null 2>&1; then
      echo "── logs: $c"; docker logs --tail 60 "$c" 2>&1 || true
      docker rm -f "$c" >/dev/null 2>&1 || true
    fi
  done
}
trap cleanup EXIT

fail() { echo "::error::container smoke: $*"; exit 1; }

wait_http() { # <url> <seconds>
  for _ in $(seq "$2"); do
    curl -fsS "$1" >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}

echo "── 1. image configuration"
for img in "$API_IMAGE" "$WORKER_IMAGE"; do
  user="$(docker inspect --format '{{.Config.User}}' "$img")"
  [ -n "$user" ] && [ "${user%%:*}" != "0" ] && [ "${user%%:*}" != "root" ] || fail "$img runs as root ($user)"
  docker inspect --format '{{json .Config.Healthcheck.Test}}' "$img" | grep -q healthz \
    || fail "$img has no /healthz HEALTHCHECK"
  [ "$(docker run --rm --entrypoint id "$img" -u)" != "0" ] || fail "$img: id -u is 0"
  docker run --rm --entrypoint python "$img" -c \
    "import sys; assert sys.version_info[:2] == (3, 12), sys.version" || fail "$img: not Python 3.12"
  echo "$img: user $user, HEALTHCHECK /healthz, Python 3.12"
done

common=(--network host -e "DATABASE_URL=$DATABASE_URL" -e QCOMPASS_ENV=production)

echo "── 2. migrations from the api image"
docker run --rm "${common[@]}" --entrypoint python "$API_IMAGE" -m ucgle_f1.db.migrate up

echo "── 3. api /healthz and /readyz"
docker run -d --name "$NAME-api" "${common[@]}" -e "PORT=$API_PORT" "$API_IMAGE" >/dev/null
wait_http "$API/healthz" 90 || fail "api /healthz did not answer"
curl -fsS "$API/healthz"; echo
ready="$(curl -sS -w '\n%{http_code}' "$API/readyz")"
echo "$ready"
[ "$(tail -n1 <<<"$ready")" = "200" ] || fail "api /readyz is not 200"
# Production configuration: no anonymous access.
code="$(curl -s -o /dev/null -w '%{http_code}' "$API/api/qcompass/domains")"
[ "$code" = "401" ] || fail "anonymous request got $code, expected 401 (dev access must be off)"

echo "── 4. worker starts and answers /healthz"
docker run -d --name "$NAME-worker" "${common[@]}" -e "PORT=$WORKER_PORT" "$WORKER_IMAGE" \
  --classes cpu --poll-seconds 0.5 >/dev/null
wait_http "http://127.0.0.1:$WORKER_PORT/healthz" 90 || fail "worker /healthz did not answer"
curl -fsS "http://127.0.0.1:$WORKER_PORT/healthz"; echo
for _ in $(seq 60); do
  docker logs "$NAME-worker" 2>&1 | grep -q "serving cpu" && break
  sleep 1
done
docker logs "$NAME-worker" 2>&1 | grep -q "serving cpu" || fail "worker never reported serving"

echo "── 5. a job through the api and worker containers"
TOKEN="$(docker run --rm "${common[@]}" --entrypoint python "$API_IMAGE" -c '
from ucgle_f1.m8_agent.auth import get_auth_store
store = get_auth_store()
store.ensure_tenant("smoke")
print(store.issue("smoke", scopes=["read", "run"]).token_id)
' | tail -n1)"
[ -n "$TOKEN" ] || fail "could not issue an API key"
auth=(-H "Authorization: Bearer $TOKEN" -H "X-QCompass-Tenant: smoke")
body='{"manifest":{"domain":"chemistry","version":"1.0","problem":{"molecule":"H2","basis":"sto-3g","backend_preference":"classical","reference":"FCI","shots":1,"seed":0},"backend_request":{"kind":"classical"}}}'
sub="$(curl -sS -w '\n%{http_code}' "${auth[@]}" -H 'Content-Type: application/json' \
  -d "$body" "$API/api/qcompass/domains/chemistry/runs")"
echo "$sub"
[ "$(tail -n1 <<<"$sub")" = "202" ] || fail "submit was not 202"
run_id="$(head -n1 <<<"$sub" | python3 -c 'import json,sys; print(json.load(sys.stdin)["runId"])')"
status=""
for _ in $(seq 180); do
  run="$(curl -fsS "${auth[@]}" "$API/api/qcompass/domains/chemistry/runs/$run_id")"
  status="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' <<<"$run")"
  [ "$status" = "completed" ] || [ "$status" = "failed" ] && break
  sleep 1
done
[ "$status" = "completed" ] || fail "run $run_id ended '$status'"
hash="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["provenance"]["classical_reference_hash"])' <<<"$run")"
[ -n "$hash" ] || fail "completed run has no classical-reference hash"
echo "run $run_id completed in the worker container; classical_reference_hash=$hash"
echo "container smoke: OK"
