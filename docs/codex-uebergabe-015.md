# Codex Uebergabe Aufgabe 015

Stand: 2026-05-30

## Status

Aufgabe 015 ist technisch abgeschlossen: Die Bilder-Pipeline fuer Instagram-Posts laeuft mit Claude + OpenAI + Gemini Crosscheck, lokaler Synthese ueber `qwen3:30b`, Kostenbericht und Qdrant-Indexierung.

## Dateien

- Script: `C:\AI\projects\09-video-analyse\scripts\analyze_post_crosscheck.py`
- Batch erweitert: `C:\AI\projects\09-video-analyse\scripts\run_batch_pipeline.py`
- Qdrant erweitert: `C:\AI\projects\09-video-analyse\scripts\qdrant_video_knowledge.py`
- Doku: `C:\Users\nexil\Desktop\KI\BILDER-PIPELINE-CROSSCHECK.md`

## Test

URL:

`https://www.instagram.com/p/DYKtypgglev/`

Frage:

`Um was geht es hier genau?`

Output:

- Markdown: `C:\AI\projects\09-video-analyse\analysis\IT-post-DYKtypgglev-crosscheck.image-crosscheck-2026-05-30_184924.md`
- JSON: `C:\AI\projects\09-video-analyse\analysis\IT-post-DYKtypgglev-crosscheck.image-crosscheck-2026-05-30_184924.json`
- Bild: `C:\AI\projects\09-video-analyse\downloads\posts\IT-post-DYKtypgglev-crosscheck\html-image-01.jpg`

## Kosten

- Claude: `$0.012801`
- OpenAI: `$0.004492`
- Gemini: `$0.006694`
- Gesamt: `$0.023987`, also ca. 2,4 Cent

Damit klar unter dem Limit von 0,50 EUR.

## Qdrant

Erfolgreich gespeichert in `video_knowledge`.

- Point-ID: `f310818c-2fd1-b590-f4a4-40e0deb2f5c4`
- Payload: `type=image-post`, `crosscheck=3way`

## Inhalt kurz

Der Post geht um neue chinesische Regeln fuer Influencer/Creator. Bei Fachthemen wie Medizin, Recht, Finanzen, Bildung oder Gesundheit muessen Qualifikationen nachgewiesen werden. Offiziell wird das mit Desinformation begruendet, praktisch ist es auch ein Thema von Plattformkontrolle und Meinungsfreiheit. Der Crosscheck hat genau das geliefert, wofuer er gebaut wurde: Claude las den sichtbaren Text als "ZENSIERT", OpenAI und Gemini als "BANNED"; die lokale Synthese markierte das als Widerspruch und wertete "BANNED" als wahrscheinlicher.

## Wichtiger Zwischenfall

Beim ersten echten Lauf war Docker Desktop nicht aktiv, deshalb war Qdrant nicht erreichbar. Die Cloud-Analysen waren bereits erfolgreich und Markdown wurde geschrieben. Danach wurde Docker Desktop gestartet, Qdrant lief wieder, JSON wurde nachgetragen und der Qdrant-Insert erfolgreich repariert. Das Script wurde danach gehaertet, damit Markdown/JSON bei zukuenftigem Qdrant-Ausfall nicht verloren gehen.

## Offene Punkte

- Optional: n8n Workflow optisch um Image/Post-Hinweis erweitern.
- Optional: Aufgabe 014 Telegram-Bot als naechstes, um solche Fehler und Fertigmeldungen aufs Handy zu bekommen.
- Optional: Aufgabe 010c Docker-Volumes ins Restic-Backup.
