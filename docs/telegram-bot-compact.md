# Telegram-Bot Entschlackung

Status: umgesetzt

Vorher:

```text
Telegram-Analyse fertig
- verarbeitet: 1
- Fehler: 0
- Kosten: $0.0199

Quelle: https://www.instagram.com/...

<Analyse-Auszug im Chat>

Datei: C:\AI\projects\09-video-analyse\videos\...\gemini-analyse.md
Qdrant: ...
```

Nachher:

```text
Telegram-Analyse fertig
- verarbeitet: 1
- Fehler: 0
- Kosten: $0.0199

✓ Video 1 (Kategorie TELEGRAM-SHARE) verarbeitet
Quelle: https://www.instagram.com/...
Ordner: C:\AI\projects\09-video-analyse\videos\TELEGRAM-SHARE\...
Dashboard: http://127.0.0.1:8765
Qdrant: ...
```

Regel: Telegram zeigt nur Status. Volltexte, Markdown, Transkript und Word-Bericht bleiben im Per-Video-Ordner.

`/status` bleibt aktiv und liefert die Pipeline-Uebersicht.
