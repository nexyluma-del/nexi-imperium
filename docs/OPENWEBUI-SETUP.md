# OPENWEBUI-SETUP

Stand: 2026-05-29
Phase: 1 - Lokale KI Minimal-Stack
Aufgabe: 007 - OpenWebUI als lokale Chat-Oberflaeche

## Ergebnis

OpenWebUI laeuft lokal als Docker-Container und ist erreichbar unter:

http://localhost:3000

Wichtig: Der Container ist nur lokal gebunden:

127.0.0.1:3000 -> 8080/tcp

Damit wird OpenWebUI nicht ins Internet exponiert.

## Installierte Komponenten

OpenWebUI:

- Container-Name: `open-webui`
- Image: `ghcr.io/open-webui/open-webui:main`
- Version laut Logs: `v0.9.5`
- Docker-Volume: `open-webui:/app/backend/data`
- Restart-Policy: `always`
- Port: `127.0.0.1:3000:8080`

Ollama:

- Distribution: `Ubuntu-24.04`
- Service: `ollama`
- Status beim Abschluss: `active`
- Keep-Alive: `OLLAMA_KEEP_ALIVE=30s`
- Override-Datei: `/etc/systemd/system/ollama.service.d/override.conf`

## OpenWebUI Startbefehl

Der Container wurde mit diesem Setup gestartet:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' run -d `
  --name open-webui `
  -p 127.0.0.1:3000:8080 `
  -v open-webui:/app/backend/data `
  --add-host=host.docker.internal:host-gateway `
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 `
  -e ENABLE_OLLAMA_API=true `
  -e ENABLE_OPENAI_API=false `
  -e ENABLE_OTEL=false `
  --restart always `
  ghcr.io/open-webui/open-webui:main
```

## Lokale Sicherheitsentscheidungen

- Keine Public-URL.
- Kein Port-Forwarding.
- Keine Cloud-API-Keys hinterlegt.
- OpenAI-API in OpenWebUI per Environment deaktiviert: `ENABLE_OPENAI_API=false`.
- OpenWebUI lauscht nur auf `127.0.0.1`.
- Genau ein Admin-User wurde angelegt.
- Admin-Passwort ist in Standard Notes gespeichert.

OpenWebUI setzt im Docker-Image zusaetzlich:

- `SCARF_NO_ANALYTICS=true`
- `DO_NOT_TRACK=true`
- `ANONYMIZED_TELEMETRY=false`

## Modelle

Verfuegbare Ollama-Modelle beim Abschluss:

| Modell | Zweck | Groesse |
|---|---|---:|
| `qwen3:4b` | Daily-Use, schnelle Tests, kurze Chats | 2.5 GB |
| `qwen3:30b` | Hauptmodell fuer schwere Denkaufgaben | 18 GB |

Empfehlung:

- Alltag: `qwen3:4b`
- Strategie, Architektur, lange Texte: `qwen3:30b`

## Funktionstests

Geprueft:

- Docker-Container `open-webui` laeuft `healthy`.
- `http://localhost:3000` liefert `200 OK`.
- OpenWebUI erreicht Ollama ueber `http://host.docker.internal:11434`.
- Modellliste aus OpenWebUI heraus sichtbar:
  - `qwen3:4b`
  - `qwen3:30b`
- Erster UI-Test mit `qwen3:4b` erfolgreich.
- Denkzeit im UI-Test: ca. 12 Sekunden.
- UI sieht sauber aus.
- Denkmodus/Thinking-Anzeige ist in der UI brauchbar geloest.
- `OLLAMA_KEEP_ALIVE=30s` entlaedt Modelle nach kurzer Inaktivitaet wieder aus dem VRAM.

## Wichtige Befehle

Status pruefen:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' ps
```

Logs anzeigen:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' logs --tail 100 open-webui
```

OpenWebUI stoppen:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' stop open-webui
```

OpenWebUI starten:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' start open-webui
```

Ollama-Modelle anzeigen:

```powershell
wsl.exe -d Ubuntu-24.04 -- ollama list
```

Aktiv geladene Ollama-Modelle anzeigen:

```powershell
wsl.exe -d Ubuntu-24.04 -- ollama ps
```

Ollama-Service pruefen:

```powershell
wsl.exe -d Ubuntu-24.04 -- systemctl is-active ollama
```

## Troubleshooting

Wenn `http://localhost:3000` nicht laedt:

1. Docker Desktop starten.
2. Containerstatus pruefen: `docker ps`.
3. Logs pruefen: `docker logs --tail 100 open-webui`.
4. Falls Container gestoppt ist: `docker start open-webui`.

Wenn Modelle in OpenWebUI fehlen:

1. In OpenWebUI Modellliste aktualisieren.
2. Ollama pruefen: `wsl.exe -d Ubuntu-24.04 -- ollama list`.
3. Container-zu-Ollama-Verbindung pruefen:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' exec open-webui python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:11434/api/tags', timeout=10).read().decode()[:1000])"
```

## Reset-Hinweis

OpenWebUI-Daten liegen im Docker-Volume `open-webui`.

Container entfernen wuerde die Daten nicht automatisch loeschen. Ein vollstaendiger Reset wuerde zusaetzlich das Volume entfernen, ist aber nur mit ausdruecklicher Freigabe sinnvoll:

```powershell
docker stop open-webui
docker rm open-webui
docker volume rm open-webui
```

## Abschluss

Aufgabe 007 ist technisch abgeschlossen.

Naechster sinnvoller Schritt: Aufgabe 008 - Qdrant als Vektor-Datenbank fuer RAG/Memory-KI.
