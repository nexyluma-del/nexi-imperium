#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from cost_tracker import record_call, reset_run
from qdrant_video_knowledge import upsert_video_knowledge
from telegram_common import send_message_if_configured


PROJECT_DIR = Path(__file__).resolve().parents[1]
ROOT = Path("/mnt/c/Users/nexil/Desktop/Instagram Videos")
BACKUP_LOG_DIR = Path("/mnt/c/Users/nexil/Desktop/KI/logs/backup")
LESSONS = Path("/mnt/c/Users/nexil/Desktop/KI/LESSONS.md")
RUN_ID = "run-001-validation"
RUN_DIR = PROJECT_DIR / "videos" / "_runs" / RUN_ID
WORK_DIR = RUN_DIR / "work"
REPORT_MD = RUN_DIR / "run-001-validation.md"
REPORT_JSON = RUN_DIR / "run-001-validation.json"
SELECTION_JSON = RUN_DIR / "selection-50.json"
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
NASA_TERMS = ("NASA", "LADEE", "LLCD", "Lunar Laser Communication")
ALLOWED_CATEGORIES = [
    "01-IT",
    "02-IT-HACKS",
    "03-KI-IT",
    "04-TECHNIK",
    "05-NEWS",
    "06-FINANZEN",
    "07-FILME",
    "08-MUSIK",
    "09-SONSTIGES",
    "10-SOFINELLO",
    "_unsortiert",
]

SOFINELLO_FOLDERS = {
    "Sofinello",
    "Sofinello Videos",
    "Sofinello Gerichte",
    "Sofinello To-Do",
}

FOLDER_QUOTAS = [
    ("Sofinello Videos", 2),
    ("Sofinello", 1),
    ("Sofinello Gerichte", 1),
    ("Sofinello To-Do", 1),
    ("KI Tools", 4),
    ("IT Hacks", 3),
    ("Hacking", 2),
    ("IT SICHERHEIT", 2),
    ("Technick", 2),
    ("Erfindungen", 2),
    ("News", 4),
    ("Finanzen", 4),
    ("Krypto", 2),
    ("Business", 2),
    ("KIFilme", 3),
    ("Musik", 2),
    ("Techno", 1),
    ("Web Sites", 2),
    ("Content Ideen", 2),
    ("Creatives Marketing", 1),
    ("Datenschutz Sicherheit", 1),
    ("Wissenswert & Lernen", 2),
    ("Produkte", 1),
    ("Motivation", 1),
    ("Money Motivation", 1),
]

FOLDER_EXPECTED = {
    "KI Tools": "03-KI-IT",
    "IT Hacks": "02-IT-HACKS",
    "Hacking": "02-IT-HACKS",
    "IT SICHERHEIT": "02-IT-HACKS",
    "Datenschutz Sicherheit": "02-IT-HACKS",
    "Technick": "04-TECHNIK",
    "Erfindungen": "04-TECHNIK",
    "News": "05-NEWS",
    "Finanzen": "06-FINANZEN",
    "Krypto": "06-FINANZEN",
    "Business": "06-FINANZEN",
    "KIFilme": "07-FILME",
    "Musik": "08-MUSIK",
    "Techno": "08-MUSIK",
    "Web Sites": "01-IT",
}

FOLDER_INTENT_ROUTES = {
    **FOLDER_EXPECTED,
    "Sofinello": "10-SOFINELLO",
    "Sofinello Videos": "10-SOFINELLO",
    "Sofinello Gerichte": "10-SOFINELLO",
    "Sofinello To-Do": "10-SOFINELLO",
}

CATEGORY_QUESTIONS = {
    "01-IT": "Was wird technisch gezeigt, welchen Nutzen hat es fuer Nexis KI-Imperium, und welche naechsten Schritte sind sinnvoll?",
    "02-IT-HACKS": "Was wird technisch gezeigt? Erklaere es defensiv, legal und konzeptionell. Welche sicheren Lernschritte ergeben sich daraus?",
    "03-KI-IT": "Welches KI-Tool oder welcher Workflow wird gezeigt? Wie kann Nexi das praktisch und legal nutzen?",
    "04-TECHNIK": "Welche Technik, Erfindung oder Methode wird gezeigt, und ist sie realistisch nutzbar?",
    "05-NEWS": "Was stimmt hiervon, was ist jetzt moeglich, und was ist Spekulation?",
    "06-FINANZEN": "Welche Finanzidee oder Strategie wird gezeigt? Was ist belegbar, was ist spekulativ, und welche Pruefung waere noetig?",
    "07-FILME": "Welche Film-, Serien-, Story- oder Produktionsidee steckt darin, und wie kann Nexi sie kreativ nutzen?",
    "08-MUSIK": "Welche Musikidee, Sound-Aesthetik oder Produktionsmethode wird gezeigt, und wie kann Nexi sie nutzen?",
    "09-SONSTIGES": "Was ist der Kerninhalt, lohnt sich das fuer Nexis Wissensdatenbank, und wohin sollte es spaeter einsortiert werden?",
    "10-SOFINELLO": "Was zeigt dieses Sofinello-Video, welche Zutaten/Produkte/Claims sind erkennbar, und was muss compliance-seitig geprueft werden?",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return cleaned[:90] or "video"


def wsl_to_windows(path: str | Path | None) -> str | None:
    if path is None:
        return None
    value = str(path)
    if value.startswith("/mnt/c/"):
        return "C:\\" + value[len("/mnt/c/") :].replace("/", "\\")
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def read_text(path: Path, limit: int | None = None) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="strict")
    except UnicodeError:
        text = path.read_text(encoding="utf-16", errors="replace")
    return text[:limit] if limit else text


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_restic_snapshot() -> dict[str, Any]:
    logs = sorted(BACKUP_LOG_DIR.glob("backup-*.log"), key=lambda item: item.stat().st_mtime, reverse=True)
    for log in logs:
        text = read_text(log)
        matches = re.findall(r"snapshot\s+([0-9a-f]+)\s+saved", text)
        if matches:
            return {"snapshot_id": matches[-1], "log": str(log), "log_windows": wsl_to_windows(log)}
    return {"snapshot_id": None, "log": None, "warning": "Kein Restic-Snapshot im Backup-Log gefunden."}


def list_videos(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    files = [item for item in folder.rglob("*") if item.is_file() and item.suffix.lower() in VIDEO_SUFFIXES]
    return sorted(files, key=lambda item: (item.stat().st_size, item.as_posix().lower()))


def pick_varied(files: list[Path], count: int, used: set[Path]) -> list[Path]:
    available = [item for item in files if item not in used]
    if count <= 0 or not available:
        return []
    if len(available) <= count:
        picked = available
    else:
        positions = [round(index * (len(available) - 1) / max(1, count - 1)) for index in range(count)]
        picked = []
        for pos in positions:
            candidate = available[pos]
            if candidate not in picked:
                picked.append(candidate)
        cursor = 0
        while len(picked) < count and cursor < len(available):
            if available[cursor] not in picked:
                picked.append(available[cursor])
            cursor += 1
    used.update(picked)
    return picked


def select_50() -> list[dict[str, Any]]:
    used: set[Path] = set()
    selected: list[dict[str, Any]] = []
    for folder_name, count in FOLDER_QUOTAS:
        folder = ROOT / folder_name
        for path in pick_varied(list_videos(folder), count, used):
            selected.append(
                {
                    "source_path": str(path),
                    "source_path_windows": wsl_to_windows(path),
                    "top_folder": folder_name,
                    "expected_category": "10-SOFINELLO" if folder_name in SOFINELLO_FOLDERS else FOLDER_EXPECTED.get(folder_name),
                    "must_be_sofinello": folder_name in SOFINELLO_FOLDERS,
                    "size_mb": round(path.stat().st_size / 1024 / 1024, 3),
                }
            )
    if len(selected) < 50:
        fallback_folders = [item for item in ROOT.iterdir() if item.is_dir() and item.name != "🔒"]
        for folder in sorted(fallback_folders, key=lambda item: item.name.lower()):
            if len(selected) >= 50:
                break
            for path in pick_varied(list_videos(folder), 1, used):
                selected.append(
                    {
                        "source_path": str(path),
                        "source_path_windows": wsl_to_windows(path),
                        "top_folder": folder.name,
                        "expected_category": "10-SOFINELLO" if folder.name in SOFINELLO_FOLDERS else FOLDER_EXPECTED.get(folder.name),
                        "must_be_sofinello": folder.name in SOFINELLO_FOLDERS,
                        "size_mb": round(path.stat().st_size / 1024 / 1024, 3),
                    }
                )
                if len(selected) >= 50:
                    break
    return selected[:50]


def run_command(command: list[str], timeout: int, cwd: Path = PROJECT_DIR) -> tuple[str, float]:
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    output = (completed.stdout or "") + (completed.stderr or "")
    elapsed = round(time.perf_counter() - started, 3)
    if completed.returncode != 0:
        raise RuntimeError(output[-4000:])
    return output, elapsed


def has_audio_stream(path: Path) -> bool:
    try:
        output, _elapsed = run_command(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                str(path),
            ],
            timeout=60,
        )
    except Exception:
        return False
    return bool(output.strip())


def ffprobe_duration(path: Path) -> float | None:
    try:
        output, _elapsed = run_command(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ],
            timeout=60,
        )
        return round(float(output.strip()), 3)
    except Exception:
        return None


def parse_prefixed_path(output: str, prefix: str) -> str | None:
    for line in output.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def transcribe_or_no_audio(path: Path, item_dir: Path) -> tuple[Path, dict[str, Any]]:
    item_dir.mkdir(parents=True, exist_ok=True)
    if not has_audio_stream(path):
        transcript = item_dir / "Whisper-Transkript.txt"
        transcript.write_text(
            "NO_AUDIO_VERIFIED: ffprobe hat keinen Audio-Stream gefunden. Visuelle Analyse ist erlaubt.\n",
            encoding="utf-8",
        )
        return transcript, {"no_audio_verified": True, "seconds": 0.0}

    output, elapsed = run_command(
        [
            str(PROJECT_DIR / ".venv" / "bin" / "python"),
            str(PROJECT_DIR / "scripts" / "transcribe.py"),
            str(path),
            "--data-class",
            "D2",
            "--output-dir",
            str(item_dir),
        ],
        timeout=2400,
    )
    transcript_txt = parse_prefixed_path(output, "Transcript TXT")
    if not transcript_txt:
        raise RuntimeError("Transkript-Pfad konnte aus transcribe.py Output nicht gelesen werden.")
    transcript = item_dir / "Whisper-Transkript.txt"
    source = Path(transcript_txt)
    if source.resolve() != transcript.resolve():
        transcript.write_text(source.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    return transcript, {"no_audio_verified": False, "seconds": elapsed}


def qwen_generate(prompt: str, timeout: int = 600) -> str:
    payload = json.dumps(
        {
            "model": "qwen3:30b",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": 8192},
        }
    ).encode("utf-8")
    request = Request("http://127.0.0.1:11434/api/generate", data=payload, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str(data.get("response") or "")


def extract_json(text: str) -> dict[str, Any]:
    clean = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I).strip()
    match = re.search(r"\{.*\}", clean, flags=re.S)
    if not match:
        raise RuntimeError(f"Klassifizierer gab kein JSON aus: {text[:1000]}")
    return json.loads(match.group(0))


def normalize_category(value: str) -> str:
    raw = value.strip().upper().replace(" ", "-")
    aliases = {
        "IT": "01-IT",
        "01-IT": "01-IT",
        "IT-HACKS": "02-IT-HACKS",
        "02-IT-HACKS": "02-IT-HACKS",
        "KI-IT": "03-KI-IT",
        "KI": "03-KI-IT",
        "AI": "03-KI-IT",
        "03-KI-IT": "03-KI-IT",
        "TECHNIK": "04-TECHNIK",
        "TECHNICK": "04-TECHNIK",
        "04-TECHNIK": "04-TECHNIK",
        "NEWS": "05-NEWS",
        "05-NEWS": "05-NEWS",
        "FINANZEN": "06-FINANZEN",
        "FINANCE": "06-FINANZEN",
        "KRYPTO": "06-FINANZEN",
        "06-FINANZEN": "06-FINANZEN",
        "FILME": "07-FILME",
        "FILM": "07-FILME",
        "07-FILME": "07-FILME",
        "MUSIK": "08-MUSIK",
        "08-MUSIK": "08-MUSIK",
        "SONSTIGES": "09-SONSTIGES",
        "09-SONSTIGES": "09-SONSTIGES",
        "SOFINELLO": "10-SOFINELLO",
        "10-SOFINELLO": "10-SOFINELLO",
        "_UNSORTIERT": "_unsortiert",
        "UNSORTIERT": "_unsortiert",
    }
    return aliases.get(raw, value)


def classify(path: Path, top_folder: str, transcript: Path) -> dict[str, Any]:
    excerpt = read_text(transcript, limit=6000)
    folder_route = FOLDER_INTENT_ROUTES.get(top_folder)
    if folder_route:
        return {
            "category": folder_route,
            "confidence": 0.98,
            "reason": f"Folder-Intent-Regel: Ordner '{top_folder}' routet stabil nach {folder_route}.",
            "seconds": 0.0,
            "raw": "deterministic-folder-intent",
        }

    prompt = f"""Du bist Nexis lokaler Routing-Klassifizierer. Antworte NUR als JSON.

Erlaubte Kategorien:
{json.dumps(ALLOWED_CATEGORIES, ensure_ascii=False)}

Regeln:
- Der Ordnername ist ein starkes Signal fuer Nexis Geschaeftsabsicht. Wenn der Ordner eindeutig ist, folge dem Ordner statt einzelne Transcript-Woerter zu ueberbewerten.
- Wenn der Ordnername mit "Sofinello" beginnt, ist die Kategorie PFLICHT: 10-SOFINELLO. Das gilt auch fuer Meditation, Frequenzen, Third Eye, Dr. Sebi, Kraeuter, natuerliche Heilung, Mixturen, Nahrungsergaenzung, Verpackungen, Rezepte oder allgemeine Gesundheitsinhalte in diesem Ordner.
- Gesundheitsbezogene Inhalte aus Sofinello-Ordnern duerfen NIEMALS 09-SONSTIGES oder _unsortiert werden.
- Sofinello, Dr. Sebi, Kraeuter, natuerliche Heilung, Mixturen, Nahrungsergaenzung, Verpackungen oder Rezepturen fuer Nexis Heilungsfirma => 10-SOFINELLO.
- Cybersecurity, Hacking, IT-Sicherheit, Tools gegen Angriffe => 02-IT-HACKS.
- KI-Tools, Agenten, Automatisierung, LLMs, Coding mit KI => 03-KI-IT.
- Filmproduktion, KI-Filme, Serienideen, Storytelling, Trailer, visuelle Filmproduktion => 07-FILME.
- Webseiten, Website-Bau, Website-Cloning, Frontend, Apps, Dev-Tools ohne klaren Security-Fokus => 01-IT.
- Finanz-, Krypto-, Business-, Markt-, Geldsystem- oder Investmentthemen => 06-FINANZEN.
- News-Ordner bleibt 05-NEWS, ausser Nexi markiert es spaeter manuell als Finanzen.
- Unklare Faelle => _unsortiert.

Datei: {path.name}
Ordner: {top_folder}
Transkript-Auszug:
{excerpt}

JSON-Schema:
{{"category":"03-KI-IT","confidence":0.0,"reason":"kurz"}}
"""
    started = time.perf_counter()
    response = qwen_generate(prompt)
    elapsed = round(time.perf_counter() - started, 3)
    payload = extract_json(response)
    category = normalize_category(str(payload.get("category") or ""))
    if category not in ALLOWED_CATEGORIES:
        raise RuntimeError(f"Ungueltige Kategorie vom Klassifizierer: {payload}")
    return {
        "category": category,
        "confidence": float(payload.get("confidence") or 0),
        "reason": str(payload.get("reason") or ""),
        "seconds": elapsed,
        "raw": response[:2000],
    }


def parse_json_from_output(output: str) -> dict[str, Any]:
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end <= start:
        raise RuntimeError(f"Kein JSON im Pipeline-Output:\n{output[-3000:]}")
    return json.loads(output[start : end + 1])


def gemini_api_for_model(model: str) -> str:
    return "gemini-pro" if "pro" in model else "gemini-flash"


def model_for_category(category: str) -> str:
    return "gemini-2.5-pro" if category == "10-SOFINELLO" else "gemini-2.5-flash"


def run_gemini_pipeline(entry: dict[str, Any], transcript: Path, index: int, remaining: int, started_at: float) -> dict[str, Any]:
    category = entry["classified"]["category"]
    model = model_for_category(category)
    max_cost = "2.50" if model.endswith("pro") else "0.75"
    question = CATEGORY_QUESTIONS.get(category, CATEGORY_QUESTIONS["09-SONSTIGES"])
    source = Path(entry["source_path"])
    slug = f"{RUN_ID}-{index:03d}-{entry['sha256'][:12]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    output, elapsed = run_command(
        [
            str(PROJECT_DIR / ".venv" / "bin" / "python"),
            str(PROJECT_DIR / "scripts" / "run_video_pipeline.py"),
            "--video-file",
            str(source),
            "--data-class",
            "D2",
            "--topic",
            category,
            "--question",
            question,
            "--max-cost-eur",
            max_cost,
            "--max-video-mb",
            "250",
            "--max-duration-sec",
            "900",
            "--approve-large",
            "--model",
            model,
            "--slug",
            slug,
            "--existing-transcript",
            str(transcript),
        ],
        timeout=4800,
    )
    payload = parse_json_from_output(output)
    if not payload.get("ok"):
        raise RuntimeError(payload.get("error") or output[-3000:])
    analysis_markdown = Path(payload["files"]["analysis_markdown"])
    transcript_txt = Path(payload["files"]["transcript_txt"])
    cost = float(payload.get("cost", {}).get("estimated_actual_usd") or 0.0)
    qdrant = upsert_video_knowledge(
        url=f"local://{wsl_to_windows(source)}",
        topic=category,
        data_class="D2",
        questions=[question],
        analysis_markdown=analysis_markdown,
        transcript_txt=transcript_txt,
        cost_usd=cost,
        slug=payload["slug"],
        provenance={
            **(payload.get("provenance") or {}),
            "run_id": RUN_ID,
            "source_path": str(source),
            "source_path_windows": wsl_to_windows(source),
            "classified": entry["classified"],
        },
    )
    payload["qdrant"] = qdrant
    payload["steps"]["qdrant_seconds"] = 0.0
    payload["steps"]["gemini_pipeline_seconds"] = elapsed
    processed = max(1, index)
    rate = processed / max(0.01, ((time.perf_counter() - started_at) / 3600))
    record_call(
        api_name=gemini_api_for_model(model),
        model=model,
        cost_usd=cost,
        run_id=RUN_ID,
        video_id=payload.get("video_id"),
        category=category,
        remaining_videos=remaining,
        rate_videos_per_hour=rate,
    )
    text = read_text(analysis_markdown)
    for term in NASA_TERMS:
        if term.lower() in text.lower():
            raise RuntimeError(f"Anti-NASA-Waechter Treffer in {analysis_markdown}: {term}")
    return payload


def existing_sha_index() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for manifest in (PROJECT_DIR / "videos").glob("*/*/pipeline-manifest.json"):
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            if str(payload.get("requested_slug") or "").startswith(RUN_ID) or str(payload.get("slug") or "").startswith(RUN_ID):
                continue
            sha = (payload.get("provenance") or {}).get("video_sha256")
            if sha and sha not in result:
                result[sha] = {
                    "manifest": str(manifest),
                    "video_dir": str(manifest.parent),
                    "topic": payload.get("topic"),
                    "video_id": payload.get("video_id"),
                }
        except Exception:
            continue
    return result


def write_reference_manifest(entry: dict[str, Any], original: dict[str, Any]) -> Path:
    category = entry.get("classified", {}).get("category") or original.get("topic") or "_unsortiert"
    video_id = slugify(f"{Path(entry['source_path']).stem}-{entry['sha256'][:12]}")
    target = PROJECT_DIR / "videos" / category / video_id
    target.mkdir(parents=True, exist_ok=True)
    manifest = target / "reference-manifest.json"
    write_json(
        manifest,
        {
            "type": "duplicate-reference",
            "run_id": RUN_ID,
            "source_path": entry["source_path"],
            "source_path_windows": entry["source_path_windows"],
            "sha256": entry["sha256"],
            "references": original,
            "created_at": now_iso(),
        },
    )
    return manifest


def run_nasa_audit() -> dict[str, Any]:
    collections = ["video_knowledge", "open-webui_knowledge", "sofinello_knowledge", "memory_voice"]
    entries = []
    counts = {}
    for collection in collections:
        offset = None
        points = []
        while True:
            body: dict[str, Any] = {"limit": 100, "with_payload": True, "with_vectors": False}
            if offset is not None:
                body["offset"] = offset
            request = Request(
                f"http://127.0.0.1:6333/collections/{collection}/points/scroll",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urlopen(request, timeout=60) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except Exception:
                break
            result = payload.get("result") or {}
            points.extend(result.get("points") or [])
            offset = result.get("next_page_offset")
            if offset is None:
                break
        counts[collection] = len(points)
        for point in points:
            payload = point.get("payload") or {}
            text = json.dumps(payload, ensure_ascii=False)
            for key in ("analysis_markdown", "raw_analysis_markdown", "transcript_txt"):
                file_value = payload.get(key)
                if file_value:
                    candidate = Path(str(file_value))
                    if candidate.exists():
                        text += "\n" + read_text(candidate, limit=12000)
            found = [term for term in NASA_TERMS if term.lower() in text.lower()]
            if found:
                entries.append({"collection": collection, "id": point.get("id"), "terms": found, "payload": payload})
    return {
        "generated_at": now_iso(),
        "collection_counts": counts,
        "match_count": len(entries),
        "suspect_count": len(entries),
        "entries": entries,
    }


def render_report(result: dict[str, Any]) -> str:
    rows = []
    for item in result["items"]:
        rows.append(
            "| {index} | {folder} | {category} | {model} | {status} | {cost:.6f} | {seconds:.1f} | {path} |".format(
                index=item["index"],
                folder=item.get("top_folder", ""),
                category=item.get("classified", {}).get("category") or item.get("status"),
                model=item.get("model") or "",
                status=item.get("status"),
                cost=float(item.get("cost_usd") or 0),
                seconds=float(item.get("total_seconds") or 0),
                path=wsl_to_windows(item.get("source_path")) or item.get("source_path"),
            )
        )
    fulltexts = []
    for item in [entry for entry in result["items"] if entry.get("analysis_markdown")][:5]:
        path = Path(item["analysis_markdown"])
        fulltexts.extend(
            [
                f"### Volltext {item['index']} - {item.get('classified', {}).get('category')}",
                "",
                f"Pfad: `{wsl_to_windows(path)}`",
                "",
                read_text(path, limit=18000),
                "",
            ]
        )
    accuracy = result["classifier"].get("accuracy_percent")
    return "\n".join(
        [
            "# Run 001 - Validation 50",
            "",
            f"Stand: {result['finished_at']}",
            f"Restic Snapshot vor Start: `{result['restic'].get('snapshot_id')}`",
            f"Backup-Log: `{result['restic'].get('log_windows')}`",
            f"Lessons beachtet: `{result['lessons_scan'].get('nasa_lesson_present')}`",
            "",
            "## Ergebnis",
            "",
            f"- Status: `{result['status']}`",
            f"- Videos geplant: `{result['planned_count']}`",
            f"- Gemini verarbeitet: `{result['gemini_processed_count']}`",
            f"- Duplikat-Referenzen: `{result['duplicate_count']}`",
            f"- _unsortiert ohne Gemini: `{result['unsorted_count']}`",
            f"- Fehler: `{len(result['errors'])}`",
            f"- Kosten gesamt USD/EUR Guard: `{result['cost_total_usd']:.6f}`",
            f"- Klassifizierer-Genauigkeit Heuristik: `{accuracy}` %",
            f"- Sofinello Pflichtpruefung: `{result['classifier'].get('sofinello_check')}`",
            "",
            "## Tabelle 50 Videos",
            "",
            "| # | Ordner | Klasse | Modell | Status | Cost | Sekunden | Quelle |",
            "|---:|---|---|---|---|---:|---:|---|",
            *rows,
            "",
            "## Zeiten pro Stufe",
            "",
            *[f"- {name}: {seconds:.1f}s" for name, seconds in result["timings"].items()],
            "",
            "## Cost-Reporting",
            "",
            f"- Cost pro Video Durchschnitt: `{result['cost_per_gemini_video_usd']:.6f}`",
            f"- Hochrechnung 3000 x 1.3: `{result['projection_3000_eur_with_safety']:.2f}` EUR",
            f"- Hartes Cap geplant: `160` EUR, Telegram-Warnung ab `120` EUR",
            "",
            "## Aktuelles Guthaben",
            "",
            result["balance_note"],
            "",
            "## Anti-NASA Audit",
            "",
            "```json",
            json.dumps(result.get("nasa_audit"), ensure_ascii=False, indent=2),
            "```",
            "",
            "## 5 Volltexte",
            "",
            *fulltexts,
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Nexi validation stage 1 with 50 local videos.")
    parser.add_argument("--max-videos", type=int, default=50)
    parser.add_argument("--min-sofinello", type=int, default=5)
    parser.add_argument("--max-total-cost-eur", type=float, default=160.0)
    parser.add_argument("--warning-cost-eur", type=float, default=120.0)
    args = parser.parse_args()

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    started_at = time.perf_counter()
    restic = latest_restic_snapshot()
    lessons_text = read_text(LESSONS) if LESSONS.exists() else ""
    lessons_scan = {
        "path": str(LESSONS),
        "nasa_lesson_present": all(term.lower() in lessons_text.lower() for term in ("NASA", "slug", "statisch")),
    }
    reset_run(RUN_ID, "Stufe 1 Validierungs-Run 50: Gemini Counter auf 0 gesetzt.")
    selected = select_50()
    if len(selected) != args.max_videos:
        raise RuntimeError(f"Auswahl hat {len(selected)} statt {args.max_videos} Videos.")
    if sum(1 for item in selected if item["must_be_sofinello"]) < args.min_sofinello:
        raise RuntimeError("Auswahl enthaelt nicht genug Sofinello-Videos.")
    write_json(SELECTION_JSON, selected)

    result: dict[str, Any] = {
        "run_id": RUN_ID,
        "started_at": now_iso(),
        "finished_at": None,
        "status": "running",
        "restic": restic,
        "lessons_scan": lessons_scan,
        "planned_count": len(selected),
        "items": [],
        "errors": [],
        "timings": {"sha": 0.0, "transcribe": 0.0, "classify": 0.0, "gemini": 0.0, "qdrant": 0.0},
        "cost_total_usd": 0.0,
        "gemini_processed_count": 0,
        "duplicate_count": 0,
        "unsorted_count": 0,
        "classifier": {},
        "balance_note": (
            "Gemini/Anthropic/OpenAI Restguthaben ist ueber API-Keys nicht direkt maschinell auslesbar. "
            "Der Counter misst ab Run-Start Verbrauch ab 0 EUR. Fuer Restguthaben-Alarme koennen "
            "GEMINI_FLASH_INITIAL_CREDIT_EUR und GEMINI_PRO_INITIAL_CREDIT_EUR gesetzt werden."
        ),
        "nasa_audit": None,
    }
    write_json(REPORT_JSON, result)
    REPORT_MD.write_text(render_report({**result, "finished_at": now_iso(), "cost_per_gemini_video_usd": 0, "projection_3000_eur_with_safety": 0}), encoding="utf-8")

    sha_seen = existing_sha_index()
    classifier_total = 0
    classifier_hits = 0
    sofinello_ok = True

    try:
        for index, selected_item in enumerate(selected, start=1):
            item_started = time.perf_counter()
            source = Path(selected_item["source_path"])
            item_dir = WORK_DIR / f"{index:03d}-{slugify(source.stem)}"
            item = {**selected_item, "index": index, "status": "started", "timings": {}}
            result["items"].append(item)
            write_json(REPORT_JSON, result)

            t0 = time.perf_counter()
            sha = file_sha256(source)
            item["sha256"] = sha
            item["duration_seconds"] = ffprobe_duration(source)
            item["timings"]["sha_seconds"] = round(time.perf_counter() - t0, 3)
            result["timings"]["sha"] += item["timings"]["sha_seconds"]

            if sha in sha_seen:
                item["status"] = "duplicate_reference"
                item["reference_manifest"] = str(write_reference_manifest(item, sha_seen[sha]))
                item["reference_manifest_windows"] = wsl_to_windows(item["reference_manifest"])
                item["total_seconds"] = round(time.perf_counter() - item_started, 3)
                result["duplicate_count"] += 1
                continue

            transcript, transcribe_meta = transcribe_or_no_audio(source, item_dir)
            item["transcript"] = str(transcript)
            item["transcript_windows"] = wsl_to_windows(transcript)
            item["no_audio_verified"] = transcribe_meta["no_audio_verified"]
            item["timings"]["transcribe_seconds"] = transcribe_meta["seconds"]
            result["timings"]["transcribe"] += transcribe_meta["seconds"]

            classified = classify(source, selected_item["top_folder"], transcript)
            item["classified"] = classified
            item["timings"]["classify_seconds"] = classified["seconds"]
            result["timings"]["classify"] += classified["seconds"]

            expected = selected_item.get("expected_category")
            if expected:
                classifier_total += 1
                if classified["category"] == expected:
                    classifier_hits += 1
            if selected_item["must_be_sofinello"] and classified["category"] != "10-SOFINELLO":
                sofinello_ok = False
                raise RuntimeError(
                    f"Klassifizierer-Fehler: Sofinello-Video {source} wurde als {classified['category']} klassifiziert."
                )
            if classified["category"] == "_unsortiert":
                item["status"] = "waiting_manual_sort"
                item["total_seconds"] = round(time.perf_counter() - item_started, 3)
                result["unsorted_count"] += 1
                continue

            if result["cost_total_usd"] >= args.max_total_cost_eur:
                raise RuntimeError("Budget-Cap erreicht.")
            payload = run_gemini_pipeline(item, transcript, index, len(selected) - index, started_at)
            item["status"] = "ok"
            item["model"] = payload.get("cost", {}).get("model") or model_for_category(classified["category"])
            item["video_dir"] = payload.get("video_dir")
            item["analysis_markdown"] = payload.get("files", {}).get("analysis_markdown")
            item["summary_markdown"] = payload.get("files", {}).get("summary_markdown")
            item["word_report"] = payload.get("files", {}).get("word_report")
            item["qdrant"] = payload.get("qdrant")
            item["cost_usd"] = float(payload.get("cost", {}).get("estimated_actual_usd") or 0.0)
            item["timings"]["gemini_seconds"] = float(payload.get("steps", {}).get("gemini_pipeline_seconds") or 0.0)
            item["total_seconds"] = round(time.perf_counter() - item_started, 3)
            result["timings"]["gemini"] += item["timings"]["gemini_seconds"]
            result["cost_total_usd"] = round(result["cost_total_usd"] + item["cost_usd"], 6)
            result["gemini_processed_count"] += 1
            sha_seen[sha] = {"manifest": payload.get("files", {}).get("run_manifest"), "video_dir": payload.get("video_dir"), "topic": classified["category"], "video_id": payload.get("video_id")}

            if result["cost_total_usd"] >= args.warning_cost_eur:
                send_message_if_configured(f"Kostenwarnung {RUN_ID}: {result['cost_total_usd']:.2f} EUR erreicht.")
            if index % 10 == 0:
                audit = run_nasa_audit()
                result["nasa_audit"] = audit
                if int(audit.get("suspect_count") or audit.get("match_count") or 0) > 0:
                    raise RuntimeError("Anti-NASA-Audit meldet Treffer in Qdrant.")
            write_json(REPORT_JSON, result)

        result["nasa_audit"] = run_nasa_audit()
        if int(result["nasa_audit"].get("suspect_count") or result["nasa_audit"].get("match_count") or 0) > 0:
            raise RuntimeError("Anti-NASA-Audit meldet Treffer in Qdrant.")
        result["status"] = "stopped_after_50_for_review"
    except Exception as exc:  # noqa: BLE001
        result["status"] = "stopped_with_error"
        result["errors"].append({"at": now_iso(), "error": str(exc)})
        send_message_if_configured(f"Pipeline-Stop {RUN_ID}: {exc}")
    finally:
        result["finished_at"] = now_iso()
        result["classifier"] = {
            "checked_against_folder_heuristic": classifier_total,
            "matches": classifier_hits,
            "accuracy_percent": round((classifier_hits / classifier_total * 100), 2) if classifier_total else None,
            "sofinello_check": "ok" if sofinello_ok else "failed",
        }
        result["timings"] = {key: round(value, 3) for key, value in result["timings"].items()}
        result["cost_total_usd"] = round(float(result["cost_total_usd"]), 6)
        processed = max(1, int(result["gemini_processed_count"]))
        result["cost_per_gemini_video_usd"] = round(result["cost_total_usd"] / processed, 6)
        result["projection_3000_eur_with_safety"] = round(result["cost_per_gemini_video_usd"] * 3000 * 1.3, 2)
        write_json(REPORT_JSON, result)
        REPORT_MD.write_text(render_report(result), encoding="utf-8")
        print(json.dumps({"status": result["status"], "processed": result["gemini_processed_count"], "cost_usd": result["cost_total_usd"], "report": str(REPORT_MD)}, ensure_ascii=False, indent=2))

    return 0 if result["status"] == "stopped_after_50_for_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
