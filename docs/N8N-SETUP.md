# N8N-SETUP

Stand: 2026-05-29
Phase: 1 - Lokale KI Minimal-Stack
Aufgabe: 009 - n8n Workflow-Engine

## Ergebnis

n8n laeuft lokal als Docker-Container und ist erreichbar unter:

http://localhost:5678

Healthcheck:

http://localhost:5678/healthz

Wichtig: n8n ist auf dem Windows-Host nur lokal gebunden:

127.0.0.1:5678 -> 5678/tcp

Damit wird n8n nicht ins Internet exponiert.

## Installierte Komponenten

n8n:

- Container-Name: `n8n`
- Image: `docker.n8n.io/n8nio/n8n`
- Version laut Logs: `2.22.5`
- Docker-Volume: `n8n_data:/home/node/.n8n`
- Restart-Policy: `always`
- Host-Binding: `127.0.0.1`
- Timezone: `Europe/Berlin`

Bestehende lokale Dienste:

- Ollama: http://host.docker.internal:11434
- Qdrant: http://host.docker.internal:6333
- OpenWebUI: http://localhost:3000

## Startbefehl

Der finale Container wurde mit diesem Setup gestartet:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' run -d `
  --name n8n `
  -p 127.0.0.1:5678:5678 `
  -v n8n_data:/home/node/.n8n `
  --add-host=host.docker.internal:host-gateway `
  -e N8N_HOST=localhost `
  -e N8N_PORT=5678 `
  -e N8N_PROTOCOL=http `
  -e N8N_EDITOR_BASE_URL=http://localhost:5678 `
  -e WEBHOOK_URL=http://localhost:5678 `
  -e GENERIC_TIMEZONE=Europe/Berlin `
  -e TZ=Europe/Berlin `
  -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true `
  -e N8N_SECURE_COOKIE=false `
  -e N8N_DIAGNOSTICS_ENABLED=false `
  -e N8N_VERSION_NOTIFICATIONS_ENABLED=false `
  -e N8N_TEMPLATES_ENABLED=false `
  -e EXTERNAL_FRONTEND_HOOKS_URLS= `
  -e N8N_DIAGNOSTICS_CONFIG_FRONTEND= `
  -e N8N_DIAGNOSTICS_CONFIG_BACKEND= `
  --restart always `
  docker.n8n.io/n8nio/n8n
```

Hinweis: `N8N_SECURE_COOKIE=false` ist nur fuer lokale HTTP-Nutzung auf `localhost` gesetzt. Falls n8n spaeter ueber HTTPS/VPS laeuft, muss diese Einstellung neu bewertet werden.

## Lokale Sicherheitsentscheidungen

- Keine Public-URL.
- Kein Port-Forwarding.
- Keine externen Credentials angelegt.
- Keine Telegram-, GitHub-, Shopify- oder Cloud-Keys gesetzt.
- Keine echten sensiblen Workflows gebaut.
- Nur lokaler Test-Workflow mit D0-Testprompt.
- n8n-Diagnostik deaktiviert: `N8N_DIAGNOSTICS_ENABLED=false`.
- Version-Notifications deaktiviert.
- Templates deaktiviert.
- Externe Frontend-Hooks geleert.

## Owner-Account

Der erste n8n-Owner wurde laut Logs erfolgreich eingerichtet:

`Owner was set up successfully`

Das Passwort gehoert in Standard Notes unter:

`n8n Owner`

Codex kann Standard Notes nicht pruefen.

## Funktionstests

Geprueft:

- Docker-Container `n8n` laeuft.
- `http://localhost:5678` antwortet mit `200 OK`.
- `http://localhost:5678/healthz` antwortet mit `{"status":"ok"}`.
- Persistentes Docker-Volume `n8n_data` ist eingebunden.
- Restart-Policy ist `always`.
- n8n kann Qdrant erreichen:
  - URL: `http://host.docker.internal:6333/collections`
  - Ergebnis: `200`, Collections leer
- n8n kann Ollama erreichen:
  - URL: `http://host.docker.internal:11434/api/generate`
  - Modell: `qwen3:4b`
  - Ergebnis: erfolgreiche Antwort

## Test-Workflow

Workflow-Name:

`000-Hello-World-Test`

Workflow-ID:

`000HelloWorldTest`

Aufbau:

- Manual Trigger
- HTTP Request Node an Ollama
- POST `http://host.docker.internal:11434/api/generate`
- Payload:

```json
{
  "model": "qwen3:4b",
  "prompt": "Sag Hallo Nexi",
  "stream": false
}
```

Ausfuehrung:

- Status: erfolgreich
- Letzter Node: `Ollama Hello`
- Antwort: `Hallo Nexi!`
- Dauer des Ollama-Calls: ca. 8.4 Sekunden

## Wichtige Befehle

n8n-Status:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' ps --filter "name=n8n"
```

Logs:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' logs --tail 100 n8n
```

n8n stoppen:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' stop n8n
```

n8n starten:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' start n8n
```

Workflows auflisten:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' exec n8n n8n list:workflow
```

Alle Workflows exportieren:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' exec n8n n8n export:workflow --all --output=/home/node/.n8n/workflows-export.json
```

## Wichtige Node-Typen fuer spaeter

- Manual Trigger: manueller Start
- Schedule Trigger: zeitgesteuerte Workflows
- Webhook: externe Ereignisse empfangen
- HTTP Request: APIs aufrufen
- Code: kleine JS-Logik
- IF: Bedingungen und Routing
- Set/Edit Fields: Daten strukturieren
- Split Out / Loop Over Items: Listen verarbeiten

## Backup-Strategie

n8n-Daten liegen im Docker-Volume `n8n_data`.

Dieses Volume ist nicht automatisch durch das bisherige Restic-Backup erfasst.

Empfehlung vor echten Workflows:

1. Regelmaessiger Workflow-Export:

```powershell
docker exec n8n n8n export:workflow --all --output=/home/node/.n8n/workflows-export.json
```

2. Export-Datei oder Volume-Snapshot in Restic-Backup aufnehmen.
3. Credentials niemals unverschluesselt exportieren oder teilen.

## Bekannte Warnung

Die Logs enthalten:

`Failed to start Python task runner in internal mode. because Python 3 is missing from this system.`

Bewertung:

- Fuer Phase 1 nicht blockierend.
- JS Task Runner ist registriert.
- Der Hello-World-Testworkflow laeuft.
- Python-Code-Nodes werden spaeter separat bewertet, falls wirklich noetig.

## Datenregel

Bis zur naechsten Phase gilt:

- Keine echten sensiblen Workflows.
- Keine D3/D4-Daten.
- Keine externen Credentials.
- Nur D0-Testdaten.

## Abschluss

Aufgabe 009 ist technisch abgeschlossen.

Minimal-Stack ist damit komplett:

- Ollama
- OpenWebUI
- Qdrant
- n8n

Naechster sinnvoller Schritt: Aufgabe 010 - Video-Analyse-Pipeline starten.
