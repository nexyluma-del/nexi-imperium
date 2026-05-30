# Codex Uebergabe - Aufgabe 016 Lokale Videos Pipeline

Stand: 2026-05-30 20:50

## Status

Aufgabe 016 ist umgesetzt und getestet. Die lokale Pipeline verarbeitet Videos aus `C:\Users\nexil\Desktop\Instagram Videos`, ohne die komplette Videodatei an Gemini zu senden. Es werden lokal Audio, Whisper-Transkript und Frames erzeugt; an Gemini gehen nur Transkript, Fragen und ausgewaehlte Frames.

## Sofinello-Sperre

Sofinello wurde fuer Aufgabe 016 vollstaendig ausgespart. Alle Kategorien, deren Name mit `Sofinello` beginnt, werden automatisch uebersprungen. Die spaetere Sofinello-Spezialstrecke bleibt fuer Aufgabe 016b reserviert; Real-ESRGAN/Upscaling bleibt fuer Aufgabe 016c reserviert.

## Neue/aktualisierte Dateien

- `C:\AI\projects\09-video-analyse\scripts\analyze_local_video.py`
- `C:\AI\projects\09-video-analyse\scripts\process_local_folder.py`
- `C:\AI\projects\09-video-analyse\scripts\qdrant_video_knowledge.py`
- `C:\AI\projects\09-video-analyse\scripts\run_batch_pipeline.py`
- `C:\AI\projects\09-video-analyse\category_prompts.json`
- `C:\Users\nexil\Desktop\KI\LOKALE-VIDEOS-PIPELINE.md`

## Testlauf

Getestet wurden genau drei normale Kategorien:

- `Finanzen`: erfolgreich, Qdrant ID `61e15c41-fbae-eee5-05d2-9985147b7846`, Kosten `$0.014672`
- `IT Hacks`: erfolgreich, Qdrant ID `47a73475-0894-07e3-ec62-313eff0b559d`, Kosten `$0.013604`
- `KI Tools`: erfolgreich, Qdrant ID `66973134-b996-0460-63fb-7a5974d8705a`, Kosten `$0.013769`

Gesamtkosten: `$0.042045`, also rund 4,2 Cent.

## Analyse-Dateien

- `C:\AI\projects\09-video-analyse\analysis\local\Finanzen\Finanzen-SnapInsta.to_AQM1tTpcD98avMs18ZgWCmGDHq0QJ525CkKGHucyqZzWqBOCOTGL2msTRPmQOdN73nSi.local-video-2026-05-30_204232.md`
- `C:\AI\projects\09-video-analyse\analysis\local\IT-Hacks\IT-Hacks-SnapInsta.to_AQM0uVSeRPWH_Nwq06K8TDhtGCKL6KVj-R8WFmpxh4x71cXBxT3vZWzxjlinedb9MLZR.local-video-2026-05-30_204341.md`
- `C:\AI\projects\09-video-analyse\analysis\local\KI-Tools\KI-Tools-SnapInsta.to_AQM0O-49nROSs9I55xKSek-GneHmA6Pb9P8Huw8n7LDQSY7XHxHEch8Knpx4I3EJcOzh.local-video-2026-05-30_204450.md`

## Verifikation

- `py_compile` fuer neue und geaenderte Skripte: OK
- Dry-Run der Ordnerpipeline: OK
- Echter Testlauf mit 3 Videos: OK
- Qdrant-Insert fuer alle 3 lokalen Videos: OK
- `run_batch_pipeline.py` akzeptiert Ordner-Modus per `--topic-file <Ordner>`: OK

## Naechster Vorschlag

Als naechstes ist Aufgabe 010c sinnvoll: Docker-Volumes ins Restic-Backup. Das schuetzt n8n, Qdrant und OpenWebUI-Daten, bevor weitere Automatisierung aufgebaut wird.
