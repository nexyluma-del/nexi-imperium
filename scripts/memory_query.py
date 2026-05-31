#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from memory_common import (
    COLLECTIONS,
    FAST_MODEL,
    MEMORY_MODEL,
    build_context,
    memory_system_prompt,
    ollama_generate,
    search_all_collections,
)
from telegram_common import send_message


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "analysis" / "memory"


def answer_prompt(question: str, context: str) -> str:
    return f"""
{memory_system_prompt()}

AUFGABE:
Beantworte Nexis Frage aus dem lokalen Kontext. Wenn der Kontext nicht reicht, sag das klar.

FRAGE VON NEXI:
{question}

LOKALER KONTEXT AUS QDRANT:
{context or "Keine passenden Quellen gefunden."}

FORMAT:
- Sprich Nexi direkt an.
- Erst klare Antwort, dann Quellen.
- Maximal 8 Bulletpoints, ausser die Frage verlangt Details.
- Nutze Quellen nur, wenn sie wirklich zur Frage passen.
- Wenn die Treffer thematisch daneben liegen, sag offen: "Ich finde lokal gerade keine belastbare Quelle dazu."
- Keine Cloud behaupten. Keine Heilversprechen.
- Keine Emojis. Keine Denknotizen.
"""


def render_answer(question: str, answer: str, sources: list[dict[str, Any]]) -> str:
    lines = [
        f"# Memory-KI Antwort - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Frage: {question}",
        "",
        "## Antwort",
        answer.strip() or "Ich habe lokal keine belastbare Antwort erzeugen koennen.",
        "",
        "## Quellen",
    ]
    if not sources:
        lines.append("- Keine passenden Qdrant-Quellen gefunden.")
    for source in sources:
        lines.append(
            f"- [{source['index']}] {source['collection']} | Score {source['score']} | "
            f"{source['title']} | {source['source']}"
        )
    return "\n".join(lines) + "\n"


def is_usable_answer(answer: str) -> bool:
    clean = answer.strip()
    if len(clean) < 220:
        return False
    lowered = clean.lower()
    bad_markers = ("okay, let me", "i need to", "the user wants", "denkprozess", "keine finale antwort")
    return not any(marker in lowered for marker in bad_markers)


def run_query(question: str, limit: int, model: str) -> dict[str, Any]:
    points = search_all_collections(question, limit_per_collection=limit)
    context, sources = build_context(points, max_chars=14000)
    prompt = answer_prompt(question, context)
    answer = ollama_generate(prompt, model=model, timeout=900 if model == MEMORY_MODEL else 360)
    if model != MEMORY_MODEL and not is_usable_answer(answer):
        model = MEMORY_MODEL
        answer = ollama_generate(prompt, model=model, timeout=900)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    markdown = render_answer(question, answer, sources)
    markdown_path = OUTPUT_DIR / f"memory-answer-{stamp}.md"
    json_path = OUTPUT_DIR / f"memory-answer-{stamp}.json"
    payload = {
        "ok": True,
        "question": question,
        "model": model,
        "collections": list(COLLECTIONS),
        "sources": sources,
        "answer": answer,
        "markdown_path": str(markdown_path),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["json_path"] = str(json_path)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask local Memory-KI with Qdrant RAG.")
    parser.add_argument("question", nargs="*", help="Frage an Memory-KI")
    parser.add_argument("--query", help="Frage an Memory-KI")
    parser.add_argument("--limit", type=int, default=4)
    parser.add_argument("--model", default=MEMORY_MODEL)
    parser.add_argument("--fast", action="store_true", help=f"Nutze {FAST_MODEL} fuer schnelle Tests.")
    parser.add_argument("--send-telegram", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    question = (args.query or " ".join(args.question)).strip()
    if not question:
        raise SystemExit("Bitte Frage angeben.")
    model = FAST_MODEL if args.fast else args.model
    payload = run_query(question, limit=args.limit, model=model)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.send_telegram:
        text = "\n".join(
            [
                "Memory-KI",
                "",
                payload["answer"][:3200],
                "",
                "Quellen:",
                *[
                    f"- {source['collection']} | {source['title']} | Score {source['score']}"
                    for source in payload["sources"][:5]
                ],
            ]
        )
        send_message(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
