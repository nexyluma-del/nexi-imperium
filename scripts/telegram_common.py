from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests


PROJECT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_DIR / ".env"
MAX_TELEGRAM_CHARS = 3900


def read_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def get_setting(name: str, default: str = "") -> str:
    return os.getenv(name) or read_env_file().get(name, default)


def require_token() -> str:
    token = get_setting("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(f"TELEGRAM_BOT_TOKEN fehlt in {ENV_FILE}")
    return token


def get_chat_id() -> str:
    return get_setting("TELEGRAM_CHAT_ID")


def set_env_value(name: str, value: str) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines() if ENV_FILE.exists() else []
    new_lines = [line for line in lines if not line.startswith(f"{name}=")]
    new_lines.append(f"{name}={value}")
    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def telegram_api(method: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    token = require_token()
    url = f"https://api.telegram.org/bot{token}/{method}"
    response = requests.post(url, json=payload or {}, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API Fehler bei {method}: {json.dumps(data, ensure_ascii=False)}")
    return data


def get_updates(offset: int | None = None, timeout: int = 25) -> list[dict[str, Any]]:
    payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": ["message"]}
    if offset is not None:
        payload["offset"] = offset
    return telegram_api("getUpdates", payload=payload, timeout=timeout + 10).get("result", [])


def latest_private_chat_id() -> str | None:
    updates = get_updates(timeout=2)
    for update in reversed(updates):
        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat") or {}
        if chat.get("type") == "private" and chat.get("id") is not None:
            return str(chat["id"])
    return None


def ensure_chat_id_from_updates() -> str | None:
    current = get_chat_id()
    if current:
        return current
    chat_id = latest_private_chat_id()
    if chat_id:
        set_env_value("TELEGRAM_CHAT_ID", chat_id)
    return chat_id


def split_message(text: str) -> list[str]:
    if len(text) <= MAX_TELEGRAM_CHARS:
        return [text]
    chunks: list[str] = []
    current = text
    while len(current) > MAX_TELEGRAM_CHARS:
        split_at = current.rfind("\n", 0, MAX_TELEGRAM_CHARS)
        if split_at < 1000:
            split_at = MAX_TELEGRAM_CHARS
        chunks.append(current[:split_at].strip())
        current = current[split_at:].strip()
    if current:
        chunks.append(current)
    return chunks


def send_message(text: str, chat_id: str | None = None, disable_web_preview: bool = True) -> bool:
    target_chat = chat_id or get_chat_id()
    if not target_chat:
        return False
    for chunk in split_message(text):
        telegram_api(
            "sendMessage",
            {
                "chat_id": target_chat,
                "text": chunk,
                "disable_web_page_preview": disable_web_preview,
            },
            timeout=30,
        )
    return True


def send_message_if_configured(text: str) -> bool:
    try:
        return send_message(text)
    except Exception:
        return False
