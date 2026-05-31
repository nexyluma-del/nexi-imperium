# Memory-KI Setup

Stand: 2026-05-31

## Zweck

Die Memory-KI ist Nexis lokales zweites Gehirn. Sie liest lokale Qdrant-Collections, nutzt lokale Ollama-Modelle und spricht ueber Telegram.

Keine Cloud-API wird fuer Memory-Fragen, Briefings oder Linkchecks genutzt.

## Quellen

- `video_knowledge`
- `sofinello_knowledge`
- `memory_voice`

Die Basis-DNA liegt unter:

`C:\Users\nexil\Desktop\KI\v3\chiefs\01-MEMORY-COFOUNDER-FINAL.md`

## Telegram-Befehle

- `/memory <Frage>` fragt die lokale Memory-KI mit Qdrant-Kontext.
- `/briefing` erzeugt ein manuelles Memory-Briefing.
- `/briefing morning`, `/briefing midday`, `/briefing evening` erzwingen ein bestimmtes Briefing-Format.
- `/links <Text>` sucht semantische Verknuepfungen in den lokalen Wissens-Collections.
- Instagram-Link plus Kommentar nutzt den Kommentar als Gemini-Frage-Kontext, z.B. `https://... interessant wegen Heilung`.

## Automatische Briefings

Windows-Aufgabenplanung:

- 07:00 `Nexi Memory-KI Morgenbriefing`
- 13:00 `Nexi Memory-KI Mittagscheck`
- 19:00 `Nexi Memory-KI Tagesabschluss`
- Sonntag 17:00 `Nexi Memory-KI KI-PUSH Wochen-Scan`

Alle Jobs starten WSL:

`wsl.exe -d Ubuntu-24.04 -- bash -lc "cd '/mnt/c/AI/projects/09-video-analyse' && .venv/bin/python ..."`

## Skripte

- `scripts/memory_common.py`: Qdrant/Ollama/DNA-Helfer.
- `scripts/memory_query.py`: lokale Memory-Frage mit Quellen.
- `scripts/memory_briefing.py`: Tagesbriefings und Snapshot.
- `scripts/memory_link_detector.py`: Verknuepfungen finden.
- `scripts/memory_ki_push_scan.py`: `Desktop\KI\KI-PUSH` scannen.
- `scripts/register-memory-ki-tasks.ps1`: Scheduler registrieren.
- `scripts/telegram_bot.py`: Telegram-Befehle und Share-Modus.

## Qualitaetslogik

- qwen3:4b wird fuer schnelle Antworten genutzt.
- Wenn eine Memory-Antwort zu kurz, abgeschnitten oder nach Denktext aussieht, faellt `memory_query.py` automatisch auf qwen3:30b zurueck.
- Briefings haben eine deterministische Fallback-Antwort, falls qwen3 kein sauberes Kurzbriefing liefert.
- Thinking-/Reasoning-Text wird aus Modellantworten entfernt.

## Manuelle Tests

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/memory_query.py --query 'Was weiss mein lokales Wissen ueber Sofinello und Compliance?' --fast --limit 1"
```

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/memory_briefing.py --kind manual --send-telegram"
```

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/memory_link_detector.py --text 'interessant wegen Heilung und Sebi Verpackungsdetails'"
```

## Sicherheit

- Keine externen Mails, Posts, Kaeufe oder Account-Aktionen.
- Keine Cloud-Verarbeitung fuer D3/D4 ohne Freigabe.
- Telegram ist Push-/Abfragekanal, aber die Wissensarbeit bleibt lokal.
