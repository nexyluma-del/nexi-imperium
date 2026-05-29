#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]


def parse_json_output(output: str) -> dict[str, Any]:
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {"ok": False, "error": "No JSON object in runner output", "raw": output[-4000:]}
    try:
        return json.loads(output[start : end + 1])
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"JSON parse failed: {exc}", "raw": output[-4000:]}


class PipelineHandler(BaseHTTPRequestHandler):
    server_version = "NexiVideoPipelineBridge/1.0"

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        print(f"{self.address_string()} - {format % args}")

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(
                {
                    "ok": True,
                    "service": "nexi-video-pipeline-bridge",
                    "project_dir": str(PROJECT_DIR),
                }
            )
            return
        self._send_json({"ok": False, "error": "not found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/run", "/batch"}:
            self._send_json({"ok": False, "error": "not found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            request = json.loads(body or "{}")
            if self.path == "/batch":
                topic_file = str(request.get("topic_file", "")).strip()
                if not topic_file:
                    raise ValueError("topic_file fehlt")

                command = [
                    str(PROJECT_DIR / ".venv" / "bin" / "python"),
                    str(PROJECT_DIR / "scripts" / "run_batch_pipeline.py"),
                    "--topic-file",
                    topic_file,
                    "--budget-eur",
                    str(request.get("budget_eur", "5.00")),
                    "--sleep-seconds",
                    str(request.get("sleep_seconds", "2")),
                ]
                max_videos = str(request.get("max_videos", "")).strip()
                if max_videos:
                    command.extend(["--max-videos", max_videos])

                completed = subprocess.run(
                    command,
                    cwd=PROJECT_DIR,
                    text=True,
                    capture_output=True,
                    timeout=7200,
                )
                output = (completed.stdout or "") + (completed.stderr or "")
                payload = parse_json_output(output)
                payload["bridge_exit_code"] = completed.returncode
                if completed.returncode != 0:
                    payload["ok"] = False
                    payload.setdefault("raw", output[-4000:])
                self._send_json(payload, status=200)
                return

            url = str(request.get("url", "")).strip()
            if not url:
                raise ValueError("url fehlt")

            data_class = str(request.get("data_class", "D0")).strip() or "D0"
            slug = str(request.get("slug", "")).strip()
            model = str(request.get("model", "")).strip()
            max_cost_eur = str(request.get("max_cost_eur", "0.30")).strip() or "0.30"
            topic = str(request.get("topic", "")).strip()
            questions = request.get("questions", [])

            command = [
                str(PROJECT_DIR / ".venv" / "bin" / "python"),
                str(PROJECT_DIR / "scripts" / "run_video_pipeline.py"),
                "--url",
                url,
                "--data-class",
                data_class,
                "--max-cost-eur",
                max_cost_eur,
            ]
            if slug:
                command.extend(["--slug", slug])
            if model:
                command.extend(["--model", model])
            if topic:
                command.extend(["--topic", topic])
            if isinstance(questions, list):
                for question in questions:
                    if str(question).strip():
                        command.extend(["--question", str(question).strip()])

            completed = subprocess.run(
                command,
                cwd=PROJECT_DIR,
                text=True,
                capture_output=True,
                timeout=2400,
            )
            output = (completed.stdout or "") + (completed.stderr or "")
            payload = parse_json_output(output)
            payload["bridge_exit_code"] = completed.returncode
            if completed.returncode != 0:
                payload["ok"] = False
                payload.setdefault("raw", output[-4000:])
            self._send_json(payload, status=200)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": str(exc)}, status=200)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local HTTP bridge for n8n video pipeline runs.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), PipelineHandler)
    print(f"Pipeline bridge listening on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
