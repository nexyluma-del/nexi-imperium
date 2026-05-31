#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from telegram_common import send_message_if_configured


PROJECT_DIR = Path(__file__).resolve().parents[1]
COST_DIR = PROJECT_DIR / "videos" / "_cost"
COST_FILE = COST_DIR / "api-costs.json"
ALERT_THRESHOLD_EUR = 30.0
USD_TO_EUR_GUARD = 1.0

API_DEFAULTS = {
    "gemini-flash": {
        "credit_env": "GEMINI_FLASH_INITIAL_CREDIT_EUR",
        "billing_url": "https://aistudio.google.com/usage",
    },
    "gemini-pro": {
        "credit_env": "GEMINI_PRO_INITIAL_CREDIT_EUR",
        "billing_url": "https://aistudio.google.com/usage",
    },
    "claude-vision": {
        "credit_env": "ANTHROPIC_INITIAL_CREDIT_EUR",
        "billing_url": "https://console.anthropic.com/settings/billing",
    },
    "openai-vision": {
        "credit_env": "OPENAI_INITIAL_CREDIT_EUR",
        "billing_url": "https://platform.openai.com/settings/organization/billing/overview",
    },
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def env_float(name: str) -> float | None:
    raw = os.getenv(name)
    if not raw:
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def empty_provider(name: str, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = API_DEFAULTS[name]
    previous = previous or {}
    starting_credit = previous.get("starting_credit_eur")
    if starting_credit is None:
        starting_credit = env_float(defaults["credit_env"])
    return {
        "calls": 0,
        "spent_usd": 0.0,
        "spent_eur": 0.0,
        "starting_credit_eur": starting_credit,
        "remaining_eur": starting_credit,
        "alert_threshold_eur": ALERT_THRESHOLD_EUR,
        "alert_sent": False,
        "billing_url": defaults["billing_url"],
        "last_model": None,
        "last_call_at": None,
    }


def reset_run(run_id: str, note: str = "") -> dict[str, Any]:
    previous = load_json(COST_FILE, {})
    previous_providers = previous.get("providers") if isinstance(previous, dict) else {}
    payload = {
        "run_id": run_id,
        "note": note,
        "reset_at": now_iso(),
        "updated_at": now_iso(),
        "currency_guard": "USD wird lokal konservativ 1:1 als EUR gerechnet.",
        "balance_notice": (
            "API-Guthaben ist nicht ueber den Gemini/Claude/OpenAI API-Key auslesbar. "
            "Setze optional *_INITIAL_CREDIT_EUR Umgebungsvariablen fuer Restguthaben-Alarme."
        ),
        "total_spent_usd": 0.0,
        "total_spent_eur": 0.0,
        "providers": {
            name: empty_provider(name, previous_providers.get(name) if isinstance(previous_providers, dict) else None)
            for name in API_DEFAULTS
        },
        "events": [],
    }
    write_json(COST_FILE, payload)
    return payload


def maybe_alert(api_name: str, provider: dict[str, Any], remaining_videos: int | None, rate_videos_per_hour: float | None) -> None:
    remaining = provider.get("remaining_eur")
    if remaining is None or provider.get("alert_sent"):
        return
    if float(remaining) >= float(provider.get("alert_threshold_eur") or ALERT_THRESHOLD_EUR):
        return

    spent = float(provider.get("spent_eur") or 0)
    calls = int(provider.get("calls") or 0)
    avg = spent / calls if calls else 0
    projected = None if remaining_videos is None else round(avg * remaining_videos, 2)
    eta = "n/a"
    if rate_videos_per_hour and avg > 0:
        videos_until_empty = max(0.0, float(remaining) / avg)
        eta = f"{videos_until_empty / rate_videos_per_hour:.1f} h"

    send_message_if_configured(
        "\n".join(
            [
                "API-Guthaben-Warnung",
                f"API: {api_name}",
                f"Restguthaben: {remaining:.2f} EUR",
                f"Hochrechnung Restvideos: {projected if projected is not None else 'n/a'} EUR",
                f"ETA bis Budget leer: {eta}",
                f"Aufladen: {provider.get('billing_url')}",
            ]
        )
    )
    provider["alert_sent"] = True


def record_call(
    api_name: str,
    model: str,
    cost_usd: float,
    run_id: str | None = None,
    video_id: str | None = None,
    category: str | None = None,
    remaining_videos: int | None = None,
    rate_videos_per_hour: float | None = None,
) -> dict[str, Any]:
    payload = load_json(COST_FILE, {})
    if not payload or (run_id and payload.get("run_id") != run_id):
        payload = reset_run(run_id or "manual")

    providers = payload.setdefault("providers", {})
    if api_name not in providers:
        providers[api_name] = {
            "calls": 0,
            "spent_usd": 0.0,
            "spent_eur": 0.0,
            "starting_credit_eur": None,
            "remaining_eur": None,
            "alert_threshold_eur": ALERT_THRESHOLD_EUR,
            "alert_sent": False,
            "billing_url": "",
            "last_model": None,
            "last_call_at": None,
        }
    provider = providers[api_name]
    cost_eur = round(float(cost_usd or 0) * USD_TO_EUR_GUARD, 6)
    provider["calls"] = int(provider.get("calls") or 0) + 1
    provider["spent_usd"] = round(float(provider.get("spent_usd") or 0) + float(cost_usd or 0), 6)
    provider["spent_eur"] = round(float(provider.get("spent_eur") or 0) + cost_eur, 6)
    provider["last_model"] = model
    provider["last_call_at"] = now_iso()
    if provider.get("starting_credit_eur") is not None:
        provider["remaining_eur"] = round(float(provider["starting_credit_eur"]) - float(provider["spent_eur"]), 6)

    event = {
        "at": now_iso(),
        "api": api_name,
        "model": model,
        "cost_usd": round(float(cost_usd or 0), 6),
        "cost_eur": cost_eur,
        "video_id": video_id,
        "category": category,
    }
    payload.setdefault("events", []).append(event)
    payload["total_spent_usd"] = round(sum(float(item.get("spent_usd") or 0) for item in providers.values()), 6)
    payload["total_spent_eur"] = round(sum(float(item.get("spent_eur") or 0) for item in providers.values()), 6)
    payload["updated_at"] = now_iso()

    maybe_alert(api_name, provider, remaining_videos, rate_videos_per_hour)
    write_json(COST_FILE, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Track API costs for Nexi video pipelines.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    reset = sub.add_parser("reset")
    reset.add_argument("--run-id", required=True)
    reset.add_argument("--note", default="")
    record = sub.add_parser("record")
    record.add_argument("--api", required=True)
    record.add_argument("--model", required=True)
    record.add_argument("--cost-usd", type=float, required=True)
    record.add_argument("--run-id", default=None)
    record.add_argument("--video-id", default=None)
    record.add_argument("--category", default=None)
    summary = sub.add_parser("summary")
    summary.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.cmd == "reset":
        payload = reset_run(args.run_id, args.note)
    elif args.cmd == "record":
        payload = record_call(args.api, args.model, args.cost_usd, args.run_id, args.video_id, args.category)
    else:
        payload = load_json(COST_FILE, {})

    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
