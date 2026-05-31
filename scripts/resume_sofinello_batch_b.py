#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from telegram_common import send_message_if_configured


PROJECT_DIR = Path(__file__).resolve().parents[1]
STATUS_FILE = PROJECT_DIR / "logs" / "sofinello" / "sofinello-batch-b-status.json"
LOG_FILE = PROJECT_DIR / "logs" / "sofinello" / "sofinello-batch-b-resume.out"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def is_batch_running() -> bool:
    completed = subprocess.run(
        ["pgrep", "-f", "scripts/process_sofinello_batch.py.*sofinello-batch-b-status.json"],
        text=True,
        capture_output=True,
        timeout=10,
    )
    return completed.returncode == 0 and bool(completed.stdout.strip())


def status_summary(status: dict[str, Any]) -> dict[str, Any]:
    total = int(status.get("total_videos") or 722)
    processed = int(status.get("processed_count") or len(status.get("processed") or {}))
    errors = int(status.get("error_count") or len(status.get("errors") or []))
    cost = float(status.get("actual_cost_usd") or 0.0)
    return {
        "total_videos": total,
        "processed_count": processed,
        "error_count": errors,
        "actual_cost_usd": round(cost, 6),
        "complete": processed >= total,
    }


def start_batch(max_cost_eur: float) -> int:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / "process_sofinello_batch.py"),
        "--status-file",
        str(STATUS_FILE),
        "--max-cost-eur",
        str(max_cost_eur),
        "--sleep-seconds",
        "1",
    ]
    with LOG_FILE.open("ab") as log:
        log.write(f"\n\n=== resume {datetime.now().isoformat(timespec='seconds')} ===\n".encode("utf-8"))
        process = subprocess.Popen(
            command,
            cwd=PROJECT_DIR,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return int(process.pid)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resume Sofinello Batch B if needed.")
    parser.add_argument("--max-cost-eur", type=float, default=50.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status = load_json(STATUS_FILE)
    summary = status_summary(status)
    payload: dict[str, Any] = {
        "ok": True,
        "status": summary,
        "running": is_batch_running(),
        "started": False,
        "pid": None,
        "log_file": str(LOG_FILE),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    if payload["running"]:
        payload["message"] = "Sofinello Batch B laeuft bereits."
    elif summary["complete"]:
        payload["message"] = "Sofinello Batch B ist bereits komplett."
    elif args.dry_run:
        payload["message"] = "Dry-run: Resume waere gestartet."
    else:
        pid = start_batch(args.max_cost_eur)
        payload["started"] = True
        payload["pid"] = pid
        payload["message"] = f"Sofinello Batch B Resume gestartet (PID {pid})."
        send_message_if_configured(
            "Sofinello Batch B Resume gestartet.\n"
            f"Fortschritt: {summary['processed_count']}/{summary['total_videos']}\n"
            f"Fehler: {summary['error_count']}\n"
            f"Kosten bisher: ${summary['actual_cost_usd']:.4f}"
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
