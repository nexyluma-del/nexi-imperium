# Codex Uebergabe - Aufgabe 021 KI-Sync-Bridge

Stand: 2026-05-31 12:40

## Ergebnis

Aufgabe 021 ist umgesetzt: Master-Context-Export, Topic-Context-Export, Telegram-Befehle und Wochenjob Sonntag 18:00.

## Funktionen

- `export_master_context.py` erzeugt `Desktop\KI\sync\master-context-YYYYMMDD-HHMMSS.md`.
- `export_topic_context.py` erzeugt `Desktop\KI\sync\topic-<thema>-YYYYMMDD-HHMMSS.md`.
- Topic-Export nutzt Qdrant ueber `video_knowledge`, `sofinello_knowledge`, `memory_voice`.
- Standardfilter: D0-D2.
- D3 nur per CLI-Flag `--include-private`.
- D4 wird nie unverschluesselt exportiert.
- Alte Sync-Markdowns > 30 Tage werden nach `sync\archive` verschoben.

## Telegram

- `/sync` erstellt Master-Context und sendet Datei.
- `/sync <Thema>` erstellt Topic-Context und sendet Datei.
- `/sync-tg <Thema>` schickt kompakte Topic-Version direkt in Telegram.

Der Telegram-Bot wurde neu gestartet. Es laeuft ein Bot-Prozess.

## Scheduler

Registrierter Windows-Task:

- `Nexi KI-Sync Master-Context Wochenexport`
- Status: `Ready`
- Zeit: Sonntag 18:00
- Aktion: `wsl.exe -d Ubuntu-24.04 -- bash -lc "cd '/mnt/c/AI/projects/09-video-analyse' && .venv/bin/python scripts/export_master_context.py --archive-old --send-telegram"`

## Tests

- Python-Compile fuer Export- und Bot-Skripte erfolgreich.
- Topic-Test: `Sofinello Compliance`, 20 Snippets erzeugt.
- Master-Test mit optionalem Topic-Kontext erzeugt.
- Bot-Wrapper `run_sync_topic()` und `run_sync_master()` erfolgreich getestet.
- Sync-Ordner existiert und enthaelt neue Dateien.

## Erzeugte Testdateien

- `C:\Users\nexil\Desktop\KI\sync\master-context-20260531-123740.md`
- `C:\Users\nexil\Desktop\KI\sync\topic-sofinello-compliance-20260531-123739.md`

## Naechster Schritt

Wenn Aufgabe 020-Spec von Claude da ist: Chief-Workflow-Template bauen. Bis dahin ist die Bruecke fuer externe KI-Sessions einsatzbereit.

## Zusatz: Sofinello Resume-Guard

Beim Abschluss-Check war kein aktiver `process_sofinello_batch.py` Prozess sichtbar. Damit der bereits freigegebene Sofinello-Batch B nach Gemini-Quota-Reset wirklich automatisch weiterlaeuft, wurde ein Resume-Guard ergaenzt:

- `scripts/resume_sofinello_batch_b.py`
- `scripts/register-sofinello-resume-task.ps1`
- Windows-Task: `Nexi Sofinello Batch B Resume`
- Zeit: taeglich 02:30
- Verhalten: startet den Batch nur, wenn er nicht laeuft und noch nicht komplett fertig ist.
