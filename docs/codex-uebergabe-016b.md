# Codex Uebergabe - Aufgabe 016b Sofinello Spezial-Pipeline

Datum: 2026-05-30

## Ergebnis

Sofinello-Testpipeline ist umgesetzt und getestet.

Der grosse 722er-Batch wurde nicht gestartet.

## Umsetzung

- Datenklasse: D2, Gemini-Cloud erlaubt.
- Pflicht-Upscaling mit Real-ESRGAN vor Analyse.
- Eigener Compliance-Agent.
- Eigene Qdrant-Collection: `sofinello_knowledge`.
- Eigene Wissens-Anker unter `C:\AI\projects\06-heilung\knowledge`.
- Finaler Output enthaelt Disclaimer und Compliance-Status.
- Riskante Wirkformulierungen werden im finalen Markdown, JSON und Qdrant-Kontext maskiert.

## Testvideos

1. Health/Sebi-Lehre:
   - Datei: `C:\Users\nexil\Desktop\Instagram Videos\Sofinello\2) Bilder Allgemein\Health\Snapinsta.app_video_1742149D5E92B100A472D135269332BF_video_dashinit.mp4`
   - Final: `C:\AI\projects\09-video-analyse\analysis\sofinello\final\016b-test-1-sebi-lehre.sofinello-final-2026-05-30_222457.md`
   - Status: `FREIGEGEBEN`
   - Kosten: `$0.016108`

2. Mixtur/Rezept:
   - Datei: `C:\Users\nexil\Desktop\Instagram Videos\Sofinello\Back Up\Salat\IMG_0892.MOV`
   - Final: `C:\AI\projects\09-video-analyse\analysis\sofinello\final\016b-test-2-mixtur.sofinello-final-2026-05-30_223351.md`
   - Status: `FREIGEGEBEN`
   - Kosten: `$0.014540`

3. Produkt/Verpackung:
   - Datei: `C:\Users\nexil\Desktop\Instagram Videos\Sofinello\1 NEUE PRODUKTE\Zubehör Produkte\Urin Analyse\1\1.mp4`
   - Final: `C:\AI\projects\09-video-analyse\analysis\sofinello\final\016b-test-3-produkt-verpackung.sofinello-final-2026-05-30_224019.md`
   - Status: `FREIGEGEBEN`
   - Kosten: `$0.014259`

Gesamt-Testkosten: `$0.044907`.

## Qdrant

- Collection: `sofinello_knowledge`
- Punkte: 3
- Status: gruen

## 722er-Schaetzung

Bestand:

- 722 Videos
- 19.3 GB
- 4.65 Stunden Videomaterial
- Median: 18.21 Sekunden
- Durchschnitt: 23.19 Sekunden
- P90: 50.1 Sekunden

Cloud:

- ca. `$18-43` konservativ fuer den vollen Lauf.

GPU:

- Full-Video-Upscaling aller 722: ca. 176-703 Stunden, nicht empfohlen.
- Frame-Only-Upscaling: ca. 2.5-10 Stunden, empfohlen.
- Hybrid: ca. 10-40 Stunden.

## Approval-Vorschlag

A - Full-Video-Upscaling fuer alle 722:

- Maximal streng, aber viel zu langsam.
- Nicht empfohlen.

B - Frame-Only-Upscaling fuer alle 722:

- Empfohlen.
- Sehr viel schneller, fuer Wissensextraktion ausreichend.
- Braucht kleine Code-Anpassung vor Batch.

C - Hybrid:

- Frame-Only fuer normale Videos.
- Full-Video nur fuer Low-Res/OCR/Verpackungsfaelle.
- Gute Qualitaet, aber laenger als B.

## Naechster Schritt

Auf Nexis A/B/C-Freigabe warten. Danach entweder Batch-Variante vorbereiten/starten oder mit Aufgabe 018 Voice-Capture weitermachen.
