# BACKUP-SYSTEM - Restic lokal auf externer SSD

**Status:** aktiv - Aufgabe 002 abgeschlossen, Aufgabe 010b erweitert am 2026-05-29
**Datenklasse:** D1 intern
**Repository:** `D:\Restic-Backup`
**Restic:** portable Installation unter `C:\Users\nexil\Desktop\KI\tools\restic\restic.exe`

## Ziel

Dieses Backup-System schuetzt Nexis neue KI-Arbeitsstation vor Datenverlust. Es ist lokal, verschluesselt und nutzt die externe Kingston-SSD `D:`.

## Was gesichert wird

Aktuelle Quellen ab Aufgabe 010b:

| Quelle | Zweck |
|---|---|
| `C:\Users\nexil\Desktop` | KI-Ordner, Codex-KI-Ordner, Instagram-Ordner, Desktop-Dateien |
| `C:\Users\nexil\Documents` | Codex-Arbeitsordner und Dokumente |
| `C:\Users\nexil\Pictures` | Bilder, falls vorhanden |
| `C:\Users\nexil\Videos` | Videos, falls vorhanden |
| `C:\AI` | KI-Projekte, Konfigurationen, Skripte, Transkripte und Analyse-Ergebnisse |

Hinweis: Die Instagram-Daten liegen inzwischen getrennt unter `C:\Users\nexil\Desktop\Instagram Videos` und `C:\Users\nexil\Desktop\Instagram Liste`. Beide liegen auf dem Desktop und sind dadurch weiterhin im Backup.

## Excludes

Die Exclude-Datei liegt hier:

```text
D:\Restic-Backup\restic-excludes.txt
```

Ausgeschlossen werden bewusst:

| Ausschluss | Grund |
|---|---|
| `C:\AI\models\` | Modelle sind gross und reproduzierbar |
| `C:\AI\projects\09-video-analyse\models\` | Whisper large-v3 kann neu geladen werden |
| `**\.venv\` | Python-Umgebungen sind reproduzierbar |
| `**\node_modules\` | Node-Abhaengigkeiten sind reproduzierbar |
| `**\__pycache__\`, `**\.cache\`, `**\.huggingface\` | Cache-Dateien sollen das Backup nicht aufblasen |

Wichtig: Projektdateien, Skripte, README-Dateien, Transkripte, Logs und spaetere Analyse-Ergebnisse unter `C:\AI` werden gesichert.

## Was nicht gemacht wird

- Kein Cloud-Backup.
- Keine BitLocker-Aenderung.
- Keine WSL2-Installation.
- Keine vorhandenen Daten werden geloescht oder verschoben.
- Das Restic-Passwort wird nicht im Klartext in Skripten gespeichert.
- Keine Docker-Volumes in diesem Backup. OpenWebUI, n8n und Qdrant folgen separat in Aufgabe 010c.
- Keine grossen KI-Modelle oder reproduzierbaren Cache-/Dependency-Ordner.

## Passwort-Regel

Ohne Restic-Passwort sind alle Backups verloren. Es gibt keine Wiederherstellung ohne Passwort.

Empfohlene Ablage:

1. In Standard Notes als Eintrag `Restic Backup Imperium`.
2. Optional zusaetzlich auf Papier an einem sicheren Ort.
3. Nicht nur als Textdatei auf demselben Laptop.

## Installation

Restic wurde portabel installiert:

```powershell
C:\Users\nexil\Desktop\KI\tools\restic\restic.exe version
```

Verifizierte Version:

```text
restic 0.18.1 compiled with go1.25.1 on windows/amd64
```

## Repository initialisieren

Das Repository liegt auf der externen SSD:

```text
D:\Restic-Backup
```

Initialisierung:

```text
created restic repository 1476d76e31 at D:\Restic-Backup
Repository erfolgreich initialisiert: D:\Restic-Backup
```

Repository-ID:

```text
1476d76e31
```

## Backup ausfuehren

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\nexil\Desktop\KI\scripts\run-backup.ps1
```

Das Skript fragt interaktiv nach dem Restic-Passwort.
Seit Aufgabe 010b nutzt es zusaetzlich die Exclude-Datei `D:\Restic-Backup\restic-excludes.txt`.

## Erster Backup-Lauf

Der erste Backup-Lauf wurde erfolgreich abgeschlossen.

| Feld | Wert |
|---|---|
| Datum | 2026-05-29 |
| Snapshot | `6a94fd33` |
| Verarbeitete Dateien | 3494 |
| Verarbeitete Daten | 29.350 GiB |
| Gespeichert im Repository | 25.861 GiB |
| Dauer | 00:01:11 |
| Log | `C:\Users\nexil\Desktop\KI\logs\backup\backup-2026-05-29_115548.log` |

## Backup-Lauf nach Aufgabe 010b

Der Backup-Scope wurde erfolgreich um `C:\AI` erweitert.

| Feld | Wert |
|---|---|
| Datum | 2026-05-29 |
| Snapshot | `5f2c97ea` |
| Quellen | Desktop, Documents, Pictures, Videos, `C:\AI` |
| Verarbeitete Dateien | 3643 |
| Verarbeitete Daten | 29.352 GiB |
| Neu zum Repository hinzugefuegt | 2.371 MiB |
| Neu gespeichert | 1.836 MiB |
| Dauer | 00:00:18 |
| Exclude-Datei | `D:\Restic-Backup\restic-excludes.txt` |
| Log | `C:\Users\nexil\Desktop\KI\logs\backup\backup-2026-05-29_182512.log` |

Interpretation: Obwohl `C:\AI` hinzugekommen ist, wurde nur sehr wenig neu gespeichert. Das bestaetigt, dass Deduplizierung und Excludes greifen und die grossen reproduzierbaren Modell-/venv-Dateien nicht unnoetig ins Backup laufen.

## Restore-Test ausfuehren

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\nexil\Desktop\KI\scripts\run-restore-test.ps1
```

Das Skript stellt zufaellig bis zu 3 kleine Dateien aus dem letzten Snapshot nach `D:\Restic-Restore-Test` wieder her, vergleicht sie und loescht nur diesen Testordner nach Erfolg.

## Erster Restore-Test

Der erste Restore-Test wurde erfolgreich bestanden.

| Feld | Wert |
|---|---|
| Datum | 2026-05-29 |
| Snapshot | `6a94fd33` |
| Ergebnis | Restore-Test bestanden |
| Testordner | `D:\Restic-Restore-Test` wurde nach Erfolg geloescht |
| Log | `C:\Users\nexil\Desktop\KI\logs\backup\restore-test-2026-05-29_115822.log` |

## Restore-Test nach Aufgabe 010b

Der Restore-Test wurde erfolgreich um eine Pflichtprobe aus `C:\AI` erweitert.

| Feld | Wert |
|---|---|
| Datum | 2026-05-29 |
| Snapshot | `5f2c97ea` |
| Ergebnis | Restore-Test bestanden |
| C:\AI-Pflichtprobe | `/C/AI/imperium-config/.gitignore` |
| Hash-Pruefung | OK: `C:\AI\imperium-config\.gitignore` |
| Weitere Stichproben | 2 Dateien aus `C:\Users\nexil\Desktop\Instagram Videos` |
| Testordner | `D:\Restic-Restore-Test` wurde nach Erfolg geloescht |
| Log | `C:\Users\nexil\Desktop\KI\logs\backup\restore-test-2026-05-29_182612.log` |

Damit ist nachgewiesen, dass Dateien aus `C:\AI` im Backup enthalten und wiederherstellbar sind.

## Logs

Logs liegen unter:

```text
C:\Users\nexil\Desktop\KI\logs\backup
```

## Empfohlener Rhythmus

- Backup: taeglich oder nach jeder groesseren Aenderung.
- Restore-Test: monatlich.
- Vor WSL2, BitLocker-Aenderungen oder grosser Tool-Installation: immer vorher Backup + Restore-Test.

## Wenn das Passwort vergessen wird

Dann sind die Backups verloren. Restic ist bewusst so gebaut: sicher heisst, dass niemand ohne Passwort an die Daten kommt.
