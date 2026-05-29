# Video-Pipeline Setup - Aufgabe 010

Stand: 2026-05-29

## Ergebnis

Aufgabe 010 ist abgeschlossen. Der lokale Kern der Video-Pipeline ist eingerichtet:

- yt-dlp fuer Video-/Audio-Downloads
- ffmpeg fuer Audio-Extraktion
- faster-whisper mit Whisper `large-v3`
- CUDA/GPU-Nutzung ueber die RTX 5090 Laptop GPU
- lokale Helper-Skripte fuer Download, Transkription und Smoke-Test

Es wurden keine privaten Instagram-Videos verarbeitet, keine Gemini-Analyse gestartet, kein n8n-Workflow gebaut und nichts in eine Cloud hochgeladen.

## Projektpfad

Windows:

```text
C:\AI\projects\09-video-analyse
```

WSL:

```text
/mnt/c/AI/projects/09-video-analyse
```

## Ordnerstruktur

```text
C:\AI\projects\09-video-analyse\
  .venv\
  downloads\
  audio\
  transcripts\
  analysis\
  scripts\
  logs\
  models\
```

## Installierte Komponenten

WSL-Distribution:

```text
Ubuntu-24.04
```

Python/Tools:

```text
Python:         3.12.3
yt-dlp:         2026.03.17
ffmpeg:         6.1.1-3ubuntu5
faster-whisper: 1.2.1
ctranslate2:    4.7.2
CUDA devices:   1
```

Python-Umgebung:

```text
C:\AI\projects\09-video-analyse\.venv
```

CUDA-Libraries in der venv:

```text
nvidia-cublas-cu12
nvidia-cudnn-cu12
nvidia-cuda-nvrtc-cu12
```

Modell-Cache:

```text
C:\AI\projects\09-video-analyse\models\faster-whisper\models--Systran--faster-whisper-large-v3
```

## GPU-Status

GPU:

```text
NVIDIA GeForce RTX 5090 Laptop GPU
VRAM laut nvidia-smi: 24463 MiB
Windows/NVIDIA Driver: 596.49
CUDA laut nvidia-smi: 13.2
```

Smoke-Test GPU-Spitzenwert:

```text
Max. VRAM im Sampling: 6959 MiB / 24463 MiB
Max. GPU-Auslastung im Sampling: 63 %
```

Damit ist bestaetigt, dass faster-whisper/large-v3 lokal mit CUDA auf der GPU laeuft.

## Skripte

Download:

```text
C:\AI\projects\09-video-analyse\scripts\download.sh
```

Nutzung aus WSL:

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/download.sh "<oeffentliche-video-url>" D0 eigener-slug
```

Transkription:

```text
C:\AI\projects\09-video-analyse\scripts\transcribe.py
```

Nutzung aus WSL:

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/transcribe.py audio/eigener-slug.mp3 --data-class D0
```

Smoke-Test:

```text
C:\AI\projects\09-video-analyse\scripts\run_transcribe_test.sh
```

Nutzung aus WSL:

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/run_transcribe_test.sh audio/nasa-llcd-laser-communication.mp3
```

## Erfolgreicher End-to-End-Test

Testquelle:

```text
NASA public MP4:
https://www.nasa.gov/wp-content/uploads/2023/09/nsn-llcd-1.mp4
```

Kontext zur Quelle:

```text
https://www.nasa.gov/content/goddard/historic-demonstration-proves-laser-communication-possible
```

Download-Ergebnis:

```text
C:\AI\projects\09-video-analyse\audio\nasa-llcd-laser-communication.mp3
C:\AI\projects\09-video-analyse\audio\nasa-llcd-laser-communication.info.json
C:\AI\projects\09-video-analyse\audio\nasa-llcd-laser-communication.pipeline-meta.json
```

Transkript-Ergebnis:

```text
C:\AI\projects\09-video-analyse\transcripts\nasa-llcd-laser-communication.txt
C:\AI\projects\09-video-analyse\transcripts\nasa-llcd-laser-communication.json
```

Logs:

```text
C:\AI\projects\09-video-analyse\logs\download-20260529-174701.log
C:\AI\projects\09-video-analyse\logs\transcribe-20260529-174716.log
C:\AI\projects\09-video-analyse\logs\gpu-sample-20260529-174716.log
```

Transkript-Messwerte:

```text
Sprache: en
Sprachwahrscheinlichkeit: 0.9833984375
Audio-Dauer: 58.166 s
Transkriptionszeit inkl. Modellstart: 12.209 s
Geschwindigkeit: 4.764x Echtzeit
Segmente: 2
```

## Bekannte Hinweise

- Die zuerst getesteten NASA-Earth-Minute-Links unter `climate.nasa.gov/internal_resources/...` leiten aktuell auf eine generische NASA-Climate-Seite um. Sie wurden deshalb nicht als finaler Smoke-Test verwendet.
- `transcribe.py` setzt die Projekt-venv und die CUDA-Library-Pfade automatisch, damit es auch direkt als Script aus WSL funktioniert.
- `C:\AI` liegt nach aktuellem Stand nicht im Restic-Backupumfang aus Aufgabe 002. Fuer die naechste Backup-Runde sollte entschieden werden, ob `C:\AI` komplett oder mindestens `C:\AI\projects\09-video-analyse\scripts` und wichtige Projektdaten gesichert werden.

## Datenregel

- D0: oeffentliche Testvideos, harmlose Beispiele
- D1/D2: erst nach bewusster Freigabe
- D3/D4: nicht in Aufgabe 010 verarbeiten

Private Instagram-Videos und URL-Listen bleiben fuer spaetere Aufgaben unangetastet.

## Naechster sinnvoller Schritt

Aufgabe 011: Gemini API fuer visuelle Videoanalyse konzipieren und anbinden.

