#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from qdrant_video_knowledge import upsert_video_knowledge
from failed_videos import append_failed_video
from telegram_common import send_message_if_configured


PROJECT_DIR = Path(__file__).resolve().parents[1]
ENTRY_RE = re.compile(r"^## Eintrag\s+(.+?)\s*$", re.M)
VALID_DATA_CLASSES = {"D0", "D1", "D2", "D3", "D4"}


def normalize_input_path(path: Path) -> Path:
    value = str(path)
    match = re.match(r"^([A-Za-z]):\\(.*)$", value)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/")
        return Path(f"/mnt/{drive}/{rest}")
    return path


def ensure_project_venv() -> None:
    if os.environ.get("VIDEO_PIPELINE_VENV_READY") == "1":
        return
    venv_dir = PROJECT_DIR / ".venv"
    venv_python = venv_dir / "bin" / "python"
    if not venv_python.exists():
        return
    if Path(sys.prefix).resolve() == venv_dir.resolve():
        return
    env = os.environ.copy()
    env["VIDEO_PIPELINE_VENV_READY"] = "1"
    os.execvpe(str(venv_python), [str(venv_python), *sys.argv], env)


ensure_project_venv()


@dataclass
class BatchEntry:
    number: str
    url: str
    tags: str
    questions: list[str]
    status: str
    data_class: str
    raw_block: str
    analysis: str = ""
    cost_usd: str = ""
    qdrant_id: str = ""


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return value[:80] or "video"


def read_topic(text: str, topic_file: Path) -> str:
    match = re.search(r"^# Thema:\s*(.+?)\s*$", text, re.M)
    return match.group(1).strip() if match else topic_file.stem


def field_value(block: str, field: str) -> str:
    match = re.search(rf"^{re.escape(field)}:[ \t]*(.*?)[ \t\r]*$", block, re.M)
    return match.group(1).strip() if match else ""


def parse_questions(block: str) -> list[str]:
    match = re.search(r"^Fragen:\s*$([\s\S]*?)(?=^Status:|^Datenklasse:|^Analyse:|\Z)", block, re.M)
    if not match:
        return []
    questions = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("-"):
            questions.append(stripped.lstrip("- ").strip())
    return [question for question in questions if question]


def parse_entries(text: str) -> list[BatchEntry]:
    matches = list(ENTRY_RE.finditer(text))
    entries: list[BatchEntry] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        entries.append(
            BatchEntry(
                number=match.group(1).strip(),
                url=field_value(block, "URL"),
                tags=field_value(block, "Tags"),
                questions=parse_questions(block),
                status=field_value(block, "Status"),
                data_class=field_value(block, "Datenklasse") or "D2",
                analysis=field_value(block, "Analyse"),
                cost_usd=field_value(block, "Kosten USD"),
                qdrant_id=field_value(block, "Qdrant ID"),
                raw_block=block,
            )
        )
    return entries


def render_entry(entry: BatchEntry) -> str:
    lines = [
        f"## Eintrag {entry.number}",
        f"URL: {entry.url}",
        f"Tags: {entry.tags}",
        "Fragen:",
    ]
    lines.extend(f"- {question}" for question in (entry.questions or ["Allgemein: Was ist die wichtigste Aussage?"]))
    lines.extend(
        [
            f"Status: {entry.status}",
            f"Datenklasse: {entry.data_class}",
            f"Analyse: {entry.analysis}",
            f"Kosten USD: {entry.cost_usd}",
            f"Qdrant ID: {entry.qdrant_id}",
            "",
        ]
    )
    return "\n".join(lines)


def write_topic_file(topic_file: Path, original_text: str, entries: list[BatchEntry]) -> None:
    first_match = ENTRY_RE.search(original_text)
    header = original_text[: first_match.start()].rstrip() if first_match else original_text.rstrip()
    body = "\n".join(render_entry(entry) for entry in entries)
    topic_file.write_text(header + "\n\n" + body, encoding="utf-8")


def is_image_post_url(url: str) -> bool:
    return "instagram.com/p/" in url.lower()


def topic_context(topic: str, entry: BatchEntry) -> str:
    return f"{topic} | Tags: {entry.tags}" if entry.tags else topic


def notify_batch_summary(summary: dict[str, Any]) -> None:
    processed = summary.get("processed") or []
    errors = summary.get("errors") or []
    if not processed and not errors:
        return
    text = "\n".join(
        [
            "Batch-Pipeline fertig",
            f"Thema: {summary.get('topic')}",
            f"Verarbeitet: {len(processed)}",
            f"Fehler: {len(errors)}",
            f"Kosten: ${float(summary.get('actual_cost_usd') or 0):.4f}",
            f"Datei: {summary.get('topic_file')}",
        ]
    )
    send_message_if_configured(text)


def run_single(entry: BatchEntry, topic: str, topic_slug: str, index: int, budget_eur: float) -> dict[str, Any]:
    slug = slugify(f"{topic_slug}-{index}")
    script = "analyze_post_crosscheck.py" if is_image_post_url(entry.url) else "run_video_pipeline.py"
    entry_topic = topic_context(topic, entry)
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / script),
        "--url",
        entry.url,
        "--data-class",
        entry.data_class,
        "--slug",
        slug,
        "--topic",
        entry_topic,
        "--max-cost-eur",
        str(budget_eur),
    ]
    for question in entry.questions:
        command.extend(["--question", question])

    completed = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        text=True,
        capture_output=True,
        timeout=2400,
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end <= start:
        raise RuntimeError(f"Pipeline output enthaelt kein JSON: {output[-2000:]}")
    payload = json.loads(output[start : end + 1])
    if completed.returncode != 0 or not payload.get("ok"):
        raise RuntimeError(payload.get("error") or output[-3000:])
    return payload


def run_local_folder_mode(args: argparse.Namespace, root: Path) -> int:
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / "process_local_folder.py"),
        "--root",
        str(root),
        "--data-class",
        args.local_data_class,
        "--max-cost-eur",
        str(args.budget_eur),
        "--per-video-estimate-eur",
        str(args.per_video_estimate_eur),
    ]
    if args.max_videos > 0:
        command.extend(["--max-videos", str(args.max_videos)])
    for category_filter in args.local_filter:
        command.extend(["--filter", category_filter])
    if args.one_per_category:
        command.append("--one-per-category")
    if args.local_force:
        command.append("--force")
    if args.dry_run:
        command.append("--dry-run")

    completed = subprocess.run(command, cwd=PROJECT_DIR, text=True, capture_output=True, timeout=7200)
    output = (completed.stdout or "") + (completed.stderr or "")
    print(output)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run batch video pipeline for one topic file.")
    parser.add_argument("--topic-file", type=Path, required=True)
    parser.add_argument("--budget-eur", type=float, default=5.0)
    parser.add_argument("--per-video-estimate-eur", type=float, default=0.06)
    parser.add_argument("--sleep-seconds", type=float, default=2.0)
    parser.add_argument("--max-videos", type=int, default=0, help="0 means all pending entries.")
    parser.add_argument("--allow-cloud-data-class", action="append", default=["D0", "D1"])
    parser.add_argument("--local-data-class", default="D2", choices=sorted(VALID_DATA_CLASSES))
    parser.add_argument("--local-filter", action="append", default=[])
    parser.add_argument("--one-per-category", action="store_true")
    parser.add_argument("--local-force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    topic_file = normalize_input_path(args.topic_file)
    if topic_file.is_dir():
        return run_local_folder_mode(args, topic_file)

    text = topic_file.read_text(encoding="utf-8")
    topic = read_topic(text, topic_file)
    entries = parse_entries(text)
    pending = [entry for entry in entries if entry.status.lower().startswith("noch nicht")]
    if args.max_videos > 0:
        pending = pending[: args.max_videos]

    estimated_cost = len(pending) * args.per_video_estimate_eur
    summary: dict[str, Any] = {
        "ok": False,
        "topic": topic,
        "topic_file": str(topic_file),
        "pending_count": len(pending),
        "estimated_cost_eur": round(estimated_cost, 4),
        "budget_eur": args.budget_eur,
        "processed": [],
        "errors": [],
    }

    if estimated_cost > args.budget_eur:
        summary["error"] = f"Batch-Schaetzung {estimated_cost:.2f} EUR > Budget {args.budget_eur:.2f} EUR"
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 3

    allowed = set(args.allow_cloud_data_class)
    spent = 0.0
    topic_slug = slugify(topic)
    for pending_index, entry in enumerate(pending, start=1):
        entry_index = entries.index(entry) + 1
        if entry.data_class not in allowed:
            entry.status = f"gesperrt - Cloud-Freigabe fuer {entry.data_class} fehlt"
            summary["errors"].append({"entry": entry.number, "url": entry.url, "error": entry.status})
            append_failed_video(url=entry.url, topic=topic_context(topic, entry), error=entry.status, source="run_batch_pipeline")
            write_topic_file(topic_file, text, entries)
            continue
        if spent + args.per_video_estimate_eur > args.budget_eur:
            entry.status = "gestoppt - Batch-Budget erreicht"
            summary["errors"].append({"entry": entry.number, "url": entry.url, "error": entry.status})
            break

        try:
            result = run_single(entry, topic, topic_slug, entry_index, args.budget_eur)
            if result.get("pipeline_type") == "image-post":
                cost = float(result.get("cost", {}).get("actual_total_usd") or 0.0)
                qdrant = result.get("qdrant") or {}
                entry.status = f"analysiert am {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                entry.analysis = result["files"].get("analysis_markdown_windows") or result["files"].get("analysis_markdown", "")
                entry.cost_usd = f"{cost:.6f}"
                entry.qdrant_id = qdrant.get("point_id", "")
                spent += cost
                summary["processed"].append(
                    {
                        "entry": entry.number,
                        "url": entry.url,
                        "pipeline_type": "image-post",
                        "analysis": entry.analysis,
                        "cost_usd": cost,
                        "qdrant_id": entry.qdrant_id,
                    }
                )
                continue

            cost = float(result.get("cost", {}).get("estimated_actual_usd") or 0.0)
            spent += cost
            analysis_md = Path(result["files"]["analysis_markdown"])
            transcript_txt = Path(result["files"]["transcript_txt"])
            qdrant = upsert_video_knowledge(
                url=entry.url,
                topic=topic_context(topic, entry),
                data_class=entry.data_class,
                questions=entry.questions,
                analysis_markdown=analysis_md,
                transcript_txt=transcript_txt,
                cost_usd=cost,
                slug=result.get("slug", topic_slug),
            )
            entry.status = f"analysiert am {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            entry.analysis = result["files"].get("analysis_markdown_windows") or str(analysis_md)
            entry.cost_usd = f"{cost:.6f}"
            entry.qdrant_id = qdrant["point_id"]
            summary["processed"].append(
                {
                    "entry": entry.number,
                    "url": entry.url,
                    "analysis": entry.analysis,
                    "cost_usd": cost,
                    "qdrant_id": qdrant["point_id"],
                }
            )
        except Exception as exc:  # noqa: BLE001
            entry.status = f"Fehler - siehe Log ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
            summary["errors"].append({"entry": entry.number, "url": entry.url, "error": str(exc)})
            append_failed_video(url=entry.url, topic=topic_context(topic, entry), error=str(exc), source="run_batch_pipeline")
        finally:
            write_topic_file(topic_file, text, entries)
            text = topic_file.read_text(encoding="utf-8")
            if pending_index < len(pending):
                time.sleep(args.sleep_seconds)

    summary["ok"] = len(summary["errors"]) == 0
    summary["actual_cost_usd"] = round(spent, 6)
    summary["finished_at"] = datetime.now().isoformat(timespec="seconds")
    notify_batch_summary(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
