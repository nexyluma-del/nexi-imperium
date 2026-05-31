# Sofinello Batch B - Zwischenstopp

Stand: 2026-05-31 06:35 Europe/Berlin

## Ergebnis bis zum Stopp

- Modus: Frame-Only-Upscaling fuer alle Sofinello-Videos.
- Erfolgreich verarbeitet: 197 von 722 Videos.
- Noch nicht erfolgreich abgeschlossen: 525 Videos.
- Fehler im Status: 9, alle durch Gemini-Tageslimit/Quota, keine inhaltlichen Video-Fehler.
- Kosten bisher: 3.735829 USD.
- Qdrant: `sofinello_knowledge` enthaelt 200 Punkte (3 Tests + 197 Batch-Erfolge).
- Letzter erfolgreicher Clip: `/mnt/c/Users/nexil/Desktop/Instagram Videos/Sofinello/2) Bilder Allgemein/Pixabay/Himmel/158384-816637349_tiny.mp4`

## Warum gestoppt wurde

Gemini meldete:

`429 RESOURCE_EXHAUSTED - generate_requests_per_model_per_day, limit: 250, model: gemini-3.1-pro`

Der Retry-Hinweis lag bei ca. 20 Stunden. Der praktische Reset-Zeitpunkt ist voraussichtlich um 2026-06-01 gegen 02:00 Europe/Berlin.

Ich habe den Batch gestoppt, damit nicht hunderte weitere Videos faelschlich als fehlgeschlagen markiert werden. n8n, Ollama, Qdrant, OpenWebUI und Telegram wurden nicht gestoppt.

## Technische Korrektur

`scripts/process_sofinello_batch.py` wurde angepasst:

- Bei Gemini-Quota-Fehlern pausiert der Batch jetzt automatisch.
- Quota-Fehler werden nicht mehr als echte Video-Fehler weitergeschrieben.
- Wenn ein zuvor fehlerhaft markierter Pfad spaeter erfolgreich verarbeitet wird, wird der alte Fehler aus der Statusdatei entfernt.

Syntax-Check:

`python -m py_compile scripts/process_sofinello_batch.py` erfolgreich.

## Dateien

- Statusdatei: `C:\AI\projects\09-video-analyse\logs\sofinello\sofinello-batch-b-status.json`
- Fehlerliste: `C:\AI\projects\09-video-analyse\failed-videos.md`
- Analyse-Outputs: `C:\AI\projects\09-video-analyse\analysis\sofinello\final`

## Fortsetzung

Nach Quota-Reset kann der Batch mit derselben Statusdatei fortgesetzt werden. Bereits erfolgreiche Videos werden automatisch uebersprungen.

Empfohlener Resume-Befehl:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && nohup .venv/bin/python scripts/process_sofinello_batch.py --max-cost-eur 50 --per-video-estimate-eur 0.06 --per-video-cost-cap-eur 0.25 --max-frames 6 --frame-long-side 1280 --progress-every 25 --status-file logs/sofinello/sofinello-batch-b-status.json > logs/sofinello/sofinello-batch-b-resume.out 2>&1 &"
```

Wichtig: Aufgabe 018 wurde noch nicht gestartet, weil das hier ein vereinbarter Stop-Fall war.
