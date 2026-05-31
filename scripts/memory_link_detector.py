#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from memory_common import build_context, search_all_collections
from telegram_common import send_message


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "analysis" / "memory"


def detect_links(text: str, threshold: float, limit: int) -> dict[str, Any]:
    points = search_all_collections(text, limit_per_collection=limit)
    context, sources = build_context(points, max_chars=7000)
    hits = [source for source in sources if float(source.get("score") or 0.0) >= threshold]
    return {
        "ok": True,
        "text": text,
        "threshold": threshold,
        "hit_count": len(hits),
        "hits": hits,
        "context_preview": context[:2000],
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def render(payload: dict[str, Any]) -> str:
    if not payload["hits"]:
        return "Memory-Linkcheck: keine starken Verknuepfungen gefunden."
    lines = [
        "Memory-Linkcheck: starke Verknuepfungen gefunden",
        f"Schwelle: {payload['threshold']}",
        "",
    ]
    for hit in payload["hits"][:8]:
        lines.append(
            f"- {hit['collection']} | Score {hit['score']} | {hit['title']} | {hit['source']}"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect semantic links in Nexis local knowledge.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--threshold", type=float, default=0.72)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--send-telegram", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = detect_links(args.text, args.threshold, args.limit)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"memory-linkcheck-{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["json_path"] = str(path)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.send_telegram and payload["hits"]:
        send_message(render(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
