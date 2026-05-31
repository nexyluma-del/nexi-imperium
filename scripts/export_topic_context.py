#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from memory_common import DESKTOP_KI, payload_source, payload_text, payload_title, search_all_collections
from telegram_common import send_message


SYNC_DIR = DESKTOP_KI / "sync"
DEFAULT_ALLOWED_DATA_CLASSES = {"D0", "D1", "D2"}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    return re.sub(r"[^a-z0-9._-]+", "-", value).strip("-._")[:80] or "thema"


def trim_words(text: str, max_words: int = 200) -> str:
    words = re.split(r"\s+", text.strip())
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip() + " ..."


def topic_terms(topic: str) -> list[str]:
    return [term for term in re.findall(r"[a-zA-ZäöüÄÖÜß0-9]{3,}", topic.lower()) if term]


def allowed_data_class(value: Any, include_private: bool) -> bool:
    data_class = str(value or "").strip().upper()
    if data_class in DEFAULT_ALLOWED_DATA_CLASSES:
        return True
    if include_private and data_class == "D3":
        return True
    return False


def collect_topic_snippets(topic: str, limit: int, include_private: bool) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    raw_points = search_all_collections(topic, limit_per_collection=max(limit, 8))
    snippets: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    terms = topic_terms(topic)
    skipped_private = 0
    skipped_unknown = 0

    for point in raw_points:
        payload = point.get("payload") or {}
        data_class = str(payload.get("data_class") or "").strip().upper()
        if not data_class:
            skipped_unknown += 1
            continue
        if data_class == "D4":
            skipped_private += 1
            continue
        if not allowed_data_class(data_class, include_private):
            skipped_private += 1
            continue

        text = payload_text(payload)
        title = payload_title(payload)
        source = payload_source(payload)
        haystack = f"{title}\n{source}\n{text[:2500]}".lower()
        overlap = sum(1 for term in terms if term in haystack)
        collection = str(point.get("collection") or "")
        boost = min(0.25, overlap * 0.05)
        if any(term in {"sofinello", "sebi"} for term in terms) and collection == "sofinello_knowledge":
            boost += 0.15
        candidates.append(
            {
                "collection": collection,
                "score": round(float(point.get("score") or 0.0), 4),
                "rank_score": round(float(point.get("score") or 0.0) + boost, 4),
                "title": title,
                "source": source,
                "data_class": data_class,
                "excerpt": trim_words(text, max_words=200),
            }
        )

    snippets = sorted(candidates, key=lambda item: item["rank_score"], reverse=True)[:limit]

    if skipped_private:
        warnings.append(f"{skipped_private} Treffer wegen D3/D4-Datenklasse uebersprungen.")
    if skipped_unknown:
        warnings.append(f"{skipped_unknown} Treffer ohne Datenklasse uebersprungen.")
    return snippets, warnings


def render_topic_context(topic: str, snippets: list[dict[str, Any]], warnings: list[str]) -> str:
    lines = [
        f"# TOPIC-CONTEXT: {topic}",
        f"Stand: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Sicherheit",
        "",
        "- Standardfilter: nur D0-D2.",
        "- D3/D4 sind nicht enthalten, ausser D3 wurde explizit per Flag erlaubt.",
        "- D4 wird in dieser Version nie unverschluesselt exportiert.",
        "",
    ]
    if warnings:
        lines.extend(["## Filter-Hinweise", "", *[f"- {warning}" for warning in warnings], ""])

    lines.extend(["## Relevante Wissens-Snippets", ""])
    if not snippets:
        lines.append("Keine passenden D0-D2-Snippets gefunden.")
    for index, snippet in enumerate(snippets, start=1):
        lines.extend(
            [
                f"### Snippet {index}",
                "",
                f"Collection: {snippet['collection']}",
                f"Score: {snippet['score']}",
                f"Rank-Score: {snippet['rank_score']}",
                f"Datenklasse: {snippet['data_class']}",
                f"Titel: {snippet['title']}",
                f"Quelle: {snippet['source']}",
                "",
                snippet["excerpt"],
                "",
            ]
        )
    lines.extend(
        [
            "## Anleitung an die KI",
            "",
            "Nutze diese Snippets als Kontext aus Nexis lokaler Wissenssammlung. "
            "Wenn etwas nicht belegt ist, sage es klar und frage Nexi nach weiterem Topic-Context.",
            "",
        ]
    )
    return "\n".join(lines)


def export_topic_context(topic: str, limit: int = 20, include_private: bool = False) -> dict[str, Any]:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    snippets, warnings = collect_topic_snippets(topic, limit=limit, include_private=include_private)
    markdown = render_topic_context(topic, snippets, warnings)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = SYNC_DIR / f"topic-{slugify(topic)}-{stamp}.md"
    path.write_text(markdown, encoding="utf-8")
    return {
        "ok": True,
        "topic": topic,
        "markdown_path": str(path),
        "snippet_count": len(snippets),
        "warnings": warnings,
        "compact": compact_for_telegram(markdown),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def compact_for_telegram(markdown: str, max_chars: int = 3600) -> str:
    text = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    split_at = max(cut.rfind("\n### "), cut.rfind("\n\n"))
    if split_at > 1200:
        cut = cut[:split_at]
    return cut.rstrip() + "\n\n[gekuerzt - volle Datei liegt im Sync-Ordner]"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export topic context for external KI sessions.")
    parser.add_argument("topic", nargs="*", help="Thema fuer den Export")
    parser.add_argument("--topic", dest="topic_option", help="Thema fuer den Export")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--include-private", action="store_true", help="Erlaubt D3, D4 bleibt gesperrt.")
    parser.add_argument("--send-telegram", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    topic = (args.topic_option or " ".join(args.topic)).strip()
    if not topic:
        raise SystemExit("Bitte Thema angeben.")
    payload = export_topic_context(topic, limit=args.limit, include_private=args.include_private)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.send_telegram:
        send_message(f"Topic-Context erstellt: {payload['markdown_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
