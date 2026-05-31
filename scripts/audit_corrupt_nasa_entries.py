#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


QDRANT_URL = "http://127.0.0.1:6333"
PROJECT_DIR = Path(r"C:\AI\projects\09-video-analyse")
REPORT = PROJECT_DIR / "failed-or-corrupt.md"
COLLECTIONS = ["video_knowledge", "open-webui_knowledge", "sofinello_knowledge", "memory_voice"]
TERMS = [
    "NASA",
    "LADEE",
    "LLCD",
    "LLGT",
    "Minotaur",
    "Lunar Laser",
    "Lasercomm",
    "moon dust",
    "lunar atmosphere",
    "White Sands",
    "nasa.gov",
]
TERM_PATTERNS = {
    term: re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])",
        re.IGNORECASE,
    )
    for term in TERMS
}


def normalize_path(value: str | None) -> Path | None:
    if not value:
        return None
    match = re.match(r"^/mnt/([a-zA-Z])/(.*)$", value)
    if match:
        rest = match.group(2).replace("/", "\\")
        return Path(f"{match.group(1).upper()}:\\{rest}")
    return Path(value)


def read_file_excerpt(path_value: str | None, limit: int = 12000) -> str:
    path = normalize_path(path_value)
    if not path or not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def point_text(point: dict[str, Any]) -> str:
    payload = point.get("payload") or {}
    parts = [json.dumps(payload, ensure_ascii=False)]
    for key in ("analysis_markdown", "raw_analysis_markdown", "transcript_txt"):
        parts.append(read_file_excerpt(payload.get(key)))
    return "\n\n".join(parts)


def matches(text: str) -> list[str]:
    found = []
    for term in TERMS:
        if TERM_PATTERNS[term].search(text):
            found.append(term)
    return found


def scroll_collection(collection: str) -> list[dict[str, Any]]:
    points = []
    offset = None
    while True:
        body: dict[str, Any] = {"limit": 100, "with_payload": True, "with_vectors": False}
        if offset is not None:
            body["offset"] = offset
        response = requests.post(f"{QDRANT_URL}/collections/{collection}/points/scroll", json=body, timeout=60)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        result = response.json().get("result") or {}
        points.extend(result.get("points") or [])
        offset = result.get("next_page_offset")
        if offset is None:
            return points


def classify(payload: dict[str, Any], found_terms: list[str]) -> str:
    source = " ".join(
        str(payload.get(key) or "") for key in ("url", "source_path", "source_info", "topic", "category", "slug")
    ).lower()
    expected_nasa = "nasa" in source or "d0 nasa" in source
    if expected_nasa:
        return "expected-test-or-nasa-source"
    if found_terms:
        return "suspect-cross-contamination"
    return "clean"


def audit() -> dict[str, Any]:
    entries = []
    counts = {}
    for collection in COLLECTIONS:
        points = scroll_collection(collection)
        counts[collection] = len(points)
        for point in points:
            payload = point.get("payload") or {}
            found = matches(point_text(point))
            if not found:
                continue
            entries.append(
                {
                    "collection": collection,
                    "id": point.get("id"),
                    "classification": classify(payload, found),
                    "terms": found,
                    "url": payload.get("url"),
                    "source_path": payload.get("source_path"),
                    "topic": payload.get("topic") or payload.get("category"),
                    "analysis_markdown": payload.get("analysis_markdown"),
                    "transcript_txt": payload.get("transcript_txt"),
                    "slug": payload.get("slug"),
                    "tainted": bool(payload.get("tainted")),
                    "taint_reason": payload.get("taint_reason"),
                }
            )
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "terms": TERMS,
        "collection_counts": counts,
        "match_count": len(entries),
        "suspect_count": sum(1 for item in entries if item["classification"] == "suspect-cross-contamination"),
        "entries": entries,
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Failed or Corrupt Entries",
        "",
        f"Stand: {result['generated_at']}",
        "",
        "## Suchbegriffe",
        "",
        ", ".join(f"`{term}`" for term in result["terms"]),
        "",
        "## Zusammenfassung",
        "",
        f"- Treffer gesamt: {result['match_count']}",
        f"- Verdacht auf Cross-Contamination: {result['suspect_count']}",
        "",
        "## Collection-Groessen",
        "",
    ]
    for collection, count in result["collection_counts"].items():
        lines.append(f"- `{collection}`: {count}")
    lines.extend(["", "## Treffer", ""])
    for item in result["entries"]:
        lines.extend(
            [
                f"### {item['classification']} - {item['collection']} - {item['id']}",
                "",
                f"- Begriffe: {', '.join(item['terms'])}",
                f"- URL: `{item.get('url')}`",
                f"- Source Path: `{item.get('source_path')}`",
                f"- Thema: `{item.get('topic')}`",
                f"- Slug: `{item.get('slug')}`",
                f"- Analyse: `{item.get('analysis_markdown')}`",
                f"- Transkript: `{item.get('transcript_txt')}`",
                f"- Tainted: `{item.get('tainted')}`",
                f"- Taint Reason: `{item.get('taint_reason')}`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    result = audit()
    REPORT.write_text(render_report(result), encoding="utf-8")
    json_path = REPORT.with_suffix(".json")
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(REPORT), "json": str(json_path), **{k: result[k] for k in ("match_count", "suspect_count")}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
