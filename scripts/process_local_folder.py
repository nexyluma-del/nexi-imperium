#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = Path("/mnt/c/Users/nexil/Desktop/Instagram Videos")
DEFAULT_PROMPTS = PROJECT_DIR / "category_prompts.json"
DEFAULT_STATUS = PROJECT_DIR / "logs" / "local-video-processed.json"
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
VALID_DATA_CLASSES = {"D0", "D1", "D2", "D3", "D4"}
SOFINELLO_PREFIX = "sofinello"


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


def normalize_input_path(path: Path) -> Path:
    value = str(path)
    match = re.match(r"^([A-Za-z]):\\(.*)$", value)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/")
        return Path(f"/mnt/{drive}/{rest}")
    return path


def wsl_to_windows(path: str | Path | None) -> str | None:
    if path is None:
        return None
    value = str(path)
    if value.startswith("/mnt/c/"):
        return "C:\\" + value[len("/mnt/c/") :].replace("/", "\\")
    return value


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return cleaned[:90] or "video"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def category_for(path: Path, root: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return path.parent.name
    return relative.parts[0] if relative.parts else path.parent.name


def status_key(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}|{stat.st_size}|{int(stat.st_mtime)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def is_sofinello_category(category: str) -> bool:
    return category.strip().lower().startswith(SOFINELLO_PREFIX)


def should_skip_category(category: str, prompts: dict[str, Any]) -> tuple[bool, str]:
    if is_sofinello_category(category):
        return True, "Sofinello ist fuer Aufgabe 016 gesperrt und fuer 016b/016c reserviert."
    config = prompts.get(category, {})
    if config.get("skip"):
        return True, f"Kategorie laut category_prompts.json gesperrt: {config.get('pipeline', 'skip')}"
    return False, ""


def scan_videos(root: Path, prompts: dict[str, Any], filters: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    skipped: list[dict[str, str]] = []
    videos: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix().lower()):
        if not path.is_file() or path.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        category = category_for(path, root)
        if filters and category.lower() not in filters:
            continue
        skip, reason = should_skip_category(category, prompts)
        if skip:
            skipped.append({"category": category, "path": str(path), "reason": reason})
            continue
        videos.append({"path": path, "category": category})
    return videos, skipped


def pick_one_per_category(videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for video in videos:
        category = video["category"]
        if category.lower() in seen:
            continue
        selected.append(video)
        seen.add(category.lower())
    return selected


def category_config(prompts: dict[str, Any], category: str) -> dict[str, Any]:
    default = prompts.get("default", {})
    current = prompts.get(category, {})
    merged = {**default, **current}
    merged.setdefault("question", "Was wird in diesem Video gezeigt und gesagt?")
    merged.setdefault("pipeline", "default_local_video")
    merged.setdefault("preprocessor", None)
    return merged


def run_local_video(video: dict[str, Any], args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    path = video["path"]
    category = video["category"]
    slug = slugify(f"{category}-{path.stem}")
    command = [
        str(PROJECT_DIR / ".venv" / "bin" / "python"),
        str(PROJECT_DIR / "scripts" / "analyze_local_video.py"),
        "--video-path",
        str(path),
        "--data-class",
        args.data_class,
        "--category",
        category,
        "--question",
        args.question or config["question"],
        "--source-info",
        f"Lokaler Ordner: {wsl_to_windows(path.parent)}",
        "--slug",
        slug,
        "--max-cost-eur",
        str(args.per_video_cost_cap_eur),
        "--max-frames",
        str(args.max_frames),
        "--upscale",
        args.upscale,
        "--upscale-scale",
        str(args.upscale_scale),
        "--upscale-model",
        args.upscale_model,
        "--upscale-max-duration-seconds",
        str(args.upscale_max_duration_seconds),
        "--pipeline",
        str(config.get("pipeline") or "default_local_video"),
    ]
    if args.keep_upscale_workdir:
        command.append("--keep-upscale-workdir")
    if config.get("preprocessor"):
        command.extend(["--preprocessor", str(config["preprocessor"])])
    if args.dry_run:
        command.append("--dry-run")
    completed = subprocess.run(command, cwd=PROJECT_DIR, text=True, capture_output=True, timeout=args.timeout_seconds)
    output = (completed.stdout or "") + (completed.stderr or "")
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end <= start:
        raise RuntimeError(f"Lokale Pipeline gab kein JSON zurueck: {output[-3000:]}")
    payload = json.loads(output[start : end + 1])
    if completed.returncode != 0 or not payload.get("ok"):
        raise RuntimeError(payload.get("error") or output[-3000:])
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process a local Instagram video folder.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--data-class", default="D2", choices=sorted(VALID_DATA_CLASSES))
    parser.add_argument("--filter", action="append", default=[], help="Top-level category, repeatable.")
    parser.add_argument("--question", default=None, help="Override category question for every selected video.")
    parser.add_argument("--category-prompts", type=Path, default=DEFAULT_PROMPTS)
    parser.add_argument("--status-file", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--max-videos", type=int, default=0)
    parser.add_argument("--one-per-category", action="store_true")
    parser.add_argument("--max-cost-eur", type=float, default=5.0)
    parser.add_argument("--per-video-estimate-eur", type=float, default=0.08)
    parser.add_argument("--per-video-cost-cap-eur", type=float, default=0.50)
    parser.add_argument("--max-frames", type=int, default=6)
    parser.add_argument("--upscale", choices=["auto", "always", "never"], default="auto")
    parser.add_argument("--upscale-scale", type=int, choices=[2, 3, 4], default=2)
    parser.add_argument("--upscale-model", default="realesrgan-x4plus")
    parser.add_argument("--upscale-max-duration-seconds", type=float, default=180.0)
    parser.add_argument("--keep-upscale-workdir", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=int, default=2400)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = normalize_input_path(args.root).resolve()
    prompts = load_json(normalize_input_path(args.category_prompts), {})
    status_file = normalize_input_path(args.status_file)
    status = load_json(status_file, {"processed": {}})
    processed_status = status.setdefault("processed", {})
    filters = {item.lower() for item in args.filter}

    summary: dict[str, Any] = {
        "ok": False,
        "pipeline_type": "local-folder",
        "root": str(root),
        "root_windows": wsl_to_windows(root),
        "data_class": args.data_class,
        "filters": args.filter,
        "max_cost_eur": args.max_cost_eur,
        "dry_run": args.dry_run,
        "processed": [],
        "skipped": [],
        "errors": [],
        "actual_cost_usd": 0.0,
        "status_file": str(status_file),
        "status_file_windows": wsl_to_windows(status_file),
    }

    if not root.exists():
        summary["error"] = f"Root-Ordner nicht gefunden: {root}"
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 1

    videos, skipped = scan_videos(root, prompts, filters)
    summary["skipped"].extend(skipped[:50])
    if args.one_per_category:
        videos = pick_one_per_category(videos)
    if args.max_videos > 0:
        videos = videos[: args.max_videos]

    planned: list[dict[str, Any]] = []
    for video in videos:
        key = status_key(video["path"])
        existing = processed_status.get(key)
        if existing and existing.get("status") == "ok" and not args.force:
            summary["skipped"].append(
                {
                    "category": video["category"],
                    "path": str(video["path"]),
                    "reason": "bereits verarbeitet",
                }
            )
            continue
        planned.append({**video, "status_key": key})

    estimated_total = len(planned) * args.per_video_estimate_eur
    summary["planned_count"] = len(planned)
    summary["estimated_cost_eur"] = round(estimated_total, 4)
    if estimated_total > args.max_cost_eur:
        summary["error"] = f"Kosten-Schaetzung {estimated_total:.2f} EUR > Budget {args.max_cost_eur:.2f} EUR"
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 3

    if args.dry_run:
        summary["ok"] = True
        summary["planned"] = [
            {
                "category": video["category"],
                "path": str(video["path"]),
                "path_windows": wsl_to_windows(video["path"]),
                "question": args.question or category_config(prompts, video["category"])["question"],
            }
            for video in planned
        ]
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 0

    spent = 0.0
    for index, video in enumerate(planned, start=1):
        category = video["category"]
        path = video["path"]
        config = category_config(prompts, category)
        if spent + args.per_video_estimate_eur > args.max_cost_eur:
            reason = "Batch-Budget erreicht"
            summary["errors"].append({"category": category, "path": str(path), "error": reason})
            break
        try:
            result = run_local_video(video, args, config)
            cost = float(result.get("cost", {}).get("estimated_actual_usd") or 0.0)
            spent += cost
            qdrant = result.get("qdrant") or {}
            processed_status[video["status_key"]] = {
                "status": "ok",
                "processed_at": datetime.now().isoformat(timespec="seconds"),
                "category": category,
                "path": str(path),
                "path_windows": wsl_to_windows(path),
                "analysis_markdown": result.get("files", {}).get("analysis_markdown"),
                "analysis_markdown_windows": result.get("files", {}).get("analysis_markdown_windows"),
                "qdrant_id": qdrant.get("point_id"),
                "cost_usd": cost,
            }
            summary["processed"].append(
                {
                    "category": category,
                    "path": str(path),
                    "path_windows": wsl_to_windows(path),
                    "analysis": result.get("files", {}).get("analysis_markdown_windows")
                    or result.get("files", {}).get("analysis_markdown"),
                    "qdrant_id": qdrant.get("point_id"),
                    "cost_usd": cost,
                }
            )
        except Exception as exc:  # noqa: BLE001
            processed_status[video["status_key"]] = {
                "status": "error",
                "processed_at": datetime.now().isoformat(timespec="seconds"),
                "category": category,
                "path": str(path),
                "path_windows": wsl_to_windows(path),
                "error": str(exc),
            }
            summary["errors"].append({"category": category, "path": str(path), "error": str(exc)})
        finally:
            write_json(status_file, status)
            if index < len(planned):
                time.sleep(args.sleep_seconds)

    summary["actual_cost_usd"] = round(spent, 6)
    summary["ok"] = len(summary["errors"]) == 0
    summary["finished_at"] = datetime.now().isoformat(timespec="seconds")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
