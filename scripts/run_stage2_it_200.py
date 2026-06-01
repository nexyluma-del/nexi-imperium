#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import shutil
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import run_validation_50 as rv
from telegram_common import send_message_if_configured


RUN_ID = "run-002-it-stress-200"
IT_CATEGORIES = ("01-IT", "02-IT-HACKS", "03-KI-IT", "04-TECHNIK")
TARGET_COUNT = 200
TELEGRAM_EVERY = 50
MAX_STAGE_COST_USD = 30.0
SEED = 20260531

PROJECT_DIR = rv.PROJECT_DIR
RUN_DIR = PROJECT_DIR / "videos" / "_runs" / RUN_ID
WORK_DIR = RUN_DIR / "work"
REPORT_JSON = RUN_DIR / f"{RUN_ID}.json"
REPORT_MD = RUN_DIR / f"{RUN_ID}.md"
SELECTION_JSON = RUN_DIR / "selection-200.json"
INVENTORY_JSON = PROJECT_DIR / "videos" / "_inventory" / "full-inventory.json"
VALIDATION_SELECTION_JSON = PROJECT_DIR / "videos" / "_runs" / "run-001-validation" / "selection-50.json"
SANITY_JSON = PROJECT_DIR / "docs" / "classifier-sanity-30.json"
RESTIC_SNAPSHOT = "3ec4e511"
NASA_TERMS = rv.NASA_TERMS
QUALITY_FLAGS_JSON = PROJECT_DIR / "videos" / "_quality_flags.json"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def excluded_paths() -> set[str]:
    excluded: set[str] = set()
    for item in read_json(VALIDATION_SELECTION_JSON, default=[]) or []:
        if item.get("source_path"):
            excluded.add(str(item["source_path"]))
    sanity = read_json(SANITY_JSON, default={}) or {}
    for item in sanity.get("items") or []:
        if item.get("source_path"):
            excluded.add(str(item["source_path"]))
    return excluded


def inventory_candidates() -> list[dict[str, Any]]:
    inventory = read_json(INVENTORY_JSON, default={}) or {}
    excluded = excluded_paths()
    items: list[dict[str, Any]] = []
    for item in inventory.get("local_files") or []:
        category = item.get("category_hint")
        source = item.get("source_path")
        if category not in IT_CATEGORIES or not source or source in excluded:
            continue
        path = Path(source)
        if not path.exists():
            continue
        items.append(
            {
                "source_path": source,
                "source_path_windows": item.get("source_path_windows") or rv.wsl_to_windows(source),
                "top_folder": item.get("top_folder") or "",
                "expected_category": category,
                "must_be_sofinello": False,
                "size_mb": item.get("size_mb"),
                "inventory_category_hint": category,
            }
        )
    return items


def select_200() -> list[dict[str, Any]]:
    existing = read_json(SELECTION_JSON, default=None)
    if existing:
        return existing
    rng = random.Random(SEED)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in inventory_candidates():
        by_category[item["expected_category"]].append(item)
    for bucket in by_category.values():
        rng.shuffle(bucket)

    selected: list[dict[str, Any]] = []
    categories = list(IT_CATEGORIES)
    while len(selected) < TARGET_COUNT and any(by_category.values()):
        for category in categories:
            if len(selected) >= TARGET_COUNT:
                break
            bucket = by_category[category]
            if bucket:
                selected.append(bucket.pop())

    if len(selected) < TARGET_COUNT:
        raise RuntimeError(f"Nur {len(selected)} IT-Kandidaten fuer Stufe 2 gefunden.")
    selected = selected[:TARGET_COUNT]
    write_json(SELECTION_JSON, selected)
    return selected


def init_result(selection: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_id": RUN_ID,
        "stage": "Stufe 2 - 200er IT-Stress-Test",
        "started_at": now_iso(),
        "finished_at": None,
        "status": "running",
        "restic_snapshot_before_run": RESTIC_SNAPSHOT,
        "policy": {
            "categories": list(IT_CATEGORIES),
            "telegram_every": TELEGRAM_EVERY,
            "max_stage_cost_usd": MAX_STAGE_COST_USD,
            "anti_nasa_hard_terms": list(NASA_TERMS),
            "anti_nasa_soft_flag": "NASA in Gemini, aber nicht in Whisper",
            "exclude_validation_50": True,
            "exclude_sanity_30": True,
        },
        "planned_count": len(selection),
        "items": [],
        "errors": [],
        "classifier": {"checked": 0, "matches": 0, "accuracy_percent": None},
        "counts": {"processed": 0, "duplicate_reference": 0, "unsorted": 0, "failed": 0},
        "cost_total_usd": 0.0,
        "category_counts": {},
        "nasa_audit": None,
        "quality_flags": [],
        "last_telegram_at": 0,
    }


def load_or_init(selection: list[dict[str, Any]]) -> dict[str, Any]:
    existing = read_json(REPORT_JSON, default=None)
    if existing:
        return existing
    result = init_result(selection)
    write_json(REPORT_JSON, result)
    return result


def completed_sources(result: dict[str, Any]) -> set[str]:
    done_statuses = {"processed", "duplicate_reference", "waiting_manual_sort"}
    return {
        item["source_path"]
        for item in result.get("items") or []
        if item.get("source_path") and item.get("status") in done_statuses
    }


def seed_sha_seen_from_result(sha_seen: dict[str, dict[str, Any]], result: dict[str, Any]) -> None:
    for item in result.get("items") or []:
        if item.get("status") != "processed" or not item.get("sha256"):
            continue
        payload = item.get("pipeline") or {}
        files = payload.get("files") or {}
        sha_seen.setdefault(
            item["sha256"],
            {
                "manifest": files.get("run_manifest"),
                "video_dir": payload.get("video_dir"),
                "topic": (item.get("classified") or {}).get("category"),
                "video_id": payload.get("video_id"),
            },
        )


def is_transient_gemini_503_error(error: dict[str, Any]) -> bool:
    text = str(error.get("error") or "").lower()
    return "503 unavailable" in text or "high demand" in text


def is_transient_stage_timeout_error(error: dict[str, Any]) -> bool:
    text = str(error.get("error") or "").lower()
    return "timed out after 4800 seconds" in text and "run_video_pipeline.py" in text


def clear_resolved_transient_503_errors(result: dict[str, Any]) -> None:
    errors = result.get("errors") or []
    transient = [error for error in errors if is_transient_gemini_503_error(error)]
    if not transient:
        return
    result["errors"] = [error for error in errors if not is_transient_gemini_503_error(error)]
    result.setdefault("resolved_errors", []).append(
        {
            "resolved_at": now_iso(),
            "source": "run-002-resume",
            "resolution": "transient_gemini_503_high_demand; retry_policy_hardened_7_attempts_2_cycles; resume_from_failed_video",
            "original_errors": transient,
        }
    )
    result["counts"]["failed"] = max(0, int(result["counts"].get("failed") or 0) - len(transient))


def clear_resolved_transient_stage_timeout_errors(result: dict[str, Any]) -> None:
    errors = result.get("errors") or []
    transient = [error for error in errors if is_transient_stage_timeout_error(error)]
    if not transient:
        return
    result["errors"] = [error for error in errors if not is_transient_stage_timeout_error(error)]
    result.setdefault("resolved_errors", []).append(
        {
            "resolved_at": now_iso(),
            "source": "run-002-resume",
            "resolution": "outer_stage_timeout_4800s_increased_to_30000s; resume_from_failed_video",
            "original_errors": transient,
        }
    )
    result["counts"]["failed"] = max(0, int(result["counts"].get("failed") or 0) - len(transient))


def read_quality_flags() -> list[dict[str, Any]]:
    payload = read_json(QUALITY_FLAGS_JSON, default={}) or {}
    return [flag for flag in payload.get("flags", []) if flag.get("run_id") == RUN_ID]


def send_progress(result: dict[str, Any], force: bool = False) -> None:
    processed = result["counts"]["processed"]
    duplicates = result["counts"]["duplicate_reference"]
    unsorted = result["counts"]["unsorted"]
    failed = result["counts"]["failed"]
    completed = processed + duplicates + unsorted
    if not force and completed < result.get("last_telegram_at", 0) + TELEGRAM_EVERY:
        return
    result["last_telegram_at"] = completed
    elapsed_hours = max(0.01, (time.perf_counter() - STARTED_PERF) / 3600)
    rate = completed / elapsed_hours
    remaining = max(0, result["planned_count"] - completed)
    eta_hours = remaining / max(0.01, rate)
    send_message_if_configured(
        "Stufe 2 IT-Stress-Test Status\n"
        f"- fertig: {completed}/{result['planned_count']}\n"
        f"- Gemini verarbeitet: {processed}\n"
        f"- Duplikate: {duplicates}\n"
        f"- unsortiert: {unsorted}\n"
        f"- Fehler: {failed}\n"
        f"- Kosten: ${float(result.get('cost_total_usd') or 0):.4f}\n"
        f"- Rate: {rate:.1f} Videos/h\n"
        f"- ETA: {eta_hours:.1f} h"
    )


def render_report(result: dict[str, Any]) -> str:
    lines = [
        f"# {result['stage']}",
        "",
        f"Run: `{RUN_ID}`",
        f"Status: `{result['status']}`",
        f"Start: `{result['started_at']}`",
        f"Ende: `{result.get('finished_at')}`",
        f"Restic-Snapshot vor Start: `{result['restic_snapshot_before_run']}`",
        "",
        "## Ergebnis",
        "",
        f"- Geplant: `{result['planned_count']}`",
        f"- Gemini verarbeitet: `{result['counts']['processed']}`",
        f"- Duplikat-Referenzen: `{result['counts']['duplicate_reference']}`",
        f"- Unsortiert: `{result['counts']['unsorted']}`",
        f"- Fehler: `{result['counts']['failed']}`",
        f"- Kosten USD: `{float(result.get('cost_total_usd') or 0):.6f}`",
        f"- Klassifizierer: `{result['classifier'].get('accuracy_percent')}` %",
        "",
        "## Kategorien",
        "",
    ]
    for category, count in sorted((result.get("category_counts") or {}).items()):
        lines.append(f"- `{category}`: `{count}`")
    lines += [
        "",
        "## Anti-NASA Audit",
        "",
        f"- Match Count: `{(result.get('nasa_audit') or {}).get('match_count')}`",
        f"- Quality Flags: `{len(result.get('quality_flags') or [])}`",
        "",
        "## Erste Review-Outputs",
        "",
    ]
    samples = [item for item in result.get("items", []) if item.get("status") == "processed"][:10]
    for item in samples:
        payload = item.get("pipeline") or {}
        files = payload.get("files") or {}
        lines += [
            f"### {item['index']} - {item.get('classified', {}).get('category')}",
            "",
            f"- Quelle: `{item.get('source_path_windows')}`",
            f"- Analyse: `{files.get('analysis_markdown_windows') or files.get('analysis_markdown')}`",
            f"- Zusammenfassung: `{files.get('summary_markdown_windows') or files.get('summary_markdown')}`",
            f"- Word: `{files.get('word_report_windows') or files.get('word_report')}`",
            f"- Qdrant: `{(payload.get('qdrant') or {}).get('point_id')}`",
            f"- Kosten: `${float(item.get('cost_usd') or 0):.6f}`",
            "",
        ]
    lines += [
        "## Tabelle",
        "",
        "| # | Status | Erwartet | Klassifiziert | Kosten USD | Quelle |",
        "|---:|---|---|---|---:|---|",
    ]
    for item in result.get("items", []):
        lines.append(
            f"| {item.get('index')} | {item.get('status')} | {item.get('expected_category')} | "
            f"{(item.get('classified') or {}).get('category')} | {float(item.get('cost_usd') or 0):.6f} | "
            f"{Path(item.get('source_path_windows') or item.get('source_path') or '').name} |"
        )
    return "\n".join(lines) + "\n"


def save_result(result: dict[str, Any]) -> None:
    result["category_counts"] = dict(Counter((item.get("classified") or {}).get("category") for item in result.get("items", []) if item.get("classified")))
    checked = result["classifier"]["checked"]
    matches = result["classifier"]["matches"]
    result["classifier"]["accuracy_percent"] = round(matches / checked * 100, 2) if checked else None
    write_json(REPORT_JSON, result)
    REPORT_MD.write_text(render_report(result), encoding="utf-8")


def hard_stop(result: dict[str, Any], message: str) -> None:
    result["status"] = "stopped"
    result["finished_at"] = now_iso()
    result["errors"].append({"at": now_iso(), "error": message})
    result["counts"]["failed"] += 1
    save_result(result)
    send_message_if_configured("STUFE 2 HARTER STOP\n" + message + f"\nReport: {rv.wsl_to_windows(REPORT_MD)}")
    raise RuntimeError(message)


STARTED_PERF = time.perf_counter()


def main() -> int:
    rv.RUN_ID = RUN_ID
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    selection = select_200()
    result = load_or_init(selection)
    clear_resolved_transient_503_errors(result)
    clear_resolved_transient_stage_timeout_errors(result)
    result["status"] = "running"
    result["finished_at"] = None
    result["quality_flags"] = read_quality_flags()
    save_result(result)
    done = completed_sources(result)
    sha_seen = rv.existing_sha_index()
    seed_sha_seen_from_result(sha_seen, result)
    send_message_if_configured(
        "Stufe 2 gestartet: 200er IT-Stress-Test. Kategorien: 01-IT, 02-IT-HACKS, 03-KI-IT, 04-TECHNIK. "
        "Telegram alle 50. Hard Stop nur bei LADEE/LLCD/lunar laser communication/laser communications demonstration oder Klassifizierer-Fehler. NASA-only wird als Quality-Flag geloggt."
    )

    try:
        for selected_index, selected_item in enumerate(selection, start=1):
            if selected_item["source_path"] in done:
                continue
            item_started = time.perf_counter()
            source = Path(selected_item["source_path"])
            item_dir = WORK_DIR / f"{selected_index:03d}-{rv.slugify(source.stem)}"
            item = {**selected_item, "index": selected_index, "status": "started", "timings": {}}
            result["items"].append(item)
            save_result(result)

            sha = rv.file_sha256(source)
            item["sha256"] = sha
            item["duration_seconds"] = rv.ffprobe_duration(source)
            transcript, transcribe_meta = rv.transcribe_or_no_audio(source, item_dir)
            item["transcript"] = str(transcript)
            item["transcript_windows"] = rv.wsl_to_windows(transcript)
            item["no_audio_verified"] = transcribe_meta["no_audio_verified"]
            item["timings"]["transcribe_seconds"] = transcribe_meta["seconds"]

            classified = rv.classify(source, selected_item["top_folder"], transcript)
            item["classified"] = classified
            item["timings"]["classify_seconds"] = classified["seconds"]
            result["classifier"]["checked"] += 1
            if classified["category"] == selected_item["expected_category"]:
                result["classifier"]["matches"] += 1
            else:
                hard_stop(
                    result,
                    "Klassifizierer-Fehler: "
                    f"{rv.wsl_to_windows(source)} erwartet {selected_item['expected_category']}, "
                    f"bekommen {classified['category']}.",
                )

            if classified["category"] == "_unsortiert":
                item["status"] = "waiting_manual_sort"
                item["total_seconds"] = round(time.perf_counter() - item_started, 3)
                result["counts"]["unsorted"] += 1
                save_result(result)
                send_progress(result)
                continue

            if sha in sha_seen:
                item["status"] = "duplicate_reference"
                item["reference_manifest"] = str(rv.write_reference_manifest(item, sha_seen[sha]))
                item["reference_manifest_windows"] = rv.wsl_to_windows(item["reference_manifest"])
                item["total_seconds"] = round(time.perf_counter() - item_started, 3)
                result["counts"]["duplicate_reference"] += 1
                save_result(result)
                send_progress(result)
                continue

            remaining = max(0, TARGET_COUNT - selected_index)
            payload = rv.run_gemini_pipeline(item, transcript, selected_index, remaining, STARTED_PERF)
            result["quality_flags"] = read_quality_flags()
            item["pipeline"] = payload
            item["cost_usd"] = float(payload.get("cost", {}).get("estimated_actual_usd") or 0.0)
            item["status"] = "processed"
            item["total_seconds"] = round(time.perf_counter() - item_started, 3)
            result["cost_total_usd"] = round(float(result.get("cost_total_usd") or 0.0) + item["cost_usd"], 6)
            result["counts"]["processed"] += 1
            if result["cost_total_usd"] > MAX_STAGE_COST_USD:
                hard_stop(result, f"Cost-Cap Stufe 2 ueberschritten: ${result['cost_total_usd']:.4f} > ${MAX_STAGE_COST_USD:.2f}")
            sha_seen[sha] = {
                "manifest": payload.get("files", {}).get("run_manifest"),
                "video_dir": payload.get("video_dir"),
                "topic": classified["category"],
                "video_id": payload.get("video_id"),
            }
            save_result(result)
            send_progress(result)

            completed = result["counts"]["processed"] + result["counts"]["duplicate_reference"] + result["counts"]["unsorted"]
            if completed and completed % TELEGRAM_EVERY == 0:
                audit = rv.run_nasa_audit()
                result["nasa_audit"] = audit
                result["quality_flags"] = read_quality_flags()
                save_result(result)
                if audit.get("match_count"):
                    hard_stop(result, f"Anti-NASA-Hard-Audit meldet Treffer: {audit.get('match_count')}")

        audit = rv.run_nasa_audit()
        result["nasa_audit"] = audit
        result["quality_flags"] = read_quality_flags()
        if audit.get("match_count"):
            hard_stop(result, f"Anti-NASA-Hard-Audit meldet Treffer am Ende: {audit.get('match_count')}")
        result["status"] = "complete"
        result["finished_at"] = now_iso()
        save_result(result)
        send_progress(result, force=True)
        send_message_if_configured(
            "Stufe 2 IT-Stress-Test fertig.\n"
            f"- verarbeitet: {result['counts']['processed']}\n"
            f"- Duplikate: {result['counts']['duplicate_reference']}\n"
            f"- Kosten: ${float(result['cost_total_usd']):.4f}\n"
            f"- Klassifizierer: {result['classifier']['accuracy_percent']}%\n"
            f"- Report: {rv.wsl_to_windows(REPORT_MD)}"
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        if result.get("status") != "stopped":
            result["status"] = "failed"
            result["finished_at"] = now_iso()
            result["errors"].append({"at": now_iso(), "error": str(exc)})
            result["counts"]["failed"] += 1
            save_result(result)
            send_message_if_configured("Stufe 2 FEHLER\n" + str(exc)[:1800] + f"\nReport: {rv.wsl_to_windows(REPORT_MD)}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
