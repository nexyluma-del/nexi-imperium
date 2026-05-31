from __future__ import annotations

import json
import hashlib
import mimetypes
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = PROJECT_DIR / ".env"
DEFAULT_ANALYSIS_DIR = PROJECT_DIR / "analysis"
DEFAULT_MODEL = "gemini-2.5-pro"
VALID_DATA_CLASSES = {"D0", "D1", "D2", "D3", "D4"}

# Official Gemini Developer API paid-tier prices, USD per 1M tokens.
# Checked against Google docs on 2026-05-29. The cap is treated 1 USD ~= 1 EUR
# for a conservative local guardrail.
MODEL_PRICES_USD = {
    "gemini-2.5-pro": {
        "input_per_million": 1.25,
        "output_per_million": 10.00,
        "input_over_200k_per_million": 2.50,
        "output_over_200k_per_million": 15.00,
    },
    "gemini-3.1-pro-preview": {
        "input_per_million": 2.00,
        "output_per_million": 12.00,
        "input_over_200k_per_million": 4.00,
        "output_over_200k_per_million": 18.00,
    },
    "gemini-2.5-flash": {
        "input_per_million": 0.30,
        "output_per_million": 2.50,
    },
    "gemini-3.5-flash": {
        "input_per_million": 1.50,
        "output_per_million": 9.00,
    },
}


@dataclass
class Preflight:
    video_file: Path
    size_mb: float
    duration_seconds: float | None
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    estimated_cost_eur_conservative: float


def load_settings(env_file: Path = DEFAULT_ENV_FILE) -> dict[str, str]:
    load_dotenv(env_file, encoding="utf-8-sig")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            f"GEMINI_API_KEY fehlt. Erwartet in Umgebungsvariable oder {env_file}."
        )

    return {
        "api_key": api_key,
        "model": os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
        "cost_cap_eur": os.getenv("GEMINI_COST_CAP_EUR", "0.30"),
    }


def make_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


def instagram_shortcode(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"instagram\.com/(?:reel|p|tv)/([^/?#]+)/?", url, re.I)
    return match.group(1) if match else None


def metadata_matches_url(metadata: dict[str, Any], source_url: str) -> bool:
    expected = instagram_shortcode(source_url)
    if expected:
        candidates = {
            str(metadata.get("id") or ""),
            str(metadata.get("display_id") or ""),
            str(metadata.get("webpage_url_basename") or ""),
        }
        webpage_url = str(metadata.get("webpage_url") or metadata.get("original_url") or "")
        webpage_shortcode = instagram_shortcode(webpage_url)
        if webpage_shortcode:
            candidates.add(webpage_shortcode)
        return expected in candidates

    source = source_url.rstrip("/")
    for key in ("webpage_url", "original_url", "url"):
        value = str(metadata.get(key) or "").rstrip("/")
        if value and (value == source or source in value or value in source):
            return True
    return False


def validate_info_json_for_url(info_json: Path, source_url: str) -> dict[str, Any]:
    if not info_json.exists():
        raise FileNotFoundError(f"yt-dlp info.json fehlt: {info_json}")
    metadata = json.loads(info_json.read_text(encoding="utf-8"))
    if not metadata_matches_url(metadata, source_url):
        raise RuntimeError(
            "Download-Provenance-Check fehlgeschlagen: info.json passt nicht zur URL.\n"
            f"URL: {source_url}\n"
            f"Info: {info_json}\n"
            f"id={metadata.get('id')} webpage_url={metadata.get('webpage_url')}"
        )
    return metadata


def cleanup_gemini_files(client: Any, label: str = "pre-run") -> dict[str, Any]:
    """Delete stale Gemini File API files before/after a run.

    The pipeline never relies on persisted Gemini files. Keeping the remote
    file store empty removes any chance of old test media being referenced.
    """
    deleted: list[str] = []
    errors: list[str] = []
    try:
        files = client.files.list()
        for current in files:
            name = getattr(current, "name", None)
            if not name:
                continue
            try:
                client.files.delete(name=name)
                deleted.append(name)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{name}: {exc}")
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))
    return {
        "label": label,
        "deleted_count": len(deleted),
        "deleted": deleted,
        "errors": errors,
    }


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return cleaned[:120] or "video"


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def get_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".mov":
        return "video/quicktime"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def ffprobe_duration_seconds(path: Path) -> float | None:
    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ],
            check=True,
            text=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    try:
        return float(completed.stdout.strip())
    except ValueError:
        return None


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    prices = MODEL_PRICES_USD.get(model, MODEL_PRICES_USD[DEFAULT_MODEL])
    if input_tokens > 200_000:
        input_rate = prices.get("input_over_200k_per_million", prices["input_per_million"])
        output_rate = prices.get(
            "output_over_200k_per_million", prices["output_per_million"]
        )
    else:
        input_rate = prices["input_per_million"]
        output_rate = prices["output_per_million"]

    return (input_tokens / 1_000_000 * input_rate) + (
        output_tokens / 1_000_000 * output_rate
    )


def run_preflight(
    video_file: Path,
    model: str,
    max_cost_eur: float,
    max_video_mb: float,
    max_duration_seconds: float,
    expected_output_tokens: int,
    extra_text_tokens: int = 0,
    approve_large: bool = False,
) -> Preflight:
    video_file = video_file.resolve()
    if not video_file.exists():
        raise FileNotFoundError(f"Video nicht gefunden: {video_file}")

    size_mb = video_file.stat().st_size / 1024 / 1024
    duration_seconds = ffprobe_duration_seconds(video_file)
    video_tokens = int((duration_seconds or 60.0) * 300)
    estimated_input_tokens = video_tokens + extra_text_tokens + 2_000
    estimated_cost_usd = estimate_cost_usd(
        model=model,
        input_tokens=estimated_input_tokens,
        output_tokens=expected_output_tokens,
    )

    preflight = Preflight(
        video_file=video_file,
        size_mb=round(size_mb, 3),
        duration_seconds=round(duration_seconds, 3) if duration_seconds else None,
        estimated_input_tokens=estimated_input_tokens,
        estimated_output_tokens=expected_output_tokens,
        estimated_cost_usd=round(estimated_cost_usd, 6),
        estimated_cost_eur_conservative=round(estimated_cost_usd, 6),
    )

    blockers: list[str] = []
    if size_mb > max_video_mb:
        blockers.append(f"Video ist {size_mb:.2f} MB > Limit {max_video_mb:.2f} MB")
    if duration_seconds and duration_seconds > max_duration_seconds:
        blockers.append(
            f"Video ist {duration_seconds:.1f}s > Limit {max_duration_seconds:.1f}s"
        )
    if preflight.estimated_cost_eur_conservative > max_cost_eur:
        blockers.append(
            "Kosten-Schaetzung "
            f"{preflight.estimated_cost_eur_conservative:.4f} EUR > Limit {max_cost_eur:.2f} EUR"
        )

    if blockers and not approve_large:
        joined = "\n- ".join(blockers)
        raise RuntimeError(
            "Kosten-/Groessen-Schutz hat den API-Call gestoppt:\n"
            f"- {joined}\n"
            "Nutze --approve-large nur nach ausdruecklicher Freigabe."
        )

    return preflight


def usage_to_dict(usage: Any) -> dict[str, int | None]:
    if usage is None:
        return {
            "prompt_token_count": None,
            "candidates_token_count": None,
            "total_token_count": None,
            "thoughts_token_count": None,
        }

    def read(name: str) -> int | None:
        value = getattr(usage, name, None)
        return int(value) if value is not None else None

    return {
        "prompt_token_count": read("prompt_token_count"),
        "candidates_token_count": read("candidates_token_count"),
        "total_token_count": read("total_token_count"),
        "thoughts_token_count": read("thoughts_token_count"),
    }


def actual_cost_from_usage(model: str, usage: dict[str, int | None]) -> float | None:
    input_tokens = usage.get("prompt_token_count")
    output_tokens = usage.get("candidates_token_count")
    if input_tokens is None or output_tokens is None:
        return None
    return round(estimate_cost_usd(model, input_tokens, output_tokens), 6)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def print_cost_summary(
    model: str,
    usage: dict[str, int | None],
    estimated_cost_usd: float,
    actual_cost_usd: float | None,
) -> None:
    print(f"Model: {model}")
    print(f"Prompt tokens: {usage.get('prompt_token_count')}")
    print(f"Output tokens: {usage.get('candidates_token_count')}")
    print(f"Total tokens: {usage.get('total_token_count')}")
    print(f"Estimated preflight cost: ${estimated_cost_usd:.6f}")
    if actual_cost_usd is not None:
        print(f"Estimated actual cost: ${actual_cost_usd:.6f}")
