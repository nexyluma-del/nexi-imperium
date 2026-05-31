# IMPERIUM-NUTZUNG

Stand: 2026-05-31

Diese Datei ist die kurze Bedienungszentrale fuer Nexis lokales KI-Imperium.

## Schnellstart

Wichtige URLs:

- OpenWebUI: http://127.0.0.1:3000
- n8n: http://127.0.0.1:5678
- Qdrant API: http://127.0.0.1:6333
- Ollama API: http://127.0.0.1:11434

Wichtige Projektpfade:

- Hauptprojekt: `C:\AI\projects\09-video-analyse`
- Privates GitHub-Repo: `C:\AI\imperium-config`
- KI-Masterordner: `C:\Users\nexil\Desktop\KI`
- Aufgabenordner: `C:\Users\nexil\Desktop\KI\aufgaben`
- Instagram-Rohlisten: `C:\Users\nexil\Desktop\Instagram Liste`
- Lokale Instagram-Videos: `C:\Users\nexil\Desktop\Instagram Videos`
- Obsidian Vault: `C:\Users\nexil\Documents\Obsidian-Imperium`
- KI-Sync Exporte: `C:\Users\nexil\Desktop\KI\sync`

## Dienste pruefen

```powershell
docker ps
```

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "curl -s http://127.0.0.1:11434/api/tags"
```

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "curl -s http://127.0.0.1:6333/collections"
```

Laufende Docker-Dienste:

- `open-webui` -> OpenWebUI
- `n8n` -> Workflow-Automatisierung
- `qdrant` -> Vektor-Wissensspeicher

Docker-Volumes:

- `open-webui`
- `n8n_data`
- `qdrant_storage`

## Modelle

Lokale Ollama-Modelle:

- `qwen3:30b` -> Standard fuer Wissensfragen
- `qwen3:4b` -> schnelle Alltags-/Testfragen
- `nomic-embed-text` -> Embeddings fuer Qdrant

OpenWebUI Default-Wissensmodell:

- Modell-ID: `nexi-rag-qwen3-30b`
- Basis: `qwen3:30b`
- Knowledge-Base: `nexi-video-knowledge`

## Backup

Restic-Repository:

- `D:\Restic-Backup`

Backup starten:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nexil\Desktop\KI\scripts\run-backup.ps1"
```

Restore-Test:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nexil\Desktop\KI\scripts\run-restore-test.ps1"
```

Docker-Volume-Backup/Exports:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nexil\Desktop\KI\scripts\export-qdrant-snapshot.ps1"
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nexil\Desktop\KI\scripts\export-n8n-workflows.ps1"
```

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nexil\Desktop\KI\scripts\export-openwebui-db.ps1"
```

## Telegram-Bot

Bot starten:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nexil\Desktop\KI\scripts\start-telegram-bot.ps1"
```

Status lokal pruefen:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/telegram_status.py"
```

Testnachricht:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/telegram_send.py 'Test'"
```

Bot-Kommandos:

- `/help` -> Hilfe
- `/status` -> Systemstatus
- `/analyze <URL> [Frage]` -> Video/Post analysieren
- direkt geteilte Instagram-URL + Kommentar -> Kommentar wird als Analysefrage genutzt
- `/memory <Frage>` -> lokale Memory-KI fragen
- `/briefing [morning|midday|evening]` -> Memory-Briefing erzeugen
- `/links <Text>` -> Wissens-Verknuepfungen suchen
- `/sync` -> Master-Kontext fuer Claude/ChatGPT/Gemini exportieren
- `/sync <Thema>` -> Topic-Kontext exportieren
- `/sync-tg <Thema>` -> Topic-Kontext direkt in Telegram anzeigen

## Video-Pipeline

Rohlisten-Splitter:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/split_roh_liste.py --input '/mnt/c/Users/nexil/Desktop/Instagram Liste/videos-roh.md' --output-dir work/topics --data-class D2 --overwrite"
```

Batch fuer eine Themen-Datei:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/run_batch_pipeline.py --topic-file work/topics/DATEI.md --budget-eur 5 --allow-cloud-data-class D2"
```

Lokale Videos aus normalen Kategorien:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/process_local_folder.py --root '/mnt/c/Users/nexil/Desktop/Instagram Videos' --data-class D2 --filter 'KI Tools' --filter 'IT Hacks' --filter 'Finanzen' --max-videos 3 --one-per-category --max-cost-eur 1"
```

Sofinello-Spezialbatch, Frame-Only-Upscaling:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/process_sofinello_batch.py --root '/mnt/c/Users/nexil/Desktop/Instagram Videos/Sofinello' --max-cost-eur 60 --upscale-scale 2 --progress-every 10"
```

Sofinello-Resume-Guard manuell:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/resume_sofinello_batch_b.py --dry-run"
```

## OpenWebUI + Qdrant

Qdrant-Spiegel fuer OpenWebUI aktualisieren:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/sync_openwebui_qdrant.py"
```

OpenWebUI Default-RAG erneut setzen:

```powershell
docker cp C:\AI\projects\09-video-analyse\scripts\configure_openwebui_default_rag.py open-webui:/tmp/configure_openwebui_default_rag.py
docker exec open-webui python /tmp/configure_openwebui_default_rag.py
docker restart open-webui
```

RAG-Test:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/test_openwebui_default_rag.py"
```

## Memory-KI

Lokale Memory-KI fragen:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/memory_query.py 'Was ist heute wichtig fuer mein KI-Imperium?'"
```

Schneller Test mit kleinem Modell:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/memory_query.py --fast 'Was ist der naechste Schritt?'"
```

Briefing erzeugen:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/memory_briefing.py --kind morning"
```

KI-PUSH Wochen-Scan:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/memory_ki_push_scan.py"
```

## KI-Sync-Bridge

Master-Kontext exportieren:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/export_master_context.py --archive-old"
```

Topic-Kontext exportieren:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/export_topic_context.py --topic 'Sofinello'"
```

## Voice-Capture

Einmal-Test:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\AI\projects\09-video-analyse\scripts\start-voice-capture-once-test.ps1"
```

Hotkey-Modus:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\AI\projects\09-video-analyse\scripts\start-voice-capture.ps1"
```

Import-Ordner verarbeiten:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/voice_capture.py --process-import-dir"
```

## Scheduler

Aktive Nexi-Aufgaben:

- `Nexi Memory-KI Morgenbriefing`
- `Nexi Memory-KI Mittagscheck`
- `Nexi Memory-KI Tagesabschluss`
- `Nexi Memory-KI KI-PUSH Wochen-Scan`
- `Nexi KI-Sync Master-Context Wochenexport`
- `Nexi Voice Memory Daily Review`
- `Nexi Voice Memory Weekly Review`
- `Nexi Sofinello Batch B Resume`

Scheduler pruefen:

```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -like 'Nexi*' } | Select-Object TaskName,State | Sort-Object TaskName
```

## GitHub

Repo:

```powershell
cd C:\AI\imperium-config
git status
git add .
git commit -m "Kurzbeschreibung"
git push
```

## Geheimnisse

`.env` liegt hier:

- `C:\AI\projects\09-video-analyse\.env`

Gespeicherte Schluessel-Namen:

- `GEMINI_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Keys nie in Chat, Doku oder GitHub schreiben.

## Fehlerlisten und Reports

- Zentrale Fehlerliste: `C:\AI\projects\09-video-analyse\failed-videos.md`
- Kopie fuer Uebergaben: `C:\Users\nexil\Desktop\KI\aufgaben\failed-videos.md`
- Projektanalysen: `C:\AI\projects\09-video-analyse\analysis`
- Logs: `C:\AI\projects\09-video-analyse\logs`
- Backup-Logs: `C:\Users\nexil\Desktop\KI\logs\backup`

## Grundregeln

- D0/D1: lokal oder Cloud unkritisch.
- D2: Cloud erlaubt, wenn es oeffentliche Inhalte sind und Nexi es freigibt.
- D3/D4: keine Cloud ohne explizite Freigabe.
- Sofinello: immer Compliance-Agent, keine Heilversprechen, keine Diagnosen.
- Grosse Batches: vorher Kostenlimit setzen.
- Vor Loeschungen: manuell bestaetigen lassen.
