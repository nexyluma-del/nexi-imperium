#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
from pathlib import Path
from typing import Any

from analyze_local_video import normalize_input_path, wsl_to_windows


DEFAULT_ROOT = Path("/mnt/c/Users/nexil/Desktop/Instagram Videos/Sofinello")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}


def ffprobe_video(path: Path) -> dict[str, Any] | None:
    try:
        output = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,duration,avg_frame_rate",
                "-of",
                "json",
                str(path),
            ],
            text=True,
            timeout=15,
        )
        stream = json.loads(output)["streams"][0]
        fps_raw = stream.get("avg_frame_rate") or "30/1"
        if "/" in fps_raw:
            left, right = fps_raw.split("/", 1)
            fps = float(left) / float(right) if float(right) else 30.0
        else:
            fps = float(fps_raw or 30.0)
        duration = float(stream.get("duration") or 0.0)
        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
        return {
            "path": str(path),
            "width": width,
            "height": height,
            "fps": fps,
            "duration_seconds": duration,
            "size_mb": path.stat().st_size / 1024 / 1024,
            "pixel_frames_million": width * height * fps * duration / 1_000_000,
        }
    except Exception:
        return None


def scan(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in root.rglob("*"):
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        info = ffprobe_video(path)
        if info:
            rows.append(info)
    return rows


def summarize(rows: list[dict[str, Any]], *, count_override: int | None = None) -> dict[str, Any]:
    count = len(rows)
    durations = [row["duration_seconds"] for row in rows]
    total_duration = sum(durations)
    total_size = sum(row["size_mb"] for row in rows)
    total_pf = sum(row["pixel_frames_million"] for row in rows)
    effective_count = count_override or count
    return {
        "count": count,
        "count_for_batch": effective_count,
        "total_duration_hours": round(total_duration / 3600, 2),
        "total_size_gb": round(total_size / 1024, 2),
        "median_duration_seconds": round(statistics.median(durations), 2) if durations else 0,
        "average_duration_seconds": round(total_duration / count, 2) if count else 0,
        "p90_duration_seconds": round(sorted(durations)[int(count * 0.9)], 2) if count else 0,
        "total_pixel_frames_million": round(total_pf, 1),
        "short_side_lt_720": sum(1 for row in rows if min(row["width"], row["height"]) < 720),
        "short_side_ge_1080": sum(1 for row in rows if min(row["width"], row["height"]) >= 1080),
        "cloud_cost_usd": {
            "low_0_015_each": round(effective_count * 0.015, 2),
            "normal_0_025_each": round(effective_count * 0.025, 2),
            "high_0_040_each": round(effective_count * 0.040, 2),
            "max_0_060_each": round(effective_count * 0.060, 2),
        },
        "full_video_upscale_hours": {
            "fast_0_5s_per_mpf": round(total_pf * 0.5 / 3600, 1),
            "normal_1_0s_per_mpf": round(total_pf * 1.0 / 3600, 1),
            "slow_2_0s_per_mpf": round(total_pf * 2.0 / 3600, 1),
        },
        "frame_only_upscale_hours": {
            "6_frames_each_2s_per_frame": round(effective_count * 6 * 2 / 3600, 2),
            "8_frames_each_3s_per_frame": round(effective_count * 8 * 3 / 3600, 2),
            "10_frames_each_5s_per_frame": round(effective_count * 10 * 5 / 3600, 2),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate Sofinello full-batch cost and upscaling time.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--count-override", type=int, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = normalize_input_path(args.root).resolve()
    rows = scan(root)
    summary = summarize(rows, count_override=args.count_override)
    summary["root"] = str(root)
    summary["root_windows"] = wsl_to_windows(root)
    if args.output_json:
        output = normalize_input_path(args.output_json)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
