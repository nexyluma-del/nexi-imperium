#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from memory_common import (
    FAST_MODEL,
    MEMORY_MODEL,
    KI_PUSH_DIR,
    PROJECT_DIR,
    memory_system_prompt,
    ollama_generate,
    qdrant_points_count,
    recent_file_lines,
    read_text,
)
from telegram_common import send_message


OUTPUT_DIR = PROJECT_DIR / "analysis" / "memory"
SOFINELLO_STATUS = PROJECT_DIR / "logs" / "sofinello" / "sofinello-batch-b-status.json"
FAILED_FILE = PROJECT_DIR / "failed-videos.md"


KIND_LABELS = {
    "morning": "Morgenbriefing 07:00",
    "midday": "Mittagscheck 13:00",
    "evening": "Tagesabschluss 19:00",
    "manual": "Memory-Check",
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def failed_count() -> int:
    if not FAILED_FILE.exists():
        return 0
    return sum(1 for line in FAILED_FILE.read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("## "))


def system_snapshot() -> dict[str, Any]:
    sofinello = load_json(SOFINELLO_STATUS)
    return {
        "time": datetime.now().isoformat(timespec="seconds"),
        "qdrant": {
            "video_knowledge": qdrant_points_count("video_knowledge"),
            "sofinello_knowledge": qdrant_points_count("sofinello_knowledge"),
            "memory_voice": qdrant_points_count("memory_voice"),
        },
        "sofinello_batch": {
            "processed": sofinello.get("processed_count"),
            "errors": sofinello.get("error_count"),
            "cost_usd": sofinello.get("actual_cost_usd"),
            "updated_at": sofinello.get("updated_at"),
            "stopped_reason": sofinello.get("stopped_reason") or "",
        },
        "failed_videos": failed_count(),
        "recent_analysis": recent_file_lines(PROJECT_DIR / "analysis", "*.md", hours=24, limit=8),
        "recent_voice": recent_file_lines(Path("/mnt/c/Users/nexil/Documents/Obsidian-Imperium/inbox"), "*.md", hours=24, limit=5),
        "ki_push_recent": recent_file_lines(KI_PUSH_DIR, "*", hours=168, limit=6),
    }


def build_prompt(kind: str, snapshot: dict[str, Any]) -> str:
    return f"""
{memory_system_prompt()}

AUFGABE:
Erstelle ein {KIND_LABELS.get(kind, kind)} fuer Nexi.

SYSTEM-SNAPSHOT:
{json.dumps(snapshot, ensure_ascii=False, indent=2)}

FORMAT:
- Kurz, knackig, 3-5 Stichpunkte.
- Eine konkrete Entscheidung/Naechster Schritt, falls sinnvoll.
- Wenn Sofinello wegen Quota steht: klar sagen, aber nicht dramatisieren.
- Nur fertige Antwort, keine Denknotizen.
- Keine Emojis.
- Kein Gelaber. Co-Founder-Ton.
"""


def fallback_briefing(snapshot: dict[str, Any]) -> str:
    sofinello = snapshot.get("sofinello_batch") or {}
    qdrant = snapshot.get("qdrant") or {}
    processed = sofinello.get("processed")
    errors = sofinello.get("errors")
    cost = sofinello.get("cost_usd")
    stopped_reason = sofinello.get("stopped_reason") or ""
    voice_count = qdrant.get("memory_voice")
    failed = snapshot.get("failed_videos")
    reason_note = f" Grund: {stopped_reason}." if stopped_reason else ""
    return "\n".join(
        [
            f"- Nexi, Memory steht lokal: video_knowledge={qdrant.get('video_knowledge')}, "
            f"sofinello_knowledge={qdrant.get('sofinello_knowledge')}, memory_voice={voice_count}.",
            f"- Sofinello-Batch: {processed} verarbeitet, {errors} Fehler, Kosten bisher ${float(cost or 0):.4f}.{reason_note}",
            f"- Failed-Liste: {failed} Eintraege. Das ist der erste Punkt, den wir nach Quota/Resume sauber pruefen.",
            "- KI-PUSH ist eingebunden: neue Tutorials/Tipps werden woechentlich fuer Strategie-Updates gescannt.",
            "- Naechster Schritt: Sofinello erst weiterlaufen lassen, danach Fehlerliste und Memory-Verknuepfungen nachziehen.",
        ]
    )


def is_usable_briefing(answer: str) -> bool:
    clean = answer.strip()
    if len(clean) < 220:
        return False
    bullet_lines = [line for line in clean.splitlines() if line.lstrip().startswith(("-", "*"))]
    if len(bullet_lines) < 3:
        return False
    lowered = clean.lower()
    bad_markers = ("let me", "i need to", "i'll", "the user wants", "system-snapshot", "denkprozess")
    return not any(marker in lowered for marker in bad_markers)


def create_briefing(kind: str, model: str) -> dict[str, Any]:
    snapshot = system_snapshot()
    answer = ollama_generate(build_prompt(kind, snapshot), model=model, timeout=600 if model == MEMORY_MODEL else 240)
    if not is_usable_briefing(answer):
        answer = fallback_briefing(snapshot)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    markdown_path = OUTPUT_DIR / f"memory-briefing-{kind}-{stamp}.md"
    json_path = OUTPUT_DIR / f"memory-briefing-{kind}-{stamp}.json"
    markdown = "\n".join(
        [
            f"# {KIND_LABELS.get(kind, kind)} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            answer,
            "",
            "## Snapshot",
            "```json",
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    markdown_path.write_text(markdown, encoding="utf-8")
    payload = {
        "ok": True,
        "kind": kind,
        "model": model,
        "briefing": answer,
        "snapshot": snapshot,
        "markdown_path": str(markdown_path),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["json_path"] = str(json_path)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate local Memory-KI briefing.")
    parser.add_argument("--kind", choices=sorted(KIND_LABELS), default="manual")
    parser.add_argument("--model", default=FAST_MODEL)
    parser.add_argument("--deep", action="store_true", help=f"Nutze {MEMORY_MODEL}.")
    parser.add_argument("--send-telegram", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model = MEMORY_MODEL if args.deep else args.model
    payload = create_briefing(args.kind, model=model)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.send_telegram:
        send_message(f"{KIND_LABELS[payload['kind']]}\n\n{payload['briefing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
