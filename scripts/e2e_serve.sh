#!/usr/bin/env bash
# Serve two PRODUCTION Worker builds on workerd for the Playwright suite
# (P0-06). Neither `vite preview` nor `vite dev` is the production runtime.
#
#   default  (E2E_PORT_DEFAULT, 4310): no VITE_QCOMPASS_* flags, which is what
#            users get today; cosmology regression, smoke, admin 404.
#   domains  (E2E_PORT_DOMAINS, 4311): every VITE_QCOMPASS_* flag on, for the
#            QCompass domain specs.
#
# Builds land in dist-e2e/{default,domains}; each runs its own wrangler dev
# with separate state so the two instances don't share a .wrangler dir.
set -euo pipefail
DEF="${E2E_PORT_DEFAULT:-4310}"
DOM="${E2E_PORT_DOMAINS:-4311}"
export WRANGLER_SEND_METRICS=false

rm -rf dist-e2e && mkdir -p dist-e2e
bun run build
cp -r dist dist-e2e/default
VITE_QCOMPASS_MULTIDOMAIN=true VITE_QCOMPASS_CHEMISTRY=true VITE_QCOMPASS_CONDMAT=true \
  VITE_QCOMPASS_AMO=true VITE_QCOMPASS_HEP=true VITE_QCOMPASS_NUCLEAR=true \
  VITE_QCOMPASS_GRAVITY=true VITE_QCOMPASS_STATMECH=true VITE_QCOMPASS_AUTH=true \
  bun run build
cp -r dist dist-e2e/domains

pids=()
trap 'kill "${pids[@]}" 2>/dev/null || true' EXIT INT TERM

# Supervise each server: if wrangler dev exits (it has crashed mid-suite in CI
# with an empty "[ERROR]"), restart it so the remaining specs still run and
# report. Every restart is recorded in dist-e2e/RESTARTS; CI fails the job if
# that file exists (scripts/check_e2e_restarts.sh), so a crash is never hidden.
serve() {
  local name="$1" port="$2"
  while true; do
    npx wrangler dev --config "dist-e2e/$name/server/wrangler.json" --port "$port" --ip 127.0.0.1 \
      --persist-to "dist-e2e/.state-$name" || true
    echo "$(date -u +%FT%TZ) wrangler dev ($name, :$port) exited; restarting" | tee -a dist-e2e/RESTARTS >&2
    sleep 1
  done
}

serve default "$DEF" &
pids+=($!)
for _ in $(seq 120); do
  curl -s -o /dev/null "http://127.0.0.1:$DEF/" && break
  sleep 1
done
serve domains "$DOM" &
pids+=($!)
wait
