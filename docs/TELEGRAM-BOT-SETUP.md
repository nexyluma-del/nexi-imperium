# Telegram Bot Setup

Stand: 2026-05-30

## Zweck

Der Telegram-Bot ist die Handy-Schicht fuer die Video-Pipeline.

Er kann:

- Status der lokalen KI-Dienste melden.
- Instagram-/Video-URLs aus Telegram entgegennehmen.
- Geteilte Links automatisch als Batch an die bestehende Pipeline uebergeben.
- Analyse-Ergebnisse per Telegram zurueckmelden.
- Fehlgeschlagene URLs in `failed-videos.md` eintragen.

## Dateien

- `scripts/telegram_common.py` - sichere Telegram-Hilfsfunktionen, `.env` lesen/schreiben.
- `scripts/telegram_send.py` - einfache Testnachricht senden und Chat-ID erkennen.
- `scripts/telegram_status.py` - Status von Ollama, Qdrant, OpenWebUI, n8n und Qdrant-Zaehlern.
- `scripts/telegram_bot.py` - Long-Polling-Bot mit Share-Modus.
- `scripts/start-telegram-bot.ps1` - Bot unter Windows/WSL im Hintergrund starten.
- `scripts/failed_videos.py` - zentrale Fehlerliste fuer Batches.
- `failed-videos.md` - laufende Fehlerliste.

## Befehle

Bot starten:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nexil\Desktop\KI\scripts\start-telegram-bot.ps1"
```

Status lokal pruefen:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/telegram_status.py"
```

Testnachricht senden:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/telegram_send.py 'Test'"
```

## Bot-Kommandos

- `/help` - zeigt Hilfe.
- `/status` - zeigt Dienste, Qdrant-Zaehler, letzte Analysen und Fehleranzahl.
- `/analyze <URL> <Frage>` - startet Analyse fuer eine URL.
- Direkt geteilte URL - startet Share-Modus mit Standardfrage.
- URL plus Text - nutzt den Text als Frage.
- Reiner Text ohne URL - wird als lokale Notiz unter `notes/telegram` gespeichert.

## Schutzlogik

- Standard-Datenklasse: `D2`.
- Telegram-Batch-Cap: 5 EUR.
- Schaetzung: 0.08 EUR pro URL, bevor der Bot startet.
- Keine Tokens oder Chat-IDs werden in Dokus ausgegeben.
- Unautorisierte Chats werden ignoriert.

## Teststand

- Telegram-Token in `.env` gespeichert.
- Telegram-Chat-ID automatisch erkannt und in `.env` gespeichert.
- Testnachricht erfolgreich gesendet.
- `/help` und `/status` ueber Bot-Code erfolgreich getestet.
- `/analyze` mit NASA-Testvideo erfolgreich getestet.
- NASA-Testkosten: ca. 0.019895 USD.
- `video_knowledge` danach: 55 Punkte.
- `failed-videos.md`: 0 echte Fehler.
