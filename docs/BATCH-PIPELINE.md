# Batch-Pipeline fuer Rohlisten, Themen und Qdrant

Stand: 2026-05-29

## Ziel

Eine einzige Roh-Liste enthaelt Themen, URLs und konkrete Fragen pro Video. Der Splitter erzeugt daraus Themen-Dateien. Der Batch-Workflow verarbeitet jede noch offene URL mit yt-dlp, Whisper, Gemini und schreibt das Ergebnis als Markdown. Danach landet der Wissensanker in Qdrant in der Collection `video_knowledge`.

## Rohlisten-Format

Standard-Ort:

`C:\Users\nexil\Desktop\Instagram Liste\videos-roh.md`

Beispiel:

```md
[Heilfrequenzen Grundlagen]
https://example.com/video-1
Fragen:
- Was ist die Kernaussage?
- Welche Behauptungen muss ich spaeter pruefen?
- Welche Zitate oder Begriffe sind wichtig?

[KI Business Ideen]
https://example.com/video-2
Was ich wissen will:
- Welche konkreten Geschaeftsideen nennt das Video?
- Welche Schritte kann ich daraus ableiten?
```

Regel: Thema in eckigen Klammern, darunter URL, darunter Fragen als Bulletpoints.

## Splitter

Script:

`C:\AI\projects\09-video-analyse\scripts\split_roh_liste.py`

Beispiel in WSL:

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/split_roh_liste.py \
  --input "/mnt/c/Users/nexil/Desktop/Instagram Liste/videos-roh.md" \
  --output-dir "/mnt/c/Users/nexil/Desktop/Instagram Liste" \
  --data-class D0
```

Ergebnis:

`C:\Users\nexil\Desktop\Instagram Liste\<Thema>.md`

Die Themen-Dateien enthalten pro Eintrag URL, Fragen, Status, Datenklasse, Analyse-Pfad, Kosten und Qdrant-ID.

## Batch-Verarbeitung

Direkter Test in WSL:

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/run_batch_pipeline.py \
  --topic-file "/mnt/c/Users/nexil/Desktop/Instagram Liste/D0-NASA-Batch-Test.md" \
  --budget-eur 5.00 \
  --sleep-seconds 2
```

Der Batch verarbeitet nur Eintraege mit:

`Status: noch nicht analysiert`

D2/D3 werden standardmaessig blockiert, bis du Cloud-Verarbeitung ausdruecklich freigibst.

## n8n Workflow

Workflow:

`200-Video-Pipeline-Batch`

Export:

`C:\AI\projects\09-video-analyse\workflows\200-Video-Pipeline-Batch.exported.json`

Nutzung:

1. n8n oeffnen: `http://localhost:5678`
2. Workflow `200-Video-Pipeline-Batch` oeffnen
3. Node `Input - Edit Topic File Here` anpassen:
   - `topic_file`: Pfad zur Themen-Datei
   - `budget_eur`: meistens `5.00`
   - `sleep_seconds`: meistens `2`
4. Manuell starten.

Wichtig: Der lokale Bridge-Server muss laufen:

`C:\Users\nexil\Desktop\KI\scripts\start-video-pipeline-bridge.ps1`

## Qdrant

Collection:

`video_knowledge`

Embedding:

`nomic-embed-text` lokal ueber Ollama

Gespeicherte Felder:

- URL
- Thema
- Datenklasse
- Fragen
- Analyse-Markdown
- Transcript-Pfad
- Kosten
- Qdrant-ID

Suche in WSL:

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/search_video_knowledge.py "Welche Technik ist im NASA Video sichtbar?" --limit 3
```

## Schutzregeln

- Kosten-Vorpruefung: Default `0.06 EUR` pro Video.
- Stop, wenn Schaetzung ueber `5.00 EUR` liegt.
- D2/D3 gehen nicht in Gemini/Cloud ohne explizite Freigabe.
- Kein Instagram-Login.
- Keine Telegram-Aktion in dieser Aufgabe.
- Aktuell bewusst sequentiell, nicht parallel, damit Kosten und Fehler leichter kontrollierbar bleiben.

## Testlauf 2026-05-29

Direkter Batch-Test:

- Datei: `C:\Users\nexil\Desktop\Instagram Liste\D0-NASA-Batch-Test.md`
- Videos: 3 D0 NASA-Testeintraege
- Gemini-Kosten: `0.052321 USD`
- Alle 3 Eintraege analysiert und in Qdrant gespeichert.

n8n Workflow-Test:

- Datei: `C:\Users\nexil\Desktop\Instagram Liste\D0-NASA-Workflow-Test.md`
- Videos: 1 D0 NASA-Testeintrag
- Gemini-Kosten: `0.015230 USD`
- Workflow lief sauber ueber n8n -> Bridge -> Python -> Qdrant.

Gesamt Testkosten Aufgabe 013:

`0.067551 USD`

## Naechster sinnvoller Schritt

Aufgabe 014 sollte die Pipeline nach aussen bedienbarer machen, zum Beispiel per Telegram-Bot, Statusmeldungen oder einem kleinen Kontroll-Interface. Vorher bleibt wichtig: echte Instagram- oder private Inhalte nur nach Datenklasse und Freigabe.
