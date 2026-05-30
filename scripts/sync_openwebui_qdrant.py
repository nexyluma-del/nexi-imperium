#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


QDRANT_URL = "http://127.0.0.1:6333"
SOURCE_COLLECTION = "video_knowledge"
DEST_COLLECTION = "open-webui_knowledge"
ALL_KNOWLEDGE_ID = "nexi-video-knowledge"
MAX_TEXT_CHARS = 9000


def normalize_path(value: str | None) -> Path | None:
    if not value:
        return None
    match = re.match(r"^([A-Za-z]):\\(.*)$", value)
    if match:
        drive = match.group(1).lower()
        rest = match.group(2).replace("\\", "/")
        return Path(f"/mnt/{drive}/{rest}")
    return Path(value)


def read_text(path_value: str | None, limit: int) -> str:
    path = normalize_path(path_value)
    if not path or not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def slugify(value: str) -> str:
    value = value.split("|", 1)[0].strip()
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value[:60] or "allgemein"


def base_category(payload: dict[str, Any]) -> str:
    value = payload.get("category") or payload.get("topic") or "Unkategorisiert"
    return str(value).split("|", 1)[0].strip() or "Unkategorisiert"


def stable_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))


def qdrant_request(method: str, path: str, **kwargs) -> requests.Response:
    response = requests.request(method, f"{QDRANT_URL}{path}", timeout=120, **kwargs)
    if response.status_code >= 400:
        response.raise_for_status()
    return response


def ensure_dest_collection(vector_size: int) -> None:
    response = requests.get(f"{QDRANT_URL}/collections/{DEST_COLLECTION}", timeout=30)
    if response.status_code == 404:
        qdrant_request(
            "PUT",
            f"/collections/{DEST_COLLECTION}",
            json={"vectors": {"size": vector_size, "distance": "Cosine"}},
        )
    elif response.status_code >= 400:
        response.raise_for_status()

    for field_name in ("tenant_id", "metadata.file_id", "metadata.category", "metadata.type"):
        try:
            qdrant_request(
                "PUT",
                f"/collections/{DEST_COLLECTION}/index",
                json={"field_name": field_name, "field_schema": "keyword"},
            )
        except Exception:
            pass


def scroll_source() -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    offset = None
    while True:
        body: dict[str, Any] = {"limit": 100, "with_payload": True, "with_vectors": True}
        if offset is not None:
            body["offset"] = offset
        payload = qdrant_request("POST", f"/collections/{SOURCE_COLLECTION}/points/scroll", json=body).json()
        result = payload.get("result", {})
        points.extend(result.get("points", []))
        offset = result.get("next_page_offset")
        if offset is None:
            break
    return points


def text_for_payload(payload: dict[str, Any]) -> str:
    questions = "\n".join(f"- {q}" for q in payload.get("questions") or [])
    analysis = read_text(payload.get("analysis_markdown"), 5500)
    transcript = read_text(payload.get("transcript_txt"), 1800)
    source = payload.get("url") or payload.get("source_path") or ""
    lines = [
        f"Thema/Kategorie: {payload.get('topic') or payload.get('category') or 'Unbekannt'}",
        f"Typ: {payload.get('type') or 'video'}",
        f"Datenklasse: {payload.get('data_class') or ''}",
        f"Quelle: {source}",
        "Fragen:",
        questions,
        "Analyse:",
        analysis,
        "Transkript-Auszug:",
        transcript,
    ]
    return "\n\n".join(part for part in lines if part).strip()[:MAX_TEXT_CHARS]


def tenant_ids_for(payload: dict[str, Any]) -> list[tuple[str, str]]:
    category = base_category(payload)
    return [
        (ALL_KNOWLEDGE_ID, "Nexi Video Knowledge - Alle Kategorien"),
        (f"nexi-video-knowledge-{slugify(category)}", f"Nexi Video Knowledge - {category}"),
    ]


def delete_tenant(tenant_id: str) -> None:
    qdrant_request(
        "POST",
        f"/collections/{DEST_COLLECTION}/points/delete?wait=true",
        json={"filter": {"must": [{"key": "tenant_id", "match": {"value": tenant_id}}]}},
    )


def upsert_points(points: list[dict[str, Any]]) -> None:
    if not points:
        return
    qdrant_request("PUT", f"/collections/{DEST_COLLECTION}/points?wait=true", json={"points": points})


def convert_point(source_point: dict[str, Any], tenant_id: str) -> dict[str, Any] | None:
    payload = source_point.get("payload") or {}
    vector = source_point.get("vector")
    if isinstance(vector, dict):
        vector = vector.get("") or next(iter(vector.values()), None)
    if not vector:
        return None

    source_id = str(source_point.get("id"))
    category = base_category(payload)
    source = payload.get("url") or payload.get("source_path") or payload.get("analysis_markdown") or source_id
    text = text_for_payload(payload)
    metadata = {
        "id": source_id,
        "file_id": source_id,
        "hash": stable_id(source_id, tenant_id),
        "name": payload.get("slug") or category,
        "source": source,
        "category": category,
        "topic": payload.get("topic") or category,
        "type": payload.get("type") or "video",
        "data_class": payload.get("data_class"),
        "analysis_markdown": payload.get("analysis_markdown"),
        "url": payload.get("url"),
        "source_path": payload.get("source_path"),
    }
    return {
        "id": stable_id(source_id, tenant_id),
        "vector": vector,
        "payload": {
            "text": text,
            "metadata": metadata,
            "tenant_id": tenant_id,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync video_knowledge into OpenWebUI-compatible Qdrant knowledge.")
    parser.add_argument("--manifest", type=Path, default=Path("openwebui-rag-manifest.json"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_points = scroll_source()
    if not source_points:
        raise RuntimeError(f"Keine Punkte in {SOURCE_COLLECTION} gefunden.")

    first_vector = source_points[0].get("vector")
    if isinstance(first_vector, dict):
        first_vector = first_vector.get("") or next(iter(first_vector.values()), None)
    vector_size = len(first_vector)

    tenant_to_points: dict[str, list[dict[str, Any]]] = defaultdict(list)
    tenant_names: dict[str, str] = {}
    for source_point in source_points:
        payload = source_point.get("payload") or {}
        if str(payload.get("topic") or payload.get("category") or "").lower().startswith("sofinello"):
            continue
        for tenant_id, tenant_name in tenant_ids_for(payload):
            converted = convert_point(source_point, tenant_id)
            if converted:
                tenant_to_points[tenant_id].append(converted)
                tenant_names[tenant_id] = tenant_name

    if not args.dry_run:
        ensure_dest_collection(vector_size)
        for tenant_id, points in tenant_to_points.items():
            delete_tenant(tenant_id)
            for index in range(0, len(points), 64):
                upsert_points(points[index : index + 64])

    knowledge_bases = [
        {
            "id": tenant_id,
            "name": tenant_names[tenant_id],
            "description": (
                "OpenWebUI-RAG-Spiegel aus Qdrant video_knowledge. "
                "Quelle bleibt video_knowledge; Sofinello ist nicht enthalten."
            ),
            "points": len(points),
        }
        for tenant_id, points in sorted(tenant_to_points.items())
    ]
    manifest = {
        "ok": True,
        "source_collection": SOURCE_COLLECTION,
        "dest_collection": DEST_COLLECTION,
        "vector_size": vector_size,
        "source_points": len(source_points),
        "synced_points_total": sum(len(points) for points in tenant_to_points.values()),
        "knowledge_bases": knowledge_bases,
        "dry_run": args.dry_run,
        "synced_at": datetime.now().isoformat(timespec="seconds"),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
