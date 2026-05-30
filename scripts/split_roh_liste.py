#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


DEFAULT_RAW_FILE = Path("/mnt/c/Users/nexil/Desktop/Instagram Liste/videos-roh.md")
DEFAULT_OUTPUT_DIR = Path("/mnt/c/Users/nexil/Desktop/Instagram Liste")
URL_RE = re.compile(r"https?://\S+")
TOPIC_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")


@dataclass
class Entry:
    topic: str
    url: str
    tags: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)


def slugify_topic(topic: str) -> str:
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
    }
    value = topic.strip()
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return value or "Unsortiert"


def clean_question(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^(Was ich wissen will|Fragen?|Frage|Q)\s*:\s*", "", line, flags=re.I)
    line = line.lstrip("-* ").strip()
    return line


def split_question_line(line: str) -> list[str]:
    cleaned = clean_question(line)
    if not cleaned:
        return []
    parts = re.split(r"\s*(?:\?|;|\|)\s*", cleaned)
    questions = []
    for part in parts:
        part = part.strip(" -")
        if not part:
            continue
        if not part.endswith("?") and line.strip().endswith("?"):
            part += "?"
        questions.append(part)
    return questions or [cleaned]


def parse_raw_file(raw_file: Path) -> list[Entry]:
    text = raw_file.read_text(encoding="utf-8-sig")
    current_topic = "Unsortiert"
    pending_tags: list[str] = []
    entries: list[Entry] = []
    current: Entry | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        topic_match = TOPIC_RE.match(line)
        if topic_match:
            current_topic = topic_match.group(1).strip()
            pending_tags = []
            current = None
            continue

        tag_match = re.match(r"^Tags?\s*:\s*(.+?)\s*$", line, flags=re.I)
        if tag_match:
            tags = [tag.strip() for tag in re.split(r"[,;|]", tag_match.group(1)) if tag.strip()]
            if current is None:
                pending_tags = tags
            else:
                current.tags.extend(tags)
            continue

        url_match = URL_RE.search(line)
        if url_match:
            current = Entry(topic=current_topic, url=url_match.group(0).rstrip(").,]"), tags=pending_tags)
            pending_tags = []
            entries.append(current)
            rest = line.replace(url_match.group(0), "").strip(" -:|")
            if rest:
                current.questions.extend(split_question_line(rest))
            continue

        if current is not None:
            current.questions.extend(split_question_line(line))

    return entries


def render_topic_file(topic: str, entries: list[Entry], raw_file: Path, data_class: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# Thema: {topic}",
        f"Quelle: {raw_file}",
        f"Gesplittet am: {now}",
        "",
    ]

    for index, entry in enumerate(entries, start=1):
        lines.extend(
            [
                f"## Eintrag {index}",
                f"URL: {entry.url}",
                f"Tags: {', '.join(entry.tags)}",
                "Fragen:",
            ]
        )
        if entry.questions:
            lines.extend(f"- {question}" for question in entry.questions)
        else:
            lines.append("- Allgemein: Was ist die wichtigste Aussage dieses Videos?")
        lines.extend(
            [
                "Status: noch nicht analysiert",
                f"Datenklasse: {data_class}",
                "Analyse: ",
                "Kosten USD: ",
                "Qdrant ID: ",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Split Nexis raw video list into topic files.")
    parser.add_argument("--input", type=Path, default=DEFAULT_RAW_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--data-class", default="D2")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Roh-Liste nicht gefunden: {args.input}")

    entries = parse_raw_file(args.input)
    by_topic: dict[str, list[Entry]] = {}
    for entry in entries:
        by_topic.setdefault(entry.topic, []).append(entry)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    created = []
    for topic, topic_entries in by_topic.items():
        output_file = args.output_dir / f"{slugify_topic(topic)}.md"
        if output_file.exists() and not args.overwrite:
            raise FileExistsError(f"Themen-Datei existiert bereits: {output_file}. Nutze --overwrite.")
        output_file.write_text(
            render_topic_file(topic, topic_entries, args.input, args.data_class),
            encoding="utf-8",
        )
        created.append(output_file)

    print(f"Entries: {len(entries)}")
    print(f"Topics: {len(created)}")
    for path in created:
        print(f"Topic file: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
