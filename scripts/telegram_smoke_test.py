#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from telegram_bot import run_batch_for_urls


PROJECT_DIR = Path(__file__).resolve().parents[1]
REPORT_JSON = PROJECT_DIR / "docs" / "telegram-smoke-test.json"
REPORT_MD = PROJECT_DIR / "docs" / "telegram-smoke-test.md"


def wsl_to_windows(path: str | Path | None) -> str | None:
    if path is None:
        return None
    value = str(path)
    if value.startswith("/mnt/c/"):
        return "C:\\" + value[len("/mnt/c/") :].replace("/", "\\")
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Telegram Smoke Test",
        "",
        f"Stand: {payload['finished_at']}",
        f"Status: `{payload['status']}`",
        f"URL: `{payload['url']}`",
        f"Frage/Kontext: {payload['question']}",
        "",
        "## Ergebnis",
        "",
        f"- Verarbeitet: `{len(payload.get('processed') or [])}`",
        f"- Fehler: `{len(payload.get('errors') or [])}`",
        f"- Kosten USD: `{payload.get('actual_cost_usd')}`",
        "",
    ]
    for item in payload.get("processed") or []:
        lines.extend(
            [
                "### Analyse",
                "",
                f"- Analyse: `{item.get('analysis')}`",
                f"- Video-Ordner: `{item.get('video_dir')}`",
                f"- Zusammenfassung: `{item.get('summary_markdown')}`",
                f"- Word: `{item.get('word_report')}`",
                f"- Qdrant: `{item.get('qdrant_id')}`",
                "",
            ]
        )
    if payload.get("errors"):
        lines.extend(["## Fehler", ""])
        for error in payload["errors"]:
            lines.append(f"- {error}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the Telegram share workflow without needing a live Telegram update.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--question", default="Smoke-Test nach Tabula Rasa: Worum geht es hier und passt die Analyse zur URL?")
    args = parser.parse_args()

    payload: dict[str, Any] = {
        "status": "running",
        "url": args.url,
        "question": args.question,
        "started_at": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        result = run_batch_for_urls([args.url], args.question)
        payload.update(result)
        payload["status"] = "ok"
    except Exception as exc:  # noqa: BLE001
        payload["status"] = "error"
        payload["error"] = str(exc)
    finally:
        payload["finished_at"] = datetime.now().isoformat(timespec="seconds")
        write_json(REPORT_JSON, payload)
        REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")
        print(json.dumps({"ok": payload["status"] == "ok", "status": payload["status"], "report": str(REPORT_MD), "json": str(REPORT_JSON), "cost": payload.get("actual_cost_usd"), "error": payload.get("error")}, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
