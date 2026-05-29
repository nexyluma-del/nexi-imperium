# QDRANT-SETUP

Stand: 2026-05-29
Phase: 1 - Lokale KI Minimal-Stack
Aufgabe: 008 - Qdrant Vektor-Datenbank + Embedding-Modell

## Ergebnis

Qdrant laeuft lokal als Docker-Container und ist erreichbar unter:

- API: http://localhost:6333
- Healthcheck: http://localhost:6333/healthz
- Dashboard: http://localhost:6333/dashboard
- gRPC: localhost:6334

Wichtig: Qdrant ist auf dem Windows-Host nur lokal gebunden:

127.0.0.1:6333-6334 -> 6333-6334/tcp

Damit wird Qdrant nicht ins Internet exponiert.

## Installierte Komponenten

Qdrant:

- Container-Name: `qdrant`
- Image: `qdrant/qdrant`
- Version laut Logs: `1.18.1`
- Docker-Volume: `qdrant_storage:/qdrant/storage`
- Restart-Policy: `always`
- Host-Binding: `127.0.0.1`
- Telemetry: deaktiviert mit `QDRANT__TELEMETRY_DISABLED=true`

Ollama Embedding-Modell:

- Modell: `nomic-embed-text:latest`
- Groesse: ca. 274 MB
- Embedding-Dimension im Test: 768

## Startbefehl

Der finale Container wurde mit diesem Setup gestartet:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' run -d `
  --name qdrant `
  -p 127.0.0.1:6333:6333 `
  -p 127.0.0.1:6334:6334 `
  -v qdrant_storage:/qdrant/storage `
  -e QDRANT__TELEMETRY_DISABLED=true `
  --restart always `
  qdrant/qdrant
```

## Lokale Sicherheitsentscheidungen

- Keine Public-URL.
- Kein Port-Forwarding.
- Keine API-Keys in Qdrant gesetzt.
- Keine Produktivdaten geladen.
- Keine D3/D4-Daten geladen.
- Keine zweite Vektor-Datenbank installiert.
- Qdrant-Telemetry deaktiviert.
- Test-Collection nach dem End-to-End-Test geloescht.

Hinweis: Qdrant lauscht innerhalb des Containers auf `0.0.0.0`, Docker veroeffentlicht den Dienst auf dem Windows-Host aber nur auf `127.0.0.1`. Das ist der relevante Schutz nach aussen.

## Funktionstests

Geprueft:

- Docker-Container `qdrant` laeuft.
- `http://localhost:6333/healthz` antwortet mit `healthz check passed`.
- `http://localhost:6333/dashboard` antwortet mit `200 OK`.
- Docker-Volume `qdrant_storage` existiert.
- `nomic-embed-text:latest` ist in Ollama geladen.
- Telemetry-Log meldet: `Telemetry reporting disabled`.
- Collections nach Test: leer.

End-to-End-Test:

- Testtext per Ollama in ein Embedding gewandelt.
- Test-Collection `codex_qdrant_test` angelegt.
- Testpunkt mit D0-Testpayload gespeichert.
- Suche gegen Qdrant ausgefuehrt.
- Treffer erfolgreich zurueckbekommen.
- Test-Collection danach geloescht.

Finaler Test:

- Status: `PASSED`
- Embedding-Dimension: `768`
- Returned ID: `1`
- Score: `0.8114`
- Cleanup: `collection deleted`

## Wichtige Befehle

Qdrant-Status:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' ps --filter "name=qdrant"
```

Logs:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' logs --tail 100 qdrant
```

Healthcheck:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:6333/healthz'
```

Collections anzeigen:

```powershell
Invoke-RestMethod -Uri 'http://localhost:6333/collections'
```

Qdrant stoppen:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' stop qdrant
```

Qdrant starten:

```powershell
$env:PATH = 'C:\Program Files\Docker\Docker\resources\bin;' + $env:PATH
& 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' start qdrant
```

Ollama-Modelle:

```powershell
wsl.exe -d Ubuntu-24.04 -- ollama list
```

## Beispiel: Embedding + Insert + Search

Dieses Beispiel ist nur fuer D0-Testdaten gedacht.

```powershell
$ollamaUrl = 'http://localhost:11434/api/embeddings'
$qdrantUrl = 'http://localhost:6333'
$collection = 'demo_test'
$text = 'Kurzer D0-Testtext fuer Qdrant.'

$embedBody = @{ model = 'nomic-embed-text'; prompt = $text } | ConvertTo-Json
$embed = Invoke-RestMethod -Method Post -Uri $ollamaUrl -ContentType 'application/json' -Body $embedBody
$vector = $embed.embedding

$collectionBody = @{ vectors = @{ size = $vector.Count; distance = 'Cosine' } } | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method Put -Uri "$qdrantUrl/collections/$collection" -ContentType 'application/json' -Body $collectionBody

$pointBody = @{
  points = @(
    @{
      id = 1
      vector = $vector
      payload = @{ source = 'demo'; text = $text; data_class = 'D0-test' }
    }
  )
} | ConvertTo-Json -Depth 20
Invoke-RestMethod -Method Put -Uri "$qdrantUrl/collections/$collection/points?wait=true" -ContentType 'application/json' -Body $pointBody

$searchBody = @{ vector = $vector; limit = 1; with_payload = $true } | ConvertTo-Json -Depth 20
Invoke-RestMethod -Method Post -Uri "$qdrantUrl/collections/$collection/points/search" -ContentType 'application/json' -Body $searchBody

Invoke-RestMethod -Method Delete -Uri "$qdrantUrl/collections/$collection"
```

## Backup-Strategie

Qdrant-Daten liegen im Docker-Volume `qdrant_storage`.

Aktuell sind keine Produktivdaten enthalten. Sobald echte Memory-/RAG-Daten geladen werden, muss vorab ein Backup-Konzept definiert werden:

- Qdrant-Snapshots pro Collection nutzen oder
- Docker-Volume gezielt exportieren und in Restic aufnehmen oder
- spaeter Qdrant-Datenpfad kontrolliert unter `C:\AI` legen, falls das Projekt es verlangt.

Wichtig: Die aktuelle Restic-Strategie sichert Desktop, Documents, Pictures und Videos. Docker-Volumes sind damit nicht automatisch als normale Windows-Ordner abgedeckt.

## Datenregel

Qdrant ist technisch D-neutral. Die Datenklasse entsteht durch den Inhalt.

Bis zur Memory-KI-Phase gilt:

- Keine echten persoenlichen Daten.
- Keine Heilungs-/Business-/Drehbuch-Wissensbestaende.
- Keine Instagram-/YouTube-Transkripte.
- Nur D0-Testdaten.

## Troubleshooting

Wenn das Dashboard nicht laedt:

1. Docker Desktop starten.
2. `docker ps` pruefen.
3. `docker logs --tail 100 qdrant` pruefen.
4. Healthcheck testen: `http://localhost:6333/healthz`.

Wenn Embeddings nicht funktionieren:

1. Ollama-Service pruefen.
2. Modellliste pruefen: `ollama list`.
3. Sicherstellen, dass `nomic-embed-text:latest` vorhanden ist.

Wenn Port 6333 belegt ist:

- Qdrant nicht doppelt starten.
- Erst bestehende Container pruefen.
- Alternative Ports nur mit Doku-Aenderung nutzen.

## Quellenhinweis

Qdrant-Telemetry wurde gemaess offizieller Qdrant-Dokumentation mit `QDRANT__TELEMETRY_DISABLED=true` deaktiviert:

https://qdrant.tech/documentation/guides/usage-statistics/

## Abschluss

Aufgabe 008 ist technisch abgeschlossen.

Naechster sinnvoller Schritt: Aufgabe 009 - n8n als Workflow-Engine, letzter Baustein des lokalen Minimal-Stacks.
