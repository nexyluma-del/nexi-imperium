#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
AUDIO_DIR="$PROJECT_DIR/audio"
LOG_DIR="$PROJECT_DIR/logs"

usage() {
  cat <<'EOF'
Usage:
  download.sh <url> [data_class] [slug]

Examples:
  download.sh "https://www.youtube.com/watch?v=BaW_jenozKc" D0 test-video

Notes:
  - Downloads audio only as MP3.
  - data_class must be one of D0, D1, D2, D3, D4.
  - No cloud upload is performed.
EOF
}

URL="${1:-}"
DATA_CLASS="${2:-D0}"
SLUG="${3:-}"

if [[ -z "$URL" ]]; then
  usage
  exit 2
fi

case "$DATA_CLASS" in
  D0|D1|D2|D3|D4) ;;
  *)
    echo "Invalid data_class: $DATA_CLASS" >&2
    exit 2
    ;;
esac

if [[ ! -x "$VENV_DIR/bin/yt-dlp" ]]; then
  echo "yt-dlp not found in $VENV_DIR" >&2
  exit 1
fi

mkdir -p "$AUDIO_DIR" "$LOG_DIR"

if [[ -n "$SLUG" ]]; then
  OUTPUT_TEMPLATE="${SLUG}.%(ext)s"
else
  OUTPUT_TEMPLATE="%(title).80B-%(id)s.%(ext)s"
fi

TIMESTAMP="$(date -Iseconds)"
LOG_FILE="$LOG_DIR/download-$(date +%Y%m%d-%H%M%S).log"

echo "Download started: $TIMESTAMP" | tee "$LOG_FILE"
echo "URL: $URL" | tee -a "$LOG_FILE"
echo "Data class: $DATA_CLASS" | tee -a "$LOG_FILE"

set +e
YTDLP_OUTPUT="$("$VENV_DIR/bin/yt-dlp" \
  --no-progress \
  --extract-audio \
  --audio-format mp3 \
  --audio-quality 0 \
  --paths "$AUDIO_DIR" \
  --output "$OUTPUT_TEMPLATE" \
  --write-info-json \
  --print after_move:filepath \
  "$URL" 2>&1)"
STATUS=$?
set -e

printf '%s\n' "$YTDLP_OUTPUT" | tee -a "$LOG_FILE"

if [[ "$STATUS" -ne 0 ]]; then
  echo "yt-dlp failed with status $STATUS" | tee -a "$LOG_FILE" >&2
  exit "$STATUS"
fi

AUDIO_FILE="$(printf '%s\n' "$YTDLP_OUTPUT" | awk '/\.mp3$/ {print $0}' | tail -1)"
if [[ -z "$AUDIO_FILE" || ! -f "$AUDIO_FILE" ]]; then
  if [[ -n "$SLUG" ]]; then
    AUDIO_FILE="$(find "$AUDIO_DIR" -maxdepth 1 -type f -name "${SLUG}*.mp3" -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)"
  else
    AUDIO_FILE=""
  fi
fi

if [[ -z "$AUDIO_FILE" || ! -f "$AUDIO_FILE" ]]; then
  echo "Could not determine downloaded audio file." | tee -a "$LOG_FILE" >&2
  exit 1
fi

META_FILE="${AUDIO_FILE%.mp3}.pipeline-meta.json"
"$VENV_DIR/bin/python" - "$META_FILE" "$URL" "$DATA_CLASS" "$AUDIO_FILE" "$TIMESTAMP" <<'PY'
import json
import sys
from pathlib import Path

meta_file, url, data_class, audio_file, timestamp = sys.argv[1:6]
payload = {
    "source_url": url,
    "data_class": data_class,
    "audio_file": audio_file,
    "downloaded_at": timestamp,
    "tool": "yt-dlp",
}
Path(meta_file).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY

echo "Audio file: $AUDIO_FILE" | tee -a "$LOG_FILE"
echo "Metadata: $META_FILE" | tee -a "$LOG_FILE"
echo "Download finished: $(date -Iseconds)" | tee -a "$LOG_FILE"
