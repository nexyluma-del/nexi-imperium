# Codex Uebergabe - Aufgabe 010c Docker-Volumes ins Restic-Backup

Stand: 2026-05-30 21:08

## Status

Aufgabe 010c ist technisch umgesetzt und die Export-/Restore-Strecke ist getestet. Live-Container wurden nicht gestoppt. Ollama-Modelle werden weiterhin nicht gesichert.

## Neue/aktualisierte Dateien

- `C:\Users\nexil\Desktop\KI\scripts\export-qdrant-snapshot.ps1`
- `C:\Users\nexil\Desktop\KI\scripts\export-n8n-workflows.ps1`
- `C:\Users\nexil\Desktop\KI\scripts\export-openwebui-db.ps1`
- `C:\Users\nexil\Desktop\KI\scripts\test-docker-volume-restore.ps1`
- `C:\Users\nexil\Desktop\KI\scripts\run-backup.ps1`
- `C:\Users\nexil\Desktop\KI\BACKUP-SYSTEM.md`

## Was jetzt gesichert wird

`run-backup.ps1` erzeugt vor dem Restic-Lauf automatisch Exports nach `D:\Restic-Sources`:

- Qdrant: offizieller Snapshot fuer `video_knowledge`
- n8n: Workflows, nicht entschluesselte Credentials, plus `n8n-volume.tgz`
- OpenWebUI: konsistente SQLite-Kopie `webui.db` plus leichtes Daten-Tar

Danach nimmt Restic `D:\Restic-Sources` als zusaetzliche Quelle mit.

## Tests

- Einzel-Export Qdrant: OK
- Einzel-Export n8n: OK, 3 Workflows, keine Credentials vorhanden
- Einzel-Export OpenWebUI: OK
- `run-backup.ps1 -ExportOnly`: OK
- Restore-Test: OK
  - Qdrant Snapshot in temporaerem Container wiederhergestellt: `video_knowledge`, 54 Punkte
  - n8n Volume-Tar in temporaeres Volume restored, CLI konnte 3 Workflows lesen
  - OpenWebUI SQLite-Dump gelesen, Tabellenprobe OK

Restore-Test Ergebnis:

`D:\Restic-Restore-Test\docker-volumes-2026-05-30_210508\restore-test-result.json`

## Offener Punkt

Der vollstaendige Restic-Snapshot nach 010c wurde noch nicht gestartet, weil das Restic-Passwort bewusst nicht im Chat oder in Skripten liegt. Beim naechsten manuellen Lauf von `run-backup.ps1` fragt das Skript nach dem Passwort und sichert dann `D:\Restic-Sources` mit.

Scheduler ist aus demselben Grund noch nicht aktiviert: Ein echter unbeaufsichtigter Task braucht eine Entscheidung, wie das Restic-Passwort sicher bereitgestellt wird.

## Naechster Vorschlag

Weiter mit Aufgabe 017: OpenWebUI mit Qdrant verknuepfen, damit Nexi direkt im Chat mit dem gespeicherten Video-Wissen sprechen kann.
