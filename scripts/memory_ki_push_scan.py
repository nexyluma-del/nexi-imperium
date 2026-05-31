#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from memory_common import FAST_MODEL, KI_PUSH_DIR, PROJECT_DIR, ollama_generate, read_text
from telegram_common import send_message


OUTPUT_DIR = PROJECT_DIR / "analysis" / "memory"
SUPPORTED_TEXT_EXTENSIONS = {".md", ".txt", ".json", ".csv", ".log"}


def scan_files(limit: int = 20) -> list[dict[str, Any]]:
    if not KI_PUSH_DIR.exists():
        KI_PUSH_DIR.mkdir(parents=True, exist_ok=True)
    files = [path for path in KI_PUSH_DIR.rglob("*") if path.is_file()]
    files = sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)[:limit]
    result: list[dict[str, Any]] = []
    for path in files:
        text = read_text(path, limit=6000) if path.suffix.lower() in SUPPORTED_TEXT_EXTENSIONS else ""
        result.append(
            {
                "path": str(path),
                "name": path.name,
                "suffix": path.suffix.lower(),
                "size": path.stat().st_size,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                "text_preview": text,
            }
        )
    return result


def build_prompt(files: list[dict[str, Any]]) -> str:
    compact = [
        {
            "name": item["name"],
            "path": item["path"],
            "modified": item["modified"],
            "text_preview": item["text_preview"][:2500],
        }
        for item in files
    ]
    return f"""
Du bist Memory-KI. Nexi sammelt im Ordner KI-PUSH Tutorials und Best Practices fuer KI-Arbeit.
Analysiere diese lokalen Dateien und extrahiere:
- 3-7 wichtigste Erkenntnisse
- konkrete Auswirkungen auf unser KI-Imperium
- welche Aufgaben/Prompts/Policies angepasst werden sollten
- was noch manuell gelesen werden muss

DATEIEN:
{json.dumps(compact, ensure_ascii=False, indent=2)}

Antworte kurz, direkt und umsetzungsorientiert auf Deutsch.
"""


def create_report(limit: int, model: str) -> dict[str, Any]:
    files = scan_files(limit=limit)
    if not files:
        summary = "KI-PUSH ist leer. Noch keine neuen Tutorials oder Best Practices."
    else:
        summary = ollama_generate(build_prompt(files), model=model, timeout=360)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    markdown_path = OUTPUT_DIR / f"ki-push-scan-{stamp}.md"
    payload = {
        "ok": True,
        "folder": str(KI_PUSH_DIR),
        "file_count": len(files),
        "files": files,
        "summary": summary,
        "markdown_path": str(markdown_path),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    markdown = "\n".join(
        [
            f"# KI-PUSH Wochen-Scan - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            summary,
            "",
            "## Dateien",
            *[f"- {item['name']} | {item['modified']} | {item['path']}" for item in files],
            "",
        ]
    )
    markdown_path.write_text(markdown, encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan Desktop/KI/KI-PUSH for local AI best-practice notes.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--model", default=FAST_MODEL)
    parser.add_argument("--send-telegram", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = create_report(args.limit, args.model)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.send_telegram:
        send_message(f"KI-PUSH Wochen-Scan\n\n{payload['summary'][:3400]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
