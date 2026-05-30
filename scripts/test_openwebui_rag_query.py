#!/usr/bin/env python3
from __future__ import annotations

import json

import requests


QUERY = "Was wurde in den IT-Sicherheits-Videos zu Tools gesagt?"
TENANT_ID = "nexi-video-knowledge-it-hacking-sicherheit"


def main() -> int:
    embedding_response = requests.post(
        "http://127.0.0.1:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": QUERY},
        timeout=120,
    )
    embedding_response.raise_for_status()
    embedding = embedding_response.json()["embedding"]

    search_body = {
        "vector": embedding,
        "limit": 4,
        "with_payload": True,
        "filter": {"must": [{"key": "tenant_id", "match": {"value": TENANT_ID}}]},
    }
    response = requests.post(
        "http://127.0.0.1:6333/collections/open-webui_knowledge/points/search",
        json=search_body,
        timeout=60,
    )
    if response.status_code == 404:
        query_body = {
            "query": embedding,
            "limit": 4,
            "with_payload": True,
            "filter": search_body["filter"],
        }
        response = requests.post(
            "http://127.0.0.1:6333/collections/open-webui_knowledge/points/query",
            json=query_body,
            timeout=60,
        )
    response.raise_for_status()
    result = response.json().get("result")
    points = result if isinstance(result, list) else result.get("points", [])
    context = "\n\n".join(
        f"Quelle {index + 1}: {point['payload']['metadata'].get('source')}\n"
        f"{point['payload']['text'][:1400]}"
        for index, point in enumerate(points)
    )
    prompt = (
        "Antworte kurz auf Deutsch nur aus diesem Kontext.\n"
        f"Frage: {QUERY}\n\n"
        f"Kontext:\n{context}\n\n"
        "Antwort mit 3 Bulletpoints und Quellenhinweis."
    )
    answer_response = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={"model": "qwen3:4b", "prompt": prompt, "stream": False, "options": {"temperature": 0.2}},
        timeout=240,
    )
    answer_response.raise_for_status()
    print(
        json.dumps(
            {
                "query": QUERY,
                "tenant_id": TENANT_ID,
                "retrieved": [
                    {
                        "score": point.get("score"),
                        "source": point["payload"]["metadata"].get("source"),
                        "category": point["payload"]["metadata"].get("category"),
                    }
                    for point in points
                ],
                "answer": answer_response.json().get("response", "").strip(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
