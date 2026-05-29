#!/usr/bin/env bash
set -euo pipefail

cd /mnt/c/AI/projects/09-video-analyse

stamp="$(date +%Y%m%d-%H%M%S)"
gpu_log="logs/gpu-sample-${stamp}.log"
transcribe_log="logs/transcribe-${stamp}.log"
audio_file="${1:-audio/nasa-llcd-laser-communication.mp3}"

scripts/transcribe.py "$audio_file" \
  --data-class D0 \
  --device cuda \
  --compute-type float16 \
  --model large-v3 > "$transcribe_log" 2>&1 &

pid="$!"

while kill -0 "$pid" 2>/dev/null; do
  date -Iseconds >> "$gpu_log"
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader >> "$gpu_log" 2>&1 || true
  sleep 1
done

wait "$pid"
status="$?"

echo "TRANSCRIBE_LOG=$transcribe_log"
echo "GPU_LOG=$gpu_log"
cat "$transcribe_log"
exit "$status"
