# Voice-Capture Setup

Stand: 2026-05-31

## Kurzfassung

Voice-Capture ist der lokale Input-Kanal fuer Nexis Gedanken.

- Hotkey: `Strg+Shift+Space`
- Start: erster Hotkey-Druck startet Aufnahme
- Stopp: zweiter Hotkey-Druck stoppt Aufnahme und verarbeitet sie lokal
- Audio: bleibt lokal auf dem Laptop
- Whisper: lokal via WSL/faster-whisper
- Auto-Tags: lokal via Ollama `qwen3:4b`
- Wissensspeicher: Qdrant Collection `memory_voice`
- Notizen: `C:\Users\nexil\Documents\Obsidian-Imperium\inbox\`

## Starten

PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\AI\projects\09-video-analyse\scripts\start-voice-capture.ps1"
```

Dann:

1. `Strg+Shift+Space` druecken.
2. Sprechen.
3. Wieder `Strg+Shift+Space` druecken.
4. Die Notiz landet automatisch in Obsidian und Qdrant.

## Testaufnahme

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\AI\projects\09-video-analyse\scripts\start-voice-capture-once-test.ps1" -Seconds 6
```

## Wo Dateien landen

- Roh-Audio: `C:\AI\projects\09-video-analyse\audio\voice-capture\`
- Whisper-Transkripte: `C:\AI\projects\09-video-analyse\transcripts\voice\`
- Obsidian-Inbox: `C:\Users\nexil\Documents\Obsidian-Imperium\inbox\`
- Wichtige Notizen: `C:\Users\nexil\Desktop\KI\WICHTIGE-NOTIZEN.md`

## Wichtigkeit und Push

Wenn eine Notiz Wichtigkeit `7/10` oder hoeher bekommt:

- Ein Eintrag wird in `WICHTIGE-NOTIZEN.md` geschrieben.
- Wenn Telegram korrekt konfiguriert ist, wird ein Push an Nexi gesendet.

## Scheduled Reviews

Registrierte Windows Tasks:

- `Nexi Voice Memory Daily Review`: taeglich 19:00
- `Nexi Voice Memory Weekly Review`: sonntags 18:00

Die Tasks senden Telegram-Erinnerungen, damit Nexi wichtige Gedanken festhaelt.

## Mobile-Sync Vorbereitung

Vorbereiteter Import-Ordner:

`C:\AI\projects\09-video-analyse\audio\voice-import\`

Spaeter kann iPhone/Syncthing oder eine andere lokale Sync-Loesung Audiodateien dort ablegen.
Verarbeitung:

```powershell
& "C:\AI\projects\09-video-analyse\.venv-win\Scripts\python.exe" "C:\AI\projects\09-video-analyse\scripts\voice_capture.py" --process-import-dir
```

Wichtig: Keine Roh-Audios in unverschluesselte Cloud-Syncs legen.

## Sicherheit

- Keine Cloud-Transkription.
- Keine Daueraufnahme.
- Keine Tracking-Tools.
- Standard-Datenklasse: `D3` lokal.
- Cloud-APIs werden fuer Voice-Capture nicht verwendet.
