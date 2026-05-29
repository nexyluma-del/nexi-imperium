#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_CACHE = PROJECT_DIR / "models" / "faster-whisper"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "transcripts"
VALID_DATA_CLASSES = {"D0", "D1", "D2", "D3", "D4"}


def ensure_project_venv() -> None:
    if os.environ.get("VIDEO_PIPELINE_VENV_READY") == "1":
        return

    venv_dir = PROJECT_DIR / ".venv"
    venv_python = venv_dir / "bin" / "python"
    if not venv_python.exists():
        return

    try:
        current_prefix = Path(sys.prefix).resolve()
        target_prefix = venv_dir.resolve()
    except OSError:
        current_prefix = Path(sys.prefix)
        target_prefix = venv_dir

    if current_prefix == target_prefix:
        return

    env = os.environ.copy()
    env["VIDEO_PIPELINE_VENV_READY"] = "1"
    os.execvpe(str(venv_python), [str(venv_python), *sys.argv], env)


def ensure_cuda_library_path() -> None:
    if os.environ.get("VIDEO_PIPELINE_LD_READY") == "1":
        return

    site_packages = PROJECT_DIR / ".venv" / "lib" / "python3.12" / "site-packages" / "nvidia"
    lib_paths = [
        site_packages / "cublas" / "lib",
        site_packages / "cudnn" / "lib",
    ]
    existing_paths = [str(path) for path in lib_paths if path.exists()]
    if not existing_paths:
        return

    env = os.environ.copy()
    current = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = ":".join(existing_paths + ([current] if current else []))
    env["VIDEO_PIPELINE_LD_READY"] = "1"
    os.execvpe(sys.executable, [sys.executable, *sys.argv], env)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe an audio file with faster-whisper.")
    parser.add_argument("audio_file", type=Path)
    parser.add_argument("--data-class", default="D0", choices=sorted(VALID_DATA_CLASSES))
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--language", default=None, help="Optional language hint, e.g. de or en.")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model-cache", type=Path, default=DEFAULT_MODEL_CACHE)
    return parser.parse_args()


def safe_stem(path: Path) -> str:
    return "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in path.stem)[:120]


def main() -> int:
    ensure_project_venv()
    args = parse_args()
    ensure_cuda_library_path()

    from faster_whisper import WhisperModel

    audio_file = args.audio_file.resolve()
    if not audio_file.exists():
        print(f"Audio file not found: {audio_file}", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.model_cache.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    model = WhisperModel(
        args.model,
        device=args.device,
        compute_type=args.compute_type,
        download_root=str(args.model_cache),
    )

    segments_iter, info = model.transcribe(
        str(audio_file),
        beam_size=args.beam_size,
        language=args.language,
    )

    segments = []
    for segment in segments_iter:
        segments.append(
            {
                "id": segment.id,
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": segment.text.strip(),
            }
        )

    elapsed = time.perf_counter() - started
    duration = float(getattr(info, "duration", 0.0) or 0.0)
    speed_factor = (duration / elapsed) if elapsed > 0 and duration > 0 else None

    base = safe_stem(audio_file)
    txt_file = args.output_dir / f"{base}.txt"
    json_file = args.output_dir / f"{base}.json"

    payload = {
        "audio_file": str(audio_file),
        "data_class": args.data_class,
        "model": args.model,
        "device": args.device,
        "compute_type": args.compute_type,
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "duration_seconds": duration,
        "elapsed_seconds": round(elapsed, 3),
        "speed_factor": round(speed_factor, 3) if speed_factor else None,
        "segment_count": len(segments),
        "segments": segments,
    }

    lines = [
        f"audio_file: {audio_file}",
        f"data_class: {args.data_class}",
        f"model: {args.model}",
        f"device: {args.device}",
        f"language: {payload['language']} ({payload['language_probability']})",
        f"duration_seconds: {duration:.3f}",
        f"elapsed_seconds: {elapsed:.3f}",
        f"speed_factor: {speed_factor:.3f}x" if speed_factor else "speed_factor: n/a",
        "",
    ]
    for segment in segments:
        lines.append(f"[{segment['start']:.2f}s - {segment['end']:.2f}s] {segment['text']}")

    txt_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Transcript TXT: {txt_file}")
    print(f"Transcript JSON: {json_file}")
    print(f"Detected language: {payload['language']} ({payload['language_probability']})")
    print(f"Elapsed: {elapsed:.3f}s")
    if speed_factor:
        print(f"Speed: {speed_factor:.3f}x realtime")
    print(f"Segments: {len(segments)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
