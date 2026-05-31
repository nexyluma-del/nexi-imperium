#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from run_validation_50 import PROJECT_DIR, classify, wsl_to_windows


INVENTORY_JSON = PROJECT_DIR / "videos" / "_inventory" / "full-inventory.json"
ORIGINAL_SELECTION_JSON = PROJECT_DIR / "videos" / "_runs" / "run-001-validation" / "selection-50.json"
OUT_JSON = PROJECT_DIR / "docs" / "classifier-sanity-30.json"
OUT_MD = PROJECT_DIR / "docs" / "classifier-sanity-30.md"
WORK_DIR = PROJECT_DIR / "docs" / "classifier-sanity-30-work"
SEED = 20260531
TARGET_COUNT = 30
MIN_ACCURACY = 85.0


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def original_paths() -> set[str]:
    payload = read_json(ORIGINAL_SELECTION_JSON)
    return {str(item.get("source_path") or "") for item in payload if item.get("source_path")}


def candidates() -> list[dict[str, Any]]:
    inventory = read_json(INVENTORY_JSON)
    excluded = original_paths()
    items = []
    for item in inventory.get("local_files") or []:
        category = item.get("category_hint")
        source = item.get("source_path")
        if not source or source in excluded:
            continue
        if not category or category.startswith("_"):
            continue
        items.append(
            {
                "source_path": source,
                "source_path_windows": item.get("source_path_windows") or wsl_to_windows(source),
                "top_folder": item.get("top_folder") or "",
                "expected_category": category,
                "size_mb": item.get("size_mb"),
            }
        )
    return items


def stratified_random_sample(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_category[item["expected_category"]].append(item)
    for bucket in by_category.values():
        rng.shuffle(bucket)

    selected: list[dict[str, Any]] = []
    categories = sorted(by_category)
    cursor = 0
    while len(selected) < TARGET_COUNT and any(by_category.values()):
        category = categories[cursor % len(categories)]
        bucket = by_category[category]
        if bucket:
            selected.append(bucket.pop())
        cursor += 1
    rng.shuffle(selected)
    return selected[:TARGET_COUNT]


def dummy_transcript(index: int, item: dict[str, Any]) -> Path:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    path = WORK_DIR / f"{index:02d}-{item['expected_category']}-{Path(item['source_path']).stem[:40]}.txt"
    path.write_text(
        "\n".join(
            [
                "SANITY_CLASSIFIER_TEST_NO_GEMINI.",
                "Dieser Test prueft die robuste Folder-Intent-Routing-Regel ohne Gemini-Call.",
                f"Top-Ordner: {item['top_folder']}",
                f"Erwartete Kategorie laut Voll-Inventar: {item['expected_category']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Klassifizierer-Sanity-Test 30",
        "",
        f"Stand: {payload['finished_at']}",
        f"Seed: `{payload['seed']}`",
        f"Quelle: `{wsl_to_windows(INVENTORY_JSON)}`",
        "",
        "## Ergebnis",
        "",
        f"- Geprueft: `{payload['checked']}` neue Videos, nicht aus den urspruenglichen 50",
        f"- Treffer: `{payload['matches']}`",
        f"- Genauigkeit: `{payload['accuracy_percent']}` %",
        f"- Ziel >85%: `{'erreicht' if payload['passed'] else 'NICHT erreicht'}`",
        f"- Gemini-Calls: `0`",
        "",
        "## Kategorie-Verteilung",
        "",
    ]
    for category, count in payload["distribution"].items():
        lines.append(f"- `{category}`: `{count}`")
    lines += [
        "",
        "## Vergleich",
        "",
        "| # | Ordner | Erwartet | Neu | Treffer | Begruendung |",
        "|---:|---|---|---|---|---|",
    ]
    for item in payload["items"]:
        reason = str(item.get("reason") or "").replace("|", "/")[:140]
        lines.append(
            f"| {item['index']} | {item['top_folder']} | {item['expected_category']} | "
            f"{item['classified_category']} | {'ja' if item['match'] else 'nein'} | {reason} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    items = stratified_random_sample(candidates())
    if len(items) < TARGET_COUNT:
        raise RuntimeError(f"Nur {len(items)} Kandidaten fuer Sanity-Test gefunden.")

    results = []
    matches = 0
    distribution: dict[str, int] = defaultdict(int)
    for index, item in enumerate(items, start=1):
        transcript = dummy_transcript(index, item)
        classified = classify(Path(item["source_path"]), item["top_folder"], transcript)
        match = classified.get("category") == item["expected_category"]
        matches += 1 if match else 0
        distribution[item["expected_category"]] += 1
        results.append(
            {
                **item,
                "index": index,
                "classified_category": classified.get("category"),
                "confidence": classified.get("confidence"),
                "reason": classified.get("reason"),
                "raw": classified.get("raw"),
                "match": match,
            }
        )

    accuracy = round(matches / len(results) * 100, 2)
    payload = {
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "seed": SEED,
        "checked": len(results),
        "matches": matches,
        "accuracy_percent": accuracy,
        "passed": accuracy > MIN_ACCURACY,
        "min_accuracy_percent": MIN_ACCURACY,
        "gemini_calls": 0,
        "distribution": dict(sorted(distribution.items())),
        "items": results,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": payload["passed"], "accuracy_percent": accuracy, "report": str(OUT_MD)}, ensure_ascii=False, indent=2))
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
