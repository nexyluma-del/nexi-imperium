# Upscaling Setup - Real-ESRGAN

Stand: 2026-05-30

## Ergebnis

Real-ESRGAN ist fuer die lokale Video-Pipeline vorbereitet.

Wichtig: In WSL nutzt `realesrgan-ncnn-vulkan` nur `llvmpipe` und damit Software-Vulkan. Fuer echte RTX-5090-Nutzung verwendet die Pipeline deshalb die Windows-native Binary und startet sie aus WSL heraus.

Quelle der Binary: https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0

## Installierte Pfade

- Windows GPU Binary: `C:\AI\tools\realesrgan-ncnn-vulkan-windows\realesrgan-ncnn-vulkan.exe`
- Windows Modelle: `C:\AI\tools\realesrgan-ncnn-vulkan-windows\models`
- WSL CPU/llvmpipe Binary als Fallback: `C:\AI\tools\realesrgan-ncnn-vulkan\realesrgan-ncnn-vulkan`
- Python-Skripte: `C:\AI\projects\09-video-analyse\scripts`
- Upscale-Ausgaben: `C:\AI\projects\09-video-analyse\upscaled`
- Upscale-Logs: `C:\AI\projects\09-video-analyse\logs\upscale`

## Python-Pakete

In der Projekt-venv wurden installiert:

- `opencv-python-headless`
- `pillow`

## Neue Skripte

- `scripts/check_video_quality.py`
  - prueft Aufloesung, Bitrate pro Pixel/Frame und Schaerfe.
  - gibt `needs_upscaling` plus Gruende als JSON zurueck.

- `scripts/upscale_video.py`
  - extrahiert Frames mit ffmpeg.
  - verarbeitet Frames mit Real-ESRGAN.
  - baut ein neues MP4 mit Original-Audio.
  - ueberschreibt nie das Original.

- `scripts/analyze_local_video.py`
  - neue Option `--upscale auto|always|never`.
  - `auto`: nur Low-Quality-Videos werden upscaled.
  - `always`: Pflicht-Upscaling, spaeter fuer Sofinello nutzbar.
  - `never`: schneller Test ohne Upscaling.

- `scripts/process_local_folder.py`
  - reicht die Upscale-Optionen an `analyze_local_video.py` weiter.

## Schwellwerte

Standard-Detector:

- Low-Res, wenn kurze Videoseite `< 720px`.
- Low-Bitrate, wenn `bits_per_pixel_frame < 0.045`.
- Niedrige Schaerfe, wenn Laplacian-Varianz `< 55` und die kurze Seite nicht groesser als 900px ist.

Auto-Sicherheitslimit:

- `--upscale-max-duration-seconds 180`
- Bedeutet: Auto-Upscaling stoppt lange Videos, damit nicht versehentlich stundenlange GPU-Jobs starten.
- Fuer spaetere Pflicht-Pipeline: `--upscale always --upscale-max-duration-seconds 0`

## Beispielbefehle

Video nur pruefen:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/check_video_quality.py '/mnt/c/pfad/video.mp4'"
```

Ein Video upscalen:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/upscale_video.py '/mnt/c/pfad/video.mp4' --scale 2 --max-duration-seconds 30"
```

Lokale Analyse mit Auto-Upscaling:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/analyze_local_video.py --video-path '/mnt/c/pfad/video.mp4' --data-class D2 --category 'KI Tools' --question 'Was ist sichtbar?' --upscale auto --max-cost-eur 0.50"
```

Sofinello-spaeterer Pflichtmodus:

```powershell
wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && .venv/bin/python scripts/analyze_local_video.py --video-path '/mnt/c/pfad/sofinello.mp4' --data-class D2 --category 'Sofinello' --question 'Analyse mit Compliance' --upscale always --upscale-max-duration-seconds 0"
```

## Tests

Real-ESRGAN Windows-Test:

- RTX erkannt: `NVIDIA GeForce RTX 5090 Laptop GPU`
- Testbild erfolgreich erzeugt.

Qualitaetsdetektor:

- 360x450 Video: `needs_upscaling = true`
- 1080x1920 Video: `needs_upscaling = false`

Upscale-Test:

- Input: 360x450, 5.2 Sekunden
- Output: 720x900
- Frames: 156 rein, 156 raus
- GPU-Binary: Windows Real-ESRGAN

Pipeline-Test:

- Ohne Upscaling: erfolgreich, Gemini-Kosten ca. `$0.002881`
- Mit Auto-Upscaling: erfolgreich, Gemini-Kosten ca. `$0.003540`
- HD-Dry-Run mit Auto: kein Upscaling, korrekt.

## Zeit-Hinweis

Gemessener kurzer Test:

- 5.2 Sekunden Video brauchten rund 66 Sekunden fuer Upscaling.

Arbeitsregel:

- Kurze Clips: Auto-Upscaling ist praktikabel.
- Lange Videos: nur bewusst starten.
- Sofinello 016b: vor 722 Videos unbedingt Cost-/Zeit-Schaetzung und Freigabe.
