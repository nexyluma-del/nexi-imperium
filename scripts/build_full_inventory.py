#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from split_roh_liste import parse_raw_file


PROJECT_DIR = Path(__file__).resolve().parents[1]
LOCAL_ROOT = Path("/mnt/c/Users/nexil/Desktop/Instagram Videos")
RAW_URL_FILE = Path("/mnt/c/Users/nexil/Desktop/Instagram Liste/videos-roh.md")
INVENTORY_DIR = PROJECT_DIR / "videos" / "_inventory"
FULL_JSON = INVENTORY_DIR / "full-inventory.json"
URL_JSON = INVENTORY_DIR / "url-inventory.json"
SUMMARY_MD = INVENTORY_DIR / "full-inventory.md"
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


TOPIC_MAP = {
    "IT": "01-IT",
    "WEBSEITEN": "01-IT",
    "KI-IT": "03-KI-IT",
    "KI-AVATARE": "03-KI-IT",
    "IT-HACKING-SICHERHEIT": "02-IT-HACKS",
    "NEWS": "05-NEWS",
    "IT NEWS": "05-NEWS",
    "FINANZEN": "06-FINANZEN",
    "KRYPTO": "06-FINANZEN",
    "FILME": "07-FILME",
    "MUSIK": "08-MUSIK",
    "NEUHEITEN-PRODUKTE": "04-TECHNIK",
    "TECHNIK": "04-TECHNIK",
    "SOFINELLO": "10-SOFINELLO",
}

LOCAL_FOLDER_HINTS = {
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
    "Sofinello": "10-SOFINELLO",
    "Sofinello Videos": "10-SOFINELLO",
    "Sofinello Gerichte": "10-SOFINELLO",
    "Sofinello To-Do": "10-SOFINELLO",
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def wsl_to_windows(path: str | Path | None) -> str | None:
    if path is None:
        return None
    value = str(path)
    if value.startswith("/mnt/c/"):
        return "C:\\" + value[len("/mnt/c/") :].replace("/", "\\")
    return value


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


def instagram_id(url: str) -> str | None:
    match = re.search(r"instagram\.com/(?:reel|p|tv)/([^/?#]+)", url, flags=re.I)
    return match.group(1) if match else None


def route_topic(topic: str) -> str:
    normalized = re.sub(r"\s+", " ", topic.strip()).upper()
    return TOPIC_MAP.get(normalized, "_unsortiert")


def local_top_folder(path: Path) -> str:
    try:
        relative = path.relative_to(LOCAL_ROOT)
    except ValueError:
        return path.parent.name
    return relative.parts[0] if relative.parts else path.parent.name


def scan_local() -> list[dict[str, Any]]:
    entries = []
    for path in sorted(LOCAL_ROOT.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or path.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        folder = local_top_folder(path)
        category_hint = LOCAL_FOLDER_HINTS.get(folder, "_classifier_required")
        entries.append(
            {
                "source_kind": "local-file",
                "source_path": str(path),
                "source_path_windows": wsl_to_windows(path),
                "top_folder": folder,
                "category_hint": category_hint,
                "auto_gemini": category_hint != "_unsortiert",
                "requires_classifier": True,
                "size_mb": round(path.stat().st_size / 1024 / 1024, 3),
                "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
            }
        )
    return entries


def scan_urls() -> list[dict[str, Any]]:
    raw_entries = parse_raw_file(RAW_URL_FILE)
    result = []
    seen: dict[str, int] = {}
    for index, entry in enumerate(raw_entries, start=1):
        route = route_topic(entry.topic)
        clean_url = entry.url.strip()
        seen[clean_url] = seen.get(clean_url, 0) + 1
        result.append(
            {
                "source_kind": "url",
                "index": index,
                "url": clean_url,
                "url_hash": url_hash(clean_url),
                "instagram_id": instagram_id(clean_url),
                "raw_topic": entry.topic,
                "category_hint": route,
                "auto_gemini": route != "_unsortiert",
                "tags": entry.tags,
                "questions": entry.questions,
                "data_class": "D2",
                "requires_download": True,
                "anti_nasa_required": True,
                "gemini_file_cleanup_required": True,
                "duplicate_url_count_in_raw": seen[clean_url],
            }
        )
    return result


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def render_summary(payload: dict[str, Any]) -> str:
    local_counts = Counter(item["category_hint"] for item in payload["local_files"])
    url_counts = Counter(item["category_hint"] for item in payload["urls"])
    lines = [
        "# Voll-Inventar Video-Pipeline",
        "",
        f"Stand: {payload['generated_at']}",
        "",
        "## Quellen",
        "",
        f"- Lokaler Ordner: `{wsl_to_windows(LOCAL_ROOT)}`",
        f"- Roh-URL-Datei: `{wsl_to_windows(RAW_URL_FILE)}`",
        "",
        "## Zahlen",
        "",
        f"- Lokale Videodateien: `{len(payload['local_files'])}`",
        f"- Roh-URL-Eintraege: `{len(payload['urls'])}`",
        f"- Eindeutige Roh-URLs: `{payload['unique_url_count']}`",
        f"- Gesamtquellen: `{len(payload['local_files']) + len(payload['urls'])}`",
        "",
        "## URL-Integration",
        "",
        "Die 44 URLs aus `videos-roh.md` sind als `source_kind=url` aufgenommen. Im Voll-Lauf werden sie wie lokale Videos mit eindeutiger URL-ID, Download-Provenance, Gemini File API Cleanup und Anti-NASA-Waechter verarbeitet.",
        "",
        "## Lokale Kategorie-Hints",
        "",
    ]
    for category, count in sorted(local_counts.items()):
        lines.append(f"- `{category}`: {count}")
    lines.extend(["", "## URL Kategorie-Hints", ""])
    for category, count in sorted(url_counts.items()):
        lines.append(f"- `{category}`: {count}")
    return "\n".join(lines) + "\n"


def main() -> int:
    if not LOCAL_ROOT.exists():
        raise FileNotFoundError(f"Lokaler Video-Ordner fehlt: {LOCAL_ROOT}")
    if not RAW_URL_FILE.exists():
        raise FileNotFoundError(f"Roh-URL-Datei fehlt: {RAW_URL_FILE}")
    local_files = scan_local()
    urls = scan_urls()
    unique_urls = {entry["url"] for entry in urls}
    payload = {
        "generated_at": now_iso(),
        "policy": {
            "unsortiert_auto_gemini": False,
            "duplicate_handling": "URL hash and local SHA during execution; duplicates get reference manifests.",
            "anti_nasa_guard": "required for every Gemini call",
            "gemini_file_api_cleanup": "before and after each Gemini call",
        },
        "local_root": str(LOCAL_ROOT),
        "local_root_windows": wsl_to_windows(LOCAL_ROOT),
        "raw_url_file": str(RAW_URL_FILE),
        "raw_url_file_windows": wsl_to_windows(RAW_URL_FILE),
        "unique_url_count": len(unique_urls),
        "local_files": local_files,
        "urls": urls,
    }
    write_json(FULL_JSON, payload)
    write_json(URL_JSON, {"generated_at": payload["generated_at"], "raw_url_file": payload["raw_url_file"], "urls": urls})
    SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text(render_summary(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "local_files": len(local_files), "urls": len(urls), "unique_urls": len(unique_urls), "summary": str(SUMMARY_MD)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
