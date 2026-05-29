#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/mnt/c/AI/projects/09-video-analyse"
PORT="${1:-8787}"

cd "$PROJECT_DIR"
mkdir -p logs

if pgrep -af "scripts/pipeline_bridge.py --host 0.0.0.0 --port ${PORT}" >/dev/null 2>&1; then
  echo "Pipeline bridge already running on port ${PORT}."
  exit 0
fi

setsid .venv/bin/python scripts/pipeline_bridge.py --host 0.0.0.0 --port "$PORT" \
  > logs/pipeline-bridge.log 2>&1 < /dev/null &

sleep 1
if pgrep -af "scripts/pipeline_bridge.py --host 0.0.0.0 --port ${PORT}" >/dev/null 2>&1; then
  echo "Pipeline bridge started on port ${PORT}."
else
  echo "Pipeline bridge failed to start. Check logs/pipeline-bridge.log" >&2
  exit 1
fi

