#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
HEALING_KNOWLEDGE_DIR = Path("/mnt/c/AI/projects/06-heilung/knowledge")
VALID_DATA_CLASSES = {"D2"}
DEFAULT_FRAME_COUNT = 8


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

from analyze_local_video import (  # noqa: E402
    extract_audio,
    ffprobe_duration_seconds,
    normalize_input_path,
    run_command,
    transcribe_audio,
    wait_for_file,
    wsl_to_windows,
)
from gemini_common import (  # noqa: E402
    actual_cost_from_usage,
    cleanup_gemini_files,
    estimate_cost_usd,
    load_settings,
    make_client,
    now_stamp,
    slugify,
    usage_to_dict,
    write_json,
)
from qdrant_video_knowledge import upsert_sofinello_knowledge  # noqa: E402
from sofinello_compliance import apply_compliance  # noqa: E402
from upscale_video import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_MODELS,
    nvidia_smi_snapshot,
    run_command as run_upscale_command,
    tool_path,
    upscale_video as run_upscale_video,
)


SUBCATEGORIES = [
    "Sebi-Lehre",
    "Mixtur/Rezept",
    "Produkt/Verpackung",
    "Zutaten/Wirkstoffe",
    "Lifestyle/Content",
    "Sonstige",
]


def load_knowledge_context(knowledge_dir: Path) -> str:
    knowledge_dir = normalize_input_path(knowledge_dir)
    if not knowledge_dir.exists():
        return ""
    parts: list[str] = []
    for path in sorted(knowledge_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        parts.append(f"### {path.name}\n{text[:4500]}")
    return "\n\n".join(parts)


def extract_sofinello_frames(
    video_file: Path,
    slug: str,
    max_frames: int,
    log_file: Path,
    *,
    frame_long_side: int = 1920,
) -> list[Path]:
    frame_dir = PROJECT_DIR / "frames" / "sofinello" / slug
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
            f"fps=1/4,scale={frame_long_side}:-2:force_original_aspect_ratio=decrease",
            "-frames:v",
            str(max_frames),
            "-q:v",
            "2",
            str(frame_dir / "frame_%02d.jpg"),
        ],
        log_file,
        timeout=1200,
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
            "2",
            str(frame_dir / "frame_01.jpg"),
        ],
        log_file,
        timeout=900,
    )
    return sorted(frame_dir.glob("frame_*.jpg"))[:max_frames]


def upscale_sofinello_frames(
    frame_paths: list[Path],
    *,
    slug: str,
    scale: int,
    model: str,
    log_file: Path,
) -> dict[str, Any]:
    binary = normalize_input_path(DEFAULT_BINARY).resolve()
    models_dir = normalize_input_path(DEFAULT_MODELS).resolve()
    windows_binary = binary.suffix.lower() == ".exe"
    if not binary.exists():
        raise FileNotFoundError(f"Real-ESRGAN Binary nicht gefunden: {binary}")
    if not models_dir.exists():
        raise FileNotFoundError(f"Real-ESRGAN Models-Ordner nicht gefunden: {models_dir}")
    if not frame_paths:
        raise RuntimeError("Keine Frames fuer Frame-Only-Upscaling vorhanden.")

    input_dir = frame_paths[0].parent
    output_dir = PROJECT_DIR / "frames" / "sofinello_upscaled" / slug
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_frame in output_dir.glob("*"):
        if old_frame.is_file() and old_frame.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            old_frame.unlink()

    before_gpu = nvidia_smi_snapshot()
    run_upscale_command(
        [
            str(binary),
            "-i",
            tool_path(input_dir, windows_binary=windows_binary),
            "-o",
            tool_path(output_dir, windows_binary=windows_binary),
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
    after_gpu = nvidia_smi_snapshot()
    upscaled_frames = sorted(
        [path for path in output_dir.glob("*") if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    )
    if not upscaled_frames:
        raise RuntimeError("Real-ESRGAN hat keine upgescalten Analyseframes erzeugt.")
    return {
        "mode": "frame-only",
        "input_frame_dir": str(input_dir),
        "output_frame_dir": str(output_dir),
        "input_frame_count": len(frame_paths),
        "output_frame_count": len(upscaled_frames),
        "frames": [str(path) for path in upscaled_frames],
        "scale": scale,
        "model": model,
        "binary": str(binary),
        "models_dir": str(models_dir),
        "gpu_before": before_gpu,
        "gpu_after": after_gpu,
    }


def estimate_sofinello_cost(model: str, transcript: str, frame_count: int, knowledge: str) -> float:
    text_tokens = max(800, (len(transcript) + len(knowledge[:6000])) // 4)
    frame_tokens = max(1, frame_count) * 1800
    return round(estimate_cost_usd(model, text_tokens + frame_tokens + 3500, 2800), 6)


def build_prompt(
    *,
    knowledge_context: str,
    questions: list[str],
    source_path: Path,
    source_info: str,
    transcript_text: str,
    frame_count: int,
    duration_seconds: float | None,
) -> str:
    question_block = "\n".join(f"- {question}" for question in questions)
    subcat_block = ", ".join(SUBCATEGORIES)
    return f"""Du bist Sofinellos interner Video-Analyst mit Compliance-Pflicht.
Antworte auf Deutsch, sachlich, vorsichtig und strukturiert.

Datenklasse: D2, Cloud-Verarbeitung ist erlaubt.
Quelle: {source_path}
Quelle/Notiz: {source_info or "lokale Sofinello-Datei"}
Dauer: {duration_seconds if duration_seconds is not None else "unbekannt"} Sekunden
Frames: {frame_count} ausgewaehlte, vorher upgescalte Standbilder

Nexis Fragen:
{question_block}

Wissens-Anker:
{knowledge_context[:12000]}

HARTE COMPLIANCE-REGELN:
- Keine Heilversprechen.
- Keine Diagnosen.
- Keine Aussage, dass ein Produkt Krankheiten heilt, behandelt, verhindert, lindert oder beseitigt.
- Keine Dosierung als verbindliche Empfehlung.
- Wenn eine Krankheit/Symptom im Video genannt wird: nur dokumentieren als "im Video erwaehnt" oder "Sebi vertrat die Auffassung".
- Nutze sichere Sprache: "traditionell verwendet fuer", "im Sebi-Kontext eingeordnet als", "das Video stellt dar", "nicht medizinisch bestaetigt".
- Nenne keine verbotenen Beispiel-Claims im Wortlaut. Schreibe stattdessen "krankheitsbezogenes Wirkversprechen" oder "verbotene Wirkformulierung".
- Fuer oeffentlichen Output immer fachliche und rechtliche Pruefung fordern.

Whisper-Transkript:
{transcript_text[:12000]}

Erstelle exakt diese Markdown-Struktur:

## Kurzantwort fuer Nexi

## Sub-Kategorisierung
Sub-Kategorie: eine der folgenden Kategorien: {subcat_block}
Begruendung:

## Visuelle Inhalte

## Erkennbare Zutaten / Wirkstoffe

## Erwaehnte Krankheiten / Symptome / Gesundheits-Themen

## Mixtur / Rezept / Anwendung

## Verpackungs-Details / OCR

## Sebi- und Traditions-Bezuege

## Nutzwert fuer Sofinello

## Risiken, Unsicherheiten und Pruefbedarf

## Compliance-Vorpruefung
Nutze hier nur sichere Sprache. Wenn du einen riskanten Claim erkennst, formuliere ihn nicht als Wahrheit, sondern als Risiko/Pruefpunkt.
"""


def extract_subcategory(text: str) -> str:
    match = re.search(r"Sub-Kategorie:\s*(.+)", text, re.I)
    if not match:
        return "Sonstige"
    value = match.group(1).strip()
    for subcategory in SUBCATEGORIES:
        if subcategory.lower() in value.lower():
            return subcategory
    return value[:80] or "Sonstige"


def extract_section_items(text: str, heading: str, limit: int = 20) -> list[str]:
    pattern = re.compile(rf"## {re.escape(heading)}\s*(.*?)(?=\n## |\Z)", re.S | re.I)
    match = pattern.search(text)
    if not match:
        return []
    block = match.group(1)
    items: list[str] = []
    for line in block.splitlines():
        cleaned = line.strip().lstrip("-*").strip()
        if not cleaned or cleaned.endswith(":"):
            continue
        if len(cleaned) > 160:
            cleaned = cleaned[:157] + "..."
        items.append(cleaned)
        if len(items) >= limit:
            break
    return items


def render_raw_markdown(
    *,
    source_path: Path,
    analysis_media: str,
    upscale_mode: str,
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
    stamp: str,
) -> str:
    return "\n".join(
        [
            f"# Sofinello Video-Analyse: {source_path.name}",
            "",
            f"Datum: {stamp}",
            "Typ: sofinello-video",
            f"Datenklasse: {data_class}",
            f"Modell: {model}",
            f"Quelle/Notiz: {source_info or 'lokale Sofinello-Datei'}",
            f"Original-Datei: `{source_path}`",
            f"Analyse-Medium: `{analysis_media}`",
            f"Dauer: {duration_seconds if duration_seconds is not None else 'unbekannt'} s",
            f"Preprocessor: real-esrgan Pflicht-Upscaling ({upscale_mode})",
            "",
            "## Fragen",
            "",
            "\n".join(f"- {question}" for question in questions),
            "",
            "## Lokale Vorverarbeitung",
            "",
            f"- Transkript: `{transcript_file}`",
            "- An Gemini gesendet: ausgewaehlte upgescalte Frames + Transkript, nicht die ganze Videodatei.",
            "",
            "## Frames",
            "",
            "\n".join(f"- `{frame}`" for frame in frame_paths) or "- Keine Frames erzeugt.",
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
    parser = argparse.ArgumentParser(description="Analyze one Sofinello video with mandatory upscaling and compliance.")
    parser.add_argument("--video-path", type=Path, required=True)
    parser.add_argument("--data-class", default="D2", choices=sorted(VALID_DATA_CLASSES))
    parser.add_argument("--question", action="append", default=[])
    parser.add_argument("--source-info", default="")
    parser.add_argument("--slug", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-cost-eur", type=float, default=1.0)
    parser.add_argument("--max-frames", type=int, default=DEFAULT_FRAME_COUNT)
    parser.add_argument("--frame-long-side", type=int, default=1280)
    parser.add_argument("--upscale-mode", choices=["full-video", "frame-only"], default="full-video")
    parser.add_argument("--upscale-scale", type=int, choices=[2, 3, 4], default=2)
    parser.add_argument("--upscale-model", default="realesrgan-x4plus")
    parser.add_argument("--upscale-max-duration-seconds", type=float, default=180.0)
    parser.add_argument("--knowledge-dir", type=Path, default=HEALING_KNOWLEDGE_DIR)
    parser.add_argument("--keep-upscale-workdir", action="store_true")
    parser.add_argument("--keep-uploaded-files", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = load_settings()
    model = args.model or settings["model"]
    video_file = normalize_input_path(args.video_path).resolve()
    if not video_file.exists():
        raise FileNotFoundError(f"Sofinello-Video nicht gefunden: {video_file}")

    stamp = now_stamp()
    slug = slugify(args.slug or f"sofinello-{video_file.stem}-{stamp}")
    questions = args.question or [
        "Was zeigt dieses Sofinello-Video, welche Zutaten/Produkte/Claims sind erkennbar, und was muss compliance-seitig geprueft werden?"
    ]
    log_dir = PROJECT_DIR / "logs" / "sofinello"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{slug}-{stamp}.log"
    raw_dir = PROJECT_DIR / "analysis" / "sofinello" / "raw"
    final_dir = PROJECT_DIR / "analysis" / "sofinello" / "final"
    raw_dir.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "ok": False,
        "pipeline_type": "sofinello-video",
        "video_path": str(video_file),
        "video_path_windows": wsl_to_windows(video_file),
        "data_class": args.data_class,
        "questions": questions,
        "slug": slug,
        "started_at": stamp,
        "log_file": str(log_file),
        "log_file_windows": wsl_to_windows(log_file),
        "files": {},
        "cost": {},
    }

    try:
        duration_limit = None if args.upscale_max_duration_seconds <= 0 else args.upscale_max_duration_seconds
        upscaled_video: Path | None = None
        duration_seconds = ffprobe_duration_seconds(video_file)
        audio_file = extract_audio(video_file, slug, log_file)
        transcript_file = transcribe_audio(audio_file, args.data_class, slug, log_file)
        transcript_text = transcript_file.read_text(encoding="utf-8")
        if args.upscale_mode == "full-video":
            upscaled_output = PROJECT_DIR / "upscaled" / "sofinello" / f"{slug}_upscaled_x{args.upscale_scale}.mp4"
            upscale_report = run_upscale_video(
                video_file,
                output_path=upscaled_output,
                scale=args.upscale_scale,
                model=args.upscale_model,
                keep_workdir=args.keep_upscale_workdir,
                max_duration_seconds=duration_limit,
            )
            upscaled_video = Path(str(upscale_report["output_path"]))
            duration_seconds = ffprobe_duration_seconds(upscaled_video) or duration_seconds
            frame_paths = extract_sofinello_frames(
                upscaled_video,
                slug,
                args.max_frames,
                log_file,
                frame_long_side=args.frame_long_side,
            )
            analysis_media = str(upscaled_video)
        else:
            source_frames = extract_sofinello_frames(
                video_file,
                slug,
                args.max_frames,
                log_file,
                frame_long_side=args.frame_long_side,
            )
            upscale_report = upscale_sofinello_frames(
                source_frames,
                slug=slug,
                scale=args.upscale_scale,
                model=args.upscale_model,
                log_file=log_file,
            )
            frame_paths = [Path(path) for path in upscale_report["frames"]]
            analysis_media = str(Path(upscale_report["output_frame_dir"]))
        if not frame_paths:
            raise RuntimeError("Es konnten keine Sofinello-Frames erzeugt werden.")

        knowledge_context = load_knowledge_context(args.knowledge_dir)
        estimated_cost = estimate_sofinello_cost(model, transcript_text, len(frame_paths), knowledge_context)
        summary["cost"]["preflight_estimated_usd"] = estimated_cost
        if estimated_cost > args.max_cost_eur:
            raise RuntimeError(f"Kosten-Schaetzung {estimated_cost:.4f} USD > Limit {args.max_cost_eur:.2f} EUR")

        if args.dry_run:
            summary["ok"] = True
            summary["dry_run"] = True
            summary["files"].update(
                {
                    "upscaled_video": str(upscaled_video) if upscaled_video else None,
                    "upscaled_video_windows": wsl_to_windows(upscaled_video) if upscaled_video else None,
                    "upscaled_frames": [str(path) for path in frame_paths],
                    "audio": str(audio_file) if audio_file else None,
                    "transcript_txt": str(transcript_file),
                    "frames": [str(path) for path in frame_paths],
                }
            )
            print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
            return 0

        prompt = build_prompt(
            knowledge_context=knowledge_context,
            questions=questions,
            source_path=video_file,
            source_info=args.source_info,
            transcript_text=transcript_text,
            frame_count=len(frame_paths),
            duration_seconds=round(duration_seconds, 3) if duration_seconds else None,
        )

        client = make_client(settings["api_key"])
        gemini_cleanup_before = cleanup_gemini_files(client, "before-sofinello")
        uploaded = []
        try:
            for frame in frame_paths:
                uploaded.append(wait_for_file(client, client.files.upload(file=str(frame))))
            response = client.models.generate_content(
                model=model,
                contents=[*uploaded, prompt],
                config=types.GenerateContentConfig(temperature=0.15, max_output_tokens=2800),
            )
        finally:
            if not args.keep_uploaded_files:
                for current in uploaded:
                    try:
                        client.files.delete(name=current.name)
                    except Exception:
                        pass
            gemini_cleanup_after = cleanup_gemini_files(client, "after-sofinello")

        analysis_text = (response.text or "").strip()
        usage = usage_to_dict(getattr(response, "usage_metadata", None))
        actual_cost = actual_cost_from_usage(model, usage)
        raw_md = raw_dir / f"{slug}.sofinello-raw-{stamp}.md"
        final_md = final_dir / f"{slug}.sofinello-final-{stamp}.md"
        output_json = final_dir / f"{slug}.sofinello-final-{stamp}.json"

        raw_md.write_text(
            render_raw_markdown(
                source_path=video_file,
                analysis_media=analysis_media,
                upscale_mode=args.upscale_mode,
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
                stamp=stamp,
            ),
            encoding="utf-8",
        )

        compliance = apply_compliance(raw_md, final_md, args.knowledge_dir / "disclaimer-standard.md")
        final_text = final_md.read_text(encoding="utf-8")
        subcategory = extract_subcategory(final_text)
        ingredients = extract_section_items(final_text, "Erkennbare Zutaten / Wirkstoffe")
        health_mentions = extract_section_items(final_text, "Erwaehnte Krankheiten / Symptome / Gesundheits-Themen")
        product_mentions = extract_section_items(final_text, "Verpackungs-Details / OCR")
        qdrant = upsert_sofinello_knowledge(
            source_path=video_file,
            subcategory=subcategory,
            data_class=args.data_class,
            questions=questions,
            analysis_markdown=final_md,
            raw_analysis_markdown=raw_md,
            transcript_txt=transcript_file,
            frame_paths=frame_paths,
            upscaled_video=upscaled_video,
            cost_usd=actual_cost,
            slug=slug,
            compliance=compliance,
            ingredients=ingredients,
            health_mentions=health_mentions,
            product_mentions=product_mentions,
            source_info=args.source_info,
        )

        payload = {
            "pipeline_type": "sofinello-video",
            "video_path": str(video_file),
            "video_path_windows": wsl_to_windows(video_file),
            "upscale_mode": args.upscale_mode,
            "analysis_media": analysis_media,
            "upscaled_video": str(upscaled_video) if upscaled_video else None,
            "upscaled_video_windows": wsl_to_windows(upscaled_video) if upscaled_video else None,
            "data_class": args.data_class,
            "questions": questions,
            "source_info": args.source_info,
            "model": model,
            "duration_seconds": duration_seconds,
            "audio_file": str(audio_file) if audio_file else None,
            "transcript_txt": str(transcript_file),
            "frames": [str(path) for path in frame_paths],
            "raw_markdown": str(raw_md),
            "final_markdown": str(final_md),
            "compliance": compliance,
            "subcategory": subcategory,
            "ingredients": ingredients,
            "health_mentions": health_mentions,
            "product_mentions": product_mentions,
            "usage": usage,
            "gemini_file_cleanup": {"before": gemini_cleanup_before, "after": gemini_cleanup_after},
            "cost_usd": actual_cost,
            "preflight_estimated_cost_usd": estimated_cost,
            "upscale": upscale_report,
            "qdrant": qdrant,
        }
        write_json(output_json, payload)

        summary["ok"] = True
        summary["files"].update(
            {
                "upscaled_video": str(upscaled_video) if upscaled_video else None,
                "upscaled_video_windows": wsl_to_windows(upscaled_video) if upscaled_video else None,
                "upscaled_frames": [str(path) for path in frame_paths],
                "audio": str(audio_file) if audio_file else None,
                "transcript_txt": str(transcript_file),
                "raw_markdown": str(raw_md),
                "raw_markdown_windows": wsl_to_windows(raw_md),
                "final_markdown": str(final_md),
                "final_markdown_windows": wsl_to_windows(final_md),
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
        summary["subcategory"] = subcategory
        summary["compliance"] = compliance
        summary["qdrant"] = qdrant
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:  # noqa: BLE001
        summary["error"] = str(exc)
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
