#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any


MODEL_ID = "nexi-rag-qwen3-30b"
BASE_MODEL_ID = "qwen3:30b"
KNOWLEDGE_ID = "nexi-video-knowledge"
DB_PATH = Path("/app/backend/data/webui.db")


SYSTEM_PROMPT = """Du bist Nexis OpenWebUI-Wissensmodell.

Nutze standardmaessig die angehaengte Knowledge Base, bevor du frei antwortest.
Antworte auf Deutsch, klar, knapp und umsetzungsnah.
Wenn der Kontext aus der Knowledge Base nicht reicht, sage das offen.
Setze Quellenhinweise direkt an die Aussagen, z.B. [1] oder [Quelle 1].
Der interne Thinking-Teil gehoert nicht in die normale Antwort.
"""


def load_json(value: str | bytes | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def fetch_one(con: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row:
    row = con.execute(query, params).fetchone()
    if row is None:
        raise RuntimeError(f"Keine Daten gefunden fuer Query: {query}")
    return row


def configure(db_path: Path, no_backup: bool = False) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"OpenWebUI-Datenbank nicht gefunden: {db_path}")

    backup_path = None
    if not no_backup:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = db_path.with_name(f"{db_path.name}.codex-{timestamp}.bak")
        shutil.copy2(db_path, backup_path)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        user = fetch_one(
            con,
            "select id, name, email from user where role='admin' order by created_at limit 1",
        )
        knowledge = fetch_one(
            con,
            "select id, name, description from knowledge where id=?",
            (KNOWLEDGE_ID,),
        )

        now = int(time.time())
        meta = {
            "description": (
                "Default-Wissensmodell fuer Nexis Video- und Projektwissen. "
                "Die Knowledge Base ist fest am Modell hinterlegt."
            ),
            "capabilities": {
                "citations": True,
                "file_context": True,
                "web_search": False,
                "image_generation": False,
            },
            "knowledge": [
                {
                    "id": knowledge["id"],
                    "name": knowledge["name"],
                    "type": "collection",
                }
            ],
            "tags": [
                {"name": "Nexi"},
                {"name": "RAG"},
                {"name": "Default"},
            ],
        }
        params = {
            "system": SYSTEM_PROMPT.strip(),
            "reasoning_tags": ["<think>", "</think>"],
            "temperature": 0.2,
            "top_p": 0.8,
            "stream_response": True,
        }

        con.execute(
            """
            insert into model (
                id, user_id, base_model_id, name, meta, params,
                created_at, updated_at, is_active
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, 1)
            on conflict(id) do update set
                user_id=excluded.user_id,
                base_model_id=excluded.base_model_id,
                name=excluded.name,
                meta=excluded.meta,
                params=excluded.params,
                updated_at=excluded.updated_at,
                is_active=1
            """,
            (
                MODEL_ID,
                user["id"],
                BASE_MODEL_ID,
                "Nexi Wissen (qwen3:30b + Quellen)",
                json.dumps(meta, ensure_ascii=False),
                json.dumps(params, ensure_ascii=False),
                now,
                now,
            ),
        )

        config_row = fetch_one(con, "select id, data, version from config order by id limit 1")
        config_data = load_json(config_row["data"], {"version": 0})
        ui = config_data.setdefault("ui", {})
        ui["enable_signup"] = False
        ui["default_models"] = MODEL_ID
        ui["default_pinned_models"] = MODEL_ID

        con.execute(
            "update config set data=?, updated_at=CURRENT_TIMESTAMP where id=?",
            (json.dumps(config_data, ensure_ascii=False), config_row["id"]),
        )
        con.commit()

        return {
            "ok": True,
            "model_id": MODEL_ID,
            "base_model_id": BASE_MODEL_ID,
            "knowledge_id": KNOWLEDGE_ID,
            "knowledge_name": knowledge["name"],
            "admin_user": user["email"],
            "backup_path": str(backup_path) if backup_path else None,
            "default_models": MODEL_ID,
            "default_pinned_models": MODEL_ID,
            "configured_at": datetime.now().isoformat(timespec="seconds"),
        }
    finally:
        con.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set OpenWebUI default RAG model for Nexi.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--no-backup", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = configure(args.db, no_backup=args.no_backup)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
