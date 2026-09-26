#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/frontend/dist"
PORT="${EVOGENESIS_PORT:-8000}"
URL="http://127.0.0.1:$PORT"

command -v uv >/dev/null 2>&1 || { echo "!! 未找到 uv" >&2; exit 1; }

if [ ! -d "$DIST" ]; then
  command -v npm >/dev/null 2>&1 || { echo "!! 未找到 npm，无法构建前端" >&2; exit 1; }
  echo ">> 构建前端 ..."
  if [ -f "$ROOT/frontend/package-lock.json" ]; then
    ( cd "$ROOT/frontend" && npm ci && npm run build )
  else
    ( cd "$ROOT/frontend" && npm install && npm run build )
  fi
fi

echo ">> 启动 EvoGenesis: $URL"
( cd "$ROOT" && uv run python scripts/serve_api.py --port "$PORT" ) &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

if command -v curl >/dev/null 2>&1; then
  for _ in $(seq 1 30); do
    curl -sf "$URL/v1/health" >/dev/null 2>&1 && break
    sleep 0.5
  done
fi

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v open >/dev/null 2>&1; then
  open "$URL" >/dev/null 2>&1 || true
fi

wait "$SERVER_PID"
