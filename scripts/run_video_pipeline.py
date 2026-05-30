#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
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


ensure_project_venv()


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return cleaned[:90] or "video"


def wsl_to_windows(path: str | Path | None) -> str | None:
    if path is None:
        return None
    value = str(path)
    if value.startswith("/mnt/c/"):
        return "C:\\" + value[len("/mnt/c/") :].replace("/", "\\")
    return value


def parse_prefixed_path(output: str, prefix: str) -> str | None:
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def run_step(
    name: str,
    command: list[str],
    log_file: Path,
    timeout_seconds: int,
    attempts: int = 1,
    retry_on: tuple[str, ...] = (),
) -> tuple[str, float]:
    started = time.perf_counter()
    last_output = ""
    for attempt in range(1, attempts + 1):
        with log_file.open("a", encoding="utf-8") as log:
            log.write(f"\n=== {name} attempt {attempt}/{attempts} ===\n")
            log.write("Command: " + " ".join(command) + "\n")
        completed = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        last_output = output
        with log_file.open("a", encoding="utf-8") as log:
            log.write(output)
            log.write(f"\nExit code: {completed.returncode}\n")

        if completed.returncode == 0:
            return output, round(time.perf_counter() - started, 3)

        should_retry = any(marker in output for marker in retry_on)
        if attempt < attempts and should_retry:
            time.sleep(30)
            continue
        raise RuntimeError(f"Step failed: {name}\n{output[-4000:]}")

    raise RuntimeError(f"Step failed: {name}\n{last_output[-4000:]}")


def find_downloaded_video(slug: str) -> Path:
    candidates = [
        path
        for path in (PROJECT_DIR / "downloads").glob(f"{slug}.*")
        if path.is_file() and not path.name.endswith(".info.json")
    ]
    if not candidates:
        raise FileNotFoundError(f"Kein Video-Download gefunden fuer Slug {slug}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the full single-video pipeline.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--data-class", default="D0", choices=sorted(VALID_DATA_CLASSES))
    parser.add_argument("--slug", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--topic", default=None)
    parser.add_argument("--question", action="append", default=[])
    parser.add_argument("--max-cost-eur", default="0.30")
    parser.add_argument("--allow-sensitive", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.data_class in {"D3", "D4"} and not args.allow_sensitive:
        raise RuntimeError("D3/D4 sind fuer Aufgabe 012 ohne --allow-sensitive gesperrt.")

    stamp = now_stamp()
    slug = slugify(args.slug or f"manual-{stamp}")
    log_dir = PROJECT_DIR / "logs" / "pipeline"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{slug}-{stamp}.log"
    (PROJECT_DIR / "downloads").mkdir(exist_ok=True)
    (PROJECT_DIR / "workflows").mkdir(exist_ok=True)

    summary: dict[str, Any] = {
        "ok": False,
        "url": args.url,
        "data_class": args.data_class,
        "slug": slug,
        "topic": args.topic,
        "questions": args.question,
        "started_at": stamp,
        "log_file": str(log_file),
        "steps": {},
        "files": {},
        "cost": {},
    }

    try:
        ytdlp = str(PROJECT_DIR / ".venv" / "bin" / "yt-dlp")
        venv_python = str(PROJECT_DIR / ".venv" / "bin" / "python")

        video_output, elapsed = run_step(
            "download_video",
            [
                ytdlp,
                "--no-progress",
                "--format",
                "bv*+ba/best",
                "--merge-output-format",
                "mp4",
                "--paths",
                str(PROJECT_DIR / "downloads"),
                "--output",
                f"{slug}.%(ext)s",
                "--write-info-json",
                "--print",
                "after_move:filepath",
                args.url,
            ],
            log_file,
            timeout_seconds=900,
        )
        video_file = Path(
            next((line.strip() for line in video_output.splitlines() if line.strip().startswith(str(PROJECT_DIR / "downloads"))), "")
        )
        if not video_file.is_file():
            video_file = find_downloaded_video(slug)
        summary["steps"]["download_video_seconds"] = elapsed
        summary["files"]["video"] = str(video_file)

        try:
            audio_output, elapsed = run_step(
                "download_audio",
                [str(PROJECT_DIR / "scripts" / "download.sh"), args.url, args.data_class, slug],
                log_file,
                timeout_seconds=900,
            )
            audio_file = parse_prefixed_path(audio_output, "Audio file")
            if not audio_file:
                raise RuntimeError("Audio-Datei konnte aus download.sh Output nicht gelesen werden.")
            summary["steps"]["download_audio_seconds"] = elapsed
            summary["files"]["audio"] = audio_file

            transcribe_output, elapsed = run_step(
                "whisper_transcribe",
                [
                    venv_python,
                    str(PROJECT_DIR / "scripts" / "transcribe.py"),
                    audio_file,
                    "--data-class",
                    args.data_class,
                ],
                log_file,
                timeout_seconds=1800,
            )
            transcript_txt = parse_prefixed_path(transcribe_output, "Transcript TXT")
            transcript_json = parse_prefixed_path(transcribe_output, "Transcript JSON")
            if not transcript_txt:
                raise RuntimeError("Transkript-Pfad konnte aus transcribe.py Output nicht gelesen werden.")
            summary["steps"]["whisper_seconds"] = elapsed
            summary["files"]["transcript_txt"] = transcript_txt
            summary["files"]["transcript_json"] = transcript_json
        except Exception as audio_exc:  # noqa: BLE001
            if "audio codec" not in str(audio_exc) and "download_audio" not in str(audio_exc):
                raise
            transcript_path = PROJECT_DIR / "transcripts" / f"{slug}.txt"
            transcript_path.parent.mkdir(exist_ok=True)
            transcript_path.write_text(
                "\n".join(
                    [
                        f"audio_file: none",
                        f"data_class: {args.data_class}",
                        "Hinweis: Keine extrahierbare Audiospur gefunden. Analyse nutzt nur die visuellen Videoinhalte.",
                    ]
                ),
                encoding="utf-8",
            )
            transcript_txt = str(transcript_path)
            transcript_json = None
            summary["steps"]["audio_fallback"] = "no_extractable_audio"
            summary["files"]["transcript_txt"] = transcript_txt
            summary["files"]["transcript_json"] = transcript_json

        gemini_command = [
            venv_python,
            str(PROJECT_DIR / "scripts" / "analyze_full.py"),
            str(video_file),
            "--transcript",
            transcript_txt,
            "--data-class",
            args.data_class,
            "--source-url",
            args.url,
            "--max-cost-eur",
            args.max_cost_eur,
        ]
        if args.model:
            gemini_command.extend(["--model", args.model])
        if args.topic:
            gemini_command.extend(["--topic", args.topic])
        for question in args.question:
            gemini_command.extend(["--question", question])

        gemini_output, elapsed = run_step(
            "gemini_analyze_full",
            gemini_command,
            log_file,
            timeout_seconds=1200,
            attempts=2,
            retry_on=("503 UNAVAILABLE", "high demand"),
        )
        output_md = parse_prefixed_path(gemini_output, "Output Markdown")
        output_json = parse_prefixed_path(gemini_output, "Output JSON")
        if not output_json:
            raise RuntimeError("Gemini-JSON-Pfad konnte aus analyze_full.py Output nicht gelesen werden.")

        gemini_meta = json.loads(Path(output_json).read_text(encoding="utf-8"))
        summary["steps"]["gemini_seconds"] = elapsed
        summary["files"]["analysis_markdown"] = output_md
        summary["files"]["analysis_json"] = output_json
        summary["cost"] = {
            "estimated_actual_usd": gemini_meta.get("estimated_actual_cost_usd"),
            "preflight_usd": gemini_meta.get("preflight", {}).get("estimated_cost_usd"),
            "usage": gemini_meta.get("usage"),
        }
        summary["finished_at"] = now_stamp()
        summary["ok"] = True
    except Exception as exc:  # noqa: BLE001
        summary["finished_at"] = now_stamp()
        summary["error"] = str(exc)
        with log_file.open("a", encoding="utf-8") as log:
            log.write("\n=== PIPELINE ERROR ===\n")
            log.write(str(exc) + "\n")
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 1

    for key, value in list(summary["files"].items()):
        summary["files"][f"{key}_windows"] = wsl_to_windows(value)
    summary["log_file_windows"] = wsl_to_windows(log_file)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
