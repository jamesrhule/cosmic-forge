#!/usr/bin/env bash
# Serve the workbench built against a LOCAL compute API (P4-02) for the live
# Playwright project (playwright.live.config.ts).
#
# The build sets VITE_API_URL (so every service uses the SDK and reads no
# fixtures) plus every VITE_QCOMPASS_* domain flag, and is served on workerd
# (`wrangler dev`, the production runtime) at LIVE_WEB_PORT (4312). The API
# and worker are started separately by scripts/live_stack.py.
set -euo pipefail
WEB="${LIVE_WEB_PORT:-4312}"
API="${LIVE_API_PORT:-8791}"
export WRANGLER_SEND_METRICS=false

rm -rf dist-e2e-live && mkdir -p dist-e2e-live
VITE_API_URL="http://127.0.0.1:$API" \
  VITE_QCOMPASS_MULTIDOMAIN=true VITE_QCOMPASS_CHEMISTRY=true VITE_QCOMPASS_CONDMAT=true \
  VITE_QCOMPASS_AMO=true VITE_QCOMPASS_HEP=true VITE_QCOMPASS_NUCLEAR=true \
  VITE_QCOMPASS_GRAVITY=true VITE_QCOMPASS_STATMECH=true \
  bun run build
cp -r dist dist-e2e-live/web

exec npx wrangler dev --config dist-e2e-live/web/server/wrangler.json --port "$WEB" --ip 127.0.0.1 \
  --persist-to dist-e2e-live/.state
