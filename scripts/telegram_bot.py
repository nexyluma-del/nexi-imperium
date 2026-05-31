#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from failed_videos import append_failed_video
from telegram_common import get_chat_id, get_updates, send_document, send_message, set_env_value
from telegram_status import render_status, status_payload


PROJECT_DIR = Path(__file__).resolve().parents[1]
URL_RE = re.compile(r"https?://[^\s<>]+", re.I)
DEFAULT_DATA_CLASS = "D2"
MAX_TELEGRAM_BATCH_COST_EUR = 5.0
PER_URL_ESTIMATE_EUR = 0.08
MAX_CHAT_ANALYSIS_CHARS = 3200


HELP_TEXT = """Nexis Imperium Bot

Befehle:
/help - Hilfe
/status - Systemstatus
/analyze <URL> [Frage] - Video/Post analysieren
/memory <Frage> - lokale Memory-KI mit Qdrant-Wissen fragen
/briefing [morning|midday|evening] - Memory-KI Briefing erzeugen
/links <Text> - Verknuepfungen im lokalen Wissen suchen
/sync - Master-Context fuer Claude/ChatGPT/Gemini exportieren
/sync <Thema> - Topic-Context als Markdown-Datei exportieren
/sync-tg <Thema> - Topic-Context direkt im Telegram-Chat anzeigen

Share-Modus:
- Nur eine URL senden: Auto-Analyse mit Standardfrage
- URL + Text senden: Text wird als Frage genutzt
- Mehrere URLs senden: kleiner Batch, Budget-Schutz aktiv
- Nur Text senden: wird als lokale Telegram-Notiz gespeichert
"""


def now_slug() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")[:90] or "telegram"


def is_authorized(chat_id: str) -> bool:
    allowed = get_chat_id()
    if not allowed:
        set_env_value("TELEGRAM_CHAT_ID", chat_id)
        send_message("Telegram Chat-ID gespeichert. Imperium Bot ist verbunden.", chat_id=chat_id)
        return True
    return str(chat_id) == str(allowed)


def extract_urls(text: str) -> list[str]:
    urls = [url.rstrip(").,;!?]") for url in URL_RE.findall(text)]
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


def question_from_text(text: str, urls: list[str]) -> str:
    question = text
    for url in urls:
        question = question.replace(url, " ")
    question = re.sub(r"^/analy[sz]e(@\w+)?", "", question, flags=re.I).strip()
    question = re.sub(r"\s+", " ", question).strip()
    return question or "Was ist die wichtigste Aussage, wie kann Nexi das nutzen, und welche Risiken gibt es?"


def display_question(question: str) -> str:
    return question if len(question) <= 500 else question[:497].rstrip() + "..."


def local_readable_path(value: str | None) -> Path | None:
    if not value:
        return None
    raw = str(value).strip()
    match = re.match(r"^([A-Za-z]):\\(.*)$", raw)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/")
        return Path(f"/mnt/{drive}/{rest}")
    return Path(raw)


def excerpt_markdown(markdown_path: str | None) -> str:
    path = local_readable_path(markdown_path)
    if not path or not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    preferred_markers = [
        "## Antworten auf Nexis konkrete Fragen",
        "## Konsolidierter Bericht",
        "## Konsolidierte Antwort",
        "## Synthese",
        "## Was Nexi daraus praktisch mitnehmen sollte",
        "## Visuelle Analyse und Synthese",
    ]
    for marker in preferred_markers:
        index = text.find(marker)
        if index != -1:
            text = text[index:]
            break

    if len(text) <= MAX_CHAT_ANALYSIS_CHARS:
        return text
    cut = text[:MAX_CHAT_ANALYSIS_CHARS]
    split_at = max(cut.rfind("\n## "), cut.rfind("\n\n"), cut.rfind(". "))
    if split_at > 900:
        cut = cut[:split_at]
    return cut.strip() + "\n\n[gekürzt - komplette Analyse als Datei im nächsten Telegram-Anhang]"


def write_topic_file(urls: list[str], question: str) -> Path:
    topic_dir = PROJECT_DIR / "telegram_batches"
    topic_dir.mkdir(parents=True, exist_ok=True)
    path = topic_dir / f"telegram-{now_slug()}.md"
    lines = [
        "# Thema: TELEGRAM-SHARE",
        "",
        "Quelle: Telegram Share-Modus",
        "",
    ]
    for index, url in enumerate(urls, start=1):
        lines.extend(
            [
                f"## Eintrag {index}",
                f"URL: {url}",
                "Tags: telegram-share",
                "Fragen:",
                f"- {question}",
                "Status: noch nicht analysiert",
                f"Datenklasse: {DEFAULT_DATA_CLASS}",
                "Analyse: ",
                "Kosten USD: ",
                "Qdrant ID: ",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def parse_json_from_output(output: str) -> dict[str, Any]:
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end <= start:
        raise RuntimeError(output[-2500:])
    return json.loads(output[start : end + 1])


def run_batch_for_urls(urls: list[str], question: str) -> dict[str, Any]:
    estimated = len(urls) * PER_URL_ESTIMATE_EUR
    if estimated > MAX_TELEGRAM_BATCH_COST_EUR:
        raise RuntimeError(
            f"Telegram-Batch gestoppt: Schaetzung {estimated:.2f} EUR > {MAX_TELEGRAM_BATCH_COST_EUR:.2f} EUR"
        )
    topic_file = write_topic_file(urls, question)
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / "run_batch_pipeline.py"),
        "--topic-file",
        str(topic_file),
        "--budget-eur",
        str(MAX_TELEGRAM_BATCH_COST_EUR),
        "--allow-cloud-data-class",
        DEFAULT_DATA_CLASS,
        "--sleep-seconds",
        "1",
    ]
    completed = subprocess.run(command, cwd=PROJECT_DIR, text=True, capture_output=True, timeout=7200)
    output = (completed.stdout or "") + (completed.stderr or "")
    payload = parse_json_from_output(output)
    if completed.returncode != 0 or not payload.get("ok"):
        for error in payload.get("errors", []):
            append_failed_video(
                url=error.get("url", ""),
                topic=payload.get("topic", "TELEGRAM-SHARE"),
                error=error.get("error", "Telegram batch failed"),
                source="telegram_bot",
            )
        raise RuntimeError(payload.get("error") or json.dumps(payload.get("errors", []), ensure_ascii=False))
    return payload


def parse_json_from_completed(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    output = (completed.stdout or "") + (completed.stderr or "")
    payload = parse_json_from_output(output)
    if completed.returncode != 0 or not payload.get("ok"):
        raise RuntimeError(payload.get("error") or output[-2000:])
    return payload


def run_memory_query(question: str) -> dict[str, Any]:
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / "memory_query.py"),
        "--query",
        question,
        "--fast",
    ]
    return parse_json_from_completed(
        subprocess.run(command, cwd=PROJECT_DIR, text=True, capture_output=True, timeout=900)
    )


def run_memory_briefing(kind: str) -> dict[str, Any]:
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / "memory_briefing.py"),
        "--kind",
        kind,
    ]
    return parse_json_from_completed(
        subprocess.run(command, cwd=PROJECT_DIR, text=True, capture_output=True, timeout=600)
    )


def run_memory_links(text: str) -> dict[str, Any]:
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / "memory_link_detector.py"),
        "--text",
        text,
    ]
    return parse_json_from_completed(
        subprocess.run(command, cwd=PROJECT_DIR, text=True, capture_output=True, timeout=240)
    )


def run_sync_master() -> dict[str, Any]:
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / "export_master_context.py"),
        "--archive-old",
    ]
    return parse_json_from_completed(
        subprocess.run(command, cwd=PROJECT_DIR, text=True, capture_output=True, timeout=300)
    )


def run_sync_topic(topic: str) -> dict[str, Any]:
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / "export_topic_context.py"),
        "--topic",
        topic,
    ]
    return parse_json_from_completed(
        subprocess.run(command, cwd=PROJECT_DIR, text=True, capture_output=True, timeout=300)
    )


def render_batch_result(payload: dict[str, Any]) -> str:
    processed = payload.get("processed") or []
    errors = payload.get("errors") or []
    lines = [
        "Telegram-Analyse fertig",
        f"- verarbeitet: {len(processed)}",
        f"- Fehler: {len(errors)}",
        f"- Kosten: ${float(payload.get('actual_cost_usd') or 0):.4f}",
    ]
    for item in processed[:5]:
        lines.append("")
        lines.append(f"Quelle: {item.get('url')}")
        if item.get("analysis"):
            excerpt = excerpt_markdown(item.get("analysis"))
            if excerpt:
                lines.append("")
                lines.append(excerpt)
            lines.append("")
            lines.append(f"Datei: {item.get('analysis')}")
        if item.get("qdrant_id"):
            lines.append(f"Qdrant: {item.get('qdrant_id')}")
    if errors:
        lines.append("")
        lines.append("Fehler:")
        lines.extend(f"- {error.get('url')}: {error.get('error')}" for error in errors[:5])
    return "\n".join(lines)


def send_analysis_documents(payload: dict[str, Any], chat_id: str) -> None:
    processed = payload.get("processed") or []
    for item in processed[:5]:
        path = local_readable_path(item.get("analysis"))
        if not path or not path.exists():
            continue
        caption = "\n".join(
            [
                "Vollständige Analyse",
                f"Quelle: {item.get('url')}",
                f"Kosten: ${float(item.get('cost_usd') or 0):.4f}",
            ]
        )
        send_document(path, caption=caption, chat_id=chat_id)


def save_note(text: str) -> Path:
    notes_dir = PROJECT_DIR / "notes" / "telegram"
    notes_dir.mkdir(parents=True, exist_ok=True)
    path = notes_dir / f"note-{now_slug()}.md"
    tags = auto_tags(text)
    path.write_text(
        "\n".join(
            [
                "# Telegram Notiz",
                "",
                f"Datum: {datetime.now().isoformat(timespec='seconds')}",
                f"Tags: {', '.join(tags) if tags else 'telegram'}",
                "",
                text,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def auto_tags(text: str) -> list[str]:
    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "qwen3:4b",
                "prompt": (
                    "Gib 3 kurze deutsche Tags fuer diese Notiz aus, nur kommagetrennt:\n\n"
                    + text[:1500]
                ),
                "stream": False,
                "options": {"temperature": 0.1},
            },
            timeout=90,
        )
        response.raise_for_status()
        raw = response.json().get("response", "")
        return [slugify(part.strip()).lower() for part in raw.split(",") if part.strip()][:5]
    except Exception:
        return ["telegram"]


def handle_text(text: str, chat_id: str) -> None:
    stripped = text.strip()
    lower = stripped.lower()
    if lower.startswith("/help") or lower.startswith("/start"):
        send_message(HELP_TEXT, chat_id=chat_id)
        return
    if lower.startswith("/status"):
        send_message(render_status(status_payload()), chat_id=chat_id)
        return
    if lower.startswith("/memory"):
        question = re.sub(r"^/memory(@\w+)?", "", stripped, flags=re.I).strip()
        if not question:
            send_message("Bitte sende /memory <deine Frage>.", chat_id=chat_id)
            return
        send_message("Memory-KI denkt lokal. Ich hole Qdrant-Kontext dazu.", chat_id=chat_id)
        try:
            payload = run_memory_query(question)
            lines = [
                "Memory-KI Antwort",
                "",
                payload.get("answer", "")[:3300],
                "",
                "Quellen:",
            ]
            for source in (payload.get("sources") or [])[:5]:
                lines.append(f"- {source.get('collection')} | Score {source.get('score')} | {source.get('title')}")
            send_message("\n".join(lines), chat_id=chat_id)
        except Exception as exc:  # noqa: BLE001
            send_message(f"Memory-KI Fehler:\n{str(exc)[:1800]}", chat_id=chat_id)
        return
    if lower.startswith("/briefing"):
        kind = re.sub(r"^/briefing(@\w+)?", "", stripped, flags=re.I).strip().lower() or "manual"
        if kind not in {"morning", "midday", "evening", "manual"}:
            kind = "manual"
        try:
            payload = run_memory_briefing(kind)
            send_message(f"Memory-KI Briefing\n\n{payload.get('briefing', '')[:3500]}", chat_id=chat_id)
        except Exception as exc:  # noqa: BLE001
            send_message(f"Briefing Fehler:\n{str(exc)[:1800]}", chat_id=chat_id)
        return
    if lower.startswith("/links"):
        query = re.sub(r"^/links(@\w+)?", "", stripped, flags=re.I).strip()
        if not query:
            send_message("Bitte sende /links <Text oder Idee>.", chat_id=chat_id)
            return
        try:
            payload = run_memory_links(query)
            if not payload.get("hits"):
                send_message("Memory-Linkcheck: keine starken Verknuepfungen gefunden.", chat_id=chat_id)
            else:
                lines = ["Memory-Linkcheck:"]
                for hit in payload["hits"][:8]:
                    lines.append(
                        f"- {hit.get('collection')} | Score {hit.get('score')} | {hit.get('title')}"
                    )
                send_message("\n".join(lines), chat_id=chat_id)
        except Exception as exc:  # noqa: BLE001
            send_message(f"Linkcheck Fehler:\n{str(exc)[:1800]}", chat_id=chat_id)
        return
    if lower.startswith("/sync-tg"):
        topic = re.sub(r"^/sync-tg(@\w+)?", "", stripped, flags=re.I).strip()
        if not topic:
            send_message("Bitte sende /sync-tg <Thema>.", chat_id=chat_id)
            return
        try:
            payload = run_sync_topic(topic)
            send_message(payload.get("compact", "")[:3900], chat_id=chat_id)
            send_message(f"Volle Datei:\n{payload.get('markdown_path')}", chat_id=chat_id)
        except Exception as exc:  # noqa: BLE001
            send_message(f"Sync-TG Fehler:\n{str(exc)[:1800]}", chat_id=chat_id)
        return
    if lower.startswith("/sync"):
        topic = re.sub(r"^/sync(@\w+)?", "", stripped, flags=re.I).strip()
        try:
            payload = run_sync_topic(topic) if topic else run_sync_master()
            kind = "Topic-Context" if topic else "Master-Context"
            message = [
                f"{kind} erstellt",
                f"Datei: {payload.get('markdown_path')}",
            ]
            if "snippet_count" in payload:
                message.append(f"Snippets: {payload.get('snippet_count')}")
            for warning in payload.get("warnings") or []:
                message.append(f"Hinweis: {warning}")
            send_message("\n".join(message), chat_id=chat_id)
            path = local_readable_path(payload.get("markdown_path"))
            if path and path.exists():
                send_document(path, caption=kind, chat_id=chat_id)
        except Exception as exc:  # noqa: BLE001
            send_message(f"Sync Fehler:\n{str(exc)[:1800]}", chat_id=chat_id)
        return

    urls = extract_urls(stripped)
    if lower.startswith("/analyze") or lower.startswith("/analyse"):
        if not urls:
            send_message("Bitte sende /analyze <URL> und optional deine Frage.", chat_id=chat_id)
            return
        question = question_from_text(stripped, urls)
    elif urls:
        question = question_from_text(stripped, urls)
    else:
        note = save_note(stripped)
        send_message(f"Notiz lokal gespeichert:\n{note}", chat_id=chat_id)
        return

    estimated = len(urls) * PER_URL_ESTIMATE_EUR
    if estimated > MAX_TELEGRAM_BATCH_COST_EUR:
        send_message(
            f"Gestoppt: {len(urls)} URLs wuerden ca. {estimated:.2f} EUR schaetzen. Bitte am Laptop freigeben.",
            chat_id=chat_id,
        )
        return

    send_message(
        "\n".join(
            [
                f"Starte Analyse fuer {len(urls)} URL(s).",
                f"Schaetzung: ca. {estimated:.2f} EUR.",
                f"Frage/Kontext: {display_question(question)}",
                "Ergebnis kommt hier als Kurzfassung + Markdown-Datei.",
            ]
        ),
        chat_id=chat_id,
    )
    try:
        payload = run_batch_for_urls(urls, question)
        send_message(render_batch_result(payload), chat_id=chat_id)
        send_analysis_documents(payload, chat_id=chat_id)
    except Exception as exc:  # noqa: BLE001
        for url in urls:
            append_failed_video(url=url, topic="TELEGRAM-SHARE", error=str(exc), source="telegram_bot")
        send_message(f"Telegram-Analyse fehlgeschlagen:\n{str(exc)[:1800]}", chat_id=chat_id)


def latest_update_offset() -> int | None:
    updates = get_updates(timeout=1)
    if not updates:
        return None
    return max(int(update["update_id"]) for update in updates) + 1


def main() -> int:
    offset = latest_update_offset()
    print("Telegram bot polling gestartet.")
    while True:
        try:
            updates = get_updates(offset=offset, timeout=25)
            for update in updates:
                offset = int(update["update_id"]) + 1
                message = update.get("message") or {}
                chat = message.get("chat") or {}
                chat_id = str(chat.get("id") or "")
                text = message.get("text") or message.get("caption") or ""
                if not chat_id or not text:
                    continue
                if chat.get("type") != "private":
                    continue
                if not is_authorized(chat_id):
                    continue
                handle_text(text, chat_id)
        except KeyboardInterrupt:
            return 0
        except Exception as exc:  # noqa: BLE001
            print(f"Telegram bot error: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    raise SystemExit(main())
