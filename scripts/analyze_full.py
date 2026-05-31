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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine local Whisper transcript with Gemini visual video analysis."
    )
    parser.add_argument("video_file", type=Path)
    parser.add_argument("--transcript", type=Path, default=None)
    parser.add_argument("--data-class", default="D0", choices=sorted(VALID_DATA_CLASSES))
    parser.add_argument("--model", default=None)
    parser.add_argument("--topic", default=None)
    parser.add_argument("--question", action="append", default=[])
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


def default_transcript_for(video_file: Path) -> Path:
    return PROJECT_DIR / "transcripts" / f"{video_file.stem}.txt"


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


def build_prompt(transcript_text: str, topic: str | None, questions: list[str]) -> str:
    topic_block = f"\nThema / Kontext: {topic}\n" if topic else ""
    compliance_block = ""
    if topic and "sofinello" in topic.lower():
        compliance_block = """
Sofinello-Compliance-Pflicht:
- Keine Heilversprechen, keine Diagnosen, keine Therapieanweisungen.
- Keine Aussagen, dass ein Produkt Krankheiten heilen, lindern oder sicher verhindern kann.
- Formuliere vorsichtig: "traditionell verwendet", "Sebi vertrat die Auffassung", "nicht medizinisch belegt".
- Nenne bei oeffentlich nutzbaren Aussagen einen Disclaimer: keine medizinische Beratung, bei Beschwerden aerztlich abklaeren.
- Markiere kritische Claims klar als Compliance-Risiko.
"""
    questions_block = ""
    if questions:
        formatted_questions = "\n".join(f"- {question}" for question in questions)
        questions_block = f"""
Nexis konkrete Fragen, die du spezifisch beantworten musst:
{formatted_questions}
"""

    return f"""Du bist ein professioneller Videoanalyst fuer Nexis KI-Video-Pipeline.
{topic_block}{questions_block}

Analysiere das Video visuell und nutze das lokale Whisper-Transkript als Audiokontext.
Antworte in strukturiertem Markdown auf Deutsch.
Sicherheitsregel: Bei Cybersecurity, Hacking, Ueberwachung, Kennzeichen/Gesichter, Waffen, Medizin, Finanzen oder riskanten Bauanleitungen gib keine illegalen, schädlichen oder invasiven Schritt-fuer-Schritt-Anleitungen. Erklaere stattdessen defensiv, legal, konzeptionell, mit Risiken, Grenzen und sicheren Lernpfaden.

{compliance_block}

## Antworten auf Nexis konkrete Fragen
Beantworte diese Fragen zuerst, kurz, konkret und entscheidungsorientiert.
Wenn eine Frage anhand des Videos nicht beantwortbar ist, sage das klar.

## Visuelle Analyse
- Beschreibe die sichtbaren Szenen.
- Nenne relevante Objekte, Orte, Personen oder Bewegungen.
- Nenne sichtbaren Text / OCR, falls vorhanden.
- Gib Zeitstempel an, wenn moeglich.

## Audio-Kontext aus Whisper
Bewerte das Transkript kritisch: Es kann Fehler enthalten.

## Synthese: Was passiert insgesamt?
Verbinde Bildinhalt und gesprochenen Inhalt.

## Nutzen fuer spaetere Ideen-Datenbank
Extrahiere wiederverwendbare Themen, Motive, Hooks, Stilmittel und Kategorien.

## Unsicherheiten
Liste Dinge, die du nicht sicher erkennen kannst.

Whisper-Transkript:

```text
{transcript_text}
```
"""


def main() -> int:
    args = parse_args()
    if args.data_class in {"D3", "D4"} and not args.allow_sensitive:
        print("D3/D4 ist fuer Aufgabe 011 gesperrt. Nutze D0 fuer Tests.", file=sys.stderr)
        return 2

    video_file = args.video_file.resolve()
    transcript_file = (args.transcript or default_transcript_for(video_file)).resolve()
    if not transcript_file.exists():
        print(f"Transkript nicht gefunden: {transcript_file}", file=sys.stderr)
        return 1

    transcript_text = transcript_file.read_text(encoding="utf-8")
    input_video_sha256 = file_sha256(video_file)
    input_transcript_sha256 = file_sha256(transcript_file)
    settings = load_settings()
    model = args.model or settings["model"]
    max_cost_eur = args.max_cost_eur or float(settings["cost_cap_eur"])
    question_context = "\n".join(args.question)
    transcript_token_estimate = max(1, (len(transcript_text) + len(question_context) + len(args.topic or "")) // 4)

    preflight = run_preflight(
        video_file=video_file,
        model=model,
        max_cost_eur=max_cost_eur,
        max_video_mb=args.max_video_mb,
        max_duration_seconds=args.max_duration_sec,
        expected_output_tokens=2_500,
        extra_text_tokens=transcript_token_estimate,
        approve_large=args.approve_large,
    )

    if args.dry_run:
        print("DRY_RUN=1")
        print(f"Video: {preflight.video_file}")
        print(f"Transcript: {transcript_file}")
        print(f"Data class: {args.data_class}")
        print(f"Model: {model}")
        print(f"Size MB: {preflight.size_mb:.3f}")
        print(f"Duration seconds: {preflight.duration_seconds}")
        print(f"Estimated input tokens: {preflight.estimated_input_tokens}")
        print(f"Estimated output tokens: {preflight.estimated_output_tokens}")
        print(f"Estimated cost: ${preflight.estimated_cost_usd:.6f}")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    base = slugify(video_file.stem)
    stamp = now_stamp()
    output_md = args.output_dir / f"{base}.full-gemini-{stamp}.md"
    output_json = args.output_dir / f"{base}.full-gemini-{stamp}.json"

    client = make_client(settings["api_key"])
    gemini_cleanup_before = cleanup_gemini_files(client, "before-analyze-full")
    uploaded = None
    try:
        uploaded = client.files.upload(file=str(video_file))
        uploaded = wait_for_file(client, uploaded)
        response = client.models.generate_content(
            model=model,
            contents=[
                uploaded,
                build_prompt(transcript_text, args.topic, args.question),
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=6_000,
            ),
        )
    finally:
        if uploaded is not None and not args.keep_uploaded_file:
            try:
                client.files.delete(name=uploaded.name)
            except Exception as exc:  # noqa: BLE001
                print(f"WARNUNG: Uploaded file konnte nicht geloescht werden: {exc}", file=sys.stderr)
        gemini_cleanup_after = cleanup_gemini_files(client, "after-analyze-full")

    text = (response.text or "").strip()
    usage = usage_to_dict(getattr(response, "usage_metadata", None))
    actual_cost_usd = actual_cost_from_usage(model, usage)

    md = "\n".join(
        [
            f"# Video-Analyse: {video_file.name}",
            "",
            f"Datum: {stamp}",
            f"Quelle: {args.source_url or 'lokale D0-Testdatei'}",
            f"Datenklasse: {args.data_class}",
            f"Thema: {args.topic or 'n/a'}",
            f"Modell: {model}",
            f"Input-Video-SHA256: `{input_video_sha256}`",
            f"Input-Transcript-SHA256: `{input_transcript_sha256}`",
            f"Video-Datei: `{video_file}`",
            f"Whisper-Transkript: `{transcript_file}`",
            f"Groesse: {preflight.size_mb:.3f} MB",
            f"Dauer: {preflight.duration_seconds} s",
            "",
            "## Audio-Transkript (Whisper)",
            "",
            "```text",
            transcript_text.strip(),
            "```",
            "",
            "## Nexis Fragen",
            "",
            "\n".join(f"- {question}" for question in args.question) if args.question else "Keine spezifischen Fragen angegeben.",
            "",
            "## Visuelle Analyse und Synthese (Gemini Pro)",
            "",
            text,
            "",
            "## Cost-Tracking",
            "",
            "- Whisper: lokal, 0 EUR",
            f"- Gemini Prompt tokens: {usage.get('prompt_token_count')}",
            f"- Gemini Output tokens: {usage.get('candidates_token_count')}",
            f"- Gemini Total tokens: {usage.get('total_token_count')}",
            f"- Gemini Preflight-Schaetzung: ${preflight.estimated_cost_usd:.6f}",
            f"- Gemini Ist-Schaetzung: ${actual_cost_usd:.6f}" if actual_cost_usd is not None else "- Gemini Ist-Schaetzung: n/a",
            "- Hinweis: USD wird lokal konservativ 1:1 als EUR-Cap behandelt.",
            "",
        ]
    )
    output_md.write_text(md, encoding="utf-8")

    write_json(
        output_json,
        {
            "video_file": str(video_file),
            "transcript_file": str(transcript_file),
            "source_url": args.source_url,
            "data_class": args.data_class,
            "topic": args.topic,
            "questions": args.question,
            "model": model,
            "mime_type": get_mime_type(video_file),
            "input_sha256": {
                "video": input_video_sha256,
                "transcript": input_transcript_sha256,
            },
            "gemini_file_cleanup": {
                "before": gemini_cleanup_before,
                "after": gemini_cleanup_after,
            },
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
