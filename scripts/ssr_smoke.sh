#!/usr/bin/env bash
# SSR smoke test for the production Cloudflare Worker build (P0-05).
# Serves dist/ with `wrangler dev` (workerd, same runtime as production) and
# asserts every listed route returns 200 and the Worker logs no errors.
#
# Usage: scripts/ssr_smoke.sh [all-domains]
#   all-domains  also check /domains/<id>/{configurator,runs,research,visualizer}
#                (build must have the VITE_QCOMPASS_* flags on).
set -euo pipefail
PORT="${SSR_SMOKE_PORT:-8790}"
LOG="$(mktemp)"
npx wrangler dev --config dist/server/wrangler.json --port "$PORT" --ip 127.0.0.1 >"$LOG" 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true; rm -f "$LOG"' EXIT
for _ in $(seq 90); do
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/" || true)
  [ "$code" != "000" ] && break
  sleep 1
done

routes=(/ /pricing /status)
if [ "${1:-}" = "all-domains" ]; then
  for d in cosmology.ucglef1 chemistry.molecular condmat.lattice amo.rydberg hep.lattice nuclear.structure gravity.syk statmech.sampling; do
    for r in configurator runs research visualizer; do routes+=("/domains/$d/$r"); done
  done
fi

fail=0
for r in "${routes[@]}"; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -L --max-redirs 3 "http://127.0.0.1:$PORT$r")
  echo "$code $r"
  [ "$code" = "200" ] || fail=1
done
if grep -q 'ERROR' "$LOG"; then
  echo "Worker logged errors:"; grep -A5 'ERROR' "$LOG" | head -40
  fail=1
fi
exit "$fail"
