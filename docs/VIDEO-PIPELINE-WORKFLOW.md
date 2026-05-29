# Video-Pipeline Workflow - Aufgabe 012

Stand: 2026-05-29

## Status

Aufgabe 012 ist abgeschlossen. Der n8n-Workflow `100-Video-Pipeline-Manual` ist importiert, getestet und als JSON exportiert.

Der erfolgreiche Test lief mit dem oeffentlichen NASA-Video:

```text
https://www.nasa.gov/wp-content/uploads/2023/09/nsn-llcd-1.mp4
```

## Architektur

n8n laeuft als Docker-Container. Der Container kann Windows/WSL-Befehle nicht direkt ausfuehren. Deshalb nutzt der Workflow einen kleinen lokalen Bridge-Service:

```text
n8n Manual Trigger
-> Input Code Node
-> HTTP Request an http://host.docker.internal:8787/run
-> WSL Bridge
-> bestehende Pipeline-Skripte
-> Final Summary
```

Die eigentliche Pipeline-Logik bleibt in den getesteten Skripten:

```text
C:\AI\projects\09-video-analyse\scripts\download.sh
C:\AI\projects\09-video-analyse\scripts\transcribe.py
C:\AI\projects\09-video-analyse\scripts\analyze_full.py
```

Zusaetzliche Aufgabe-012-Skripte:

```text
C:\AI\projects\09-video-analyse\scripts\run_video_pipeline.py
C:\AI\projects\09-video-analyse\scripts\pipeline_bridge.py
C:\AI\projects\09-video-analyse\scripts\start_pipeline_bridge.sh
C:\Users\nexil\Desktop\KI\scripts\start-video-pipeline-bridge.ps1
```

## Bridge starten

Nach einem Neustart vor Nutzung des Workflows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nexil\Desktop\KI\scripts\start-video-pipeline-bridge.ps1"
```

Health-Check:

```powershell
curl http://localhost:8787/health
```

Erwartung:

```json
{
  "ok": true,
  "service": "nexi-video-pipeline-bridge"
}
```

## n8n Workflow

Name:

```text
100-Video-Pipeline-Manual
```

n8n URL:

```text
http://localhost:5678
```

Nodes:

| Node | Aufgabe |
|---|---|
| Manual Trigger | Startet den Workflow manuell |
| Input - Edit URL Here | URL, Datenklasse, Slug und Kostenlimit setzen |
| Run Local WSL Pipeline | Ruft die lokale Bridge per HTTP auf |
| Final Summary | Erzeugt ein kompaktes Ergebnisobjekt |

## Nutzung

1. n8n oeffnen: `http://localhost:5678`
2. Workflow `100-Video-Pipeline-Manual` oeffnen
3. Node `Input - Edit URL Here` bearbeiten
4. Werte setzen:

```javascript
url: 'https://...',
data_class: 'D0',
slug: 'eigener-slug',
max_cost_eur: '0.30'
```

5. Workflow manuell starten.

Wichtig:

- Nur ein Video pro Run.
- Kein Batch-Modus in Aufgabe 012.
- Keine Instagram-Login-Automation.
- Private Videos erst bewusst mit korrekter Datenklasse.

## Was im Pipeline-Run passiert

1. Video wird nach `downloads/` geladen.
2. Audio wird als MP3 nach `audio/` extrahiert.
3. Whisper large-v3 transkribiert lokal auf der GPU.
4. Gemini Pro analysiert Video + Whisper-Transkript.
5. Markdown + JSON landen in `analysis/`.
6. n8n zeigt Pfade, Tokens, Kosten und Laufzeiten im Final Summary.

## Erfolgreicher NASA-Test

Workflow-Ausfuehrung:

```text
100-Video-Pipeline-Manual
Status: success
```

Finale Outputs:

```text
C:\AI\projects\09-video-analyse\analysis\n8n-manual-nasa.full-gemini-2026-05-29_202858.md
C:\AI\projects\09-video-analyse\analysis\n8n-manual-nasa.full-gemini-2026-05-29_202858.json
```

Weitere Dateien:

```text
C:\AI\projects\09-video-analyse\downloads\n8n-manual-nasa.mp4
C:\AI\projects\09-video-analyse\audio\n8n-manual-nasa.mp3
C:\AI\projects\09-video-analyse\transcripts\n8n-manual-nasa.txt
C:\AI\projects\09-video-analyse\transcripts\n8n-manual-nasa.json
C:\AI\projects\09-video-analyse\logs\pipeline\n8n-manual-nasa-2026-05-29_202831.log
```

Laufzeiten:

```text
Video-Download: 1.979 s
Audio-Download: 2.702 s
Whisper:        15.996 s
Gemini:         33.775 s
```

Kosten:

```text
Preflight-Schaetzung: 0.049433 USD
Ist-Schaetzung:       0.019284 USD
Prompt Tokens:        5683
Output Tokens:        1218
Total Tokens:         8179
```

Zusatztest des lokalen Runners vor dem n8n-Test:

```text
n8n-nasa-test-2: 0.019286 USD
```

Aufgabe-012-Testverbrauch insgesamt:

```text
ca. 0.038570 USD
```

## Error Handling

Der Workflow selbst bekommt von der Bridge immer ein JSON-Objekt:

```json
{
  "ok": true
}
```

oder:

```json
{
  "ok": false,
  "error": "...",
  "log_file": "..."
}
```

Fehler werden in `logs/pipeline/` protokolliert. Der Final-Summary-Node gibt bei Fehlern `status: error` aus.

Der Runner hat Schutzmechanismen:

- Kosten-Cap via `max_cost_eur`, Standard `0.30`
- D3/D4 gesperrt ohne explizites `--allow-sensitive`
- Gemini 503 / High Demand wird einmal nach 30 Sekunden erneut versucht
- jeder Schritt schreibt Exit-Code und Output ins Pipeline-Log

## Workflow Backup / Export

Import-Datei:

```text
C:\AI\projects\09-video-analyse\workflows\100-Video-Pipeline-Manual.json
```

Export aus n8n nach erfolgreichem Import:

```text
C:\AI\projects\09-video-analyse\workflows\100-Video-Pipeline-Manual.exported.json
```

## Bekannte Limits

- Manual Single-Video only.
- Kein Batch-Modus.
- Keine Qdrant-Embeddings.
- Kein Telegram-Push.
- Kein Instagram-Login.
- Bei Neustart muss die Bridge wieder gestartet werden.
- Gemini Pro kann temporaer `503 high demand` melden; der Runner versucht einmal erneut.

## Naechster Schritt

Aufgabe 013: Batch-Modus mit URL-Listen + Qdrant-Embeddings fuer RAG.

