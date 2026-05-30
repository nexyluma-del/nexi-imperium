# Bilder-Pipeline mit 3-Way Crosscheck

Stand: 2026-05-30

## Ziel

Instagram-Posts unter `/p/` koennen Bild- oder Karussell-Posts sein. Diese Pipeline analysiert solche Posts mit drei Cloud-Modellen und erstellt danach lokal eine konsolidierte Synthese.

Modelle:

- Claude via Anthropic
- ChatGPT/OpenAI via OpenAI
- Gemini via Google
- Lokale Synthese via Ollama `qwen3:30b`

## Sicherheit

- API-Keys stehen nur lokal in `C:\AI\projects\09-video-analyse\.env`.
- `.env` ist in `.gitignore` ausgeschlossen.
- D2/D3 Cloud-Verarbeitung nur mit expliziter Freigabe.
- Kostenlimit pro Test: `--max-cost-eur`, Standard `0.50`.
- Wenn Qdrant ausfaellt, bleiben Markdown und JSON trotzdem erhalten.

## Environment

Die `.env` braucht zusaetzlich zu Gemini:

```env
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o
```

## Script

Hauptscript:

`C:\AI\projects\09-video-analyse\scripts\analyze_post_crosscheck.py`

Beispiel:

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/analyze_post_crosscheck.py \
  --url "https://www.instagram.com/p/DYKtypgglev/" \
  --data-class D2 \
  --topic "IT" \
  --question "Um was geht es hier genau?" \
  --slug "IT-post-DYKtypgglev-crosscheck" \
  --max-cost-eur 0.50
```

Outputs:

- Markdown in `C:\AI\projects\09-video-analyse\analysis`
- JSON in `C:\AI\projects\09-video-analyse\analysis`
- Bilder in `C:\AI\projects\09-video-analyse\downloads\posts\<slug>`
- Qdrant Collection `video_knowledge`

## Download-Logik

1. yt-dlp versucht Instagram-Post-Metadaten und Thumbnails zu laden.
2. Falls yt-dlp keine Bilder liefert, versucht das Script einen HTML-OG-Image-Fallback.
3. Falls auch das keine Bilder liefert, kann die Pipeline als Metadaten-Fallback laufen und markiert das im Bericht.

## Batch-Integration

`run_batch_pipeline.py` erkennt automatisch:

- `instagram.com/reel/` -> bestehende Video-Pipeline
- `instagram.com/p/` -> neue Bilder-Crosscheck-Pipeline

Der n8n Batch-Workflow kann damit weiter dieselbe Batch-Schnittstelle nutzen.

## Test 2026-05-30

Test-URL:

`https://www.instagram.com/p/DYKtypgglev/`

Frage:

`Um was geht es hier genau?`

Ergebnis:

- Bild gefunden via HTML-Fallback: `html-image-01.jpg`
- 3 Cloud-Analysen erfolgreich
- lokale Synthese erfolgreich
- Qdrant-Insert erfolgreich nach Docker-Start

Kosten:

- Claude: `$0.012801`
- OpenAI: `$0.004492`
- Gemini: `$0.006694`
- Gesamt: `$0.023987`

Qdrant:

- Collection: `video_knowledge`
- Point-ID: `f310818c-2fd1-b590-f4a4-40e0deb2f5c4`
- Payload-Tags: `type=image-post`, `crosscheck=3way`

## Inhaltliches Testergebnis

Der Post behandelt neue chinesische Regeln fuer Influencer und Content Creator. Wer ueber Fachthemen wie Medizin, Recht, Finanzen, Bildung oder Gesundheit spricht, muss fachliche Qualifikation nachweisen. Die Modelle waren sich im Kern einig. Der Crosscheck fand eine Abweichung: Claude las den Bildtext als "ZENSIERT", OpenAI und Gemini als "BANNED"; die lokale Synthese wertete "BANNED" als wahrscheinlicher.

## Offene Punkte

- Bei Docker-Neustart sicherstellen, dass Qdrant laeuft.
- Optional: n8n Workflow um einen sichtbaren "Image/Post Batch" Hinweis erweitern.
- Optional: Kostenmodelle regelmaessig aktualisieren, weil API-Preise und Modellnamen sich aendern koennen.
