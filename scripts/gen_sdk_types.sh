#!/usr/bin/env bash
# Regenerate the TypeScript SDK's types from the compute API's OpenAPI (P4-02).
#
#   scripts/gen_sdk_types.sh          write the committed files
#   scripts/gen_sdk_types.sh --check  regenerate into a temp dir and fail if
#                                     the committed files differ (CI)
#
# Inputs: the FastAPI app (`ucgle_f1.m8_agent.server.build_app`) via
# scripts/dump_openapi.py, and openapi-typescript pinned in package.json.
# Outputs (both committed, both deterministic):
#   packages/ts/qcompass-frontend-sdk/openapi.json
#   packages/ts/qcompass-frontend-sdk/src/generated/openapi.ts
set -euo pipefail
cd "$(dirname "$0")/.."

SDK=packages/ts/qcompass-frontend-sdk
JSON="$SDK/openapi.json"
TS="$SDK/src/generated/openapi.ts"
GEN=node_modules/.bin/openapi-typescript
[ -x "$GEN" ] || { echo "openapi-typescript missing: run 'bun install --frozen-lockfile'" >&2; exit 2; }

generate() { # <json-out> <ts-out>
  mkdir -p "$(dirname "$1")" "$(dirname "$2")"
  uv run --frozen python scripts/dump_openapi.py "$1"
  # Defaults do not make a property required: FastAPI request bodies may omit
  # them (ChatRequest.provider, …), and the API lists what it requires.
  "$GEN" "$1" -o "$2" --default-non-nullable false >/dev/null
}

if [ "${1:-}" = "--check" ]; then
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  generate "$tmp/openapi.json" "$tmp/openapi.ts"
  fail=0
  cmp -s "$tmp/openapi.json" "$JSON" || { echo "::error file=$JSON::stale; run scripts/gen_sdk_types.sh"; diff -u "$JSON" "$tmp/openapi.json" | head -40 || true; fail=1; }
  cmp -s "$tmp/openapi.ts" "$TS" || { echo "::error file=$TS::stale; run scripts/gen_sdk_types.sh"; diff -u "$TS" "$tmp/openapi.ts" | head -40 || true; fail=1; }
  [ "$fail" = 0 ] && echo "SDK types match the API's OpenAPI document."
  exit "$fail"
fi

generate "$JSON" "$TS"
echo "wrote $JSON and $TS"
