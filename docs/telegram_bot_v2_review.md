# Telegram Bot v2 - Self Review

Status: vorbereitet, nicht aktiv. Laufender Bot nutzt weiter `telegram_bot.py`.

## Aenderungen

- Neue parallele Datei: `scripts/telegram_bot_v2.py`
- Share-/Analyse-Ergebnis sendet pro Video nur noch:
  - Video-ID und Kategorie
  - Per-Video-Ordner
  - Dashboard-Link
- Keine Vollanalyse in Telegram.
- Keine Whisper-Transkripte in Telegram.
- `/status` ist kompakt: Run, Prozess, Fortschritt, Cost, ETA, Services, letzte 3 Kategorien.
- `/last <n>` zeigt letzte verarbeitete Videos mit Ordner-Link.
- Alarm-Pushes bleiben unberuehrt, weil sie ausserhalb dieser Ausgabe-Logik laufen.

## Edge-Case Review

- `/last 1000`: wird auf maximal 20 Eintraege gekappt, Telegram bleibt lesbar.
- `/last abc`: faellt auf 5 Eintraege zurueck.
- Sonderzeichen/lange Folder-Namen: Pfade werden einzeilig normalisiert und auf 220 Zeichen gekuerzt.
- WSL-Pfade: `/mnt/c/...` wird fuer Telegram als `C:\...` angezeigt.
- Fehlende Run-Datei: `/status` und `/last` fallen ohne Crash auf "unbekannt" bzw. "keine Videos" zurueck.
- Stufe-2-Prozess nicht aktiv: ETA wird als `gestoppt/pausiert` angezeigt, keine falsche Laufzeit-Prognose.
- Telegram-Nachrichtenlaenge: `/last` wird auf ca. 3900 Zeichen begrenzt.
- Dashboard-Link: kommt aus `DASHBOARD_LINK` in `.env`, Fallback ist `http://127.0.0.1:8765`.

## Nicht gemacht

- Kein Bot-Restart.
- Keine Aenderung an `scripts/telegram_bot.py`.
- Keine Aenderung an Pipeline-Code, Restic oder Stage-2-Runner.
