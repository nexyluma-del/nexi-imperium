#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
VALID_DATA_CLASSES = {"D0", "D1", "D2", "D3", "D4"}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def ensure_project_venv() -> None:
    if os.environ.get("VIDEO_PIPELINE_VENV_READY") == "1":
        return
    venv_dir = PROJECT_DIR / ".venv"
    venv_python = venv_dir / "bin" / "python"
    if not venv_python.exists():
        return
    if Path(sys.prefix).resolve() == venv_dir.resolve():
        return
    env = os.environ.copy()
    env["VIDEO_PIPELINE_VENV_READY"] = "1"
    os.execvpe(str(venv_python), [str(venv_python), *sys.argv], env)


ensure_project_venv()

import requests  # noqa: E402
from anthropic import Anthropic  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from google.genai import types  # noqa: E402
from openai import OpenAI  # noqa: E402

from gemini_common import (  # noqa: E402
    actual_cost_from_usage,
    cleanup_gemini_files,
    file_sha256,
    get_mime_type,
    load_settings,
    make_client,
    now_stamp,
    slugify,
    url_hash,
    usage_to_dict,
    validate_info_json_for_url,
    write_json,
)
from qdrant_video_knowledge import upsert_image_post_knowledge  # noqa: E402


@dataclass
class ProviderResult:
    provider: str
    model: str
    text: str
    usage: dict[str, Any]
    cost_usd: float
    seconds: float


def wsl_to_windows(path: str | Path | None) -> str | None:
    if path is None:
        return None
    value = str(path)
    if value.startswith("/mnt/c/"):
        return "C:\\" + value[len("/mnt/c/") :].replace("/", "\\")
    return value


def load_crosscheck_settings() -> dict[str, str]:
    load_dotenv(PROJECT_DIR / ".env")
    settings = load_settings()
    return {
        "gemini_api_key": settings["api_key"],
        "gemini_model": settings["model"],
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "anthropic_model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o"),
    }


def require_cloud_keys(settings: dict[str, str]) -> None:
    missing = [
        name
        for name, value in [
            ("ANTHROPIC_API_KEY", settings["anthropic_api_key"]),
            ("OPENAI_API_KEY", settings["openai_api_key"]),
            ("GEMINI_API_KEY", settings["gemini_api_key"]),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError("Fehlende API-Keys in .env: " + ", ".join(missing))


def estimate_crosscheck_cost_eur(image_count: int, metadata_chars: int) -> float:
    units = max(1, image_count)
    text_units = max(0, metadata_chars // 6000)
    return round(0.12 + max(0, units - 5) * 0.03 + text_units * 0.02, 4)


def run_command(command: list[str], log_file: Path, timeout: int = 180) -> str:
    with log_file.open("a", encoding="utf-8") as log:
        log.write("\n=== " + " ".join(command) + " ===\n")
    completed = subprocess.run(command, cwd=PROJECT_DIR, text=True, capture_output=True, timeout=timeout)
    output = (completed.stdout or "") + (completed.stderr or "")
    with log_file.open("a", encoding="utf-8") as log:
        log.write(output)
        log.write(f"\nExit code: {completed.returncode}\n")
    if completed.returncode != 0:
        raise RuntimeError(output[-4000:])
    return output


def collect_images(directory: Path, max_images: int) -> list[Path]:
    images = [
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES and path.stat().st_size > 0
    ]
    images = sorted(images, key=lambda path: (path.parent.as_posix(), path.name))
    return images[:max_images]


def read_metadata(directory: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for path in directory.rglob("*.info.json"):
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        metadata.update({key: value for key, value in current.items() if value})
    return metadata


def metadata_text(metadata: dict[str, Any]) -> str:
    parts = []
    for key in ("title", "description", "uploader", "webpage_url", "playlist_count"):
        if metadata.get(key) is not None:
            parts.append(f"{key}: {metadata[key]}")
    return "\n\n".join(parts)


def unique_urls(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = html.unescape(value).replace("\\u0026", "&").replace("\\/", "/")
        if cleaned.startswith("http") and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def download_url(url: str, output: Path) -> bool:
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        response.raise_for_status()
        if not response.content:
            return False
        output.write_bytes(response.content)
        return True
    except Exception:
        return False


def fallback_download_from_html(url: str, output_dir: Path, max_images: int, log_file: Path) -> list[Path]:
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        response.raise_for_status()
    except Exception as exc:
        with log_file.open("a", encoding="utf-8") as log:
            log.write(f"HTML fallback failed: {exc}\n")
        return []

    text = response.text
    candidates = []
    candidates.extend(re.findall(r'<meta property="og:image" content="([^"]+)"', text))
    candidates.extend(re.findall(r'"display_url"\s*:\s*"([^"]+)"', text))
    candidates.extend(re.findall(r'"thumbnail_src"\s*:\s*"([^"]+)"', text))
    candidates = unique_urls(candidates)

    downloaded = []
    for index, image_url in enumerate(candidates[:max_images], start=1):
        ext = ".jpg"
        if ".png" in image_url.lower():
            ext = ".png"
        elif ".webp" in image_url.lower():
            ext = ".webp"
        target = output_dir / f"html-image-{index:02d}{ext}"
        if download_url(image_url, target):
            downloaded.append(target)
    return downloaded


def download_images(url: str, slug: str, max_images: int, log_file: Path) -> tuple[Path, list[Path], dict[str, Any]]:
    output_dir = PROJECT_DIR / "downloads" / "posts" / slug
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(
            f"Bild-Download-Ziel ist nicht leer: {output_dir}. "
            "Pipeline stoppt, damit keine alten Post-Dateien wiederverwendet werden."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    ytdlp = str(PROJECT_DIR / ".venv" / "bin" / "yt-dlp")
    run_command(
        [
            ytdlp,
            "--skip-download",
            "--write-thumbnail",
            "--write-all-thumbnails",
            "--write-info-json",
            "--paths",
            str(output_dir),
            "--output",
            f"{slug}.%(ext)s",
            url,
        ],
        log_file,
    )
    info_files = list(output_dir.rglob("*.info.json"))
    if not info_files:
        raise RuntimeError(f"yt-dlp hat keine info.json fuer {url} erzeugt.")
    for info_file in info_files:
        validate_info_json_for_url(info_file, url)
    metadata = read_metadata(output_dir)
    images = collect_images(output_dir, max_images)
    if not images:
        images = fallback_download_from_html(url, output_dir, max_images, log_file)
    return output_dir, images, metadata


def data_url_for(path: Path) -> str:
    mime = detect_image_mime(path)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def detect_image_mime(path: Path) -> str:
    header = path.read_bytes()[:16]
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"RIFF") and b"WEBP" in header:
        return "image/webp"
    return mimetypes.guess_type(path.name)[0] or get_mime_type(path)


def base64_image(path: Path) -> tuple[str, str]:
    mime = detect_image_mime(path)
    return mime, base64.b64encode(path.read_bytes()).decode("ascii")


def build_prompt(topic: str, question: str, metadata: str, has_images: bool) -> str:
    image_note = "Es sind Bilder angehaengt." if has_images else "Es wurden keine Bilder gefunden; analysiere nur die Metadaten und markiere diese Grenze klar."
    return f"""Du analysierst Instagram-Karussell-Bilder im Kontext \"{topic}\".
{image_note}
Bitte beantworte konkret diese Frage: \"{question}\"
Sicherheitsregel: Bei Cybersecurity, Hacking, Ueberwachung, Kennzeichen/Gesichter, Waffen, Medizin, Finanzen oder riskanten Bauanleitungen gib keine illegalen, schädlichen oder invasiven Schritt-fuer-Schritt-Anleitungen. Erklaere stattdessen defensiv, legal, konzeptionell, mit Risiken, Grenzen und sicheren Lernpfaden.

Strukturiere deine Antwort:
## Direkte Antwort auf Frage
[konkret, ohne Floskeln]

## Visuelle Inhalte
[was zu sehen ist, oder klar sagen, dass keine Bilder vorliegen]

## Text/OCR im Bild
[falls Text in den Bildern]

## Erkennbare Personen/Marken/Objekte
[Liste]

## Kategorisierung
[Themen-Tags]

## Eigene Konfidenz
[low / medium / high und warum]

Metadaten/Textkontext:
```text
{metadata[:12000]}
```
"""


def cost_from_tokens(input_tokens: int | None, output_tokens: int | None, input_rate: float, output_rate: float) -> float:
    if input_tokens is None or output_tokens is None:
        return 0.0
    return round(input_tokens / 1_000_000 * input_rate + output_tokens / 1_000_000 * output_rate, 6)


def call_anthropic(settings: dict[str, str], prompt: str, images: list[Path]) -> ProviderResult:
    started = time.perf_counter()
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image in images:
        mime, data = base64_image(image)
        content.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}})
    client = Anthropic(api_key=settings["anthropic_api_key"])
    response = client.messages.create(
        model=settings["anthropic_model"],
        max_tokens=1800,
        temperature=0.2,
        messages=[{"role": "user", "content": content}],
    )
    text = "\n".join(block.text for block in response.content if getattr(block, "type", "") == "text").strip()
    usage = {
        "input_tokens": getattr(response.usage, "input_tokens", None),
        "output_tokens": getattr(response.usage, "output_tokens", None),
    }
    cost = cost_from_tokens(usage["input_tokens"], usage["output_tokens"], 3.0, 15.0)
    return ProviderResult("claude", settings["anthropic_model"], text, usage, cost, round(time.perf_counter() - started, 3))


def call_openai(settings: dict[str, str], prompt: str, images: list[Path]) -> ProviderResult:
    started = time.perf_counter()
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image in images:
        content.append({"type": "image_url", "image_url": {"url": data_url_for(image), "detail": "high"}})
    client = OpenAI(api_key=settings["openai_api_key"])
    response = client.chat.completions.create(
        model=settings["openai_model"],
        temperature=0.2,
        max_tokens=1800,
        messages=[
            {"role": "system", "content": "Du bist ein praeziser visueller Faktenanalyst. Antworte auf Deutsch."},
            {"role": "user", "content": content},
        ],
    )
    text = response.choices[0].message.content or ""
    usage_obj = response.usage
    usage = {
        "prompt_tokens": getattr(usage_obj, "prompt_tokens", None),
        "completion_tokens": getattr(usage_obj, "completion_tokens", None),
        "total_tokens": getattr(usage_obj, "total_tokens", None),
    }
    cost = cost_from_tokens(usage["prompt_tokens"], usage["completion_tokens"], 2.5, 10.0)
    return ProviderResult("openai", settings["openai_model"], text.strip(), usage, cost, round(time.perf_counter() - started, 3))


def call_gemini(settings: dict[str, str], prompt: str, images: list[Path]) -> ProviderResult:
    started = time.perf_counter()
    client = make_client(settings["gemini_api_key"])
    cleanup_gemini_files(client, "before-image-crosscheck")
    uploaded = []
    try:
        for image in images:
            uploaded.append(client.files.upload(file=str(image)))
        contents: list[Any] = [*uploaded, prompt] if uploaded else [prompt]
        response = client.models.generate_content(
            model=settings["gemini_model"],
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=1800),
        )
    finally:
        for current in uploaded:
            try:
                client.files.delete(name=current.name)
            except Exception:
                pass
        cleanup_gemini_files(client, "after-image-crosscheck")
    text = (response.text or "").strip()
    usage = usage_to_dict(getattr(response, "usage_metadata", None))
    cost = actual_cost_from_usage(settings["gemini_model"], usage) or 0.0
    return ProviderResult("gemini", settings["gemini_model"], text, usage, cost, round(time.perf_counter() - started, 3))


def synthesize_locally(topic: str, question: str, results: list[ProviderResult]) -> str:
    provider_blocks = "\n\n".join(
        f"## {result.provider} ({result.model})\n{result.text[:8000]}" for result in results
    )
    prompt = f"""Du bist Nexis lokaler Synthese-Analyst.
Vergleiche drei KI-Analysen zu einem Instagram-Bilderpost.

Thema: {topic}
Frage: {question}

Erstelle auf Deutsch:
## Konsolidierte Antwort auf Nexis Frage
## Uebereinstimmungen mit hoher Konfidenz
## Widersprueche oder Unsicherheiten
## Was Nexi daraus praktisch mitnehmen sollte

Analysen:
{provider_blocks}
"""
    try:
        response = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "qwen3:30b", "prompt": prompt, "stream": False, "options": {"temperature": 0.2}},
            timeout=240,
        )
        response.raise_for_status()
        return (response.json().get("response") or "").strip()
    except Exception as exc:
        return "## Lokale Synthese fehlgeschlagen\n\n" + str(exc)


def render_markdown(
    *,
    topic: str,
    question: str,
    url: str | None,
    data_class: str,
    images: list[Path],
    metadata: str,
    synthesis: str,
    results: list[ProviderResult],
    total_cost: float,
    slug: str,
) -> str:
    image_lines = "\n".join(f"- `{image}`" for image in images) if images else "- Keine Bilddateien gefunden, Metadaten-Fallback genutzt."
    provider_sections = "\n\n".join(
        [
            f"## Einzelanalyse: {result.provider} ({result.model})\n\n{result.text}\n\n"
            f"Kosten: ${result.cost_usd:.6f}\n\n"
            f"Usage: `{json.dumps(result.usage, ensure_ascii=False)}`"
            for result in results
        ]
    )
    return "\n".join(
        [
            f"# Bilder-Crosscheck: {slug}",
            "",
            f"Datum: {now_stamp()}",
            f"Quelle: {url or 'lokales Bilder-Verzeichnis'}",
            f"Datenklasse: {data_class}",
            f"Thema: {topic}",
            f"Frage: {question}",
            f"Input-Modus: {'Bilder' if images else 'Metadaten-Fallback'}",
            "",
            "## Bilder",
            "",
            image_lines,
            "",
            "## Konsolidierter Bericht",
            "",
            synthesis,
            "",
            "## Cost-Tracking",
            "",
            *[f"- {result.provider} ({result.model}): ${result.cost_usd:.6f}" for result in results],
            f"- Gesamt: ${total_cost:.6f}",
            "- Lokale Synthese: 0 EUR",
            "",
            "## Metadaten",
            "",
            "```text",
            metadata[:8000],
            "```",
            "",
            provider_sections,
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Instagram image posts with Claude + OpenAI + Gemini cross-check.")
    parser.add_argument("--url")
    parser.add_argument("--image-dir", type=Path)
    parser.add_argument("--data-class", default="D2", choices=sorted(VALID_DATA_CLASSES))
    parser.add_argument("--topic", default="Instagram Post")
    parser.add_argument("--question", action="append", default=[])
    parser.add_argument("--slug", default=None)
    parser.add_argument("--max-cost-eur", type=float, default=0.50)
    parser.add_argument("--max-images", type=int, default=8)
    parser.add_argument("--allow-sensitive", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.url and not args.image_dir:
        raise RuntimeError("Erwartet --url oder --image-dir.")
    if args.data_class in {"D3", "D4"} and not args.allow_sensitive:
        raise RuntimeError("D3/D4 sind ohne --allow-sensitive gesperrt.")

    question = " ".join(args.question).strip() or "Um was geht es hier genau?"
    requested_slug = args.slug or args.topic or f"image-post-{now_stamp()}"
    if args.url:
        slug = slugify(f"{requested_slug}-{url_hash(args.url)}-{now_stamp()}")
    else:
        slug = slugify(requested_slug)
    log_dir = PROJECT_DIR / "logs" / "pipeline"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{slug}-image-crosscheck-{now_stamp()}.log"

    settings = load_crosscheck_settings()
    summary: dict[str, Any] = {
        "ok": False,
        "pipeline_type": "image-post",
        "url": args.url,
        "data_class": args.data_class,
        "topic": args.topic,
        "question": question,
        "slug": slug,
        "requested_slug": requested_slug,
        "log_file": str(log_file),
        "files": {},
        "cost": {},
    }

    try:
        if args.image_dir:
            image_dir = args.image_dir.resolve()
            images = collect_images(image_dir, args.max_images)
            metadata = {}
        else:
            image_dir, images, metadata = download_images(args.url, slug, args.max_images, log_file)

        meta_text = metadata_text(metadata)
        estimate = estimate_crosscheck_cost_eur(len(images), len(meta_text))
        summary["files"]["image_dir"] = str(image_dir)
        summary["files"]["images"] = [str(image) for image in images]
        summary["cost"]["preflight_estimate_eur"] = estimate
        if estimate > args.max_cost_eur:
            raise RuntimeError(f"Cost-Preflight {estimate:.2f} EUR > Limit {args.max_cost_eur:.2f} EUR")
        if args.dry_run:
            summary["ok"] = True
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0

        require_cloud_keys(settings)
        prompt = build_prompt(args.topic, question, meta_text, bool(images))
        results = [
            call_anthropic(settings, prompt, images),
            call_openai(settings, prompt, images),
            call_gemini(settings, prompt, images),
        ]
        total_cost = round(sum(result.cost_usd for result in results), 6)
        if total_cost > args.max_cost_eur:
            raise RuntimeError(f"Ist-Kosten {total_cost:.2f} USD > Limit {args.max_cost_eur:.2f}")

        synthesis = synthesize_locally(args.topic, question, results)
        output_dir = PROJECT_DIR / "analysis"
        output_dir.mkdir(exist_ok=True)
        stamp = now_stamp()
        output_md = output_dir / f"{slug}.image-crosscheck-{stamp}.md"
        output_json = output_dir / f"{slug}.image-crosscheck-{stamp}.json"
        output_md.write_text(
            render_markdown(
                topic=args.topic,
                question=question,
                url=args.url,
                data_class=args.data_class,
                images=images,
                metadata=meta_text,
                synthesis=synthesis,
                results=results,
                total_cost=total_cost,
                slug=slug,
            ),
            encoding="utf-8",
        )

        payload = {
            "url": args.url,
            "data_class": args.data_class,
            "topic": args.topic,
            "question": question,
            "slug": slug,
            "input_mode": "images" if images else "metadata-only",
            "image_dir": str(image_dir),
            "images": [str(image) for image in images],
            "image_sha256": {str(image): file_sha256(image) for image in images},
            "metadata": metadata,
            "providers": [result.__dict__ for result in results],
            "total_cost_usd": total_cost,
            "output_markdown": str(output_md),
        }
        write_json(output_json, payload)

        qdrant = upsert_image_post_knowledge(
            url=args.url or str(image_dir),
            topic=args.topic,
            data_class=args.data_class,
            questions=[question],
            analysis_markdown=output_md,
            image_paths=images,
            cost_usd=total_cost,
            slug=slug,
            provider_results=[result.__dict__ for result in results],
            input_mode="images" if images else "metadata-only",
        )
        payload["qdrant"] = qdrant
        write_json(output_json, payload)

        summary["ok"] = True
        summary["files"].update(
            {
                "analysis_markdown": str(output_md),
                "analysis_json": str(output_json),
                "analysis_markdown_windows": wsl_to_windows(output_md),
                "analysis_json_windows": wsl_to_windows(output_json),
                "image_dir_windows": wsl_to_windows(image_dir),
                "images_windows": [wsl_to_windows(image) for image in images],
            }
        )
        summary["cost"]["actual_total_usd"] = total_cost
        summary["cost"]["providers"] = {result.provider: result.cost_usd for result in results}
        summary["providers"] = {result.provider: result.model for result in results}
        summary["qdrant"] = qdrant
        summary["finished_at"] = now_stamp()
        summary["log_file_windows"] = wsl_to_windows(log_file)
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 0
    except Exception as exc:  # noqa: BLE001
        summary["error"] = str(exc)
        summary["finished_at"] = now_stamp()
        summary["log_file_windows"] = wsl_to_windows(log_file)
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
