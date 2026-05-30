#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from telegram_common import ensure_chat_id_from_updates, send_message


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a Telegram message to Nexi's Imperium bot chat.")
    parser.add_argument("message", nargs="*", help="Message text. If omitted, stdin is used.")
    parser.add_argument("--discover-chat-id", action="store_true")
    args = parser.parse_args()

    if args.discover_chat_id:
        chat_id = ensure_chat_id_from_updates()
        if not chat_id:
            print("Keine Chat-ID gefunden. Schreibe dem Bot zuerst /start.", file=sys.stderr)
            return 2
        print("Chat-ID gespeichert.")
        return 0

    text = " ".join(args.message).strip() if args.message else sys.stdin.read().strip()
    if not text:
        print("Keine Nachricht angegeben.", file=sys.stderr)
        return 2
    if not send_message(text):
        print("TELEGRAM_CHAT_ID fehlt. Fuehre zuerst --discover-chat-id aus.", file=sys.stderr)
        return 2
    print("Telegram-Nachricht gesendet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
