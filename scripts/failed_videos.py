from __future__ import annotations

from datetime import datetime
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
FAILED_VIDEOS = PROJECT_DIR / "failed-videos.md"


def append_failed_video(*, url: str, topic: str = "", error: str = "", source: str = "") -> None:
    FAILED_VIDEOS.parent.mkdir(parents=True, exist_ok=True)
    if not FAILED_VIDEOS.exists():
        FAILED_VIDEOS.write_text(
            "# Failed Videos\n\n"
            "Laufende Fehlerliste fuer Batch-, Telegram- und lokale Pipeline-Laeufe.\n\n",
            encoding="utf-8",
        )
    current = FAILED_VIDEOS.read_text(encoding="utf-8")
    if "Noch keine fehlgeschlagenen Eintraege." in current:
        current = current.replace("\nNoch keine fehlgeschlagenen Eintraege.\n", "\n")
        FAILED_VIDEOS.write_text(current.rstrip() + "\n\n", encoding="utf-8")
    safe_error = error.replace("\r", " ").replace("\n", " ").strip()
    entry = "\n".join(
        [
            f"## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Quelle: `{source or 'unbekannt'}`",
            f"- Thema: `{topic or 'unbekannt'}`",
            f"- URL: {url or 'n/a'}",
            f"- Fehler: {safe_error[:1200] or 'n/a'}",
            "",
        ]
    )
    with FAILED_VIDEOS.open("a", encoding="utf-8") as handle:
        handle.write(entry)
