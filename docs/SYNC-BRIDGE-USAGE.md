# KI-Sync-Bridge Usage

Stand: 2026-05-31

## Zweck

Die KI-Sync-Bridge erzeugt Copy/Paste-Kontextpakete fuer Claude, ChatGPT, Gemini oder neue Codex-Sessions.

Wichtig: Die Bridge pusht nichts automatisch zu externen KIs. Nexi entscheidet selbst, welche Datei er wo einfuegt.

## Speicherort

Alle Exporte landen hier:

`C:\Users\nexil\Desktop\KI\sync\`

Alte Markdown-Exporte aelter als 30 Tage werden bei Master-Exporten nach:

`C:\Users\nexil\Desktop\KI\sync\archive\`

verschoben.

## Telegram-Befehle

- `/sync` erstellt ein frisches Master-Context-Paket und sendet die Markdown-Datei in Telegram.
- `/sync <Thema>` erstellt einen Topic-Context als Markdown-Datei und sendet die Datei in Telegram.
- `/sync-tg <Thema>` erstellt einen Topic-Context und zeigt die kompakte Version direkt im Telegram-Chat.

Beispiele:

```text
/sync
/sync Sofinello Compliance
/sync-tg KI Filme Hollywood Qualitaet
```

## PowerShell/WSL direkt

Master-Context:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/export_master_context.py --archive-old"
```

Topic-Context:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/export_topic_context.py --topic 'Sofinello Compliance' --limit 20"
```

## Empfohlener Ablauf fuer externe KI

1. Neues Gespraech in Claude, ChatGPT oder Gemini starten.
2. Erst den neuesten `master-context-*.md` einfuegen.
3. Danach bei Spezialfragen einen passenden `topic-*.md` einfuegen.
4. Der externen KI sagen: "Arbeite nur mit diesem Kontext. Wenn dir Belege fehlen, sag es."

## Datenklassen

- Standard: nur D0-D2 aus Qdrant-Topic-Snippets.
- D3 kann nur per CLI-Flag `--include-private` aufgenommen werden.
- D4 wird in dieser Version nie unverschluesselt exportiert.
- Master-Context enthaelt Strategie-/Prompt-Dokumente aus `Desktop\KI\v3`; Nexi entscheidet selbst, ob er diese extern nutzt.

## Automatik

Windows-Aufgabenplanung:

- `Nexi KI-Sync Master-Context Wochenexport`
- Zeit: Sonntag 18:00
- Aktion: Master-Context erstellen und alte Exporte archivieren.

## Dateien

- `scripts/export_master_context.py`
- `scripts/export_topic_context.py`
- `scripts/register-sync-bridge-tasks.ps1`
- `scripts/telegram_bot.py`
