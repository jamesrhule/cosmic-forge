#!/usr/bin/env bash
# Fails if scripts/e2e_serve.sh had to restart a crashed wrangler dev server
# during the Playwright run (the restart keeps the suite running; this keeps
# the crash visible). Wrangler logs are uploaded by the CI job.
set -euo pipefail
if [ -f dist-e2e/RESTARTS ]; then
  echo "::error::wrangler dev crashed during the e2e run and was restarted:"
  cat dist-e2e/RESTARTS
  exit 1
fi
echo "no wrangler dev restarts during the e2e run"
