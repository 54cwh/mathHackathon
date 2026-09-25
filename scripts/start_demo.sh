#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/frontend/dist"
PORT="${EVOGENESIS_PORT:-8000}"

if [ ! -d "$DIST" ]; then
  echo ">> 构建前端 ..."
  ( cd "$ROOT/frontend" && npm install && npm run build )
fi

echo ">> 启动 EvoGenesis: http://127.0.0.1:$PORT"
( cd "$ROOT" && uv run python scripts/serve_api.py --port "$PORT" ) &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:$PORT/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:$PORT" >/dev/null 2>&1 || true
fi

wait "$SERVER_PID"
