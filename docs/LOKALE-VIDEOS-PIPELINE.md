# Lokale Videos Pipeline

Stand: 2026-05-30

## Zweck

Diese Pipeline verarbeitet lokale Videos aus `C:\Users\nexil\Desktop\Instagram Videos`, ohne die komplette Videodatei an Gemini zu senden. Lokal werden Audio und Frames extrahiert. Danach gehen nur das Whisper-Transkript, wenige Standbilder und Nexis Fragen in die Cloud-Analyse.

## Wichtige Sperre

Sofinello ist in Aufgabe 016 komplett ausgespart. Alle Kategorien, deren Name mit `Sofinello` beginnt, werden automatisch uebersprungen. Sofinello bekommt spaeter eine eigene Pipeline-Variante:

- Aufgabe 016b: Sofinello-Spezial-Pipeline mit Heilungs-Compliance-Agent.
- Aufgabe 016c: Real-ESRGAN als Pflicht-Upscaling bzw. optionaler Pre-Processor.

## Dateien

- `scripts/analyze_local_video.py`: verarbeitet genau ein lokales Video.
- `scripts/process_local_folder.py`: scannt einen Ordner rekursiv, filtert Kategorien und fuehrt die Einzelanalyse aus.
- `scripts/run_batch_pipeline.py`: akzeptiert jetzt auch einen Ordner als `--topic-file` und leitet dann in die lokale Ordnerpipeline weiter.
- `category_prompts.json`: steuert Kategorie-Fragen, Pipeline-Namen, Sperren und spaetere Pre-Processor.
- `logs/local-video-processed.json`: Statusdatei gegen Doppelverarbeitung.

## Standard-Test

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/process_local_folder.py \
  --root "/mnt/c/Users/nexil/Desktop/Instagram Videos" \
  --filter "KI Tools" \
  --filter "IT Hacks" \
  --filter "Finanzen" \
  --one-per-category \
  --max-videos 3 \
  --data-class D2 \
  --max-cost-eur 5
```

## Pipeline-Schritte

1. Kategorie aus dem obersten Unterordner bestimmen.
2. Sofinello und alle in `category_prompts.json` gesperrten Kategorien ueberspringen.
3. Audio lokal mit `ffmpeg` extrahieren.
4. Audio lokal mit `faster-whisper large-v3` transkribieren.
5. Bis zu sechs Frames mit `ffmpeg` erzeugen.
6. Gemini bekommt nur Frames, Transkript, Kategorie, Quelle und Fragen.
7. Markdown und JSON werden unter `analysis/local/<Kategorie>/` geschrieben.
8. Qdrant `video_knowledge` erhaelt Eintraege mit `type=local-video`.
9. Status wird in `logs/local-video-processed.json` gespeichert.

## Erweiterung pro Kategorie

Neue Kategorien werden in `category_prompts.json` ergaenzt:

```json
{
  "Neue Kategorie": {
    "question": "Welche Frage soll standardmaessig beantwortet werden?",
    "pipeline": "default_local_video",
    "preprocessor": null
  }
}
```

Spezialstrecken koennen spaeter ueber `pipeline` und `preprocessor` angebunden werden. Fuer Real-ESRGAN ist der Hook bereits vorgesehen, aber in Aufgabe 016 noch nicht aktiv.
