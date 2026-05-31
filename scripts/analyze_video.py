#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


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

from google.genai import types

from gemini_common import (
    DEFAULT_ANALYSIS_DIR,
    VALID_DATA_CLASSES,
    actual_cost_from_usage,
    cleanup_gemini_files,
    file_sha256,
    get_mime_type,
    load_settings,
    make_client,
    now_stamp,
    print_cost_summary,
    run_preflight,
    slugify,
    usage_to_dict,
    write_json,
)


VISUAL_PROMPT = """Analysiere dieses Video. Antworte in strukturiertem Markdown auf Deutsch.

## Visuelle Inhalte

## Schluesselszenen mit Zeitstempeln

## Erkennbare Personen/Objekte

## Texte im Bild / OCR

## Themen/Kategorien

## Bemerkenswerte Details

Arbeite sachlich. Wenn etwas unsicher ist, kennzeichne es als Vermutung.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a public video with Gemini Pro.")
    parser.add_argument("video_file", type=Path)
    parser.add_argument("--data-class", default="D0", choices=sorted(VALID_DATA_CLASSES))
    parser.add_argument("--model", default=None)
    parser.add_argument("--source-url", default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_ANALYSIS_DIR)
    parser.add_argument("--max-cost-eur", type=float, default=None)
    parser.add_argument("--max-video-mb", type=float, default=25.0)
    parser.add_argument("--max-duration-sec", type=float, default=300.0)
    parser.add_argument("--approve-large", action="store_true")
    parser.add_argument("--allow-sensitive", action="store_true")
    parser.add_argument("--keep-uploaded-file", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Only run local validation and cost estimate.")
    return parser.parse_args()


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


def main() -> int:
    args = parse_args()
    if args.data_class in {"D3", "D4"} and not args.allow_sensitive:
        print("D3/D4 ist fuer Aufgabe 011 gesperrt. Nutze D0 fuer Tests.", file=sys.stderr)
        return 2

    settings = load_settings()
    model = args.model or settings["model"]
    max_cost_eur = args.max_cost_eur or float(settings["cost_cap_eur"])

    preflight = run_preflight(
        video_file=args.video_file,
        model=model,
        max_cost_eur=max_cost_eur,
        max_video_mb=args.max_video_mb,
        max_duration_seconds=args.max_duration_sec,
        expected_output_tokens=2_000,
        approve_large=args.approve_large,
    )

    if args.dry_run:
        print("DRY_RUN=1")
        print(f"Video: {preflight.video_file}")
        print(f"Data class: {args.data_class}")
        print(f"Model: {model}")
        print(f"Size MB: {preflight.size_mb:.3f}")
        print(f"Duration seconds: {preflight.duration_seconds}")
        print(f"Estimated input tokens: {preflight.estimated_input_tokens}")
        print(f"Estimated output tokens: {preflight.estimated_output_tokens}")
        print(f"Estimated cost: ${preflight.estimated_cost_usd:.6f}")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = slugify(preflight.video_file.stem)
    stamp = now_stamp()
    output_md = args.output_dir / f"{base}.visual-gemini-{stamp}.md"
    output_json = args.output_dir / f"{base}.visual-gemini-{stamp}.json"

    client = make_client(settings["api_key"])
    input_video_sha256 = file_sha256(preflight.video_file)
    gemini_cleanup_before = cleanup_gemini_files(client, "before-analyze-video")
    uploaded = None
    try:
        uploaded = client.files.upload(file=str(preflight.video_file))
        uploaded = wait_for_file(client, uploaded)
        response = client.models.generate_content(
            model=model,
            contents=[
                uploaded,
                VISUAL_PROMPT,
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2_000,
            ),
        )
    finally:
        if uploaded is not None and not args.keep_uploaded_file:
            try:
                client.files.delete(name=uploaded.name)
            except Exception as exc:  # noqa: BLE001
                print(f"WARNUNG: Uploaded file konnte nicht geloescht werden: {exc}", file=sys.stderr)
        gemini_cleanup_after = cleanup_gemini_files(client, "after-analyze-video")

    text = (response.text or "").strip()
    usage = usage_to_dict(getattr(response, "usage_metadata", None))
    actual_cost_usd = actual_cost_from_usage(model, usage)

    md = "\n".join(
        [
            f"# Visuelle Gemini-Analyse: {preflight.video_file.name}",
            "",
            f"Datum: {stamp}",
            f"Datenklasse: {args.data_class}",
            f"Modell: {model}",
            f"Quelle: {args.source_url or 'lokale D0-Testdatei'}",
            f"Datei: `{preflight.video_file}`",
            f"Input-Video-SHA256: `{input_video_sha256}`",
            f"Groesse: {preflight.size_mb:.3f} MB",
            f"Dauer: {preflight.duration_seconds} s",
            "",
            "## Gemini-Analyse",
            "",
            text,
            "",
            "## Cost-Tracking",
            "",
            f"- Prompt tokens: {usage.get('prompt_token_count')}",
            f"- Output tokens: {usage.get('candidates_token_count')}",
            f"- Total tokens: {usage.get('total_token_count')}",
            f"- Preflight-Schaetzung: ${preflight.estimated_cost_usd:.6f}",
            f"- Ist-Schaetzung: ${actual_cost_usd:.6f}" if actual_cost_usd is not None else "- Ist-Schaetzung: n/a",
            "- Hinweis: USD wird lokal konservativ 1:1 als EUR-Cap behandelt.",
            "",
        ]
    )
    output_md.write_text(md, encoding="utf-8")

    write_json(
        output_json,
        {
            "video_file": str(preflight.video_file),
            "source_url": args.source_url,
            "data_class": args.data_class,
            "model": model,
            "mime_type": get_mime_type(preflight.video_file),
            "input_sha256": {"video": input_video_sha256},
            "gemini_file_cleanup": {"before": gemini_cleanup_before, "after": gemini_cleanup_after},
            "preflight": preflight.__dict__,
            "usage": usage,
            "estimated_actual_cost_usd": actual_cost_usd,
            "output_markdown": str(output_md),
        },
    )

    print(f"Output Markdown: {output_md}")
    print(f"Output JSON: {output_json}")
    print_cost_summary(model, usage, preflight.estimated_cost_usd, actual_cost_usd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
