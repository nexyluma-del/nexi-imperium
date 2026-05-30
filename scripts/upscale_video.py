#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from check_video_quality import assess_video_quality, ffprobe_metadata, normalize_input_path, parse_ratio, video_stream


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BINARY = Path("/mnt/c/AI/tools/realesrgan-ncnn-vulkan-windows/realesrgan-ncnn-vulkan.exe")
DEFAULT_MODELS = Path("/mnt/c/AI/tools/realesrgan-ncnn-vulkan-windows/models")


def wsl_to_windows(path: str | Path | None) -> str | None:
    if path is None:
        return None
    value = str(path)
    if value.startswith("/mnt/c/"):
        return "C:\\" + value[len("/mnt/c/") :].replace("/", "\\")
    return value


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")[:100] or "video"


def run_command(command: list[str], log_file: Path, timeout: int | None = None, cwd: Path | None = None) -> str:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as log:
        log.write("\n=== " + " ".join(command) + " ===\n")
    completed = subprocess.run(command, cwd=cwd or PROJECT_DIR, text=True, capture_output=True, timeout=timeout)
    output = (completed.stdout or "") + (completed.stderr or "")
    with log_file.open("a", encoding="utf-8") as log:
        log.write(output)
        log.write(f"\nExit code: {completed.returncode}\n")
    if completed.returncode != 0:
        raise RuntimeError(output[-4000:])
    return output


def nvidia_smi_snapshot() -> str | None:
    try:
        return subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total", "--format=csv,noheader"],
            text=True,
            timeout=15,
        ).strip()
    except Exception:
        return None


def detect_fps(video_path: Path) -> float:
    metadata = ffprobe_metadata(video_path)
    stream = video_stream(metadata)
    fps = parse_ratio(stream.get("avg_frame_rate")) or parse_ratio(stream.get("r_frame_rate"))
    return round(fps or 25.0, 3)


def output_path_for(input_path: Path, scale: int) -> Path:
    return input_path.with_name(f"{input_path.stem}_upscaled_x{scale}.mp4")


def tool_path(path: Path, *, windows_binary: bool) -> str:
    if windows_binary:
        converted = wsl_to_windows(path)
        if converted:
            return converted
    return str(path)


def upscale_video(
    input_path: Path,
    *,
    output_path: Path | None = None,
    scale: int = 2,
    model: str = "realesrgan-x4plus",
    binary: Path = DEFAULT_BINARY,
    models_dir: Path = DEFAULT_MODELS,
    keep_workdir: bool = False,
    max_duration_seconds: float | None = None,
    crf: int = 18,
    preset: str = "medium",
) -> dict[str, Any]:
    input_path = normalize_input_path(input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input-Video nicht gefunden: {input_path}")
    binary = normalize_input_path(binary).resolve()
    models_dir = normalize_input_path(models_dir).resolve()
    windows_binary = binary.suffix.lower() == ".exe"
    if not binary.exists():
        raise FileNotFoundError(f"Real-ESRGAN Binary nicht gefunden: {binary}")
    if not models_dir.exists():
        raise FileNotFoundError(f"Real-ESRGAN Models-Ordner nicht gefunden: {models_dir}")
    if scale not in {2, 3, 4}:
        raise ValueError("scale muss 2, 3 oder 4 sein.")

    quality = assess_video_quality(input_path)
    duration = quality.get("duration_seconds")
    if max_duration_seconds and duration and duration > max_duration_seconds:
        raise RuntimeError(
            f"Video ist {duration:.1f}s lang und damit ueber dem Upscaling-Limit von {max_duration_seconds:.1f}s."
        )

    output_path = normalize_input_path(output_path).resolve() if output_path else output_path_for(input_path, scale)
    if output_path.resolve() == input_path.resolve():
        raise RuntimeError("Original-Videos werden nie ueberschrieben. Bitte anderen Output-Pfad waehlen.")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    work_root = PROJECT_DIR / "work" / "upscale" / f"{slugify(input_path.stem)}-{stamp}"
    frames_in = work_root / "frames_in"
    frames_out = work_root / "frames_out"
    frames_in.mkdir(parents=True, exist_ok=True)
    frames_out.mkdir(parents=True, exist_ok=True)
    log_file = PROJECT_DIR / "logs" / "upscale" / f"{slugify(input_path.stem)}-{stamp}.log"

    fps = detect_fps(input_path)
    before_gpu = nvidia_smi_snapshot()

    try:
        run_command(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-vsync",
                "0",
                str(frames_in / "%08d.png"),
            ],
            log_file,
            timeout=None,
        )
        frame_count = len(list(frames_in.glob("*.png")))
        if frame_count == 0:
            raise RuntimeError("ffmpeg hat keine Frames extrahiert.")

        run_command(
            [
                str(binary),
                "-i",
                tool_path(frames_in, windows_binary=windows_binary),
                "-o",
                tool_path(frames_out, windows_binary=windows_binary),
                "-m",
                tool_path(models_dir, windows_binary=windows_binary),
                "-n",
                model,
                "-s",
                str(scale),
                "-f",
                "png",
                "-v",
            ],
            log_file,
            timeout=None,
            cwd=binary.parent,
        )
        output_frame_count = len(list(frames_out.glob("*.png")))
        if output_frame_count == 0:
            raise RuntimeError("Real-ESRGAN hat keine Output-Frames erzeugt.")

        run_command(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(fps),
                "-start_number",
                "1",
                "-i",
                str(frames_out / "%08d.png"),
                "-i",
                str(input_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a?",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                str(crf),
                "-preset",
                preset,
                "-c:a",
                "copy",
                "-shortest",
                str(output_path),
            ],
            log_file,
            timeout=None,
        )
    finally:
        after_gpu = nvidia_smi_snapshot()
        if not keep_workdir and work_root.exists():
            resolved = work_root.resolve()
            allowed_root = (PROJECT_DIR / "work" / "upscale").resolve()
            if str(resolved).startswith(str(allowed_root)):
                shutil.rmtree(work_root, ignore_errors=True)

    result = {
        "ok": output_path.exists(),
        "input_path": str(input_path),
        "input_path_windows": wsl_to_windows(input_path),
        "output_path": str(output_path),
        "output_path_windows": wsl_to_windows(output_path),
        "scale": scale,
        "model": model,
        "fps": fps,
        "duration_seconds": duration,
        "quality_before": quality,
        "frame_count": frame_count,
        "output_frame_count": output_frame_count,
        "binary": str(binary),
        "models_dir": str(models_dir),
        "log_file": str(log_file),
        "log_file_windows": wsl_to_windows(log_file),
        "workdir": str(work_root) if keep_workdir else None,
        "gpu_before": before_gpu,
        "gpu_after": after_gpu,
    }
    sidecar = output_path.with_suffix(output_path.suffix + ".upscale.json")
    sidecar.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["sidecar_json"] = str(sidecar)
    result["sidecar_json_windows"] = wsl_to_windows(sidecar)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upscale MP4 video with Real-ESRGAN ncnn Vulkan.")
    parser.add_argument("input_path", type=Path)
    parser.add_argument("--output-path", type=Path, default=None)
    parser.add_argument("--scale", type=int, default=2, choices=[2, 3, 4])
    parser.add_argument("--model", default="realesrgan-x4plus")
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--models-dir", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--max-duration-seconds", type=float, default=None)
    parser.add_argument("--crf", type=int, default=18)
    parser.add_argument("--preset", default="medium")
    parser.add_argument("--keep-workdir", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = upscale_video(
        args.input_path,
        output_path=args.output_path,
        scale=args.scale,
        model=args.model,
        binary=args.binary,
        models_dir=args.models_dir,
        keep_workdir=args.keep_workdir,
        max_duration_seconds=args.max_duration_seconds,
        crf=args.crf,
        preset=args.preset,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
