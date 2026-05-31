#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from qdrant_video_knowledge import upsert_video_knowledge


PROJECT_DIR = Path(__file__).resolve().parents[1]


def parse_json_from_output(output: str) -> dict[str, Any]:
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end <= start:
        raise RuntimeError(f"Kein JSON im Output:\n{output[-3000:]}")
    return json.loads(output[start : end + 1])


def run_entry(entry: dict[str, Any], index: int) -> dict[str, Any]:
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / "run_video_pipeline.py"),
        "--data-class",
        "D2",
        "--topic",
        entry["topic"],
        "--question",
        entry["question"],
        "--max-cost-eur",
        "0.50",
        "--slug",
        f"CLEAN-SLATE-TEST-{index:02d}",
    ]
    if entry.get("url"):
        command.extend(["--url", entry["url"]])
    else:
        command.extend(["--video-file", entry["video_file"]])

    completed = subprocess.run(command, cwd=PROJECT_DIR, text=True, capture_output=True, timeout=3600)
    output = (completed.stdout or "") + (completed.stderr or "")
    payload = parse_json_from_output(output)
    if completed.returncode != 0 or not payload.get("ok"):
        raise RuntimeError(payload.get("error") or output[-3000:])

    qdrant = upsert_video_knowledge(
        url=payload["url"],
        topic=entry["topic"],
        data_class="D2",
        questions=[entry["question"]],
        analysis_markdown=Path(payload["files"]["analysis_markdown"]),
        transcript_txt=Path(payload["files"]["transcript_txt"]),
        cost_usd=float(payload.get("cost", {}).get("estimated_actual_usd") or 0.0),
        slug=payload["slug"],
        provenance={
            **(payload.get("provenance") or {}),
            "video_dir": payload.get("video_dir"),
            "source_kind": payload.get("source_kind"),
        },
    )
    payload["qdrant"] = qdrant
    return payload


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Clean-Slate Test 10",
        "",
        f"Stand: {result['finished_at']}",
        "",
        f"- Erfolgreich: {len(result['processed'])}",
        f"- Fehler: {len(result['errors'])}",
        f"- Kosten USD: {result['actual_cost_usd']:.6f}",
        "",
        "## Outputs",
        "",
    ]
    for item in result["processed"]:
        files = item["files"]
        lines.extend(
            [
                f"### {item['topic']} - {item['video_id']}",
                "",
                f"- Quelle: `{item['url']}`",
                f"- Video-Ordner: `{item['video_dir']}`",
                f"- Zusammenfassung: `{files.get('summary_markdown')}`",
                f"- Gemini-Analyse: `{files.get('analysis_markdown')}`",
                f"- Word-Bericht: `{files.get('word_report')}`",
                f"- Qdrant ID: `{item.get('qdrant', {}).get('point_id')}`",
                f"- Kosten USD: `{item.get('cost', {}).get('estimated_actual_usd')}`",
                "",
            ]
        )
    if result["errors"]:
        lines.extend(["## Fehler", ""])
        for error in result["errors"]:
            lines.extend(
                [
                    f"- {error['topic']} | {error.get('source')}: {error['error']}",
                ]
            )
    return "\n".join(lines)


def main() -> int:
    manifest = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_DIR / "work" / "clean-slate-test-10.json"
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    processed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    spent = 0.0

    for index, entry in enumerate(entries, start=1):
        try:
            payload = run_entry(entry, index)
            payload["topic"] = entry["topic"]
            processed.append(payload)
            spent += float(payload.get("cost", {}).get("estimated_actual_usd") or 0.0)
            print(json.dumps({"ok": True, "index": index, "topic": entry["topic"], "video_dir": payload.get("video_dir")}, ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001
            error = {
                "index": index,
                "topic": entry.get("topic"),
                "source": entry.get("url") or entry.get("video_file"),
                "error": str(exc),
            }
            errors.append(error)
            print(json.dumps({"ok": False, **error}, ensure_ascii=False))

    result = {
        "ok": not errors,
        "manifest": str(manifest),
        "processed": processed,
        "errors": errors,
        "actual_cost_usd": round(spent, 6),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }
    out_json = PROJECT_DIR / "docs" / "clean-slate-test-10-result.json"
    out_md = PROJECT_DIR / "docs" / "clean-slate-test-10-result.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "processed": len(processed), "errors": len(errors), "cost_usd": result["actual_cost_usd"], "report": str(out_md)}, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
