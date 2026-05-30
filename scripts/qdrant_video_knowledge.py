from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


QDRANT_URL = "http://127.0.0.1:6333"
OLLAMA_URL = "http://127.0.0.1:11434"
COLLECTION = "video_knowledge"
EMBED_MODEL = "nomic-embed-text"
MAX_EMBED_CHARS = 3000


def embedding(text: str) -> list[float]:
    prompt = text[:MAX_EMBED_CHARS]
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": prompt},
        timeout=120,
    )
    if response.status_code >= 400:
        fallback_prompt = prompt[:1500]
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": fallback_prompt},
            timeout=120,
        )
        if response.status_code >= 400:
            response = requests.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": fallback_prompt},
                timeout=120,
            )
            response.raise_for_status()
            return response.json()["embedding"]
        payload = response.json()
        embeddings = payload.get("embeddings") or payload.get("embedding")
        if embeddings and isinstance(embeddings[0], list):
            return embeddings[0]
        return embeddings
    response.raise_for_status()
    return response.json()["embedding"]


def ensure_collection(size: int) -> None:
    existing = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}", timeout=30)
    if existing.status_code == 200:
        return
    if existing.status_code != 404:
        existing.raise_for_status()

    response = requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}",
        json={"vectors": {"size": size, "distance": "Cosine"}},
        timeout=60,
    )
    response.raise_for_status()


def stable_point_id(url: str, topic: str, analysis_path: str) -> str:
    digest = hashlib.sha256(f"{url}|{topic}|{analysis_path}".encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))


def upsert_video_knowledge(
    *,
    url: str,
    topic: str,
    data_class: str,
    questions: list[str],
    analysis_markdown: Path,
    transcript_txt: Path,
    cost_usd: float | None,
    slug: str,
) -> dict[str, Any]:
    analysis_text = analysis_markdown.read_text(encoding="utf-8")
    transcript_text = transcript_txt.read_text(encoding="utf-8") if transcript_txt.exists() else ""
    combined = "\n\n".join(
        [
            f"Thema: {topic}",
            f"URL: {url}",
            "Fragen:",
            "\n".join(f"- {question}" for question in questions),
            "Whisper-Transkript:",
            transcript_text[:2500],
            "Gemini-Analyse:",
            analysis_text[:3500],
        ]
    )[:MAX_EMBED_CHARS]

    vector = embedding(combined)
    ensure_collection(len(vector))
    point_id = stable_point_id(url, topic, str(analysis_markdown))
    payload = {
        "url": url,
        "topic": topic,
        "data_class": data_class,
        "questions": questions,
        "analysis_markdown": str(analysis_markdown),
        "transcript_txt": str(transcript_txt),
        "cost_usd": cost_usd,
        "slug": slug,
        "indexed_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_model": EMBED_MODEL,
    }
    response = requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points?wait=true",
        json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
        timeout=120,
    )
    response.raise_for_status()
    return {"collection": COLLECTION, "point_id": point_id, "vector_size": len(vector), "payload": payload}


def upsert_image_post_knowledge(
    *,
    url: str,
    topic: str,
    data_class: str,
    questions: list[str],
    analysis_markdown: Path,
    image_paths: list[Path],
    cost_usd: float | None,
    slug: str,
    provider_results: list[dict[str, Any]],
    input_mode: str,
) -> dict[str, Any]:
    analysis_text = analysis_markdown.read_text(encoding="utf-8")
    provider_summary = "\n".join(
        f"{result.get('provider')}: {str(result.get('text', ''))[:1200]}" for result in provider_results
    )
    combined = "\n\n".join(
        [
            f"Thema: {topic}",
            f"URL: {url}",
            "Typ: image-post",
            "Crosscheck: 3way",
            f"Input-Modus: {input_mode}",
            "Fragen:",
            "\n".join(f"- {question}" for question in questions),
            "Provider-Zusammenfassung:",
            provider_summary,
            "Konsolidierte Analyse:",
            analysis_text[:3500],
        ]
    )[:MAX_EMBED_CHARS]

    vector = embedding(combined)
    ensure_collection(len(vector))
    point_id = stable_point_id(url, topic, str(analysis_markdown))
    payload = {
        "url": url,
        "topic": topic,
        "data_class": data_class,
        "questions": questions,
        "analysis_markdown": str(analysis_markdown),
        "image_paths": [str(path) for path in image_paths],
        "cost_usd": cost_usd,
        "slug": slug,
        "type": "image-post",
        "crosscheck": "3way",
        "input_mode": input_mode,
        "providers": [
            {
                "provider": result.get("provider"),
                "model": result.get("model"),
                "cost_usd": result.get("cost_usd"),
            }
            for result in provider_results
        ],
        "indexed_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_model": EMBED_MODEL,
    }
    response = requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points?wait=true",
        json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
        timeout=120,
    )
    response.raise_for_status()
    return {"collection": COLLECTION, "point_id": point_id, "vector_size": len(vector), "payload": payload}


def upsert_local_video_knowledge(
    *,
    source_path: Path,
    category: str,
    data_class: str,
    questions: list[str],
    analysis_markdown: Path,
    transcript_txt: Path,
    frame_paths: list[Path],
    cost_usd: float | None,
    slug: str,
    source_info: str = "",
    preprocessor: str | None = None,
    pipeline: str = "default_local_video",
) -> dict[str, Any]:
    analysis_text = analysis_markdown.read_text(encoding="utf-8") if analysis_markdown.exists() else ""
    transcript_text = transcript_txt.read_text(encoding="utf-8") if transcript_txt.exists() else ""
    combined = "\n\n".join(
        [
            f"Typ: local-video",
            f"Kategorie: {category}",
            f"Lokale Datei: {source_path}",
            f"Quelle/Notiz: {source_info}",
            f"Pipeline: {pipeline}",
            f"Preprocessor: {preprocessor or 'none'}",
            "Fragen:",
            "\n".join(f"- {question}" for question in questions),
            "Whisper-Transkript:",
            transcript_text[:2500],
            "Gemini-Analyse:",
            analysis_text[:3500],
        ]
    )[:MAX_EMBED_CHARS]

    vector = embedding(combined)
    ensure_collection(len(vector))
    point_id = stable_point_id(str(source_path), category, str(analysis_markdown))
    payload = {
        "type": "local-video",
        "source_path": str(source_path),
        "category": category,
        "topic": category,
        "data_class": data_class,
        "questions": questions,
        "analysis_markdown": str(analysis_markdown),
        "transcript_txt": str(transcript_txt),
        "frame_paths": [str(path) for path in frame_paths],
        "cost_usd": cost_usd,
        "slug": slug,
        "source_info": source_info,
        "preprocessor": preprocessor,
        "pipeline": pipeline,
        "indexed_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_model": EMBED_MODEL,
    }
    response = requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points?wait=true",
        json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
        timeout=120,
    )
    response.raise_for_status()
    return {"collection": COLLECTION, "point_id": point_id, "vector_size": len(vector), "payload": payload}
