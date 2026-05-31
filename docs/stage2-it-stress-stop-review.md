# Stufe 2 IT-Stress-Test - Safety-Stop Review

Stand: 2026-06-01 00:20 Europe/Berlin

## Ergebnis

- Run-ID: `run-002-it-stress-200`
- Vorstart-Restic-Snapshot: `3ec4e511`
- Status: `failed` / kontrollierter Safety-Stop
- Geplant: 200 IT-Block-Videos
- Geprueft bis Stop: 134
- Erfolgreich verarbeitet: 118
- Duplikate per SHA256/Reference gespart: 15
- Fehler/Safety-Stop: 1
- Klassifizierer: 134/134 korrekt = 100.0 %
- Kosten bis Stop: 1.251019 USD
- Stage 3 / 3000er-Lauf: nicht gestartet

## Stop-Ursache

Der Anti-NASA-Waechter hat bei Video 134 gestoppt:

- Source: `C:\Users\nexil\Desktop\Instagram Videos\KI Tools\SnapInsta.to_AQMENBE3XIO7LXR50GOsYcaGbF8hVcj5DgDgZb-OTFDOCCIViaWRr1_HTRO2IQnQFNHxiZu8er0Thk9h5smhWwhxka8P56z2D666cNA.mp4`
- Kategorie: `03-KI-IT`
- Analyse: `C:\AI\projects\09-video-analyse\videos\03-KI-IT\SnapInsta.to_AQMENBE3XIO7LXR50GOsYcaGbF8hVcj5DgDgZb-OTF-fc19ece1494b\Gemini-Analyse.md`
- Treffer: `NASA`

## Erste Diagnose

Das wirkt aktuell nicht wie ein Rueckfall des alten NASA-LADEE-Testvideos. Das Whisper-Transkript und die Gemini-Zusammenfassung passen zum lokalen KI-Tools-Video ueber Grok-1/xAI. Der Treffer kommt aus der visuellen Beschreibung: Gemini beschreibt bei 0:02-0:06 einen animierten Sprecher mit `NASA-Jacke`.

Damit hat der Waechter technisch korrekt gestoppt, aber sehr wahrscheinlich auf einen legitimen Bildinhalt bzw. ein False Positive reagiert. Es gab keinen Treffer auf `LADEE`, `LLCD`, `nasa.gov` oder die typischen alten Testvideo-Begriffe.

## Qdrant-Audit

Nach dem Stop wurde `audit_corrupt_nasa_entries.py` ausgefuehrt.

- `video_knowledge`: 177 Eintraege
- Treffer gesamt: 1
- Verdacht: 1
- Qdrant-ID: `6a2112bb-00b5-e1a5-4186-a64b85705603`
- Slug: `run-002-it-stress-200-134-fc19ece1494b-20260601000912-9495fe5e248f-2026-06-01_000912`

Der Eintrag wurde nicht geloescht, weil das eine echte Datenloeschung waere und Nexi erst entscheiden soll.

## Empfehlung vor Wiederaufnahme

Vor einem Resume von Stufe 2 sollte der Anti-NASA-Waechter in zwei Stufen getrennt werden:

1. Harte Cross-Contamination-Treffer: `LADEE`, `LLCD`, `LLGT`, `Lunar Laser`, `Lasercomm`, `nasa.gov`, `White Sands`, `Minotaur` -> sofortiger Stop.
2. Weicher Einzelbegriff `NASA` -> Kontextpruefung. Nur Stop, wenn der Kontext nach altem Testvideo riecht oder mehrere NASA-Testbegriffe zusammen auftreten. Einzelne legitime Begriffe wie `NASA-Jacke` sollen als Review-Hinweis gelten.

Danach sollte Nexi entscheiden:

- A: verdaechtigen Qdrant-Eintrag loeschen und Video 134 nach Watchdog-Fix erneut laufen lassen.
- B: Qdrant-Eintrag behalten, Watchdog-Fix einbauen, Stufe 2 ab Video 135 fortsetzen.
- C: alles ab Video 134 loeschen und Stufe 2 neu starten.
