#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from failed_videos import append_failed_video
from telegram_common import send_message_if_configured


PROJECT_DIR = Path(__file__).resolve().parents[1]
VALID_DATA_CLASSES = {"D0", "D1", "D2", "D3", "D4"}
GEMINI_503_EVENTS_JSON = PROJECT_DIR / "videos" / "_runs" / "gemini-503-events.json"
GEMINI_RETRY_DELAYS_SECONDS = (0, 30, 60, 120, 300, 900, 1800)


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


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


def run_slug(base: str, url: str, stamp: str) -> str:
    prefix = slugify(base)[:55] or "video"
    return slugify(f"{prefix}-{url_hash(url)}-{stamp}")


def topic_slug(value: str | None) -> str:
    base = (value or "TELEGRAM-SHARE").split("|", 1)[0].strip()
    return slugify(base)[:80] or "TELEGRAM-SHARE"


def video_id_for_source(source_url: str | None, video_file: Path | None = None) -> str:
    if source_url:
        shortcode = instagram_shortcode(source_url)
        return slugify(shortcode or url_hash(source_url))[:80]
    if video_file:
        base = slugify(video_file.stem)[:55] or "local-video"
        return slugify(f"{base}-{file_sha256(video_file)[:12]}")[:80]
    return "video"


def ensure_clean_video_dir(run_dir: Path) -> None:
    root = (PROJECT_DIR / "videos").resolve()
    target = run_dir.resolve()
    if root not in target.parents:
        raise RuntimeError(f"Unsicheres Video-Zielverzeichnis: {target}")
    run_dir.mkdir(parents=True, exist_ok=True)
    for child in run_dir.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def first_answer_excerpt(markdown: str, limit: int = 1200) -> str:
    marker = "## Antworten auf Nexis konkrete Fragen"
    if marker in markdown:
        text = markdown.split(marker, 1)[1]
        next_heading = re.search(r"\n##\s+", text)
        if next_heading:
            text = text[: next_heading.start()]
    else:
        text = markdown
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text[:limit].strip()


def write_summary_markdown(path: Path, summary: dict[str, Any], analysis_markdown: Path) -> None:
    analysis_text = analysis_markdown.read_text(encoding="utf-8", errors="replace")
    excerpt = first_answer_excerpt(analysis_text)
    questions = "\n".join(f"- {question}" for question in summary.get("questions") or []) or "- n/a"
    lines = [
        f"# Zusammenfassung: {summary.get('video_id')}",
        "",
        f"- Quelle: {summary.get('url')}",
        f"- Thema: {summary.get('topic') or 'n/a'}",
        f"- Datenklasse: {summary.get('data_class')}",
        f"- Video-SHA256: `{summary.get('provenance', {}).get('video_sha256')}`",
        f"- Kosten USD: `{summary.get('cost', {}).get('estimated_actual_usd')}`",
        "",
        "## Fragen",
        "",
        questions,
        "",
        "## Kurzantwort",
        "",
        excerpt,
        "",
        "## Dateien",
        "",
        f"- Original-Video: `{summary.get('files', {}).get('video')}`",
        f"- Whisper-Transkript: `{summary.get('files', {}).get('transcript_txt')}`",
        f"- Gemini-Analyse: `{summary.get('files', {}).get('analysis_markdown')}`",
        f"- Word-Bericht: `{summary.get('files', {}).get('word_report')}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def docx_paragraph(text: str, style: str | None = None) -> str:
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{style_xml}<w:r><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>"


def write_docx_report(path: Path, title: str, markdown_text: str) -> None:
    body: list[str] = [docx_paragraph(title, "Title")]
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            body.append("<w:p/>")
        elif line.startswith("# "):
            body.append(docx_paragraph(line[2:].strip(), "Heading1"))
        elif line.startswith("## "):
            body.append(docx_paragraph(line[3:].strip(), "Heading2"))
        elif line.startswith("### "):
            body.append(docx_paragraph(line[4:].strip(), "Heading3"))
        elif line.startswith("- "):
            body.append(docx_paragraph(f"• {line[2:].strip()}"))
        elif line.startswith("```"):
            continue
        else:
            body.append(docx_paragraph(line))

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(body)}<w:sectPr/></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)


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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def instagram_shortcode(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"instagram\.com/(?:reel|p|tv)/([^/?#]+)/?", url, re.I)
    return match.group(1) if match else None


def validate_info_json(info_json: Path, source_url: str, label: str) -> dict[str, Any]:
    if not info_json.exists():
        raise FileNotFoundError(f"{label}: info.json fehlt: {info_json}")
    metadata = load_json(info_json)
    expected_shortcode = instagram_shortcode(source_url)
    if expected_shortcode:
        candidates = {
            str(metadata.get("id") or ""),
            str(metadata.get("display_id") or ""),
            str(metadata.get("webpage_url_basename") or ""),
        }
        webpage_shortcode = instagram_shortcode(str(metadata.get("webpage_url") or ""))
        if webpage_shortcode:
            candidates.add(webpage_shortcode)
        if expected_shortcode not in candidates:
            raise RuntimeError(
                f"{label}: URL-Bindung fehlgeschlagen. Erwartet {expected_shortcode}, "
                f"gefunden id={metadata.get('id')} webpage_url={metadata.get('webpage_url')}"
            )
    return metadata


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def is_gemini_503(output: str) -> bool:
    text = output.lower()
    return (
        "503 unavailable" in text
        or "high demand" in text
        or "status': 'unavailable" in text
        or '"status": "unavailable' in text
    )


def append_gemini_503_event(
    *,
    video_id: str | None,
    step_name: str,
    cycle: int,
    attempt: int,
    attempts: int,
    next_delay_seconds: int | None,
    output: str,
    log_file: Path,
) -> None:
    payload = read_json_file(GEMINI_503_EVENTS_JSON, {"events": []})
    events = payload.setdefault("events", [])
    events.append(
        {
            "at": datetime.now().isoformat(timespec="seconds"),
            "video_id": video_id,
            "step": step_name,
            "cycle": cycle,
            "attempt": attempt,
            "attempts_per_cycle": attempts,
            "global_attempt": ((cycle - 1) * attempts) + attempt,
            "next_delay_seconds": next_delay_seconds,
            "log_file": str(log_file),
            "error_signature": "503 UNAVAILABLE / high demand",
            "snippet": output[-1000:],
        }
    )
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    payload["event_count"] = len(events)
    write_json_file(GEMINI_503_EVENTS_JSON, payload)


def run_step(
    name: str,
    command: list[str],
    log_file: Path,
    timeout_seconds: int,
    attempts: int = 1,
    retry_on: tuple[str, ...] = (),
    retry_delays_seconds: tuple[int, ...] | None = None,
    retry_cycles: int = 1,
    cycle_pause_seconds: int = 0,
    retry_video_id: str | None = None,
) -> tuple[str, float]:
    started = time.perf_counter()
    last_output = ""
    retry_delays_seconds = retry_delays_seconds or tuple(0 if index == 0 else min(300, 30 * (2 ** (index - 1))) for index in range(attempts))

    for cycle in range(1, retry_cycles + 1):
        for attempt in range(1, attempts + 1):
            with log_file.open("a", encoding="utf-8") as log:
                if retry_cycles > 1:
                    log.write(f"\n=== {name} cycle {cycle}/{retry_cycles} attempt {attempt}/{attempts} ===\n")
                else:
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
            if not should_retry:
                raise RuntimeError(f"Step failed: {name}\n{output[-4000:]}")

            next_delay: int | None = None
            if attempt < attempts:
                next_delay = retry_delays_seconds[attempt] if attempt < len(retry_delays_seconds) else retry_delays_seconds[-1]
            elif cycle < retry_cycles:
                next_delay = cycle_pause_seconds

            gemini_503 = is_gemini_503(output)
            if gemini_503:
                append_gemini_503_event(
                    video_id=retry_video_id,
                    step_name=name,
                    cycle=cycle,
                    attempt=attempt,
                    attempts=attempts,
                    next_delay_seconds=next_delay,
                    output=output,
                    log_file=log_file,
                )

            if attempt < attempts:
                delay = int(next_delay or 0)
                if gemini_503 and delay >= 300:
                    send_message_if_configured(
                        f"⏸ Gemini-503, warte {delay // 60} Min, Versuch {attempt + 1}/{attempts}"
                    )
                with log_file.open("a", encoding="utf-8") as log:
                    log.write(f"\nRetryable error. Sleeping {delay}s before attempt {attempt + 1}/{attempts}.\n")
                time.sleep(delay)
                continue

            if cycle < retry_cycles:
                delay = int(cycle_pause_seconds)
                if gemini_503 and delay >= 300:
                    send_message_if_configured(
                        f"⏸ Gemini-503, warte {delay // 60} Min, Versuch 1/{attempts} (Zyklus {cycle + 1}/{retry_cycles})"
                    )
                with log_file.open("a", encoding="utf-8") as log:
                    log.write(f"\nRetry cycle {cycle}/{retry_cycles} exhausted. Sleeping {delay}s before next cycle.\n")
                time.sleep(delay)
                continue

            raise RuntimeError(f"Step failed after {retry_cycles} cycle(s): {name}\n{output[-4000:]}")

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
    parser.add_argument("--url", default=None)
    parser.add_argument("--video-file", type=Path, default=None)
    parser.add_argument("--data-class", default="D0", choices=sorted(VALID_DATA_CLASSES))
    parser.add_argument("--slug", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--topic", default=None)
    parser.add_argument("--question", action="append", default=[])
    parser.add_argument("--max-cost-eur", default="0.30")
    parser.add_argument("--max-video-mb", default=None)
    parser.add_argument("--max-duration-sec", default=None)
    parser.add_argument("--approve-large", action="store_true")
    parser.add_argument("--existing-transcript", type=Path, default=None)
    parser.add_argument("--allow-sensitive", action="store_true")
    args = parser.parse_args()
    if not args.url and not args.video_file:
        parser.error("Either --url or --video-file is required.")
    if args.url and args.video_file:
        parser.error("Use only one input: --url or --video-file.")
    return args


def notify_single_summary(summary: dict[str, Any]) -> None:
    if not summary.get("url"):
        return
    if summary.get("ok"):
        text = "\n".join(
            [
                "Video-Pipeline fertig",
                f"URL: {summary.get('url')}",
                f"Kosten: ${float(summary.get('cost', {}).get('estimated_actual_usd') or 0):.4f}",
                f"Analyse: {summary.get('files', {}).get('analysis_markdown_windows') or summary.get('files', {}).get('analysis_markdown')}",
            ]
        )
    else:
        text = "\n".join(
            [
                "Video-Pipeline Fehler",
                f"URL: {summary.get('url')}",
                f"Fehler: {str(summary.get('error'))[:1500]}",
            ]
        )
    send_message_if_configured(text)


def main() -> int:
    args = parse_args()
    if args.data_class in {"D3", "D4"} and not args.allow_sensitive:
        raise RuntimeError("D3/D4 sind fuer Aufgabe 012 ohne --allow-sensitive gesperrt.")

    input_video_file = args.video_file.resolve() if args.video_file else None
    if input_video_file and not input_video_file.exists():
        raise FileNotFoundError(f"Lokale Videodatei nicht gefunden: {input_video_file}")
    source_ref = args.url or str(input_video_file)
    stamp = now_stamp()
    requested_slug = args.slug or f"manual-{stamp}"
    slug = run_slug(requested_slug, source_ref, stamp)
    video_id = video_id_for_source(args.url, input_video_file)
    topic_dir = topic_slug(args.topic)
    run_dir = PROJECT_DIR / "videos" / topic_dir / video_id
    ensure_clean_video_dir(run_dir)
    log_dir = PROJECT_DIR / "logs" / "pipeline"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{slug}-{stamp}.log"
    run_log_file = run_dir / "pipeline.log"
    (PROJECT_DIR / "downloads").mkdir(exist_ok=True)
    (PROJECT_DIR / "workflows").mkdir(exist_ok=True)

    summary: dict[str, Any] = {
        "ok": False,
        "url": source_ref,
        "source_kind": "url" if args.url else "local-file",
        "data_class": args.data_class,
        "slug": slug,
        "requested_slug": requested_slug,
        "url_hash": url_hash(source_ref),
        "video_id": video_id,
        "video_dir": str(run_dir),
        "topic": args.topic,
        "questions": args.question,
        "started_at": stamp,
        "log_file": str(log_file),
        "steps": {},
        "files": {},
        "cost": {},
    }
    run_dir.joinpath("source-url.txt").write_text(source_ref + "\n", encoding="utf-8")

    try:
        ytdlp = str(PROJECT_DIR / ".venv" / "bin" / "yt-dlp")
        venv_python = str(PROJECT_DIR / ".venv" / "bin" / "python")

        if args.url:
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
                    str(run_dir),
                    "--output",
                    "Original-Video.%(ext)s",
                    "--write-info-json",
                    "--print",
                    "after_move:filepath",
                    args.url,
                ],
                log_file,
                timeout_seconds=900,
            )
            video_file = Path(
                next((line.strip() for line in video_output.splitlines() if line.strip().startswith(str(run_dir))), "")
            )
            if not video_file.is_file():
                candidates = [
                    path
                    for path in run_dir.glob("Original-Video.*")
                    if path.is_file() and not path.name.endswith(".info.json")
                ]
                if not candidates:
                    raise FileNotFoundError(f"Kein Video-Download gefunden in {run_dir}")
                video_file = max(candidates, key=lambda path: path.stat().st_mtime)
            video_info = validate_info_json(video_file.with_suffix(".info.json"), args.url, "video-download")
            summary["steps"]["download_video_seconds"] = elapsed
        else:
            assert input_video_file is not None
            video_file = run_dir / f"Original-Video{input_video_file.suffix.lower() or '.mp4'}"
            shutil.copy2(input_video_file, video_file)
            video_info = {
                "id": video_id,
                "webpage_url": source_ref,
                "local_source_path": str(input_video_file),
            }
            (run_dir / "Original-Video.info.json").write_text(
                json.dumps(video_info, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            summary["steps"]["copy_local_video_seconds"] = 0.0
        summary["files"]["video"] = str(video_file)
        summary["files"]["video_info_json"] = str(video_file.with_suffix(".info.json"))
        summary["provenance"] = {
            "video_sha256": file_sha256(video_file),
            "video_info_id": video_info.get("id"),
            "video_info_webpage_url": video_info.get("webpage_url"),
        }

        existing_transcript = args.existing_transcript.resolve() if args.existing_transcript else None
        if existing_transcript:
            if not existing_transcript.exists():
                raise FileNotFoundError(f"Vorhandenes Transkript nicht gefunden: {existing_transcript}")
            canonical_transcript_txt = run_dir / "Whisper-Transkript.txt"
            shutil.copy2(existing_transcript, canonical_transcript_txt)
            transcript_txt = str(canonical_transcript_txt)
            transcript_json = None
            summary["steps"]["existing_transcript_seconds"] = 0.0
            summary["files"]["transcript_txt"] = transcript_txt
            summary["files"]["transcript_json"] = transcript_json
            summary["provenance"]["transcript_source"] = str(existing_transcript)
            summary["provenance"]["transcript_sha256"] = file_sha256(canonical_transcript_txt)
        else:
            try:
                if args.url:
                    audio_output, elapsed = run_step(
                        "download_audio",
                        [str(PROJECT_DIR / "scripts" / "download.sh"), args.url, args.data_class, "Whisper-Audio", str(run_dir)],
                        log_file,
                        timeout_seconds=900,
                    )
                    audio_file = parse_prefixed_path(audio_output, "Audio file")
                    if not audio_file:
                        raise RuntimeError("Audio-Datei konnte aus download.sh Output nicht gelesen werden.")
                    audio_path = Path(audio_file)
                    audio_info = validate_info_json(audio_path.with_suffix(".info.json"), args.url, "audio-download")
                    audio_meta = load_json(audio_path.with_suffix(".pipeline-meta.json"))
                    if audio_meta.get("source_url") != args.url:
                        raise RuntimeError(
                            "Audio-Provenance-Check fehlgeschlagen: pipeline-meta source_url passt nicht.\n"
                            f"URL: {args.url}\nMeta: {audio_meta.get('source_url')}"
                        )
                    summary["steps"]["download_audio_seconds"] = elapsed
                    summary["files"]["audio"] = audio_file
                    summary["files"]["audio_info_json"] = str(audio_path.with_suffix(".info.json"))
                    summary["files"]["audio_meta_json"] = str(audio_path.with_suffix(".pipeline-meta.json"))
                    summary["provenance"]["audio_sha256"] = file_sha256(audio_path)
                    summary["provenance"]["audio_info_id"] = audio_info.get("id")
                    transcribe_input = audio_file
                else:
                    transcribe_input = str(video_file)
                    summary["steps"]["audio_source"] = "local_video_file"

                transcribe_output, elapsed = run_step(
                    "whisper_transcribe",
                    [
                        venv_python,
                        str(PROJECT_DIR / "scripts" / "transcribe.py"),
                        transcribe_input,
                        "--data-class",
                        args.data_class,
                        "--output-dir",
                        str(run_dir),
                    ],
                    log_file,
                    timeout_seconds=1800,
                )
                transcript_txt = parse_prefixed_path(transcribe_output, "Transcript TXT")
                transcript_json = parse_prefixed_path(transcribe_output, "Transcript JSON")
                if not transcript_txt:
                    raise RuntimeError("Transkript-Pfad konnte aus transcribe.py Output nicht gelesen werden.")
                canonical_transcript_txt = run_dir / "Whisper-Transkript.txt"
                canonical_transcript_json = run_dir / "Whisper-Transkript.json"
                shutil.copy2(transcript_txt, canonical_transcript_txt)
                if transcript_json:
                    shutil.copy2(transcript_json, canonical_transcript_json)
                transcript_txt = str(canonical_transcript_txt)
                transcript_json = str(canonical_transcript_json) if transcript_json else None
                summary["steps"]["whisper_seconds"] = elapsed
                summary["files"]["transcript_txt"] = transcript_txt
                summary["files"]["transcript_json"] = transcript_json
            except Exception as audio_exc:  # noqa: BLE001
                raise RuntimeError(
                    "Audio-Download oder Transkription fehlgeschlagen. "
                    "Pipeline stoppt hart, damit keine alte Datei oder kein stiller Fallback "
                    "in die Analyse geraten kann."
                ) from audio_exc

        gemini_command = [
            venv_python,
            str(PROJECT_DIR / "scripts" / "analyze_full.py"),
            str(video_file),
            "--transcript",
            transcript_txt,
            "--data-class",
            args.data_class,
            "--source-url",
            source_ref,
            "--output-dir",
            str(run_dir),
            "--max-cost-eur",
            args.max_cost_eur,
        ]
        if args.max_video_mb:
            gemini_command.extend(["--max-video-mb", args.max_video_mb])
        if args.max_duration_sec:
            gemini_command.extend(["--max-duration-sec", args.max_duration_sec])
        if args.approve_large:
            gemini_command.append("--approve-large")
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
            attempts=7,
            retry_on=("429", "RESOURCE_EXHAUSTED", "rate limit", "quota", "503 UNAVAILABLE", "high demand"),
            retry_delays_seconds=GEMINI_RETRY_DELAYS_SECONDS,
            retry_cycles=2,
            cycle_pause_seconds=3600,
            retry_video_id=video_id,
        )
        output_md = parse_prefixed_path(gemini_output, "Output Markdown")
        output_json = parse_prefixed_path(gemini_output, "Output JSON")
        if not output_md or not output_json:
            raise RuntimeError("Gemini-JSON-Pfad konnte aus analyze_full.py Output nicht gelesen werden.")

        gemini_meta = json.loads(Path(output_json).read_text(encoding="utf-8"))
        if gemini_meta.get("input_sha256", {}).get("video") != summary["provenance"].get("video_sha256"):
            raise RuntimeError("Analyse-Provenance-Check fehlgeschlagen: video_sha256 passt nicht zum Input.")
        canonical_analysis_md = run_dir / "Gemini-Analyse.md"
        canonical_analysis_json = run_dir / "Gemini-Analyse.json"
        shutil.copy2(output_md, canonical_analysis_md)
        shutil.copy2(output_json, canonical_analysis_json)
        summary["steps"]["gemini_seconds"] = elapsed
        summary["files"]["analysis_markdown"] = str(canonical_analysis_md)
        summary["files"]["analysis_json"] = str(canonical_analysis_json)
        summary["cost"] = {
            "model": gemini_meta.get("model"),
            "estimated_actual_usd": gemini_meta.get("estimated_actual_cost_usd"),
            "preflight_usd": gemini_meta.get("preflight", {}).get("estimated_cost_usd"),
            "usage": gemini_meta.get("usage"),
        }
        summary_path = run_dir / "Zusammenfassung.md"
        word_report = run_dir / "Word-Bericht.docx"
        run_manifest = run_dir / "pipeline-manifest.json"
        summary["files"]["summary_markdown"] = str(summary_path)
        summary["files"]["word_report"] = str(word_report)
        summary["files"]["run_manifest"] = str(run_manifest)
        summary["files"]["pipeline_log"] = str(run_log_file)
        summary["finished_at"] = now_stamp()
        summary["ok"] = True
        write_summary_markdown(summary_path, summary, canonical_analysis_md)
        write_docx_report(
            word_report,
            f"Video-Bericht: {video_id}",
            summary_path.read_text(encoding="utf-8") + "\n\n" + canonical_analysis_md.read_text(encoding="utf-8", errors="replace"),
        )
        run_manifest.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        summary["finished_at"] = now_stamp()
        summary["error"] = str(exc)
        append_failed_video(url=source_ref, topic=args.topic or "single-video", error=str(exc), source="run_video_pipeline")
        with log_file.open("a", encoding="utf-8") as log:
            log.write("\n=== PIPELINE ERROR ===\n")
            log.write(str(exc) + "\n")
        if log_file.exists():
            shutil.copy2(log_file, run_log_file)
        notify_single_summary(summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 1

    if log_file.exists():
        shutil.copy2(log_file, run_log_file)
    for key, value in list(summary["files"].items()):
        summary["files"][f"{key}_windows"] = wsl_to_windows(value)
    summary["log_file_windows"] = wsl_to_windows(log_file)
    manifest_path = summary["files"].get("run_manifest")
    if manifest_path:
        Path(manifest_path).write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    notify_single_summary(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
