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
SOFINELLO_COLLECTION = "sofinello_knowledge"
MEMORY_VOICE_COLLECTION = "memory_voice"
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


def ensure_collection(size: int, collection: str = COLLECTION) -> None:
    existing = requests.get(f"{QDRANT_URL}/collections/{collection}", timeout=30)
    if existing.status_code == 200:
        return
    if existing.status_code != 404:
        existing.raise_for_status()

    response = requests.put(
        f"{QDRANT_URL}/collections/{collection}",
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


def upsert_sofinello_knowledge(
    *,
    source_path: Path,
    subcategory: str,
    data_class: str,
    questions: list[str],
    analysis_markdown: Path,
    raw_analysis_markdown: Path,
    transcript_txt: Path,
    frame_paths: list[Path],
    upscaled_video: Path | None,
    cost_usd: float | None,
    slug: str,
    compliance: dict[str, Any],
    ingredients: list[str] | None = None,
    health_mentions: list[str] | None = None,
    product_mentions: list[str] | None = None,
    source_info: str = "",
) -> dict[str, Any]:
    analysis_text = analysis_markdown.read_text(encoding="utf-8") if analysis_markdown.exists() else ""
    transcript_text = transcript_txt.read_text(encoding="utf-8") if transcript_txt.exists() else ""
    ingredients = ingredients or []
    health_mentions = health_mentions or []
    product_mentions = product_mentions or []
    combined = "\n\n".join(
        [
            "Typ: sofinello-video",
            f"Sub-Kategorie: {subcategory}",
            f"Lokale Datei: {source_path}",
            f"Quelle/Notiz: {source_info}",
            f"Compliance-Status: {compliance.get('status')}",
            "Fragen:",
            "\n".join(f"- {question}" for question in questions),
            "Erkannte Zutaten/Wirkstoffe:",
            ", ".join(ingredients),
            "Erwaehnte Beschwerden/Themen:",
            ", ".join(health_mentions),
            "Produkt-/Verpackungs-Hinweise:",
            ", ".join(product_mentions),
            "Whisper-Transkript:",
            transcript_text[:1800],
            "Compliance-gepruefte Analyse:",
            analysis_text[:4200],
        ]
    )[:MAX_EMBED_CHARS]

    vector = embedding(combined)
    ensure_collection(len(vector), SOFINELLO_COLLECTION)
    point_id = stable_point_id(str(source_path), subcategory, str(analysis_markdown))
    payload = {
        "type": "sofinello-video",
        "source_path": str(source_path),
        "source_info": source_info,
        "subcategory": subcategory,
        "topic": "Sofinello",
        "data_class": data_class,
        "questions": questions,
        "analysis_markdown": str(analysis_markdown),
        "raw_analysis_markdown": str(raw_analysis_markdown),
        "transcript_txt": str(transcript_txt),
        "frame_paths": [str(path) for path in frame_paths],
        "upscaled_video": str(upscaled_video) if upscaled_video else None,
        "cost_usd": cost_usd,
        "slug": slug,
        "ingredients": ingredients,
        "health_mentions": health_mentions,
        "product_mentions": product_mentions,
        "compliance": compliance,
        "pipeline": "sofinello_special_pipeline",
        "indexed_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_model": EMBED_MODEL,
    }
    response = requests.put(
        f"{QDRANT_URL}/collections/{SOFINELLO_COLLECTION}/points?wait=true",
        json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
        timeout=120,
    )
    response.raise_for_status()
    return {
        "collection": SOFINELLO_COLLECTION,
        "point_id": point_id,
        "vector_size": len(vector),
        "payload": payload,
    }


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


def upsert_memory_voice_knowledge(
    *,
    markdown_path: Path,
    audio_file: Path,
    transcript: str,
    tags: dict[str, Any],
    data_class: str,
    duration_seconds: float | None,
    language: str | None,
    source: str = "voice_capture",
) -> dict[str, Any]:
    tag_list = tags.get("tags") if isinstance(tags.get("tags"), list) else []
    links = tags.get("links") if isinstance(tags.get("links"), list) else []
    combined = "\n\n".join(
        [
            "Typ: memory-voice",
            f"Quelle: {source}",
            f"Audio-Datei: {audio_file}",
            f"Obsidian-Notiz: {markdown_path}",
            f"Tags: {', '.join(str(tag) for tag in tag_list)}",
            f"Wichtigkeit: {tags.get('importance')}",
            f"Chief/Kategorie: {tags.get('chief')}",
            f"Kurzfassung: {tags.get('summary')}",
            "Verknuepfungen:",
            "\n".join(f"- {link}" for link in links),
            "Transkript:",
            transcript[:4200],
        ]
    )[:MAX_EMBED_CHARS]

    vector = embedding(combined)
    ensure_collection(len(vector), MEMORY_VOICE_COLLECTION)
    point_id = stable_point_id(str(audio_file), "memory_voice", str(markdown_path))
    payload = {
        "type": "memory-voice",
        "source": source,
        "audio_file": str(audio_file),
        "markdown_path": str(markdown_path),
        "transcript": transcript[:9000],
        "tags": tag_list,
        "importance": tags.get("importance"),
        "chief": tags.get("chief"),
        "summary": tags.get("summary"),
        "links": links,
        "data_class": data_class,
        "duration_seconds": duration_seconds,
        "language": language,
        "indexed_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_model": EMBED_MODEL,
    }
    response = requests.put(
        f"{QDRANT_URL}/collections/{MEMORY_VOICE_COLLECTION}/points?wait=true",
        json={"points": [{"id": point_id, "vector": vector, "payload": payload}]},
        timeout=120,
    )
    response.raise_for_status()
    return {
        "collection": MEMORY_VOICE_COLLECTION,
        "point_id": point_id,
        "vector_size": len(vector),
        "payload": payload,
    }
