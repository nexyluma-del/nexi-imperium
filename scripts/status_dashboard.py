#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


PROJECT_DIR = Path(r"C:\AI\projects\09-video-analyse")
DESKTOP_KI = Path(r"C:\Users\nexil\Desktop\KI")
DASHBOARD_DIR = PROJECT_DIR / "dashboard"
STATUS_JSON = DASHBOARD_DIR / "status.json"
STATUS_HTML = DASHBOARD_DIR / "imperium-status.html"
SOFINELLO_STATUS = PROJECT_DIR / "logs" / "sofinello" / "sofinello-batch-b-status.json"
FAILED_VIDEOS = PROJECT_DIR / "failed-videos.md"
COST_JSON = PROJECT_DIR / "videos" / "_cost" / "api-costs.json"

HTTP_ENDPOINTS = {
    "Ollama": "http://127.0.0.1:11434/api/tags",
    "Qdrant": "http://127.0.0.1:6333/collections",
    "OpenWebUI": "http://127.0.0.1:3000/health",
    "n8n": "http://127.0.0.1:5678/healthz",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def run_command(command: list[str], timeout: int = 15) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "stdout": "", "stderr": ""}


def http_json(url: str, timeout: int = 8) -> tuple[bool, int | None, Any]:
    try:
        request = Request(url, headers={"User-Agent": "nexi-status-dashboard"})
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
            status = getattr(response, "status", None)
            try:
                return True, status, json.loads(body.decode("utf-8"))
            except Exception:
                return True, status, body.decode("utf-8", errors="replace")[:1000]
    except URLError as exc:
        return False, None, str(exc.reason)
    except Exception as exc:
        return False, None, str(exc)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def list_recent_files(path: Path, pattern: str = "*", limit: int = 5) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    files = [item for item in path.glob(pattern) if item.is_file()]
    files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return [
        {
            "name": item.name,
            "path": str(item),
            "updated": datetime.fromtimestamp(item.stat().st_mtime).isoformat(timespec="seconds"),
            "size": item.stat().st_size,
        }
        for item in files[:limit]
    ]


def collect_http() -> dict[str, Any]:
    result = {}
    for name, url in HTTP_ENDPOINTS.items():
        ok, status, body = http_json(url)
        result[name] = {"ok": ok, "status": status, "url": url, "body": body if not ok else None}
    return result


def collect_docker() -> list[dict[str, Any]]:
    command = [
        "docker",
        "ps",
        "--format",
        "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}",
    ]
    result = run_command(command)
    if not result["ok"]:
        return [{"name": "docker", "ok": False, "status": result.get("stderr") or result.get("error")}]
    services = []
    for line in result["stdout"].splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            services.append(
                {
                    "name": parts[0],
                    "image": parts[1],
                    "status": parts[2],
                    "ports": parts[3],
                    "ok": "Up" in parts[2],
                }
            )
    return services


def collect_ollama_models() -> list[dict[str, Any]]:
    ok, _status, data = http_json("http://127.0.0.1:11434/api/tags")
    if not ok or not isinstance(data, dict):
        return []
    return [
        {
            "name": model.get("name"),
            "size_gb": round((model.get("size") or 0) / 1024 / 1024 / 1024, 2),
        }
        for model in data.get("models", [])
    ]


def collect_qdrant() -> dict[str, Any]:
    ok, _status, data = http_json("http://127.0.0.1:6333/collections")
    collections = []
    if ok and isinstance(data, dict):
        collections = [item.get("name") for item in data.get("result", {}).get("collections", [])]
    counts = {}
    for name in collections:
        ok_count, _status_count, details = http_json(f"http://127.0.0.1:6333/collections/{name}")
        if ok_count and isinstance(details, dict):
            result = details.get("result", {})
            counts[name] = {
                "points": result.get("points_count"),
                "vectors": result.get("vectors_count"),
            }
        else:
            counts[name] = {"points": None, "vectors": None}
    return {"collections": collections, "counts": counts}


def collect_scheduler() -> list[dict[str, str]]:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        "Get-ScheduledTask | Where-Object { $_.TaskName -like 'Nexi*' } | Select-Object TaskName,State | ConvertTo-Json -Compress",
    ]
    result = run_command(command, timeout=20)
    if not result["ok"] or not result["stdout"]:
        return [{"TaskName": "Scheduler", "State": result.get("stderr") or result.get("error") or "unknown"}]
    try:
        payload = json.loads(result["stdout"])
        if isinstance(payload, dict):
            payload = [payload]
        return payload
    except Exception:
        return [{"TaskName": "Scheduler", "State": "parse_error"}]


def collect_processes() -> dict[str, Any]:
    command = [
        "wsl.exe",
        "-d",
        "Ubuntu-24.04",
        "--",
        "bash",
        "-lc",
        "pgrep -af 'scripts/telegram_bot.py|scripts/process_sofinello_batch.py|scripts/voice_capture.py' || true",
    ]
    result = run_command(command, timeout=20)
    processes = result.get("stdout", "").splitlines() if result.get("stdout") else []
    return {
        "telegram_bot": [line for line in processes if "telegram_bot.py" in line],
        "sofinello_batch": [line for line in processes if "process_sofinello_batch.py" in line],
        "voice_capture": [line for line in processes if "voice_capture.py" in line],
    }


def collect_sofinello() -> dict[str, Any]:
    status = load_json(SOFINELLO_STATUS)
    processed = status.get("processed_count")
    total = status.get("total_videos")
    if processed is None and isinstance(status.get("processed"), dict):
        processed = len(status["processed"])
    progress = None
    if total:
        progress = round((processed or 0) / total * 100, 1)
    return {
        "total": total,
        "processed": processed,
        "errors": status.get("error_count") or len(status.get("errors") or []),
        "cost_usd": status.get("actual_cost_usd"),
        "complete": bool(status.get("complete")),
        "updated_at": status.get("updated_at"),
        "progress_percent": progress,
    }


def collect_failed_videos() -> dict[str, Any]:
    if not FAILED_VIDEOS.exists():
        return {"count": 0, "path": str(FAILED_VIDEOS)}
    text = FAILED_VIDEOS.read_text(encoding="utf-8", errors="replace")
    return {
        "count": len(re.findall(r"^##\s+", text, flags=re.MULTILINE)),
        "path": str(FAILED_VIDEOS),
        "updated": datetime.fromtimestamp(FAILED_VIDEOS.stat().st_mtime).isoformat(timespec="seconds"),
    }


def collect_costs() -> dict[str, Any]:
    payload = load_json(COST_JSON)
    providers = payload.get("providers") if isinstance(payload, dict) else None
    if not isinstance(providers, dict):
        providers = {}
    return {
        "path": str(COST_JSON),
        "run_id": payload.get("run_id") if isinstance(payload, dict) else None,
        "updated_at": payload.get("updated_at") if isinstance(payload, dict) else None,
        "total_spent_eur": payload.get("total_spent_eur") if isinstance(payload, dict) else 0,
        "providers": providers,
    }


def collect_status() -> dict[str, Any]:
    processes = collect_processes()
    status = {
        "generated_at": now_iso(),
        "http": collect_http(),
        "docker": collect_docker(),
        "models": collect_ollama_models(),
        "qdrant": collect_qdrant(),
        "scheduler": collect_scheduler(),
        "processes": processes,
        "telegram_running": bool(processes.get("telegram_bot")),
        "voice_running": bool(processes.get("voice_capture")),
        "sofinello_running": bool(processes.get("sofinello_batch")),
        "sofinello": collect_sofinello(),
        "failed_videos": collect_failed_videos(),
        "costs": collect_costs(),
        "recent_analysis": list_recent_files(PROJECT_DIR / "analysis", "*.md", limit=6),
        "recent_sync": list_recent_files(DESKTOP_KI / "sync", "*.md", limit=6),
        "recent_backup_logs": list_recent_files(DESKTOP_KI / "logs" / "backup", "*.log", limit=5),
    }
    return status


def status_class(ok: bool) -> str:
    return "good" if ok else "warn"


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def metric_card(label: str, value: Any, note: str = "", klass: str = "") -> str:
    return (
        f'<section class="metric {klass}">'
        f"<span>{esc(label)}</span>"
        f"<strong>{esc(value)}</strong>"
        f"<small>{esc(note)}</small>"
        "</section>"
    )


def render_html(status: dict[str, Any]) -> str:
    http_cards = "\n".join(
        metric_card(name, item.get("status") or "ERR", item.get("url"), status_class(bool(item.get("ok"))))
        for name, item in status["http"].items()
    )
    qdrant_rows = "\n".join(
        f"<tr><td>{esc(name)}</td><td>{esc(info.get('points'))}</td><td>{esc(info.get('vectors'))}</td></tr>"
        for name, info in status["qdrant"]["counts"].items()
    )
    docker_rows = "\n".join(
        f"<tr><td>{esc(item.get('name'))}</td><td>{esc(item.get('status'))}</td><td>{esc(item.get('ports'))}</td></tr>"
        for item in status["docker"]
    )
    scheduler_rows = "\n".join(
        f"<tr><td>{esc(item.get('TaskName'))}</td><td>{esc(item.get('State'))}</td></tr>"
        for item in status["scheduler"]
    )
    model_rows = "\n".join(
        f"<tr><td>{esc(item.get('name'))}</td><td>{esc(item.get('size_gb'))} GB</td></tr>"
        for item in status["models"]
    )
    sofinello = status["sofinello"]
    progress = sofinello.get("progress_percent") or 0
    recent_analysis = "\n".join(
        f"<li><span>{esc(item['name'])}</span><small>{esc(item['updated'])}</small></li>"
        for item in status["recent_analysis"]
    )
    recent_sync = "\n".join(
        f"<li><span>{esc(item['name'])}</span><small>{esc(item['updated'])}</small></li>"
        for item in status["recent_sync"]
    )
    backup_logs = "\n".join(
        f"<li><span>{esc(item['name'])}</span><small>{esc(item['updated'])}</small></li>"
        for item in status["recent_backup_logs"]
    )
    costs = status.get("costs", {})
    cost_rows = "\n".join(
        "<tr>"
        f"<td>{esc(name)}</td>"
        f"<td>{esc(info.get('calls', 0))}</td>"
        f"<td>{esc(info.get('spent_eur', 0))}</td>"
        f"<td>{esc(info.get('remaining_eur'))}</td>"
        f"<td>{esc(info.get('last_model'))}</td>"
        "</tr>"
        for name, info in (costs.get("providers") or {}).items()
    )

    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="60">
  <title>Nexi Imperium Status</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #111316;
      --panel: #1b1f24;
      --line: #303842;
      --text: #edf1f5;
      --muted: #9aa7b4;
      --good: #2fb36f;
      --warn: #d9a441;
      --accent: #62a8ff;
      --bad: #de5f5f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.45;
    }}
    header {{
      padding: 22px 28px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 20px;
    }}
    h1 {{ margin: 0; font-size: 26px; font-weight: 650; letter-spacing: 0; }}
    h2 {{ margin: 0 0 12px; font-size: 17px; font-weight: 650; letter-spacing: 0; }}
    .sub {{ color: var(--muted); font-size: 13px; margin-top: 5px; }}
    .refresh {{
      color: var(--text);
      text-decoration: none;
      border: 1px solid var(--line);
      padding: 8px 11px;
      border-radius: 6px;
      background: #20252b;
      white-space: nowrap;
      font-size: 14px;
    }}
    main {{ padding: 22px 28px 34px; display: grid; gap: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
    .two {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    section.panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-width: 0;
    }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-left: 4px solid var(--accent);
      border-radius: 8px;
      padding: 13px 14px;
      min-height: 102px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .metric.good {{ border-left-color: var(--good); }}
    .metric.warn {{ border-left-color: var(--warn); }}
    .metric span, th {{ color: var(--muted); font-size: 13px; font-weight: 500; }}
    .metric strong {{ font-size: 24px; line-height: 1.1; letter-spacing: 0; }}
    .metric small {{ color: var(--muted); overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ text-align: left; border-bottom: 1px solid var(--line); padding: 9px 7px; vertical-align: top; }}
    td {{ overflow-wrap: anywhere; }}
    .bar {{ height: 12px; background: #2a3038; border-radius: 99px; overflow: hidden; border: 1px solid var(--line); }}
    .bar div {{ height: 100%; width: {progress}%; background: var(--good); }}
    ul {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 9px; }}
    li {{ display: grid; gap: 3px; border-bottom: 1px solid var(--line); padding-bottom: 8px; }}
    li span {{ overflow-wrap: anywhere; }}
    li small {{ color: var(--muted); }}
    @media (max-width: 1100px) {{ .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} .two {{ grid-template-columns: 1fr; }} }}
    @media (max-width: 620px) {{ header {{ align-items: start; flex-direction: column; }} main {{ padding: 16px; }} .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Nexi Imperium Status</h1>
      <div class="sub">Live-Snapshot, automatisch aktualisiert alle 60 Sekunden. Stand: {esc(status['generated_at'])}</div>
    </div>
    <a class="refresh" href="/">Aktualisieren</a>
  </header>
  <main>
    <div class="grid">
      {http_cards}
      {metric_card("Telegram Bot", "laeuft" if status["telegram_running"] else "aus", "Share-Modus und Befehle", status_class(status["telegram_running"]))}
      {metric_card("Sofinello Batch", f"{sofinello.get('processed') or 0}/{sofinello.get('total') or 0}", f"{progress}% · Kosten {sofinello.get('cost_usd') or 0} USD", "warn" if not status["sofinello_running"] else "good")}
      {metric_card("Failed Videos", status["failed_videos"]["count"], status["failed_videos"].get("updated", ""), "warn" if status["failed_videos"]["count"] else "good")}
      {metric_card("Memory Voice", status["qdrant"]["counts"].get("memory_voice", {}).get("points", 0), "Qdrant Punkte", "good")}
      {metric_card("API Costs", costs.get("total_spent_eur", 0), f"Run {costs.get('run_id') or 'n/a'}", "warn")}
    </div>

    <section class="panel">
      <h2>Sofinello Fortschritt</h2>
      <div class="bar"><div></div></div>
      <p class="sub">Letztes Update: {esc(sofinello.get('updated_at'))} · Laufender Prozess: {esc(status['sofinello_running'])}</p>
    </section>

    <div class="two">
      <section class="panel">
        <h2>Docker</h2>
        <table><thead><tr><th>Name</th><th>Status</th><th>Ports</th></tr></thead><tbody>{docker_rows}</tbody></table>
      </section>
      <section class="panel">
        <h2>Qdrant Wissen</h2>
        <table><thead><tr><th>Collection</th><th>Points</th><th>Vectors</th></tr></thead><tbody>{qdrant_rows}</tbody></table>
      </section>
    </div>

    <div class="two">
      <section class="panel">
        <h2>Scheduler</h2>
        <table><thead><tr><th>Task</th><th>Status</th></tr></thead><tbody>{scheduler_rows}</tbody></table>
      </section>
      <section class="panel">
        <h2>API Costs</h2>
        <table><thead><tr><th>API</th><th>Calls</th><th>EUR</th><th>Rest</th><th>Modell</th></tr></thead><tbody>{cost_rows}</tbody></table>
      </section>
    </div>

    <section class="panel">
      <h2>Ollama Modelle</h2>
      <table><thead><tr><th>Modell</th><th>Groesse</th></tr></thead><tbody>{model_rows}</tbody></table>
    </section>

    <div class="two">
      <section class="panel">
        <h2>Letzte Analysen</h2>
        <ul>{recent_analysis or "<li><span>Keine Analyse-Dateien gefunden</span></li>"}</ul>
      </section>
      <section class="panel">
        <h2>KI-Sync Exporte</h2>
        <ul>{recent_sync or "<li><span>Keine Sync-Dateien gefunden</span></li>"}</ul>
      </section>
    </div>

    <section class="panel">
      <h2>Backup Logs</h2>
      <ul>{backup_logs or "<li><span>Keine Backup-Logs gefunden</span></li>"}</ul>
    </section>
  </main>
</body>
</html>"""


def write_dashboard(status: dict[str, Any]) -> None:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_JSON.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    STATUS_HTML.write_text(render_html(status), encoding="utf-8")


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        status = collect_status()
        write_dashboard(status)
        if self.path.startswith("/status.json"):
            payload = json.dumps(status, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        payload = render_html(status).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def serve(port: int) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"Dashboard: http://127.0.0.1:{port}")
    server.serve_forever()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nexi local Imperium status dashboard.")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=int(os.environ.get("NEXI_STATUS_PORT", "8765")))
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    status = collect_status()
    write_dashboard(status)
    if args.serve:
        serve(args.port)
    else:
        print(json.dumps({"ok": True, "html": str(STATUS_HTML), "json": str(STATUS_JSON)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
