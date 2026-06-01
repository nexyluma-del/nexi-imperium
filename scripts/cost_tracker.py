#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from telegram_common import send_message_if_configured


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = PROJECT_DIR / ".env"
COST_DIR = PROJECT_DIR / "videos" / "_cost"
COST_FILE = COST_DIR / "api-costs.json"
DEFAULT_ALERT_THRESHOLD_EUR = 60.0
USD_TO_EUR_GUARD = 1.0

load_dotenv(DEFAULT_ENV_FILE)

API_DEFAULTS = {
    "gemini-flash": {
        "threshold_env": "GEMINI_FLASH_WARN_THRESHOLD_EUR",
        "billing_url": "https://aistudio.google.com/usage",
    },
    "gemini-pro": {
        "threshold_env": "GEMINI_PRO_WARN_THRESHOLD_EUR",
        "billing_url": "https://aistudio.google.com/usage",
    },
    "claude-vision": {
        "threshold_env": "ANTHROPIC_WARN_THRESHOLD_EUR",
        "billing_url": "https://console.anthropic.com/settings/billing",
    },
    "openai-vision": {
        "threshold_env": "OPENAI_WARN_THRESHOLD_EUR",
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


def alert_threshold_eur(api_name: str) -> float:
    defaults = API_DEFAULTS.get(api_name, {})
    specific = defaults.get("threshold_env")
    value = env_float(str(specific)) if specific else None
    if value is None:
        value = env_float("WARN_THRESHOLD_EUR")
    return float(value if value is not None else DEFAULT_ALERT_THRESHOLD_EUR)


def provider_defaults(api_name: str) -> dict[str, str]:
    return API_DEFAULTS.get(
        api_name,
        {
            "threshold_env": "",
            "billing_url": "",
        },
    )


def empty_provider(name: str, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = provider_defaults(name)
    previous = previous or {}
    return {
        "calls": 0,
        "spent_usd": 0.0,
        "spent_eur": 0.0,
        "alert_threshold_eur": alert_threshold_eur(name),
        "alert_sent": False,
        "billing_url": defaults["billing_url"],
        "last_model": None,
        "last_call_at": None,
    }


def sync_provider_config(api_name: str, provider: dict[str, Any]) -> None:
    defaults = provider_defaults(api_name)
    previous_threshold = provider.get("alert_threshold_eur")
    threshold = alert_threshold_eur(api_name)
    provider["alert_threshold_eur"] = threshold
    provider["billing_url"] = provider.get("billing_url") or defaults.get("billing_url", "")
    if previous_threshold is not None and float(previous_threshold) != threshold:
        provider["alert_sent"] = False
    provider.pop("starting_credit_eur", None)
    provider.pop("remaining_eur", None)


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
            "Counter loest pro API bei Verbrauch >= WARN_THRESHOLD_EUR Alarm aus. "
            "Reset per Telegram: /reset_cost <api_name>."
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
    if provider.get("alert_sent"):
        return
    threshold = float(provider.get("alert_threshold_eur") or DEFAULT_ALERT_THRESHOLD_EUR)
    spent = float(provider.get("spent_eur") or 0)
    if spent < threshold:
        return

    sent = send_message_if_configured(
        "\n".join(
            [
                "API-Verbrauchs-Warnung",
                f"API {api_name} hat {threshold:.2f} EUR verbraucht.",
                "Lade auf oder bestaetige Reset.",
                f"Antworte mit /reset_cost {api_name} um den Counter wieder auf 0 EUR zu setzen.",
                f"Aktueller Verbrauch: {spent:.2f} EUR",
                f"Aufladen: {provider.get('billing_url')}",
            ]
        )
    )
    provider["alert_sent"] = bool(sent)
    provider["last_alert_at"] = now_iso() if sent else provider.get("last_alert_at")


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
    if not payload:
        payload = reset_run(run_id or "manual")
    elif run_id and payload.get("run_id") != run_id:
        related = payload.setdefault("related_run_ids", [])
        if run_id not in related:
            related.append(run_id)

    providers = payload.setdefault("providers", {})
    if api_name not in providers:
        providers[api_name] = {
            "calls": 0,
            "spent_usd": 0.0,
            "spent_eur": 0.0,
            "alert_threshold_eur": alert_threshold_eur(api_name),
            "alert_sent": False,
            "billing_url": "",
            "last_model": None,
            "last_call_at": None,
        }
    provider = providers[api_name]
    sync_provider_config(api_name, provider)
    cost_eur = round(float(cost_usd or 0) * USD_TO_EUR_GUARD, 6)
    provider["calls"] = int(provider.get("calls") or 0) + 1
    provider["spent_usd"] = round(float(provider.get("spent_usd") or 0) + float(cost_usd or 0), 6)
    provider["spent_eur"] = round(float(provider.get("spent_eur") or 0) + cost_eur, 6)
    provider["last_model"] = model
    provider["last_call_at"] = now_iso()

    event = {
        "at": now_iso(),
        "api": api_name,
        "run_id": run_id,
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


def reset_api_cost(api_name: str) -> dict[str, Any]:
    payload = load_json(COST_FILE, {})
    if not payload:
        payload = reset_run("manual")
    providers = payload.setdefault("providers", {})
    if api_name not in providers:
        providers[api_name] = empty_provider(api_name)
    provider = providers[api_name]
    sync_provider_config(api_name, provider)
    previous = {
        "spent_usd": provider.get("spent_usd", 0),
        "spent_eur": provider.get("spent_eur", 0),
        "calls": provider.get("calls", 0),
    }
    provider["calls"] = 0
    provider["spent_usd"] = 0.0
    provider["spent_eur"] = 0.0
    provider["alert_sent"] = False
    provider["last_reset_at"] = now_iso()
    provider["last_reset_previous"] = previous
    payload.setdefault("events", []).append(
        {
            "at": now_iso(),
            "api": api_name,
            "type": "manual_reset",
            "previous": previous,
        }
    )
    payload["total_spent_usd"] = round(sum(float(item.get("spent_usd") or 0) for item in providers.values()), 6)
    payload["total_spent_eur"] = round(sum(float(item.get("spent_eur") or 0) for item in providers.values()), 6)
    payload["updated_at"] = now_iso()
    write_json(COST_FILE, payload)
    return payload


def sync_config() -> dict[str, Any]:
    payload = load_json(COST_FILE, {})
    if not payload:
        payload = reset_run("manual")
    payload["balance_notice"] = (
        "Counter loest pro API bei Verbrauch >= WARN_THRESHOLD_EUR Alarm aus. "
        "Reset per Telegram: /reset_cost <api_name>."
    )
    providers = payload.setdefault("providers", {})
    for api_name in API_DEFAULTS:
        if api_name not in providers:
            providers[api_name] = empty_provider(api_name)
        sync_provider_config(api_name, providers[api_name])
    payload["updated_at"] = now_iso()
    payload["config_synced_at"] = now_iso()
    write_json(COST_FILE, payload)
    return payload


def send_test_alert(
    api_name: str,
    spent_eur: float,
    threshold_eur: float | None,
    remaining_videos: int | None,
    rate_videos_per_hour: float | None,
) -> bool:
    provider = empty_provider(api_name)
    provider["spent_eur"] = spent_eur
    provider["calls"] = 1
    if threshold_eur is not None:
        provider["alert_threshold_eur"] = threshold_eur
    provider["alert_sent"] = False
    maybe_alert(api_name, provider, remaining_videos, rate_videos_per_hour)
    return bool(provider.get("alert_sent"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Track API costs for Nexi video pipelines.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    reset = sub.add_parser("reset")
    reset.add_argument("--run-id", required=True)
    reset.add_argument("--note", default="")
    reset_api = sub.add_parser("reset-api")
    reset_api.add_argument("--api", required=True)
    record = sub.add_parser("record")
    record.add_argument("--api", required=True)
    record.add_argument("--model", required=True)
    record.add_argument("--cost-usd", type=float, required=True)
    record.add_argument("--run-id", default=None)
    record.add_argument("--video-id", default=None)
    record.add_argument("--category", default=None)
    sub.add_parser("sync-config")
    test = sub.add_parser("test-alert")
    test.add_argument("--api", required=True)
    test.add_argument("--spent-eur", type=float, required=True)
    test.add_argument("--threshold-eur", type=float, default=None)
    test.add_argument("--remaining-videos", type=int, default=3000)
    test.add_argument("--rate-videos-per-hour", type=float, default=40.0)
    summary = sub.add_parser("summary")
    summary.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.cmd == "reset":
        payload = reset_run(args.run_id, args.note)
    elif args.cmd == "reset-api":
        payload = reset_api_cost(args.api)
    elif args.cmd == "record":
        payload = record_call(args.api, args.model, args.cost_usd, args.run_id, args.video_id, args.category)
    elif args.cmd == "sync-config":
        payload = sync_config()
    elif args.cmd == "test-alert":
        sent = send_test_alert(args.api, args.spent_eur, args.threshold_eur, args.remaining_videos, args.rate_videos_per_hour)
        payload = {"ok": sent, "api": args.api, "spent_eur": args.spent_eur, "threshold_eur": args.threshold_eur or alert_threshold_eur(args.api)}
    else:
        payload = sync_config()

    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
