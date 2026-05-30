#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import requests


PROJECT_DIR = Path(__file__).resolve().parents[1]


def check_http(url: str, timeout: int = 5) -> bool:
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code < 500
    except Exception:
        return False


def qdrant_points(collection: str) -> int | None:
    try:
        response = requests.get(f"http://127.0.0.1:6333/collections/{collection}", timeout=5)
        if response.status_code != 200:
            return None
        return response.json().get("result", {}).get("points_count")
    except Exception:
        return None


def docker_status() -> list[str]:
    try:
        completed = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}={{.Status}}"],
            text=True,
            capture_output=True,
            timeout=10,
        )
        if completed.returncode != 0:
            return ["Docker: nicht erreichbar"]
        return [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    except Exception:
        return ["Docker: nicht erreichbar"]


def latest_files(directory: Path, pattern: str, limit: int = 3) -> list[Path]:
    if not directory.exists():
        return []
    files = [path for path in directory.rglob(pattern) if path.is_file()]
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def status_payload() -> dict[str, Any]:
    failed_file = PROJECT_DIR / "failed-videos.md"
    failed_count = 0
    if failed_file.exists():
        failed_count = sum(1 for line in failed_file.read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("## "))

    return {
        "services": {
            "ollama": check_http("http://127.0.0.1:11434/api/tags"),
            "qdrant": check_http("http://127.0.0.1:6333/collections"),
            "openwebui": check_http("http://127.0.0.1:3000"),
            "n8n": check_http("http://127.0.0.1:5678"),
        },
        "docker": docker_status(),
        "qdrant": {
            "video_knowledge": qdrant_points("video_knowledge"),
            "open-webui_knowledge": qdrant_points("open-webui_knowledge"),
        },
        "latest_analysis": [str(path) for path in latest_files(PROJECT_DIR / "analysis", "*.md")],
        "failed_videos": failed_count,
    }


def render_status(payload: dict[str, Any]) -> str:
    service_lines = [
        f"- {name}: {'OK' if ok else 'nicht erreichbar'}" for name, ok in payload["services"].items()
    ]
    docker_lines = "\n".join(f"- {line}" for line in payload["docker"][:5])
    latest = "\n".join(f"- {Path(path).name}" for path in payload["latest_analysis"]) or "- keine"
    return "\n".join(
        [
            "Imperium Status",
            "",
            "Services:",
            *service_lines,
            "",
            "Docker:",
            docker_lines,
            "",
            "Qdrant:",
            f"- video_knowledge: {payload['qdrant']['video_knowledge']}",
            f"- open-webui_knowledge: {payload['qdrant']['open-webui_knowledge']}",
            "",
            f"Failed videos: {payload['failed_videos']}",
            "",
            "Letzte Analysen:",
            latest,
        ]
    )


def main() -> int:
    payload = status_payload()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
