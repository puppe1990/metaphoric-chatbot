#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
  local exit_code=$?

  trap - EXIT INT TERM

  if [[ -n "${AGENT_PID:-}" ]] && kill -0 "$AGENT_PID" 2>/dev/null; then
    kill "$AGENT_PID" 2>/dev/null || true
  fi

  if [[ -n "${WEB_PID:-}" ]] && kill -0 "$WEB_PID" 2>/dev/null; then
    kill "$WEB_PID" 2>/dev/null || true
  fi

  wait "${AGENT_PID:-}" "${WEB_PID:-}" 2>/dev/null || true
  exit "$exit_code"
}

trap cleanup EXIT INT TERM

# Kill any process using port 3000 (web dev server)
echo "Matando processos nas portas 3000 e 8000..."
if command -v lsof &>/dev/null; then
  lsof -ti:3000 | xargs kill -9 2>/dev/null || true
  lsof -ti:8000 | xargs kill -9 2>/dev/null || true
elif command -v fuser &>/dev/null; then
  fuser -k 3000/tcp 2>/dev/null || true
  fuser -k 8000/tcp 2>/dev/null || true
fi
# Pequena pausa para garantir que as portas sejam liberadas
sleep 1

(
  cd "$ROOT_DIR/agent_service"
  uv run python -m uvicorn app.main:app --reload
) &
AGENT_PID=$!

(
  cd "$ROOT_DIR/web"
  npm run dev
) &
WEB_PID=$!

wait "$AGENT_PID" "$WEB_PID"
