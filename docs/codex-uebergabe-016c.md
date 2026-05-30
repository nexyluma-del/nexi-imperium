# Codex Uebergabe - Aufgabe 016c Real-ESRGAN Upscaling

Datum: 2026-05-30

## Ergebnis

Aufgabe 016c ist umgesetzt.

Real-ESRGAN ist installiert, die RTX-5090-faehige Windows-Binary wurde erfolgreich getestet, und die lokale Video-Pipeline kann jetzt mit `--upscale auto|always|never` arbeiten.

## Wichtige Architekturentscheidung

Die WSL-Binary funktioniert, nutzt aber nur `llvmpipe` und damit Software-Vulkan. Deshalb nutzt die Pipeline standardmaessig:

`C:\AI\tools\realesrgan-ncnn-vulkan-windows\realesrgan-ncnn-vulkan.exe`

Diese Binary erkennt die GPU korrekt:

`NVIDIA GeForce RTX 5090 Laptop GPU`

## Neue/aktualisierte Dateien

- `C:\AI\projects\09-video-analyse\scripts\check_video_quality.py`
- `C:\AI\projects\09-video-analyse\scripts\upscale_video.py`
- `C:\AI\projects\09-video-analyse\scripts\analyze_local_video.py`
- `C:\AI\projects\09-video-analyse\scripts\process_local_folder.py`
- `C:\Users\nexil\Desktop\KI\UPSCALING-SETUP.md`

## Neue Pipeline-Optionen

- `--upscale auto` - Detector entscheidet.
- `--upscale always` - Pflicht-Upscaling, vorbereitet fuer Sofinello.
- `--upscale never` - schnelle Analyse ohne Upscaling.
- `--upscale-scale 2|3|4`
- `--upscale-model realesrgan-x4plus`
- `--upscale-max-duration-seconds 180`
- `--upscale-max-duration-seconds 0` deaktiviert das Zeitlimit.

## Tests

Detector:

- Low-Quality-Testvideo: 360x450, `needs_upscaling = true`.
- HD-Testvideo: 1080x1920, `needs_upscaling = false`.

Upscale:

- Input: 360x450, 5.2 Sekunden.
- Output: 720x900.
- Output-Datei: `C:\AI\projects\09-video-analyse\upscaled\tests\ki-tools-low-upscaled-x2.mp4`
- Real-ESRGAN-Log bestaetigt NVIDIA-GPU.

Pipeline:

- Ohne Upscaling:
  - Markdown: `C:\AI\projects\09-video-analyse\analysis\local\KI-Tools\016c-low-no-upscale-test.local-video-2026-05-30_220651.md`
  - Kosten: `$0.002881`

- Mit Auto-Upscaling:
  - Markdown: `C:\AI\projects\09-video-analyse\analysis\local\KI-Tools\016c-low-auto-upscale-test.local-video-2026-05-30_220745.md`
  - Upscaled Video: `C:\AI\projects\09-video-analyse\upscaled\local\KI-Tools\016c-low-auto-upscale-test_upscaled_x2.mp4`
  - Kosten: `$0.003540`

- HD-Dry-Run:
  - Auto-Modus hat korrekt kein Upscaling gestartet.

## Kosten

Cloud-Kosten durch Tests:

- Gesamt Gemini: ca. `$0.006421`
- Real-ESRGAN: lokal, 0 EUR.

## Offene Hinweise fuer 016b

Vor Sofinello-Grossbatch unbedingt:

- Zeit-Schaetzung fuer 722 Videos berechnen.
- Test mit 3-5 Sofinello-Clips.
- Heilungs-Compliance-Agent einbauen.
- Erst nach expliziter Freigabe gross starten.

## Git

Bitte nach Commit/Push in der Abschlussmeldung die Commit-ID nennen.
