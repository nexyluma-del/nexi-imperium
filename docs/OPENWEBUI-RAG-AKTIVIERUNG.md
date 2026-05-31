# OpenWebUI RAG Aktivierung

Stand: 2026-05-31

## Ergebnis

OpenWebUI nutzt jetzt fuer neue Chats standardmaessig ein eigenes Wissensmodell:

- Modell-ID: `nexi-rag-qwen3-30b`
- Basis-Modell: `qwen3:30b`
- Anzeigename: `Nexi Wissen (qwen3:30b + Quellen)`
- Knowledge-Base: `nexi-video-knowledge`
- Qdrant-Collection: `open-webui_knowledge`
- Default in OpenWebUI: `ui.default_models = nexi-rag-qwen3-30b`
- Gepinntes Default-Modell: `ui.default_pinned_models = nexi-rag-qwen3-30b`

Damit muss die Knowledge-Base bei neuen Chats nicht mehr manuell aktiviert werden.

## Thinking-Modus

Das Modell ist mit `reasoning_tags = ["<think>", "</think>"]` konfiguriert. OpenWebUI kann Thinking dadurch als separaten Reasoning-Block behandeln, statt ihn im normalen Hauptchattext zu vermischen.

Zusaetzlich weist der System-Prompt das Modell an, keinen sichtbaren Denkprozess in die normale Antwort zu schreiben.

## Backup

Vor der Datenbank-Aenderung wurde die OpenWebUI-Datenbank im Container gesichert:

`/app/backend/data/webui.db.codex-20260531-112416.bak`

## Test

Der Pflicht-Test wurde mit drei Wissensfragen ausgefuehrt:

- Test-Skript: `C:\AI\projects\09-video-analyse\scripts\test_openwebui_default_rag.py`
- JSON-Report: `C:\AI\projects\09-video-analyse\analysis\openwebui-rag\openwebui-rag-test-20260531-022a.json`
- Markdown-Report: `C:\AI\projects\09-video-analyse\analysis\openwebui-rag\openwebui-rag-test-20260531-022a.md`

Status: gruen. Alle drei Antworten wurden mit `qwen3:30b` erzeugt und enthalten Quellenmarker wie `[1]`, `[2]`.

## Reproduzierbare Skripte

- `scripts/configure_openwebui_default_rag.py`
- `scripts/test_openwebui_default_rag.py`
- `scripts/sync_openwebui_qdrant.py`
