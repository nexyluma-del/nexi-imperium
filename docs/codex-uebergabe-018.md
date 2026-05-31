# Aufgabe 018 - Voice-Capture Uebergabe

Stand: 2026-05-31 10:00 Europe/Berlin

## Ergebnis

Aufgabe 018 ist lokal umgesetzt.

- Laptop-Hotkey-System gebaut: `Strg+Shift+Space`
- Lokale Windows-Python-Umgebung: `C:\AI\projects\09-video-analyse\.venv-win\`
- Aufnahme via Windows-Mikrofon funktioniert.
- Whisper-Transkription laeuft lokal ueber WSL/faster-whisper.
- Obsidian-Ausgabe funktioniert: `C:\Users\nexil\Documents\Obsidian-Imperium\inbox\`
- Auto-Tagging laeuft lokal ueber Ollama `qwen3:4b`.
- Qdrant Collection `memory_voice` wurde angelegt und getestet.
- Wichtige Notizen werden ab Score 7 in `Desktop\KI\WICHTIGE-NOTIZEN.md` abgelegt.
- Telegram-Push fuer wichtige Notizen ist vorbereitet.
- Scheduled Reviews sind registriert:
  - taeglich 19:00
  - sonntags 18:00

## Neue/geaenderte Dateien

- `C:\AI\projects\09-video-analyse\scripts\voice_capture.py`
- `C:\AI\projects\09-video-analyse\scripts\voice_review_reminder.py`
- `C:\AI\projects\09-video-analyse\scripts\install-voice-capture-deps.ps1`
- `C:\AI\projects\09-video-analyse\scripts\start-voice-capture.ps1`
- `C:\AI\projects\09-video-analyse\scripts\start-voice-capture-once-test.ps1`
- `C:\AI\projects\09-video-analyse\scripts\register-voice-review-tasks.ps1`
- `C:\AI\projects\09-video-analyse\scripts\qdrant_video_knowledge.py`
- `C:\AI\projects\09-video-analyse\.gitignore`
- `C:\Users\nexil\Desktop\KI\VOICE-CAPTURE-SETUP.md`

## Tests

- Mikrofonliste erfolgreich gelesen.
- Kurze lokale Aufnahme erfolgreich erstellt.
- Whisper lokal erfolgreich ausgefuehrt.
- Obsidian-Markdown erfolgreich geschrieben.
- Qdrant `memory_voice` erfolgreich upsert-getestet.
- qwen3:4b Auto-Tagging erfolgreich getestet.
- Hotkey-Listener-Startup erfolgreich getestet.
- Scheduled Tasks registriert und Status `Ready`.

Die erzeugten Testnotizen, Testaudiodatei und Qdrant-Testpunkte wurden wieder entfernt, damit `memory_voice` sauber mit echten Nexi-Notizen startet.

## Bedienung

Start:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\AI\projects\09-video-analyse\scripts\start-voice-capture.ps1"
```

Dann `Strg+Shift+Space` zum Starten/Stoppen der Aufnahme.

## Grenzen

- Der echte Hotkey-Toggle wurde technisch gestartet, aber nicht mit einer menschlichen Live-Sprachnotiz gedrueckt, weil Codex nicht selbst deine Tastenkombination ausloesen soll.
- Mobile-Sync ist vorbereitet, aber Syncthing/iPhone-Sync ist noch nicht installiert.
- Voice-Audio bleibt lokal; keine Cloud-API wird fuer Transkription oder Tagging genutzt.

## Sofinello-Batch Hintergrund

Beim letzten Check war der Sofinello-Batch nicht aktiv und stand weiter bei `197/722`, weil Gemini das Tageslimit erreicht hatte. Keine weiteren Aktionen an diesem Batch waehrend 018.
