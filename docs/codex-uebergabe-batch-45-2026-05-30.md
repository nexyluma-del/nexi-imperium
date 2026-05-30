# Codex Uebergabe Batch videos-roh.md

Stand: 2026-05-30

## Ergebnis

Die Rohdatei `C:\Users\nexil\Desktop\Instagram Liste\videos-roh.md` wurde gesplittet und als D2-Batch verarbeitet.

Hinweis: Der Splitter hat 45 Eintraege gefunden, nicht 44.

## Gesamtstatistik

- Gesamt: 45
- Reels: 37
- Posts: 8
- Erfolgreich analysiert: 44
- Fehlgeschlagen: 1
- Erfolgreiche Reels: 36
- Erfolgreiche Posts: 8
- Qdrant-Eintraege bei erfolgreichen Analysen: 44 / 44
- Gesamtkosten: `1.014237 USD`, also ca. 1,01 EUR konservativ gerechnet
- Budget: 5,00 EUR

## Themenstatistik

| Thema | Gesamt | Erfolgreich | Fehler | Posts | Reels | Kosten USD |
|---|---:|---:|---:|---:|---:|---:|
| IT | 3 | 3 | 0 | 1 | 2 | 0.072490 |
| KI-IT | 5 | 5 | 0 | 0 | 5 | 0.088608 |
| KI-AVATARE | 1 | 1 | 0 | 0 | 1 | 0.017102 |
| NEUHEITEN-PRODUKTE | 7 | 7 | 0 | 1 | 6 | 0.144070 |
| IT-HACKING-SICHERHEIT | 14 | 14 | 0 | 2 | 12 | 0.309043 |
| IT-NEWS | 15 | 14 | 1 | 4 | 11 | 0.382924 |

## Fehlgeschlagene URL

Thema: `IT-NEWS`, Eintrag 6

URL:

`https://www.instagram.com/reel/DUvpXtWCACW/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA==`

Grund:

yt-dlp meldet, dass der Inhalt nicht verfuegbar ist, rate-limited ist oder Login/Cookies benoetigt. Da kein Instagram-Login erlaubt war, wurde der Eintrag korrekt nicht weiter verarbeitet.

## Reparaturen / Haertungen waehrend des Batchs

- Tags aus der Rohdatei bleiben jetzt in den Themen-Dateien erhalten.
- Tags werden als Kontext an die Analyse uebergeben.
- Sicherheitsregel fuer Cybersecurity/Hacking/Ueberwachung: legal, defensiv, konzeptionell, keine schaedlichen Schritt-fuer-Schritt-Anleitungen.
- Bild-MIME-Erkennung korrigiert, falls Instagram ein JPEG mit `.webp`-Dateiname liefert.
- Video-Fallback fuer Reels ohne extrahierbare Audiospur: visuelle Analyse mit Hinweis statt Komplettfehler.
- Qdrant/Ollama-Embedding robuster gemacht: kuerzerer Text und Fallback auf `/api/embed`.
- Ein grosses Video mit 36.72 MB wurde nach Dry-Run-Kostencheck (`0.055341 USD`) mit `approve-large` verarbeitet; echte Kosten `0.028234 USD`.

## Wichtige Pfade

- Themen-Dateien: `C:\Users\nexil\Desktop\Instagram Liste\`
- Analysen: `C:\AI\projects\09-video-analyse\analysis\`
- Downloads: `C:\AI\projects\09-video-analyse\downloads\`
- Qdrant Collection: `video_knowledge`

## Naechster sinnvoller Schritt

Aufgabe 014 Telegram-Bot: Push-Meldung bei fertigem Batch, Kostenbericht, Fehlerliste und Status-Befehle vom Handy.
