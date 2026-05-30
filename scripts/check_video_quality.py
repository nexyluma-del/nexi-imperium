#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

import cv2


PROJECT_DIR = Path(__file__).resolve().parents[1]


def normalize_input_path(path: Path) -> Path:
    value = str(path)
    match = re.match(r"^([A-Za-z]):\\(.*)$", value)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/")
        return Path(f"/mnt/{drive}/{rest}")
    return path


def run_json(command: list[str], timeout: int = 90) -> dict[str, Any]:
    output = subprocess.check_output(command, text=True, timeout=timeout)
    return json.loads(output)


def ffprobe_metadata(video_path: Path) -> dict[str, Any]:
    return run_json(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
    )


def parse_ratio(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    if "/" not in value:
        try:
            return float(value)
        except ValueError:
            return None
    left, right = value.split("/", 1)
    try:
        denominator = float(right)
        if denominator == 0:
            return None
        return float(left) / denominator
    except ValueError:
        return None


def parse_number(value: Any) -> float | None:
    if value is None or value == "N/A":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def video_stream(metadata: dict[str, Any]) -> dict[str, Any]:
    for stream in metadata.get("streams", []):
        if stream.get("codec_type") == "video":
            return stream
    raise RuntimeError("Kein Videostream gefunden.")


def sample_sharpness(video_path: Path, max_frames: int = 12) -> dict[str, Any]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return {"sampled_frames": 0, "laplacian_variance_avg": None, "laplacian_variance_min": None}

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_count <= 0:
        positions = list(range(max_frames))
    else:
        positions = sorted(set(int(x) for x in [i * (frame_count - 1) / max(1, max_frames - 1) for i in range(max_frames)]))

    scores: list[float] = []
    for pos in positions:
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        height, width = frame.shape[:2]
        longest = max(height, width)
        if longest > 960:
            factor = 960 / longest
            frame = cv2.resize(frame, (max(1, int(width * factor)), max(1, int(height * factor))))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        scores.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
    cap.release()

    if not scores:
        return {"sampled_frames": 0, "laplacian_variance_avg": None, "laplacian_variance_min": None}
    return {
        "sampled_frames": len(scores),
        "laplacian_variance_avg": round(sum(scores) / len(scores), 3),
        "laplacian_variance_min": round(min(scores), 3),
    }


def assess_video_quality(
    video_path: Path,
    *,
    min_short_side: int = 720,
    sharpness_threshold: float = 55.0,
    low_bpppf_threshold: float = 0.045,
    max_frames: int = 12,
) -> dict[str, Any]:
    video_path = normalize_input_path(video_path).resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video nicht gefunden: {video_path}")

    metadata = ffprobe_metadata(video_path)
    stream = video_stream(metadata)
    fmt = metadata.get("format", {})

    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    short_side = min(width, height) if width and height else 0
    long_side = max(width, height) if width and height else 0
    fps = parse_ratio(stream.get("avg_frame_rate")) or parse_ratio(stream.get("r_frame_rate")) or 0.0
    duration = parse_number(stream.get("duration")) or parse_number(fmt.get("duration"))
    bitrate = parse_number(stream.get("bit_rate")) or parse_number(fmt.get("bit_rate"))
    bitrate_mbps = (bitrate / 1_000_000) if bitrate else None
    bpppf = None
    if bitrate and width and height and fps:
        bpppf = bitrate / (width * height * fps)

    sharpness = sample_sharpness(video_path, max_frames=max_frames)
    sharpness_avg = sharpness.get("laplacian_variance_avg")

    reasons: list[str] = []
    if short_side and short_side < min_short_side:
        reasons.append(f"kurze Seite {short_side}px < {min_short_side}px")
    if sharpness_avg is not None and sharpness_avg < sharpness_threshold and short_side <= 900:
        reasons.append(f"Schaerfe niedrig ({sharpness_avg:.1f} < {sharpness_threshold:.1f})")
    if bpppf is not None and bpppf < low_bpppf_threshold and short_side <= 1080:
        reasons.append(f"niedrige Bitrate pro Pixel/Frame ({bpppf:.4f} < {low_bpppf_threshold:.4f})")

    resolution_score = min(1.0, short_side / min_short_side) if short_side else 0.0
    sharpness_score = min(1.0, float(sharpness_avg or 0) / sharpness_threshold) if sharpness_threshold else 0.0
    bitrate_score = min(1.0, float(bpppf or 0) / low_bpppf_threshold) if bpppf is not None else 0.7
    quality_score = round((0.45 * resolution_score) + (0.35 * sharpness_score) + (0.20 * bitrate_score), 3)

    return {
        "video_path": str(video_path),
        "width": width,
        "height": height,
        "short_side": short_side,
        "long_side": long_side,
        "fps": round(fps, 3) if fps else None,
        "duration_seconds": round(duration, 3) if duration is not None and math.isfinite(duration) else None,
        "bitrate_mbps": round(bitrate_mbps, 3) if bitrate_mbps is not None else None,
        "bits_per_pixel_frame": round(bpppf, 5) if bpppf is not None else None,
        "sharpness": sharpness,
        "quality_score": quality_score,
        "needs_upscaling": bool(reasons),
        "reasons": reasons,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check whether a video should be upscaled before analysis.")
    parser.add_argument("video_path", type=Path)
    parser.add_argument("--min-short-side", type=int, default=720)
    parser.add_argument("--sharpness-threshold", type=float, default=55.0)
    parser.add_argument("--low-bpppf-threshold", type=float, default=0.045)
    parser.add_argument("--max-frames", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = assess_video_quality(
        args.video_path,
        min_short_side=args.min_short_side,
        sharpness_threshold=args.sharpness_threshold,
        low_bpppf_threshold=args.low_bpppf_threshold,
        max_frames=args.max_frames,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
