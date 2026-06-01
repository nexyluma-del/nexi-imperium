#!/usr/bin/env bash
set -u

cd /mnt/c/AI/projects/09-video-analyse || exit 1
mkdir -p logs

out="logs/stage2-resume-20260601-retry2.out"
err="logs/stage2-resume-20260601-retry2.err"
marker="logs/stage2-resume-20260601-retry2.marker"

{
  printf '[%s] start pid=%s\n' "$(date -Iseconds)" "$$"
  .venv/bin/python -B scripts/run_stage2_it_200.py
  code=$?
  printf '[%s] exit code=%s\n' "$(date -Iseconds)" "$code"
  exit "$code"
} >> "$out" 2>> "$err"
