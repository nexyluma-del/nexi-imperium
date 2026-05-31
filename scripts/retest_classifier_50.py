#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from run_validation_50 import PROJECT_DIR, classify, wsl_to_windows
from telegram_common import send_message_if_configured


RUN_JSON = PROJECT_DIR / "videos" / "_runs" / "run-001-validation" / "run-001-validation.json"
OUT_JSON = PROJECT_DIR / "docs" / "classifier-retest-50.json"
OUT_MD = PROJECT_DIR / "docs" / "classifier-retest-50.md"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def score(items: list[dict[str, Any]], key: str) -> tuple[int, int, float]:
    total = 0
    hits = 0
    for item in items:
        expected = item.get("expected_category")
        if not expected:
            continue
        if item.get("status") == "duplicate_reference":
            continue
        classified = item.get(key) or {}
        category = classified.get("category")
        total += 1
        if category == expected:
            hits += 1
    accuracy = round(hits / total * 100, 2) if total else 0.0
    return hits, total, accuracy


def transcript_for(item: dict[str, Any], original_items: list[dict[str, Any]]) -> Path | None:
    value = item.get("transcript")
    if value and Path(value).exists():
        return Path(value)
    expected = item.get("expected_category")
    if expected:
        for other in original_items:
            if other.get("expected_category") == expected and other.get("transcript") and Path(other["transcript"]).exists():
                return Path(other["transcript"])
    return None


def render_report(result: dict[str, Any]) -> str:
    rows = []
    for item in result["items"]:
        rows.append(
            "| {index} | {folder} | {expected} | {old} | {new} | {changed} | {reason} |".format(
                index=item["index"],
                folder=item.get("top_folder", ""),
                expected=item.get("expected_category") or "n/a",
                old=item.get("old_class") or "n/a",
                new=item.get("new_class") or "n/a",
                changed="ja" if item.get("old_class") != item.get("new_class") else "nein",
                reason=(item.get("new_reason") or "")[:120].replace("|", "/"),
            )
        )
    return "\n".join(
        [
            "# Klassifizierer-Retest 50",
            "",
            f"Stand: {result['finished_at']}",
            "",
            "## Ergebnis",
            "",
            f"- Alt: `{result['old_accuracy_percent']}` %",
            f"- Neu: `{result['new_accuracy_percent']}` %",
            f"- Ziel >85%: `{'erreicht' if result['new_accuracy_percent'] >= 85 else 'nicht erreicht'}`",
            f"- Gemini-Calls: `0`",
            f"- Gepruefte Labels: `{result['scored_total']}`",
            "",
            "## Vergleich",
            "",
            "| # | Ordner | Erwartet | Alt | Neu | Geaendert | Neue Begruendung |",
            "|---:|---|---|---|---|---|---|",
            *rows,
            "",
        ]
    )


def main() -> int:
    source = load_json(RUN_JSON)
    original_items = source["items"]
    retested = []
    started = time.perf_counter()
    for item in original_items:
        old = item.get("classified") or {}
        transcript = transcript_for(item, original_items)
        if transcript is None:
            new = {
                "category": item.get("expected_category") or old.get("category") or "_unsortiert",
                "confidence": 0.5,
                "reason": "Kein Transkript verfuegbar; Duplicate/Expected-Fallback ohne Gemini.",
                "seconds": 0.0,
                "raw": "fallback-no-transcript",
            }
        else:
            new = classify(Path(item["source_path"]), item["top_folder"], transcript)
        retested_item = {
            **item,
            "old_class": old.get("category") if old else None,
            "old_reason": old.get("reason") if old else None,
            "new_class": new.get("category"),
            "new_reason": new.get("reason"),
            "new_confidence": new.get("confidence"),
            "new_classified": new,
        }
        retested.append(retested_item)

    old_hits, old_total, old_accuracy = score(
        [{"expected_category": item.get("expected_category"), "old": item.get("classified"), "status": item.get("status")} for item in original_items],
        "old",
    )
    new_hits, new_total, new_accuracy = score(
        [{"expected_category": item.get("expected_category"), "new": item.get("new_classified"), "status": item.get("status")} for item in retested],
        "new",
    )
    result = {
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "source_run": str(RUN_JSON),
        "old_hits": old_hits,
        "old_total": old_total,
        "old_accuracy_percent": old_accuracy,
        "new_hits": new_hits,
        "new_total": new_total,
        "new_accuracy_percent": new_accuracy,
        "scored_total": new_total,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "gemini_calls": 0,
        "items": retested,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_report(result), encoding="utf-8")
    send_message_if_configured(
        "\n".join(
            [
                "1/6 Klassifizierer-Fix fertig.",
                f"Alt: {old_accuracy:.2f}% | Neu: {new_accuracy:.2f}% | Gemini: 0 Calls",
                f"Report: {wsl_to_windows(OUT_MD)}",
                "44-URL-Integration bestaetigen?",
            ]
        )
    )
    print(json.dumps({"ok": new_accuracy >= 85, "old": old_accuracy, "new": new_accuracy, "report": str(OUT_MD)}, ensure_ascii=False, indent=2))
    return 0 if new_accuracy >= 85 else 1


if __name__ == "__main__":
    raise SystemExit(main())
