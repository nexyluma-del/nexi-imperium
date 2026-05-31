# Sanity-Check 022c

Stand: 2026-05-31 13:41

## Ergebnis

Status: gruen mit einem bekannten Hinweis.

Die Kernplattform laeuft:

- Docker-Dienste laufen.
- HTTP-Endpunkte antworten.
- Qdrant enthaelt Wissen.
- OpenWebUI nutzt das Default-RAG-Modell.
- Telegram-Bot laeuft.
- Scheduler sind bereit.
- Batch-Dry-Run laeuft ohne Pipelinefehler.
- Git-Repo war vor dem Report sauber.

## Dienste

Docker:

- `open-webui`: healthy, Port `127.0.0.1:3000`
- `n8n`: up, Port `127.0.0.1:5678`
- `qdrant`: up, Ports `127.0.0.1:6333-6334`

HTTP:

- Ollama `http://127.0.0.1:11434/api/tags`: 200
- Qdrant `http://127.0.0.1:6333/collections`: 200
- OpenWebUI `http://127.0.0.1:3000/health`: 200
- n8n `http://127.0.0.1:5678/healthz`: 200

## Lokale Modelle

- `qwen3:30b`
- `qwen3:4b`
- `nomic-embed-text`

## Qdrant

Collections:

- `video_knowledge`: 61 Punkte
- `open-webui_knowledge`: 122 Punkte
- `sofinello_knowledge`: 200 Punkte
- `memory_voice`: 0 Punkte

Hinweis: `memory_voice` ist leer, solange noch keine Voice-Notizen dauerhaft eingespielt wurden.

## OpenWebUI-RAG

Konfiguration:

- Modell-ID: `nexi-rag-qwen3-30b`
- Basis: `qwen3:30b`
- Knowledge: `nexi-video-knowledge`
- Default-Modell: `nexi-rag-qwen3-30b`
- Thinking-Tags: `<think>` / `</think>`

RAG-Test:

- `C:\AI\projects\09-video-analyse\analysis\openwebui-rag\openwebui-rag-test-20260531-022a.md`
- drei Fragen erfolgreich mit Quellen beantwortet

## Telegram

Bot-Prozess:

- `scripts/telegram_bot.py`
- PID zum Checkzeitpunkt: `154050`

Telegram-Statusskript:

- Dienste: Ollama, Qdrant, OpenWebUI, n8n = true
- Failed Videos: 9
- Letzte Analyse: OpenWebUI-RAG-Test vom 2026-05-31

## Scheduler

Alle Nexi-Scheduler stehen auf `Ready`:

- `Nexi KI-Sync Master-Context Wochenexport`
- `Nexi Memory-KI KI-PUSH Wochen-Scan`
- `Nexi Memory-KI Mittagscheck`
- `Nexi Memory-KI Morgenbriefing`
- `Nexi Memory-KI Tagesabschluss`
- `Nexi Sofinello Batch B Resume`
- `Nexi Voice Memory Daily Review`
- `Nexi Voice Memory Weekly Review`

## Pipelines

Batch-Dry-Run mit existierender Themen-Datei:

- Topic: `IT`
- Datei: `C:\Users\nexil\Desktop\Instagram Liste\IT.md`
- Ergebnis: ok
- Pending: 0
- Kosten: 0.0

Memory-KI Schnelltest:

- Modell: `qwen3:4b`
- Ergebnis: ok
- Antwort wurde lokal erzeugt

KI-Sync Export:

- Ergebnis: ok
- Export: `C:\Users\nexil\Desktop\KI\sync\master-context-20260531-134016.md`

## Sofinello

Status:

- Gesamt: 722 Videos
- Verarbeitet: 197
- Fehler: 9
- Kosten bisher: 3.735829 USD
- Complete: false
- Aktuell laufender Batch-Prozess: nein

Bekannter Hinweis:

Der Sofinello-Batch war wegen Gemini-Quota/429 unterbrochen. Der Scheduler `Nexi Sofinello Batch B Resume` ist Ready. Dry-run sagt: Resume wuerde starten. Manuell wurde im Sanity-Check nicht gestartet, weil das Cloud-Kosten ausloesen kann.

## Backup

Letzte sichtbare Logs:

- `backup-2026-05-30_205634.log`
- `restore-test-2026-05-29_182612.log`
- `backup-2026-05-29_182512.log`

Restic-Backup und Restore-Test waren in Phase 0 erfolgreich. Fuer einen neuen echten Backup-Lauf wird weiterhin das gespeicherte Restic-Passwort benoetigt.

## Fazit

Die Plattform ist arbeitsbereit. Offene Beobachtung bleibt der Sofinello-Resume, der planmaessig weiterlaufen soll, sobald Quota und Scheduler greifen.
