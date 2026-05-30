# Sofinello Spezial-Pipeline

Stand: 2026-05-30

## Status

Aufgabe 016b ist als Test-Pipeline umgesetzt.

Wichtig: Der grosse 722er-Batch wurde NICHT gestartet. Dafuer braucht es neues Approval.

## Compliance-Basis

Arbeitsstandard:

- Datenklasse D2: Gemini-Cloud fuer oeffentliche Instagram-Inhalte erlaubt.
- EU/DE-Compliance: keine Heilversprechen, keine Diagnosen, keine krankheitsbezogene Werbung.
- Jeder final nutzbare Output bekommt Disclaimer und Compliance-Check.
- Riskante Wirkformulierungen werden im finalen Markdown und in JSON/Qdrant maskiert.

Orientierende Rechtsquellen:

- HWG § 3, irrefuehrende Werbung: `https://www.gesetze-im-internet.de/heilmwerbg/__3.html`
- HWG § 12, krankheitsbezogene Werbung: `https://www.gesetze-im-internet.de/heilmwerbg/__12.html`
- EU Nutrition and Health Claims: `https://food.ec.europa.eu/food-safety/labelling-and-nutrition/nutrition-and-health-claims_en`

## Wissens-Anker

Pfad:

`C:\AI\projects\06-heilung\knowledge`

Dateien:

- `sebi-food-list.md`
- `sebi-cell-food.md`
- `tcm-grundlagen.md`
- `disclaimer-standard.md`
- `compliance-rules.md`

Diese Dateien sind Kontext fuer Gemini und fuer den Compliance-Agenten. Sie sind Arbeitskontext, keine medizinische Wahrheit.

## Pipeline-Dateien

- `C:\AI\projects\09-video-analyse\scripts\analyze_sofinello.py`
- `C:\AI\projects\09-video-analyse\scripts\sofinello_compliance.py`
- `C:\AI\projects\09-video-analyse\scripts\estimate_sofinello_batch.py`
- `C:\AI\projects\09-video-analyse\scripts\qdrant_video_knowledge.py`

## Ablauf pro Video

1. Original bleibt unveraendert.
2. Pflicht-Upscaling mit Real-ESRGAN.
3. Audio-Extraktion und lokales Whisper-Transkript.
4. Aus upgescaltem Video werden Analyse-Frames erzeugt.
5. Gemini bekommt Frames + Transkript + Wissens-Anker.
6. Roh-Markdown wird geschrieben.
7. Compliance-Agent prueft, maskiert riskante Wirkformulierungen und fuegt Disclaimer an.
8. Finales Markdown wird gespeichert.
9. Finaler Output wird in Qdrant `sofinello_knowledge` geschrieben.

## Output-Orte

- Raw: `C:\AI\projects\09-video-analyse\analysis\sofinello\raw`
- Final: `C:\AI\projects\09-video-analyse\analysis\sofinello\final`
- Upscaled Videos: `C:\AI\projects\09-video-analyse\upscaled\sofinello`
- Logs: `C:\AI\projects\09-video-analyse\logs\sofinello`
- Qdrant: `sofinello_knowledge`

## Test-Ergebnisse

Alle 3 Tests liefen erfolgreich.

| Test | Art | Status | Kosten |
|---|---|---:|---:|
| 016b-test-1-sebi-lehre | Health/Sebi-Lehre | FREIGEGEBEN | $0.016108 |
| 016b-test-2-mixtur | Salat/Mixtur | FREIGEGEBEN | $0.014540 |
| 016b-test-3-produkt-verpackung | Produkt/Verpackung | FREIGEGEBEN | $0.014259 |

Gesamt Gemini-Testkosten: `$0.044907`.

Qdrant `sofinello_knowledge`: 3 Punkte.

## 722er-Batch-Schaetzung

Bestand im Hauptordner:

- Root: `C:\Users\nexil\Desktop\Instagram Videos\Sofinello`
- Videos: 722
- Datenmenge: 19.3 GB
- Gesamtdauer: 4.65 Stunden
- Median-Dauer: 18.21 Sekunden
- Durchschnitt: 23.19 Sekunden
- P90: 50.1 Sekunden
- 456 Videos haben kurze Seite >= 1080p
- 47 Videos haben kurze Seite < 720p

Cloud-Kosten:

- sehr niedrig, $0.015 pro Video: ca. `$10.83`
- normal, $0.025 pro Video: ca. `$18.05`
- konservativ, $0.040 pro Video: ca. `$28.88`
- hoch, $0.060 pro Video: ca. `$43.32`

## Wichtige Erkenntnis: Full-Video-Upscaling ist zu teuer

Die Tests zeigen: komplettes x2-Upscaling ganzer Videos ist fuer 722 Videos zu langsam.

Geschaetzte GPU-Zeit fuer Full-Video-Upscaling:

- optimistisch: ca. 176 Stunden
- normal: ca. 352 Stunden
- langsam: ca. 703 Stunden

Das ist nicht sinnvoll fuer Phase 2.

## Empfohlenes A/B/C Approval fuer den grossen Lauf

A - Strikt wie Spec, Full-Video-Upscaling aller 722 Videos:

- Cloud: ca. 18-43 USD
- GPU: ca. 176-703 Stunden
- Nicht empfohlen.

B - Empfohlen: Frame-Only-Upscaling fuer Analyseframes:

- Nur 6-10 Analyseframes pro Video werden upgescaled, nicht das ganze Video.
- Cloud: ca. 18-43 USD
- GPU: ca. 2.5-10 Stunden
- Beste Balance fuer Wissensextraktion und Kosten.
- Braucht kleine Code-Anpassung vor Batch.

C - Hybrid:

- Full-Video-Upscaling nur fuer Low-Res/Verpackungs-/OCR-Faelle.
- Frame-Only-Upscaling fuer normale Videos.
- Cloud: ca. 18-43 USD
- GPU: grob 10-40 Stunden, je nach Anteil Full-Video.
- Sinnvoll, wenn Verpackungen/Etiketten maximal wichtig sind.

## Empfehlung

Empfehlung: Option B fuer den ersten 722er-Wissensbatch.

Danach koennen besonders wichtige Verpackungs-/OCR-Clips gezielt mit Full-Video-Upscaling nachbearbeitet werden.
