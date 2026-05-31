#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from export_topic_context import collect_topic_snippets, render_topic_context
from memory_common import DESKTOP_KI, DNA_FILE, KI_PUSH_DIR, read_text
from telegram_common import send_message
from telegram_status import status_payload


SYNC_DIR = DESKTOP_KI / "sync"
ARCHIVE_DIR = SYNC_DIR / "archive"
V3_DIR = DESKTOP_KI / "v3"
MASTER_PROMPT = V3_DIR / "MASTER-PROMPT-v3.md"
CHIEFS_DIR = V3_DIR / "chiefs"
POLICIES_DIR = V3_DIR / "policies"


def fenced_file(path: Path, title: str, limit: int | None = None) -> str:
    text = read_text(path, limit=limit)
    if not text:
        text = f"[Datei nicht gefunden oder leer: {path}]"
    return "\n".join([f"## {title}", "", f"Quelle: `{path}`", "", text.strip(), ""])


def render_file_group(title: str, directory: Path, pattern: str = "*.md", limit_per_file: int | None = None) -> str:
    lines = [f"## {title}", ""]
    if not directory.exists():
        lines.append(f"[Ordner nicht gefunden: {directory}]")
        lines.append("")
        return "\n".join(lines)
    files = sorted(path for path in directory.glob(pattern) if path.is_file())
    if not files:
        lines.append("Keine Dateien gefunden.")
        lines.append("")
        return "\n".join(lines)
    for path in files:
        lines.extend([f"### {path.name}", "", f"Quelle: `{path}`", "", read_text(path, limit=limit_per_file).strip(), ""])
    return "\n".join(lines)


def pipeline_status_block() -> str:
    try:
        payload = status_payload()
    except Exception as exc:  # noqa: BLE001
        payload = {"error": str(exc)}
    return "\n".join(
        [
            "## Aktueller Pipeline-Stand",
            "",
            "```json",
            json.dumps(payload, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )


def topic_block(topic: str | None, limit: int, include_private: bool) -> str:
    if not topic:
        return ""
    snippets, warnings = collect_topic_snippets(topic, limit=limit, include_private=include_private)
    return render_topic_context(topic, snippets, warnings)


def archive_old_exports(days: int = 30) -> list[str]:
    if not SYNC_DIR.exists():
        return []
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now() - timedelta(days=days)
    moved: list[str] = []
    for path in SYNC_DIR.glob("*.md"):
        if not path.is_file():
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        if mtime >= cutoff:
            continue
        target = ARCHIVE_DIR / path.name
        shutil.move(str(path), str(target))
        moved.append(str(target))
    return moved


def export_master_context(topic: str | None = None, limit: int = 12, include_private: bool = False, archive_old: bool = False) -> dict[str, Any]:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    archived = archive_old_exports() if archive_old else []
    topic_context = topic_block(topic, limit=limit, include_private=include_private)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = SYNC_DIR / f"master-context-{stamp}.md"
    markdown = "\n".join(
        [
            "# MASTER-CONTEXT FUER NEXIS KI-IMPERIUM",
            f"Stand: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Sicherheitsrahmen",
            "",
            "- Dieses Paket ist fuer Nexi zum manuellen Einfuegen in Claude, ChatGPT, Gemini oder Codex.",
            "- Standard: keine automatischen externen API-Pushes.",
            "- Qdrant-Topic-Snippets sind standardmaessig auf D0-D2 gefiltert.",
            "- D4 wird in dieser Version nie unverschluesselt exportiert.",
            "",
            "## Wer Nexi ist",
            "",
            "Nexi baut ein KI-Imperium mit lokalen Agenten, Video-/Bildanalyse, Sofinello-Heilungswissen, "
            "Business-Automation, Film-/Musik-KI und einer Memory-KI als zweitem Gehirn. "
            "Prioritaet: erst Fundament, dann Cashflow, dann skalierende Agenten-Infrastruktur.",
            "",
            fenced_file(DNA_FILE, "Memory-KI-DNA"),
            fenced_file(MASTER_PROMPT, "Master-Prompt v3"),
            render_file_group("Aktive Chiefs + Rollen", CHIEFS_DIR),
            render_file_group("Policies, Datenklassen und Risiko-Regeln", POLICIES_DIR),
            pipeline_status_block(),
            "## KI-PUSH",
            "",
            f"KI-PUSH-Ordner: `{KI_PUSH_DIR}`",
            "Woechentlicher Scan ist fuer neue KI-Best-Practices vorgesehen.",
            "",
            topic_context,
            "## Anleitung an dich (KI die das liest)",
            "",
            "Du arbeitest in Nexis Imperium-Kontext. Verhalte dich gemaess der Memory-KI-DNA: "
            "ehrlich, direkt, loyal, ohne Ja-Sagen. Wenn dir spezifisches Wissen fehlt, frage Nexi: "
            "\"Soll ich dir Topic-Context zu X holen?\" Er kann dann `/sync X` oder `/sync-tg X` nutzen.",
            "",
        ]
    )
    path.write_text(markdown, encoding="utf-8")
    return {
        "ok": True,
        "markdown_path": str(path),
        "topic": topic or "",
        "archived": archived,
        "include_private": include_private,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export master context for external KI sessions.")
    parser.add_argument("--topic", help="Optionales Thema fuer zusaetzliche Qdrant-Snippets.")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--include-private", action="store_true", help="Erlaubt D3 Topic-Snippets, D4 bleibt gesperrt.")
    parser.add_argument("--archive-old", action="store_true", help="Archiviert Sync-Markdowns aelter als 30 Tage.")
    parser.add_argument("--send-telegram", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = export_master_context(
        topic=args.topic,
        limit=args.limit,
        include_private=args.include_private,
        archive_old=args.archive_old,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.send_telegram:
        send_message(f"Master-Context erstellt: {payload['markdown_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
