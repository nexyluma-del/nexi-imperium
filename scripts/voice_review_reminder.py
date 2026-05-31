#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime

from telegram_common import send_message


DAILY_MESSAGE = (
    "Kurzer Memory-Check: Was willst du heute noch festhalten?\n"
    "Wenn dir eine Idee im Kopf liegt, nimm sie per Voice-Capture auf "
    "oder schick mir eine Sprachnotiz/Notiz fuer die Inbox."
)

WEEKLY_MESSAGE = (
    "Wochen-Review fuer dein zweites Gehirn:\n"
    "1. Was war diese Woche wichtig?\n"
    "2. Welche Idee darf nicht verloren gehen?\n"
    "3. Was soll Memory-KI naechste Woche im Blick behalten?"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Telegram-Reminder fuer Voice-Capture Reviews.")
    parser.add_argument("--kind", choices=["daily", "weekly"], default="daily")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    message = DAILY_MESSAGE if args.kind == "daily" else WEEKLY_MESSAGE
    send_message(f"{message}\n\nZeitpunkt: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
