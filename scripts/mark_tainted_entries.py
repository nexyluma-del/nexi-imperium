#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


QDRANT_URL = "http://127.0.0.1:6333"
PROJECT_DIR = Path(r"C:\AI\projects\09-video-analyse")
REPORT_JSON = PROJECT_DIR / "failed-or-corrupt.json"
REPORT_MD = PROJECT_DIR / "failed-or-corrupt.md"


def qdrant_set_payload(collection: str, point_id: str, payload: dict[str, Any]) -> None:
    response = requests.post(
        f"{QDRANT_URL}/collections/{collection}/points/payload?wait=true",
        json={"points": [point_id], "payload": payload},
        timeout=60,
    )
    response.raise_for_status()


def main() -> int:
    data = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    marked: list[dict[str, Any]] = []
    generated_at = datetime.now().isoformat(timespec="seconds")

    for item in data.get("entries", []):
        if item.get("classification") != "suspect-cross-contamination":
            continue
        payload = {
            "tainted": True,
            "taint_reason": "NASA/LADEE/LLCD cross-contamination audit",
            "taint_terms": item.get("terms") or [],
            "tainted_at": generated_at,
            "taint_report": str(REPORT_MD),
        }
        qdrant_set_payload(str(item["collection"]), str(item["id"]), payload)
        marked.append(
            {
                "collection": item["collection"],
                "id": item["id"],
                "url": item.get("url"),
                "slug": item.get("slug"),
                "terms": item.get("terms") or [],
            }
        )

    result = {
        "ok": True,
        "marked_count": len(marked),
        "marked": marked,
        "report_json": str(REPORT_JSON),
        "marked_at": generated_at,
    }
    out = PROJECT_DIR / "tainted-mark-report.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
