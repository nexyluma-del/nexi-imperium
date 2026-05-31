# Codex Uebergabe 022a - OpenWebUI RAG Aktivierung

Stand: 2026-05-31

## Kurzstatus

022a ist erfolgreich abgeschlossen.

OpenWebUI hat jetzt ein eigenes Default-Wissensmodell:

- `nexi-rag-qwen3-30b`
- basiert auf `qwen3:30b`
- Knowledge-Base `nexi-video-knowledge` ist direkt am Modell hinterlegt
- neue Chats nutzen dieses Modell standardmaessig
- Thinking-Tags sind als separater Reasoning-Bereich konfiguriert

## Was geaendert wurde

1. OpenWebUI-Datenbank im Container gesichert.
2. Custom Model `nexi-rag-qwen3-30b` in OpenWebUI angelegt.
3. Knowledge-Base `nexi-video-knowledge` direkt im Model-Meta hinterlegt.
4. `ui.default_models` und `ui.default_pinned_models` auf das neue Modell gesetzt.
5. Qdrant-Spiegel fuer OpenWebUI aktualisiert.
6. OpenWebUI neu gestartet.
7. Drei RAG-Fragen gegen Qdrant + `qwen3:30b` getestet.

## Testergebnis

Pflicht-Test bestanden.

- Frage 1: KI-Tools und lokale KI-Setups -> Antwort mit Quellen
- Frage 2: IT-/Sicherheits-Videos -> Antwort mit Quellen
- Frage 3: Finanz-/Business-/Produktideen -> Antwort mit Quellen

Reports:

- `C:\AI\projects\09-video-analyse\analysis\openwebui-rag\openwebui-rag-test-20260531-022a.json`
- `C:\AI\projects\09-video-analyse\analysis\openwebui-rag\openwebui-rag-test-20260531-022a.md`

## Kosten

Keine API-Kosten. Der Test lief lokal ueber Ollama + Qdrant.

## Hinweis

Die Knowledge-Base ist fuer neue Chats nicht mehr manuell notwendig, weil sie direkt am Default-Modell haengt.
