#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from qdrant_video_knowledge import QDRANT_URL, embedding


PROJECT_DIR = Path(__file__).resolve().parents[1]
DESKTOP_KI = Path("/mnt/c/Users/nexil/Desktop/KI")
DNA_FILE = DESKTOP_KI / "v3" / "chiefs" / "01-MEMORY-COFOUNDER-FINAL.md"
KI_PUSH_DIR = DESKTOP_KI / "KI-PUSH"
OLLAMA_URL = "http://127.0.0.1:11434"
MEMORY_MODEL = "qwen3:30b"
FAST_MODEL = "qwen3:4b"
COLLECTIONS = ("memory_voice", "video_knowledge", "sofinello_knowledge")
MAX_CONTEXT_CHARS = 14000


COMPACT_DNA = """
Du bist Memory-KI, Nexis lokales zweites Gehirn und Co-Founder.
Sprich Nexi direkt mit Du an. Ton: locker, ehrlich, loyal, kurz und klar.
Wahrheit vor Komfort. Kein Ja-Sagen, keine Schmeichelei.
Nutze Nexis lokale Qdrant-Wissenssammlung als Quelle Nummer 1.
Markiere Unsicherheit offen. Nenne Quellen, Collection und Datei/Pfad.
Keine Cloud, keine Ausgaben, keine externen Aktionen ohne Approval.
Respektiere Heilungs-Themen, aber formuliere ohne Heilversprechen.
Standard: kurz und brauchbar. Mehr Detail nur wenn Nexi es will.
Keine Emojis. Keine Fakten erfinden, wenn Quellen nicht reichen.
"""


def read_text(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] if limit else text


def memory_system_prompt() -> str:
    dna = read_text(DNA_FILE, limit=12000)
    return "\n\n".join(
        [
            COMPACT_DNA.strip(),
            "Finale Memory-DNA aus Datei:",
            dna,
        ]
    ).strip()


def qdrant_collection_exists(collection: str) -> bool:
    response = requests.get(f"{QDRANT_URL}/collections/{collection}", timeout=10)
    return response.status_code == 200


def qdrant_points_count(collection: str) -> int | None:
    try:
        response = requests.get(f"{QDRANT_URL}/collections/{collection}", timeout=10)
        if response.status_code != 200:
            return None
        return response.json().get("result", {}).get("points_count")
    except Exception:
        return None


def normalize_points(payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = payload.get("result")
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and isinstance(result.get("points"), list):
        return result["points"]
    return []


def search_collection(collection: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    if not qdrant_collection_exists(collection):
        return []
    vector = embedding(query)
    body = {"vector": vector, "limit": limit, "with_payload": True}
    response = requests.post(
        f"{QDRANT_URL}/collections/{collection}/points/search",
        json=body,
        timeout=60,
    )
    if response.status_code == 404:
        response = requests.post(
            f"{QDRANT_URL}/collections/{collection}/points/query",
            json={"query": vector, "limit": limit, "with_payload": True},
            timeout=60,
        )
    response.raise_for_status()
    points = normalize_points(response.json())
    for point in points:
        point["collection"] = collection
    return points


def search_all_collections(query: str, limit_per_collection: int = 4) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for collection in COLLECTIONS:
        points.extend(search_collection(collection, query, limit=limit_per_collection))
    return sorted(points, key=lambda item: float(item.get("score") or 0.0), reverse=True)


def payload_source(payload: dict[str, Any]) -> str:
    for key in (
        "markdown_path",
        "analysis_markdown",
        "raw_analysis_markdown",
        "source_path",
        "url",
        "audio_file",
        "transcript_txt",
    ):
        value = payload.get(key)
        if value:
            return str(value)
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return str(metadata.get("source") or "")


def payload_title(payload: dict[str, Any]) -> str:
    for key in ("summary", "topic", "subcategory", "category", "type", "url"):
        value = payload.get(key)
        if value:
            return str(value)[:180]
    return "Quelle"


def payload_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "summary",
        "transcript",
        "questions",
        "health_mentions",
        "ingredients",
        "product_mentions",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value[:12])
        if value:
            parts.append(f"{key}: {value}")

    for path_key in ("markdown_path", "analysis_markdown", "raw_analysis_markdown"):
        path_value = payload.get(path_key)
        if path_value:
            path = Path(str(path_value))
            if path.exists():
                parts.append(read_text(path, limit=3000))
                break

    if not parts:
        parts.append(json.dumps(payload, ensure_ascii=False)[:3000])
    return "\n".join(parts)[:4200]


def build_context(points: list[dict[str, Any]], max_chars: int = MAX_CONTEXT_CHARS) -> tuple[str, list[dict[str, Any]]]:
    chunks: list[str] = []
    sources: list[dict[str, Any]] = []
    used = 0
    for index, point in enumerate(points, start=1):
        payload = point.get("payload") or {}
        source = {
            "index": index,
            "collection": point.get("collection"),
            "score": round(float(point.get("score") or 0.0), 4),
            "title": payload_title(payload),
            "source": payload_source(payload),
            "data_class": payload.get("data_class"),
        }
        text = payload_text(payload)
        chunk = (
            f"[Quelle {index}]\n"
            f"Collection: {source['collection']}\n"
            f"Score: {source['score']}\n"
            f"Titel: {source['title']}\n"
            f"Pfad/URL: {source['source']}\n"
            f"Datenklasse: {source['data_class']}\n"
            f"Inhalt:\n{text}\n"
        )
        if used + len(chunk) > max_chars:
            break
        chunks.append(chunk)
        sources.append(source)
        used += len(chunk)
    return "\n\n".join(chunks), sources


def strip_thinking(text: str) -> str:
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()


def ollama_generate(prompt: str, model: str = MEMORY_MODEL, timeout: int = 600, temperature: float = 0.2) -> str:
    guarded_prompt = (
        "/no_think\n\n"
        "Gib nur die finale Antwort aus. Keine Analyse deines Denkprozesses, keine Meta-Erklaerung.\n\n"
        f"{prompt}"
    )
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "prompt": guarded_prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 32768,
                "num_predict": 4096,
            },
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    text = str(payload.get("response") or "").strip()
    if not text:
        text = "Nexi, das lokale Modell hat keine finale Antwort geliefert. Ich habe keinen Denktext ausgegeben."
    return strip_thinking(text)


def latest_files(directory: Path, pattern: str = "*.md", limit: int = 8) -> list[Path]:
    if not directory.exists():
        return []
    files = [path for path in directory.rglob(pattern) if path.is_file()]
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def recent_file_lines(directory: Path, pattern: str = "*.md", hours: int = 24, limit: int = 8) -> list[str]:
    cutoff = datetime.now() - timedelta(hours=hours)
    lines: list[str] = []
    for path in latest_files(directory, pattern=pattern, limit=limit * 2):
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        if mtime >= cutoff:
            lines.append(f"- {path.name} ({mtime.strftime('%Y-%m-%d %H:%M')})")
        if len(lines) >= limit:
            break
    return lines
