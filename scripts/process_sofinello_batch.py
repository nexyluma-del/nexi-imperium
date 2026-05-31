#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from analyze_local_video import normalize_input_path, wsl_to_windows
from failed_videos import append_failed_video
from gemini_common import slugify
from telegram_common import send_message_if_configured


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = Path("/mnt/c/Users/nexil/Desktop/Instagram Videos/Sofinello")
DEFAULT_STATUS = PROJECT_DIR / "logs" / "sofinello" / "sofinello-batch-status.json"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}
QUOTA_ERROR_MARKERS = (
    "RESOURCE_EXHAUSTED",
    "quota",
    "rate-limits",
    "GenerateRequestsPerDayPerProjectPerModel",
)
DEFAULT_QUESTION = (
    "Was zeigt dieses Sofinello-Video, welche Zutaten/Produkte/Claims sind erkennbar, "
    "wie ist es zu kategorisieren, und was muss compliance-seitig beachtet werden?"
)


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def is_quota_error(message: str) -> bool:
    lowered = message.lower()
    return any(marker.lower() in lowered for marker in QUOTA_ERROR_MARKERS)


def scan_videos(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.suffix.lower() in VIDEO_EXTENSIONS)


def run_one(video_path: Path, index: int, total: int, args: argparse.Namespace) -> dict[str, Any]:
    relative_slug = slugify(str(video_path.relative_to(args.root)).replace("/", "-").replace("\\", "-"))
    slug = f"sofinello-b-{index:04d}-{relative_slug}"
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / "analyze_sofinello.py"),
        "--video-path",
        str(video_path),
        "--data-class",
        "D2",
        "--question",
        args.question,
        "--source-info",
        f"Sofinello 722er Batch B Frame-Only ({index}/{total})",
        "--slug",
        slug,
        "--max-cost-eur",
        str(args.per_video_cost_cap_eur),
        "--max-frames",
        str(args.max_frames),
        "--frame-long-side",
        str(args.frame_long_side),
        "--upscale-mode",
        "frame-only",
        "--upscale-scale",
        str(args.upscale_scale),
        "--upscale-model",
        args.upscale_model,
        "--upscale-max-duration-seconds",
        "0",
    ]
    if args.dry_run:
        command.append("--dry-run")

    last_output = ""
    for attempt in range(1, args.retries + 2):
        completed = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            text=True,
            capture_output=True,
            timeout=args.timeout_seconds,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        last_output = output
        start = output.find("{")
        end = output.rfind("}")
        payload: dict[str, Any] | None = None
        if start != -1 and end > start:
            try:
                payload = json.loads(output[start : end + 1])
            except json.JSONDecodeError:
                payload = None
        if completed.returncode == 0 and payload and payload.get("ok"):
            return payload
        if attempt <= args.retries:
            time.sleep(args.retry_sleep_seconds * attempt)

    raise RuntimeError(last_output[-4000:] or "Sofinello-Analyse fehlgeschlagen.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Sofinello 722-video batch with frame-only upscaling.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--status-file", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--max-videos", type=int, default=0)
    parser.add_argument("--max-cost-eur", type=float, default=50.0)
    parser.add_argument("--per-video-estimate-eur", type=float, default=0.06)
    parser.add_argument("--per-video-cost-cap-eur", type=float, default=0.25)
    parser.add_argument("--max-frames", type=int, default=6)
    parser.add_argument("--frame-long-side", type=int, default=1280)
    parser.add_argument("--upscale-scale", type=int, choices=[2, 3, 4], default=2)
    parser.add_argument("--upscale-model", default="realesrgan-x4plus")
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--retry-sleep-seconds", type=float, default=20.0)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.root = normalize_input_path(args.root).resolve()
    args.status_file = normalize_input_path(args.status_file)
    status = load_json(args.status_file, {"processed": {}, "errors": [], "started_at": datetime.now().isoformat(timespec="seconds")})
    processed = status.setdefault("processed", {})
    errors = status.setdefault("errors", [])
    videos = scan_videos(args.root)
    if args.max_videos:
        videos = videos[: args.max_videos]
    total = len(videos)
    spent = sum(float(item.get("cost_usd") or 0.0) for item in processed.values() if isinstance(item, dict))

    summary: dict[str, Any] = {
        "ok": False,
        "pipeline_type": "sofinello-batch-frame-only",
        "root": str(args.root),
        "root_windows": wsl_to_windows(args.root),
        "total_videos": total,
        "max_cost_eur": args.max_cost_eur,
        "dry_run": args.dry_run,
        "processed_count": len(processed),
        "skipped_count": 0,
        "error_count": len(errors),
        "actual_cost_usd": round(spent, 6),
        "status_file": str(args.status_file),
        "status_file_windows": wsl_to_windows(args.status_file),
    }
    send_message_if_configured(f"Sofinello Batch B gestartet: {total} Videos, Frame-Only-Upscaling.")

    for index, video_path in enumerate(videos, start=1):
        key = str(video_path)
        if key in processed and not args.force:
            summary["skipped_count"] += 1
            continue
        if spent + args.per_video_estimate_eur > args.max_cost_eur:
            summary["stopped_reason"] = (
                f"Budgetschutz: {spent:.2f} + {args.per_video_estimate_eur:.2f} > {args.max_cost_eur:.2f}"
            )
            break

        try:
            payload = run_one(video_path, index, total, args)
            actual = float(payload.get("cost", {}).get("estimated_actual_usd") or 0.0)
            spent += actual
            processed[key] = {
                "ok": True,
                "index": index,
                "cost_usd": actual,
                "final_markdown": payload.get("files", {}).get("final_markdown"),
                "json": payload.get("files", {}).get("json"),
                "compliance_status": (payload.get("compliance") or {}).get("status"),
                "subcategory": payload.get("subcategory"),
                "qdrant_point_id": (payload.get("qdrant") or {}).get("point_id"),
                "processed_at": datetime.now().isoformat(timespec="seconds"),
            }
            errors[:] = [item for item in errors if item.get("path") != key]
            status["last_success"] = key
            if args.progress_every and index % args.progress_every == 0:
                send_message_if_configured(
                    f"Sofinello Batch B Fortschritt: {index}/{total}, "
                    f"Fehler: {len(errors)}, Kosten: ${spent:.4f}"
                )
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            if is_quota_error(message):
                stopped_reason = (
                    "Gemini-Tageslimit erreicht; Batch pausiert automatisch "
                    "und kann nach Quota-Reset fortgesetzt werden."
                )
                summary["stopped_reason"] = stopped_reason
                status["stopped_reason"] = stopped_reason
                status["last_quota_error"] = {
                    "index": index,
                    "path": key,
                    "error": message[:2500],
                    "failed_at": datetime.now().isoformat(timespec="seconds"),
                }
                send_message_if_configured(f"Sofinello Batch B pausiert: {stopped_reason}")
                break
            error = {
                "index": index,
                "path": key,
                "error": message[:2500],
                "failed_at": datetime.now().isoformat(timespec="seconds"),
            }
            errors.append(error)
            append_failed_video(url=key, topic="Sofinello Batch B", error=message, source="process_sofinello_batch")
        finally:
            status.update(
                {
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                    "total_videos": total,
                    "processed_count": len(processed),
                    "error_count": len(errors),
                    "actual_cost_usd": round(spent, 6),
                    "max_cost_eur": args.max_cost_eur,
                    "batch_mode": "frame-only",
                }
            )
            write_json(args.status_file, status)
            if args.sleep_seconds:
                time.sleep(args.sleep_seconds)

    summary.update(
        {
            "processed_count": len(processed),
            "error_count": len(errors),
            "actual_cost_usd": round(spent, 6),
            "finished_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    summary["ok"] = summary["processed_count"] + summary["error_count"] >= total or "stopped_reason" not in summary
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    send_message_if_configured(
        "Sofinello Batch B fertig.\n"
        f"Verarbeitet: {summary['processed_count']}/{total}\n"
        f"Fehler: {summary['error_count']}\n"
        f"Kosten: ${summary['actual_cost_usd']:.4f}"
    )
    return 0 if "stopped_reason" not in summary else 1


if __name__ == "__main__":
    raise SystemExit(main())
