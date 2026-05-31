# Status-Dashboard 022d

Stand: 2026-05-31

## Ergebnis

Das lokale Status-Dashboard ist gebaut und laeuft.

URL:

- http://127.0.0.1:8765

Dateien:

- `C:\AI\projects\09-video-analyse\scripts\status_dashboard.py`
- `C:\AI\projects\09-video-analyse\scripts\start-status-dashboard.ps1`
- `C:\Users\nexil\Desktop\KI\scripts\start-status-dashboard.ps1`
- `C:\AI\projects\09-video-analyse\dashboard\imperium-status.html`
- `C:\AI\projects\09-video-analyse\dashboard\status.json`

## Was angezeigt wird

- Service-Status fuer Ollama, Qdrant, OpenWebUI, n8n
- Docker-Status
- Qdrant-Collections und Punktzahlen
- Lokale Ollama-Modelle
- Scheduler-Status
- Telegram-Bot-Status
- Sofinello-Batch-Fortschritt
- Kostenverbrauch Sofinello
- Failed-Videos-Zaehler
- letzte Analysen
- KI-Sync-Exporte
- Backup-Logs

## Start

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nexil\Desktop\KI\scripts\start-status-dashboard.ps1"
```

## Snapshot erzeugen

```powershell
& "C:\AI\projects\09-video-analyse\.venv-win\Scripts\python.exe" -B "C:\AI\projects\09-video-analyse\scripts\status_dashboard.py" --once
```

## Test

HTTP-Test:

- `http://127.0.0.1:8765`: 200
- HTML enthaelt `Nexi Imperium Status`
- HTML enthaelt `Qdrant Wissen`
- HTML enthaelt `Sofinello Fortschritt`
- HTML enthaelt `Backup Logs`

Status-JSON-Test:

- `video_knowledge`: 66 Punkte zum Testzeitpunkt
- `open-webui_knowledge`: 122 Punkte zum Testzeitpunkt
- Sofinello: 197 / 722
- Failed Videos: 9
- Telegram-Bot: true

Hinweis:

Die Browser-Sichtpruefung ueber den In-App-Browser konnte nicht genutzt werden, weil der Browser-Connector in dieser Umgebung vor dem Laden der Seite abgebrochen ist. Die lokale HTTP-/HTML-/JSON-Pruefung ist erfolgreich.
