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
DEFAULT_FRAME_COUNT = 6


def ensure_project_venv() -> None:
    if os.environ.get("VIDEO_PIPELINE_VENV_READY") == "1":
        return
    venv_dir = PROJECT_DIR / ".venv"
    venv_python = venv_dir / "bin" / "python"
    if not venv_python.exists():
        return
    if Path(sys.prefix).resolve() == venv_dir.resolve():
        return
    env = os.environ.copy()
    env["VIDEO_PIPELINE_VENV_READY"] = "1"
    os.execvpe(str(venv_python), [str(venv_python), *sys.argv], env)


ensure_project_venv()

from google.genai import types  # noqa: E402

from gemini_common import (  # noqa: E402
    actual_cost_from_usage,
    estimate_cost_usd,
    load_settings,
    make_client,
    now_stamp,
    slugify,
    usage_to_dict,
    write_json,
)
from check_video_quality import assess_video_quality  # noqa: E402
from qdrant_video_knowledge import upsert_local_video_knowledge  # noqa: E402
from upscale_video import upscale_video as run_upscale_video  # noqa: E402


def normalize_input_path(path: Path) -> Path:
    value = str(path)
    match = re.match(r"^([A-Za-z]):\\(.*)$", value)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/")
        return Path(f"/mnt/{drive}/{rest}")
    return path


def wsl_to_windows(path: str | Path | None) -> str | None:
    if path is None:
        return None
    value = str(path)
    if value.startswith("/mnt/c/"):
        return "C:\\" + value[len("/mnt/c/") :].replace("/", "\\")
    return value


def run_command(command: list[str], log_file: Path, timeout: int) -> str:
    with log_file.open("a", encoding="utf-8") as log:
        log.write("\n=== " + " ".join(command) + " ===\n")
    completed = subprocess.run(command, cwd=PROJECT_DIR, text=True, capture_output=True, timeout=timeout)
    output = (completed.stdout or "") + (completed.stderr or "")
    with log_file.open("a", encoding="utf-8") as log:
        log.write(output)
        log.write(f"\nExit code: {completed.returncode}\n")
    if completed.returncode != 0:
        raise RuntimeError(output[-4000:])
    return output


def parse_prefixed_path(output: str, prefix: str) -> Path | None:
    for line in output.splitlines():
        if line.startswith(prefix):
            return Path(line.split(":", 1)[1].strip())
    return None


def ffprobe_duration_seconds(path: Path) -> float | None:
    try:
        output = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ],
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    try:
        return float(output.strip())
    except ValueError:
        return None


def has_audio_stream(path: Path) -> bool:
    try:
        output = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                str(path),
            ],
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return bool(output.strip())


def extract_audio(video_file: Path, slug: str, log_file: Path) -> Path | None:
    if not has_audio_stream(video_file):
        return None
    audio_dir = PROJECT_DIR / "audio" / "local"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_file = audio_dir / f"{slug}.mp3"
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_file),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "64k",
            str(audio_file),
        ],
        log_file,
        timeout=900,
    )
    return audio_file


def transcribe_audio(audio_file: Path | None, data_class: str, slug: str, log_file: Path) -> Path:
    transcript_dir = PROJECT_DIR / "transcripts" / "local"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    if audio_file is None:
        transcript_file = transcript_dir / f"{slug}.txt"
        transcript_file.write_text(
            "Kein Audiostream erkannt. Analyse basiert auf visuellen Frames und Metadaten.\n",
            encoding="utf-8",
        )
        return transcript_file

    output = run_command(
        [
            str(PROJECT_DIR / ".venv" / "bin" / "python"),
            str(PROJECT_DIR / "scripts" / "transcribe.py"),
            str(audio_file),
            "--data-class",
            data_class,
            "--output-dir",
            str(transcript_dir),
        ],
        log_file,
        timeout=1800,
    )
    transcript_file = parse_prefixed_path(output, "Transcript TXT")
    if transcript_file is None or not transcript_file.exists():
        raise RuntimeError("Whisper-Transkript konnte nicht gefunden werden.")
    return transcript_file


def extract_frames(video_file: Path, category_slug: str, slug: str, max_frames: int, log_file: Path) -> list[Path]:
    frame_dir = PROJECT_DIR / "frames" / "local" / category_slug / slug
    frame_dir.mkdir(parents=True, exist_ok=True)
    for old_frame in frame_dir.glob("frame_*.jpg"):
        old_frame.unlink()
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_file),
            "-vf",
            "fps=1/5,scale=1280:-2:force_original_aspect_ratio=decrease",
            "-frames:v",
            str(max_frames),
            "-q:v",
            "3",
            str(frame_dir / "frame_%02d.jpg"),
        ],
        log_file,
        timeout=900,
    )
    frames = sorted(frame_dir.glob("frame_*.jpg"))
    if frames:
        return frames[:max_frames]

    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_file),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(frame_dir / "frame_01.jpg"),
        ],
        log_file,
        timeout=900,
    )
    return sorted(frame_dir.glob("frame_*.jpg"))[:max_frames]


def estimate_local_cost(model: str, transcript: str, frame_count: int, output_tokens: int = 2200) -> float:
    text_tokens = max(500, len(transcript) // 4)
    frame_tokens = max(1, frame_count) * 1500
    return round(estimate_cost_usd(model, text_tokens + frame_tokens + 2500, output_tokens), 6)


def wait_for_file(client, uploaded_file, poll_seconds: float = 2.0, timeout_seconds: float = 180.0):
    deadline = time.monotonic() + timeout_seconds
    current = uploaded_file
    while True:
        state = getattr(current, "state", None)
        state_name = getattr(state, "name", str(state or "")).upper()
        if state_name in {"ACTIVE", "SUCCEEDED", "STATE_UNSPECIFIED", ""}:
            return current
        if state_name in {"FAILED", "ERROR"}:
            raise RuntimeError(f"Gemini File API processing failed: {state_name}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"Gemini File API timeout. Last state: {state_name}")
        time.sleep(poll_seconds)
        current = client.files.get(name=current.name)


def build_prompt(
    *,
    category: str,
    data_class: str,
    questions: list[str],
    source_info: str,
    transcript_text: str,
    frame_count: int,
    duration_seconds: float | None,
    preprocessor: str | None,
) -> str:
    question_block = "\n".join(f"- {question}" for question in questions)
    preprocessor_note = preprocessor or "none"
    return f"""Du bist Nexis lokaler Video-Analyst fuer seine Wissensdatenbank.
Antworte auf Deutsch, konkret, vorsichtig und praxisnah.

Kategorie: {category}
Datenklasse: {data_class}
Quelle/Notiz: {source_info or "lokale Datei"}
Dauer: {duration_seconds if duration_seconds is not None else "unbekannt"} Sekunden
Frames: {frame_count} ausgewaehlte Standbilder, keine komplette Videodatei
Preprocessor: {preprocessor_note}

Fragen von Nexi:
{question_block}

Wichtige Regeln:
- Nutze nur das Transkript, die sichtbaren Frames und klare Schlussfolgerungen.
- Markiere Unsicherheiten sichtbar.
- Bei IT-Hacks, Security, Tracking, Surveillance, Malware, Exploits oder Account-Zugriff: nur defensive, legale und konzeptionelle Erklaerung. Keine operativen Missbrauchsschritte.
- Bei Finanzen: keine Anlageberatung, sondern Fakten, Hypothesen, Risiken und Pruefschritte.
- Wenn Bild und Transkript widersprechen, benenne den Widerspruch.

Whisper-Transkript:
{transcript_text[:12000]}

Erstelle exakt diese Markdown-Struktur:

## Kurzantwort auf Nexis Frage

## Was im Video passiert

## Wichtige Aussagen aus Sprache/Text/Bild

## Chancen fuer Nexis Projekte

## Risiken, Fehlerquellen und offene Pruefung

## Konkrete naechste Schritte
"""


def render_markdown(
    *,
    video_file: Path,
    category: str,
    data_class: str,
    questions: list[str],
    source_info: str,
    transcript_file: Path,
    frame_paths: list[Path],
    analysis_text: str,
    usage: dict[str, int | None],
    preflight_cost_usd: float,
    actual_cost_usd: float | None,
    model: str,
    duration_seconds: float | None,
    preprocessor: str | None,
    qdrant: dict[str, Any] | None,
    stamp: str,
) -> str:
    question_lines = "\n".join(f"- {question}" for question in questions)
    frame_lines = "\n".join(f"- `{frame}`" for frame in frame_paths) or "- Keine Frames erzeugt."
    qdrant_line = qdrant["point_id"] if qdrant else "nicht indexiert"
    return "\n".join(
        [
            f"# Lokale Video-Analyse: {video_file.name}",
            "",
            f"Datum: {stamp}",
            f"Typ: local-video",
            f"Kategorie: {category}",
            f"Datenklasse: {data_class}",
            f"Modell: {model}",
            f"Quelle/Notiz: {source_info or 'lokale Datei'}",
            f"Datei: `{video_file}`",
            f"Dauer: {duration_seconds if duration_seconds is not None else 'unbekannt'} s",
            f"Preprocessor: {preprocessor or 'none'}",
            "",
            "## Fragen",
            "",
            question_lines,
            "",
            "## Lokale Vorverarbeitung",
            "",
            f"- Transkript: `{transcript_file}`",
            f"- Qdrant ID: `{qdrant_line}`",
            "- An Gemini gesendet: ausgewaehlte Frames + Transkript, nicht die ganze Videodatei.",
            "",
            "## Frames",
            "",
            frame_lines,
            "",
            "## Gemini-Analyse",
            "",
            analysis_text,
            "",
            "## Cost-Tracking",
            "",
            f"- Prompt tokens: {usage.get('prompt_token_count')}",
            f"- Output tokens: {usage.get('candidates_token_count')}",
            f"- Total tokens: {usage.get('total_token_count')}",
            f"- Preflight-Schaetzung: ${preflight_cost_usd:.6f}",
            f"- Ist-Schaetzung: ${actual_cost_usd:.6f}" if actual_cost_usd is not None else "- Ist-Schaetzung: n/a",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze one local video without uploading the full file.")
    parser.add_argument("--video-path", type=Path, required=True)
    parser.add_argument("--data-class", default="D2", choices=sorted(VALID_DATA_CLASSES))
    parser.add_argument("--category", required=True)
    parser.add_argument("--question", action="append", default=[])
    parser.add_argument("--source-info", default="")
    parser.add_argument("--slug", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-cost-eur", type=float, default=None)
    parser.add_argument("--max-frames", type=int, default=DEFAULT_FRAME_COUNT)
    parser.add_argument("--preprocessor", default=None)
    parser.add_argument("--upscale", choices=["auto", "always", "never"], default="auto")
    parser.add_argument("--upscale-scale", type=int, choices=[2, 3, 4], default=2)
    parser.add_argument("--upscale-model", default="realesrgan-x4plus")
    parser.add_argument("--upscale-max-duration-seconds", type=float, default=180.0)
    parser.add_argument("--keep-upscale-workdir", action="store_true")
    parser.add_argument("--pipeline", default="default_local_video")
    parser.add_argument("--allow-sensitive", action="store_true")
    parser.add_argument("--keep-uploaded-files", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.data_class in {"D3", "D4"} and not args.allow_sensitive:
        raise RuntimeError("D3/D4 sind fuer Aufgabe 016 ohne --allow-sensitive gesperrt.")

    settings = load_settings()
    model = args.model or settings["model"]
    max_cost_eur = args.max_cost_eur or float(settings["cost_cap_eur"])
    video_file = normalize_input_path(args.video_path).resolve()
    if not video_file.exists():
        raise FileNotFoundError(f"Video nicht gefunden: {video_file}")

    stamp = now_stamp()
    category_slug = slugify(args.category)
    slug = slugify(args.slug or f"{category_slug}-{video_file.stem}-{stamp}")
    questions = args.question or ["Was wird in diesem Video gezeigt und gesagt?"]
    log_dir = PROJECT_DIR / "logs" / "local-video"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{slug}-{stamp}.log"
    analysis_dir = PROJECT_DIR / "analysis" / "local" / category_slug
    analysis_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "ok": False,
        "pipeline_type": "local-video",
        "video_path": str(video_file),
        "video_path_windows": wsl_to_windows(video_file),
        "data_class": args.data_class,
        "category": args.category,
        "questions": questions,
        "slug": slug,
        "started_at": stamp,
        "log_file": str(log_file),
        "files": {},
        "cost": {},
        "upscale": {
            "mode": args.upscale,
            "scale": args.upscale_scale,
            "model": args.upscale_model,
        },
    }

    try:
        analysis_video_file = video_file
        preprocessor_parts = [args.preprocessor] if args.preprocessor else []
        quality_report: dict[str, Any] | None = None
        upscale_report: dict[str, Any] | None = None

        if args.upscale != "never":
            quality_report = assess_video_quality(video_file)
            summary["quality"] = quality_report
            should_upscale = args.upscale == "always" or bool(quality_report.get("needs_upscaling"))
            duration_for_guard = quality_report.get("duration_seconds")
            duration_limit = None if args.upscale_max_duration_seconds <= 0 else args.upscale_max_duration_seconds
            if should_upscale and duration_limit and duration_for_guard and duration_for_guard > duration_limit:
                message = (
                    f"Upscaling uebersprungen: {duration_for_guard:.1f}s > "
                    f"{duration_limit:.1f}s Sicherheitslimit."
                )
                if args.upscale == "always":
                    raise RuntimeError(message + " Fuer Pflicht-Upscaling Limit mit --upscale-max-duration-seconds 0 deaktivieren.")
                preprocessor_parts.append(f"quality-check:needs-upscale-but-skipped ({message})")
            elif should_upscale:
                upscale_output_dir = PROJECT_DIR / "upscaled" / "local" / category_slug
                upscale_output_dir.mkdir(parents=True, exist_ok=True)
                upscale_output_path = upscale_output_dir / f"{slug}_upscaled_x{args.upscale_scale}.mp4"
                upscale_report = run_upscale_video(
                    video_file,
                    output_path=upscale_output_path,
                    scale=args.upscale_scale,
                    model=args.upscale_model,
                    keep_workdir=args.keep_upscale_workdir,
                    max_duration_seconds=duration_limit,
                )
                analysis_video_file = Path(str(upscale_report["output_path"]))
                preprocessor_parts.append(
                    f"real-esrgan:{args.upscale_model}:x{args.upscale_scale}:{analysis_video_file.name}"
                )
            else:
                preprocessor_parts.append("quality-check:no-upscale-needed")
        else:
            preprocessor_parts.append("upscale:disabled")

        preprocessor_note = "; ".join(preprocessor_parts)
        summary["upscale"].update(
            {
                "analysis_video_path": str(analysis_video_file),
                "analysis_video_path_windows": wsl_to_windows(analysis_video_file),
                "quality": quality_report,
                "result": upscale_report,
            }
        )

        duration_seconds = ffprobe_duration_seconds(analysis_video_file)
        audio_file = extract_audio(analysis_video_file, slug, log_file)
        transcript_file = transcribe_audio(audio_file, args.data_class, slug, log_file)
        transcript_text = transcript_file.read_text(encoding="utf-8")
        frame_paths = extract_frames(analysis_video_file, category_slug, slug, args.max_frames, log_file)
        if not frame_paths:
            raise RuntimeError("Es konnten keine Frames aus dem lokalen Video erzeugt werden.")

        estimated_cost = estimate_local_cost(model, transcript_text, len(frame_paths))
        summary["cost"]["preflight_estimated_usd"] = estimated_cost
        if estimated_cost > max_cost_eur:
            raise RuntimeError(f"Kosten-Schaetzung {estimated_cost:.4f} USD > Limit {max_cost_eur:.2f} EUR")

        if args.dry_run:
            summary["ok"] = True
            summary["dry_run"] = True
            summary["files"].update(
                {
                    "audio": str(audio_file) if audio_file else None,
                    "transcript_txt": str(transcript_file),
                    "frames": [str(path) for path in frame_paths],
                }
            )
            print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
            return 0

        prompt = build_prompt(
            category=args.category,
            data_class=args.data_class,
            questions=questions,
            source_info=args.source_info,
            transcript_text=transcript_text,
            frame_count=len(frame_paths),
            duration_seconds=round(duration_seconds, 3) if duration_seconds else None,
            preprocessor=preprocessor_note,
        )

        client = make_client(settings["api_key"])
        uploaded = []
        try:
            for frame in frame_paths:
                uploaded.append(wait_for_file(client, client.files.upload(file=str(frame))))
            response = client.models.generate_content(
                model=model,
                contents=[*uploaded, prompt],
                config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=2200),
            )
        finally:
            if not args.keep_uploaded_files:
                for current in uploaded:
                    try:
                        client.files.delete(name=current.name)
                    except Exception:
                        pass

        analysis_text = (response.text or "").strip()
        usage = usage_to_dict(getattr(response, "usage_metadata", None))
        actual_cost = actual_cost_from_usage(model, usage)
        output_md = analysis_dir / f"{slug}.local-video-{stamp}.md"
        output_json = analysis_dir / f"{slug}.local-video-{stamp}.json"

        output_md.write_text(
            render_markdown(
                video_file=video_file,
                category=args.category,
                data_class=args.data_class,
                questions=questions,
                source_info=args.source_info,
                transcript_file=transcript_file,
                frame_paths=frame_paths,
                analysis_text=analysis_text,
                usage=usage,
                preflight_cost_usd=estimated_cost,
                actual_cost_usd=actual_cost,
                model=model,
                duration_seconds=round(duration_seconds, 3) if duration_seconds else None,
                preprocessor=preprocessor_note,
                qdrant=None,
                stamp=stamp,
            ),
            encoding="utf-8",
        )
        qdrant = upsert_local_video_knowledge(
            source_path=video_file,
            category=args.category,
            data_class=args.data_class,
            questions=questions,
            analysis_markdown=output_md,
            transcript_txt=transcript_file,
            frame_paths=frame_paths,
            cost_usd=actual_cost,
            slug=slug,
            source_info=args.source_info,
            preprocessor=preprocessor_note,
            pipeline=args.pipeline,
        )
        output_md.write_text(
            render_markdown(
                video_file=video_file,
                category=args.category,
                data_class=args.data_class,
                questions=questions,
                source_info=args.source_info,
                transcript_file=transcript_file,
                frame_paths=frame_paths,
                analysis_text=analysis_text,
                usage=usage,
                preflight_cost_usd=estimated_cost,
                actual_cost_usd=actual_cost,
                model=model,
                duration_seconds=round(duration_seconds, 3) if duration_seconds else None,
                preprocessor=preprocessor_note,
                qdrant=qdrant,
                stamp=stamp,
            ),
            encoding="utf-8",
        )

        write_json(
            output_json,
            {
                "pipeline_type": "local-video",
                "video_path": str(video_file),
                "video_path_windows": wsl_to_windows(video_file),
                "analysis_video_path": str(analysis_video_file),
                "analysis_video_path_windows": wsl_to_windows(analysis_video_file),
                "category": args.category,
                "data_class": args.data_class,
                "questions": questions,
                "source_info": args.source_info,
                "model": model,
                "duration_seconds": duration_seconds,
                "audio_file": str(audio_file) if audio_file else None,
                "transcript_txt": str(transcript_file),
                "frames": [str(path) for path in frame_paths],
                "preprocessor": preprocessor_note,
                "quality": quality_report,
                "upscale": upscale_report,
                "pipeline": args.pipeline,
                "usage": usage,
                "cost_usd": actual_cost,
                "preflight_estimated_cost_usd": estimated_cost,
                "analysis_markdown": str(output_md),
                "qdrant": qdrant,
            },
        )

        summary["ok"] = True
        summary["files"].update(
            {
                "audio": str(audio_file) if audio_file else None,
                "transcript_txt": str(transcript_file),
                "analysis_video": str(analysis_video_file),
                "analysis_video_windows": wsl_to_windows(analysis_video_file),
                "analysis_markdown": str(output_md),
                "analysis_markdown_windows": wsl_to_windows(output_md),
                "json": str(output_json),
                "json_windows": wsl_to_windows(output_json),
                "frames": [str(path) for path in frame_paths],
            }
        )
        summary["cost"].update(
            {
                "estimated_actual_usd": actual_cost,
                "preflight_estimated_usd": estimated_cost,
            }
        )
        summary["qdrant"] = qdrant
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:  # noqa: BLE001
        summary["error"] = str(exc)
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
