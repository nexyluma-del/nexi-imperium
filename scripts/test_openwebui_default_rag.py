#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


OLLAMA_URL = "http://127.0.0.1:11434"
QDRANT_URL = "http://127.0.0.1:6333"
COLLECTION = "open-webui_knowledge"
TENANT_ID = "nexi-video-knowledge"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen3:30b"

TEST_QUESTIONS = [
    "Welche konkreten KI-Tools oder lokalen KI-Setups wurden in meinen Videos gesammelt?",
    "Was sagen meine IT- und Sicherheits-Videos zu Tools, Hacks oder Schutzmassnahmen?",
    "Welche Finanz-, Business- oder Produktideen tauchen in meinem Video-Wissen auf?",
]


def post_json(url: str, body: dict[str, Any], timeout: int) -> dict[str, Any]:
    response = requests.post(url, json=body, timeout=timeout)
    response.raise_for_status()
    return response.json()


def embed(text: str) -> list[float]:
    payload = post_json(
        f"{OLLAMA_URL}/api/embeddings",
        {"model": EMBED_MODEL, "prompt": text},
        timeout=180,
    )
    embedding = payload.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise RuntimeError("Ollama hat kein Embedding geliefert.")
    return embedding


def search_qdrant(query: str, limit: int = 5) -> list[dict[str, Any]]:
    vector = embed(query)
    body = {
        "vector": vector,
        "limit": limit,
        "with_payload": True,
        "filter": {"must": [{"key": "tenant_id", "match": {"value": TENANT_ID}}]},
    }
    response = requests.post(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
        json=body,
        timeout=90,
    )
    if response.status_code == 404:
        body = {
            "query": vector,
            "limit": limit,
            "with_payload": True,
            "filter": body["filter"],
        }
        response = requests.post(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/query",
            json=body,
            timeout=90,
        )
    response.raise_for_status()
    result = response.json().get("result")
    if isinstance(result, dict):
        points = result.get("points", [])
    else:
        points = result or []
    return points


def source_label(point: dict[str, Any], index: int) -> str:
    payload = point.get("payload") or {}
    metadata = payload.get("metadata") or {}
    return (
        metadata.get("source")
        or metadata.get("url")
        or metadata.get("analysis_markdown")
        or metadata.get("source_path")
        or f"Quelle {index}"
    )


def build_context(points: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    blocks: list[str] = []
    sources: list[dict[str, Any]] = []
    for index, point in enumerate(points, start=1):
        payload = point.get("payload") or {}
        metadata = payload.get("metadata") or {}
        text = str(payload.get("text") or "")[:2400]
        source = source_label(point, index)
        sources.append(
            {
                "index": index,
                "score": point.get("score"),
                "source": source,
                "category": metadata.get("category"),
                "topic": metadata.get("topic"),
            }
        )
        blocks.append(f"[{index}] {source}\nKategorie: {metadata.get('category')}\n{text}")
    return "\n\n---\n\n".join(blocks), sources


def strip_thinking(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()


def answer_question(question: str, context: str) -> str:
    prompt = f"""/no_think

Du bist Nexis lokaler RAG-Test fuer OpenWebUI.

Beantworte die Frage nur mit dem Kontext.
Wenn etwas nicht im Kontext steht, sage es ehrlich.
Nutze kurze Abschnitte oder Bulletpoints.
Setze Quellenhinweise wie [1], [2] direkt hinter konkrete Aussagen.
Gib keinen sichtbaren Denkprozess aus. Beginne direkt mit der Antwort.

Frage:
{question}

Kontext:
{context}

Antwort auf Deutsch mit Quellen:
"""
    payload = post_json(
        f"{OLLAMA_URL}/api/generate",
        {
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.8,
                "num_predict": 1600,
            },
        },
        timeout=900,
    )
    raw_answer = str(payload.get("response") or "")
    answer = strip_thinking(raw_answer)
    if len(answer) < 40:
        raise RuntimeError(
            f"Antwort zu kurz fuer Frage: {question}\n"
            f"Rohantwort-Auszug: {raw_answer[:800]!r}"
        )
    if not re.search(r"\[[0-9]+\]|\[Quelle\s+[0-9]+\]", answer, re.IGNORECASE):
        raise RuntimeError(f"Antwort enthaelt keinen Quellenverweis: {question}\n{answer}")
    return answer


def run_tests() -> dict[str, Any]:
    tests = []
    for question in TEST_QUESTIONS:
        points = search_qdrant(question)
        if len(points) < 2:
            raise RuntimeError(f"Zu wenig Treffer fuer Frage: {question} ({len(points)})")
        context, sources = build_context(points)
        answer = answer_question(question, context)
        tests.append(
            {
                "question": question,
                "answer": answer,
                "sources": sources,
            }
        )
    return {
        "ok": True,
        "model": CHAT_MODEL,
        "embedding_model": EMBED_MODEL,
        "collection": COLLECTION,
        "tenant_id": TENANT_ID,
        "tests": tests,
        "tested_at": datetime.now().isoformat(timespec="seconds"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Nexi OpenWebUI default RAG source tests.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("analysis/openwebui-rag/openwebui-rag-test.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_tests()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    markdown = args.out.with_suffix(".md")
    lines = [
        "# OpenWebUI RAG Test",
        "",
        f"- OK: {result['ok']}",
        f"- Modell: `{result['model']}`",
        f"- Collection: `{result['collection']}`",
        f"- Tenant: `{result['tenant_id']}`",
        f"- Zeit: {result['tested_at']}",
        "",
    ]
    for index, test in enumerate(result["tests"], start=1):
        lines.extend(
            [
                f"## Test {index}",
                "",
                f"**Frage:** {test['question']}",
                "",
                test["answer"],
                "",
                "**Quellen:**",
            ]
        )
        for source in test["sources"]:
            lines.append(
                f"- [{source['index']}] {source['source']} "
                f"(Kategorie: {source.get('category')}, Score: {source.get('score')})"
            )
        lines.append("")
    markdown.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
