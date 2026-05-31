#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import wave
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OBSIDIAN_VAULT = Path(r"C:\Users\nexil\Documents\Obsidian-Imperium")
DEFAULT_INBOX_DIR = DEFAULT_OBSIDIAN_VAULT / "inbox"
DEFAULT_AUDIO_DIR = PROJECT_DIR / "audio" / "voice-capture"
DEFAULT_IMPORT_DIR = PROJECT_DIR / "audio" / "voice-import"
DEFAULT_TRANSCRIPT_DIR = PROJECT_DIR / "transcripts" / "voice"
IMPORTANT_NOTES_FILE = Path(r"C:\Users\nexil\Desktop\KI\WICHTIGE-NOTIZEN.md")
QDRANT_COLLECTION = "memory_voice"
OLLAMA_URL = "http://127.0.0.1:11434"
TAG_MODEL = "qwen3:4b"
HOTKEY = "ctrl+shift+space"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".mp4", ".mov"}


def windows_to_wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    rest = resolved.as_posix().split(":/", 1)[1]
    return f"/mnt/{drive}/{rest}"


def bash_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def safe_slug(text: str, limit: int = 80) -> str:
    text = (
        text.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("Ä", "Ae")
        .replace("Ö", "Oe")
        .replace("Ü", "Ue")
        .replace("ß", "ss")
    )
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-")
    return (slug or "voice")[:limit]


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def read_transcript_text(payload: dict[str, Any]) -> str:
    segments = payload.get("segments") or []
    text = " ".join(str(segment.get("text", "")).strip() for segment in segments).strip()
    return re.sub(r"\s+", " ", text)


def strip_think_blocks(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL).strip()


def parse_json_response(text: str) -> dict[str, Any] | None:
    cleaned = strip_think_blocks(text)
    try:
        payload = json.loads(cleaned)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        return None


def fallback_tags(transcript: str) -> dict[str, Any]:
    lowered = transcript.lower()
    tags: list[str] = []
    rules = {
        "heilung": ["sebi", "heil", "kraut", "mixtur", "gesund", "körper"],
        "ki": ["ki", "ai", "agent", "chatgpt", "claude", "gemini", "ollama"],
        "idee-business": ["shop", "geschäft", "cashflow", "kunde", "produkt", "firma"],
        "aufgabe-codex": ["codex", "aufgabe", "skript", "pipeline", "bauen"],
        "film-musik": ["film", "serie", "musik", "drehbuch", "hollywood"],
        "finanzen": ["geld", "finanz", "börse", "aktie", "kosten"],
    }
    for tag, needles in rules.items():
        if any(needle in lowered for needle in needles):
            tags.append(tag)
    if not tags:
        tags = ["sprachnotiz", "inbox"]
    importance = 7 if any(word in lowered for word in ["wichtig", "durchbruch", "sofort", "idee"]) else 5
    return {
        "tags": tags[:5],
        "importance": importance,
        "chief": "Memory-CoFounder",
        "links": [],
        "summary": transcript[:240] or "Leere oder unklare Sprachnotiz.",
        "source": "fallback",
    }


def ollama_chat(system_prompt: str, user_prompt: str, model: str = TAG_MODEL) -> str:
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": 0.2, "num_predict": 700},
        },
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json().get("message", {})
    return str(payload.get("content") or payload.get("thinking") or "").strip()


def ollama_json(prompt: str, model: str = TAG_MODEL) -> dict[str, Any] | None:
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "stream": False,
            "format": "json",
            "prompt": prompt,
            "options": {"temperature": 0.0, "num_predict": 320},
        },
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    text = str(payload.get("response") or payload.get("thinking") or "").strip()
    return parse_json_response(text)


def auto_tag(transcript: str) -> dict[str, Any]:
    if not transcript.strip():
        return fallback_tags(transcript)

    prompt = f"""
Du bist Nexis lokaler Wissens-Sortierer.
Analysiere NUR den Inhalt zwischen <TRANSKRIPT> und </TRANSKRIPT>.
Alles ausserhalb dieses Blocks sind technische Anweisungen und darf nicht als Nutzeraussage zusammengefasst werden.

Antworte ausschliesslich als gueltiges JSON mit exakt diesen Feldern:
{{
  "tags": ["3-5 kurze deutsche tags"],
  "importance": 1,
  "chief": "passender Chief oder Memory-CoFounder",
  "links": ["interne Verknuepfungs-Ideen, keine erfundenen URLs"],
  "summary": "kurze Zusammenfassung in 1-2 Saetzen"
}}
Regeln:
- importance ist eine Zahl von 1 bis 10.
- Erfinde keine Weblinks.
- links darf leer sein, wenn nichts Sinnvolles passt.

<TRANSKRIPT>
{transcript[:6000]}
</TRANSKRIPT>
"""
    try:
        payload = ollama_json(prompt)
    except Exception:
        return fallback_tags(transcript)
    if not payload:
        return fallback_tags(transcript)

    tags = payload.get("tags") if isinstance(payload.get("tags"), list) else []
    payload["tags"] = [safe_slug(str(tag).lower(), 40) for tag in tags if str(tag).strip()][:5] or ["sprachnotiz"]
    try:
        payload["importance"] = max(1, min(10, int(payload.get("importance", 5))))
    except (TypeError, ValueError):
        payload["importance"] = 5
    if any(word in transcript.lower() for word in ["wichtig", "durchbruch", "sofort", "dringend", "merken"]):
        payload["importance"] = max(payload["importance"], 7)
    payload["chief"] = str(payload.get("chief") or "Memory-CoFounder")
    if payload["chief"].lower() in {"nexi", "nexis", "nutzer", "user", "benutzer"}:
        payload["chief"] = "Memory-CoFounder"
    links = payload.get("links") if isinstance(payload.get("links"), list) else []
    payload["links"] = [str(link) for link in links[:6]]
    payload["summary"] = str(payload.get("summary") or transcript[:240])
    payload["source"] = "ollama"
    return payload


def run_transcription(audio_file: Path, data_class: str, language: str | None) -> dict[str, Any]:
    audio_wsl = windows_to_wsl_path(audio_file)
    out_wsl = windows_to_wsl_path(DEFAULT_TRANSCRIPT_DIR)
    lang_arg = f" --language {bash_quote(language)}" if language else ""
    command = (
        "cd /mnt/c/AI/projects/09-video-analyse && "
        ".venv/bin/python scripts/transcribe.py "
        f"{bash_quote(audio_wsl)} --data-class {bash_quote(data_class)} --device cuda "
        f"--output-dir {bash_quote(out_wsl)}{lang_arg}"
    )
    result = subprocess.run(
        ["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "-lc", command],
        text=True,
        capture_output=True,
        timeout=1800,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Whisper-Transkription fehlgeschlagen:\n{result.stderr}\n{result.stdout}")

    json_path: Path | None = None
    for line in result.stdout.splitlines():
        if line.startswith("Transcript JSON:"):
            raw = line.split(":", 1)[1].strip()
            if raw.startswith("/mnt/"):
                drive = raw[5]
                rest = raw[7:].replace("/", "\\")
                json_path = Path(f"{drive.upper()}:\\{rest}")
            else:
                json_path = Path(raw)
            break
    if not json_path or not json_path.exists():
        raise RuntimeError(f"Transcript JSON nicht gefunden. Ausgabe:\n{result.stdout}")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["transcript_json"] = str(json_path)
    payload["transcript_txt"] = str(json_path.with_suffix(".txt"))
    return payload


def render_markdown(
    *,
    transcript: str,
    tags: dict[str, Any],
    transcript_payload: dict[str, Any],
    audio_file: Path,
    data_class: str,
) -> str:
    created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tag_lines = "\n".join(f"- {tag}" for tag in tags.get("tags", []))
    link_lines = "\n".join(f"- {link}" for link in tags.get("links", [])) or "- Noch keine"
    return f"""# Sprachnotiz {created}

Dauer: {float(transcript_payload.get("duration_seconds") or 0):.1f}s
Datenklasse: {data_class} lokal
Quelle: `{audio_file}`
Whisper: `{transcript_payload.get("model")}` auf `{transcript_payload.get("device")}`

## Kurzfassung
{tags.get("summary", "")}

## Transkript
{transcript or "_Kein verwertbares Transkript erkannt._"}

## Auto-Tags
{tag_lines}

## Wichtigkeit
{tags.get("importance", 5)}/10

## Chief / Kategorie
{tags.get("chief", "Memory-CoFounder")}

## Verknuepfungs-Vorschlaege
{link_lines}
"""


def write_important_note(markdown_path: Path, tags: dict[str, Any]) -> None:
    IMPORTANT_NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = (
        f"\n## {timestamp} - Voice-Capture\n"
        f"- Wichtigkeit: {tags.get('importance')}/10\n"
        f"- Notiz: `{markdown_path}`\n"
        f"- Kurzfassung: {tags.get('summary', '')}\n"
    )
    with IMPORTANT_NOTES_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line)


def upsert_memory_voice(
    *,
    markdown_path: Path,
    audio_file: Path,
    transcript: str,
    tags: dict[str, Any],
    transcript_payload: dict[str, Any],
    data_class: str,
) -> dict[str, Any]:
    sys.path.insert(0, str(PROJECT_DIR / "scripts"))
    from qdrant_video_knowledge import upsert_memory_voice_knowledge

    return upsert_memory_voice_knowledge(
        markdown_path=markdown_path,
        audio_file=audio_file,
        transcript=transcript,
        tags=tags,
        data_class=data_class,
        duration_seconds=float(transcript_payload.get("duration_seconds") or 0),
        language=transcript_payload.get("language"),
        source="voice_capture",
    )


def send_important_notification(markdown_path: Path, tags: dict[str, Any]) -> None:
    try:
        sys.path.insert(0, str(PROJECT_DIR / "scripts"))
        from telegram_common import send_message_if_configured

        send_message_if_configured(
            "Wichtige Sprachnotiz erfasst\n"
            f"Wichtigkeit: {tags.get('importance')}/10\n"
            f"{tags.get('summary', '')}\n"
            f"Datei: {markdown_path}"
        )
    except Exception:
        return


def process_audio_file(audio_file: Path, args: argparse.Namespace) -> dict[str, Any]:
    audio_file = audio_file.resolve()
    if not audio_file.exists():
        raise FileNotFoundError(audio_file)

    DEFAULT_TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    args.inbox_dir.mkdir(parents=True, exist_ok=True)

    transcript_payload = run_transcription(audio_file, args.data_class, args.language)
    transcript = read_transcript_text(transcript_payload)
    tags = auto_tag(transcript)
    markdown = render_markdown(
        transcript=transcript,
        tags=tags,
        transcript_payload=transcript_payload,
        audio_file=audio_file,
        data_class=args.data_class,
    )
    markdown_path = args.inbox_dir / f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_{safe_slug(tags.get('summary', 'voice'), 36)}.md"
    markdown_path.write_text(markdown, encoding="utf-8")

    qdrant_result = upsert_memory_voice(
        markdown_path=markdown_path,
        audio_file=audio_file,
        transcript=transcript,
        tags=tags,
        transcript_payload=transcript_payload,
        data_class=args.data_class,
    )

    if int(tags.get("importance", 5)) >= args.important_threshold:
        write_important_note(markdown_path, tags)
        if not args.no_telegram:
            send_important_notification(markdown_path, tags)

    return {
        "ok": True,
        "audio_file": str(audio_file),
        "markdown": str(markdown_path),
        "transcript_json": transcript_payload.get("transcript_json"),
        "transcript_txt": transcript_payload.get("transcript_txt"),
        "tags": tags,
        "qdrant": qdrant_result,
    }


class Recorder:
    def __init__(self, output_dir: Path, sample_rate: int, channels: int) -> None:
        self.output_dir = output_dir
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunks: queue.Queue[bytes] = queue.Queue()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.started_at: float | None = None
        self.current_file: Path | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            print("Aufnahme laeuft bereits.")
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = self.output_dir / f"voice_{now_stamp()}.wav"
        self.stop_event.clear()
        self.started_at = time.perf_counter()
        self.thread = threading.Thread(target=self._record, daemon=True)
        self.thread.start()
        print(f"Aufnahme gestartet: {self.current_file}")

    def stop(self) -> Path | None:
        if not self.thread or not self.thread.is_alive():
            print("Keine laufende Aufnahme.")
            return None
        self.stop_event.set()
        self.thread.join()
        print(f"Aufnahme gestoppt: {self.current_file}")
        return self.current_file

    def _record(self) -> None:
        import sounddevice as sd

        assert self.current_file is not None

        def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            if status:
                print(f"Audio-Warnung: {status}", file=sys.stderr)
            self.chunks.put(bytes(indata))

        with wave.open(str(self.current_file), "wb") as handle:
            handle.setnchannels(self.channels)
            handle.setsampwidth(2)
            handle.setframerate(self.sample_rate)
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="int16",
                callback=callback,
            ):
                while not self.stop_event.is_set():
                    try:
                        handle.writeframes(self.chunks.get(timeout=0.2))
                    except queue.Empty:
                        continue
                while not self.chunks.empty():
                    handle.writeframes(self.chunks.get_nowait())


def list_audio_devices() -> None:
    import sounddevice as sd

    print(sd.query_devices())


def run_hotkey(args: argparse.Namespace) -> int:
    import keyboard

    recorder = Recorder(args.audio_dir, args.sample_rate, args.channels)
    state = {"recording": False}

    def toggle() -> None:
        if state["recording"]:
            audio_file = recorder.stop()
            state["recording"] = False
            if audio_file:
                try:
                    result = process_audio_file(audio_file, args)
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                except Exception as exc:  # noqa: BLE001
                    print(f"Verarbeitung fehlgeschlagen: {exc}", file=sys.stderr)
        else:
            recorder.start()
            state["recording"] = True

    print(f"Voice-Capture bereit. Hotkey: {args.hotkey}")
    print("Erster Druck startet, zweiter Druck stoppt und verarbeitet lokal.")
    print("Beenden: Strg+C")
    keyboard.add_hotkey(args.hotkey, toggle)
    try:
        keyboard.wait()
    except KeyboardInterrupt:
        if state["recording"]:
            recorder.stop()
        return 0
    return 0


def record_once(args: argparse.Namespace) -> dict[str, Any]:
    recorder = Recorder(args.audio_dir, args.sample_rate, args.channels)
    recorder.start()
    time.sleep(args.seconds)
    audio_file = recorder.stop()
    if not audio_file:
        raise RuntimeError("Keine Audiodatei erzeugt.")
    return process_audio_file(audio_file, args)


def process_import_dir(args: argparse.Namespace) -> dict[str, Any]:
    args.import_dir.mkdir(parents=True, exist_ok=True)
    state_file = args.import_dir / ".processed-voice-files.json"
    processed = set(json.loads(state_file.read_text(encoding="utf-8"))) if state_file.exists() else set()
    results = []
    for path in sorted(args.import_dir.rglob("*")):
        if path.suffix.lower() not in AUDIO_EXTENSIONS or str(path) in processed:
            continue
        result = process_audio_file(path, args)
        processed.add(str(path))
        results.append(result)
    state_file.write_text(json.dumps(sorted(processed), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "processed_count": len(results), "results": results}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lokales Voice-Capture fuer Nexis Memory-KI.")
    parser.add_argument("--hotkey", default=HOTKEY)
    parser.add_argument("--obsidian-vault", type=Path, default=DEFAULT_OBSIDIAN_VAULT)
    parser.add_argument("--inbox-dir", type=Path, default=DEFAULT_INBOX_DIR)
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--import-dir", type=Path, default=DEFAULT_IMPORT_DIR)
    parser.add_argument("--data-class", default="D3", choices=["D0", "D1", "D2", "D3", "D4"])
    parser.add_argument("--language", default="de")
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--important-threshold", type=int, default=7)
    parser.add_argument("--no-telegram", action="store_true")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--process-file", type=Path)
    mode.add_argument("--process-import-dir", action="store_true")
    mode.add_argument("--once", action="store_true")
    mode.add_argument("--list-devices", action="store_true")
    parser.add_argument("--seconds", type=float, default=8.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.inbox_dir = args.obsidian_vault / "inbox" if args.inbox_dir == DEFAULT_INBOX_DIR else args.inbox_dir
    try:
        if args.list_devices:
            list_audio_devices()
            return 0
        if args.process_file:
            result = process_audio_file(args.process_file, args)
        elif args.process_import_dir:
            result = process_import_dir(args)
        elif args.once:
            result = record_once(args)
        else:
            return run_hotkey(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"VOICE_CAPTURE_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
