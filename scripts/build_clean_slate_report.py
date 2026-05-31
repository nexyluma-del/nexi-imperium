#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import requests


PROJECT_DIR = Path(__file__).resolve().parents[1]


def scroll_video_points() -> list[dict]:
    points: list[dict] = []
    offset = None
    while True:
        body = {"limit": 100, "with_payload": True, "with_vectors": False}
        if offset is not None:
            body["offset"] = offset
        response = requests.post(
            "http://127.0.0.1:6333/collections/video_knowledge/points/scroll",
            json=body,
            timeout=30,
        )
        if response.status_code == 404:
            return points
        response.raise_for_status()
        result = response.json().get("result") or {}
        points.extend(result.get("points") or [])
        offset = result.get("next_page_offset")
        if offset is None:
            return points


def short_answer(summary_path: Path) -> str:
    if not summary_path.exists():
        return ""
    text = summary_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"## Kurzantwort\s+(.*?)(?:\n## |\Z)", text, re.S)
    excerpt = match.group(1).strip() if match else text.strip()
    return excerpt[:900]


def main() -> int:
    manifests = sorted(
        (PROJECT_DIR / "videos").glob("*/*/pipeline-manifest.json"),
        key=lambda path: path.stat().st_mtime,
    )
    points = scroll_video_points()
    by_analysis = {
        str((point.get("payload") or {}).get("analysis_markdown")): point
        for point in points
    }

    processed = []
    spent = 0.0
    for manifest in manifests:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        files = data.get("files") or {}
        analysis = str(files.get("analysis_markdown"))
        point = by_analysis.get(analysis)
        cost = float((data.get("cost") or {}).get("estimated_actual_usd") or 0.0)
        spent += cost
        processed.append(
            {
                "topic": data.get("topic"),
                "video_id": data.get("video_id"),
                "source": data.get("url"),
                "video_dir": data.get("video_dir"),
                "summary_markdown": files.get("summary_markdown"),
                "analysis_markdown": analysis,
                "word_report": files.get("word_report"),
                "qdrant_id": point.get("id") if point else None,
                "cost_usd": cost,
                "video_sha256": (data.get("provenance") or {}).get("video_sha256"),
                "excerpt": short_answer(Path(files.get("summary_markdown") or "")),
            }
        )

    result = {
        "ok": len(processed) == 10 and len(points) == 10,
        "processed_count": len(processed),
        "qdrant_points": len(points),
        "cost_usd": round(spent, 6),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "processed": processed,
    }

    lines = [
        "# Clean-Slate Test 10 Complete",
        "",
        f"Stand: {result['generated_at']}",
        "",
        f"- Erfolgreich: {len(processed)}/10",
        f"- Qdrant video_knowledge: {len(points)}",
        f"- Kosten USD: {result['cost_usd']:.6f}",
        "",
        "## Outputs",
        "",
    ]
    for index, item in enumerate(processed, start=1):
        lines.extend(
            [
                f"### {index}. {item['topic']} - {item['video_id']}",
                "",
                f"- Quelle: `{item['source']}`",
                f"- Video-Ordner: `{item['video_dir']}`",
                f"- Zusammenfassung: `{item['summary_markdown']}`",
                f"- Gemini-Analyse: `{item['analysis_markdown']}`",
                f"- Word-Bericht: `{item['word_report']}`",
                f"- Qdrant ID: `{item['qdrant_id']}`",
                f"- Kosten USD: `{item['cost_usd']:.6f}`",
                "",
                "Kurzantwort:",
                "",
                item["excerpt"],
                "",
            ]
        )

    out_json = PROJECT_DIR / "docs" / "clean-slate-test-10-complete.json"
    out_md = PROJECT_DIR / "docs" / "clean-slate-test-10-complete.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "processed": len(processed), "qdrant_points": len(points), "cost_usd": result["cost_usd"], "report": str(out_md)}, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
