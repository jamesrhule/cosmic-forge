#!/usr/bin/env bash
# R19 lock (PLAN.md correction 7b): every cosmology-byte-identity baseline
# PNG must match e2e/__screenshots__/R19.sha256 exactly, and no unpinned
# cosmology PNG may exist. R19.sha256 changes only in an authorised rebaseline
# (JAMES DECISIONS 13, 15, 16; any other is a Decision-by-build, Decision 22).
set -euo pipefail
cd "$(dirname "$0")/../e2e/__screenshots__"
sha256sum --check --strict R19.sha256
pinned=$(awk '{print $2}' R19.sha256 | sort)
present=$(find . -path '*cosmology-byte-identity.spec.ts/*.png' | sort)
if [ "$pinned" != "$present" ]; then
  echo "::error::cosmology baseline set differs from R19.sha256"
  diff <(echo "$pinned") <(echo "$present") || true
  exit 1
fi
echo "R19 baselines locked: $(echo "$present" | wc -l) PNGs match R19.sha256"
