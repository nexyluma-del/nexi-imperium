# Codex Uebergabe - Aufgabe 017 OpenWebUI mit Qdrant

Stand: 2026-05-30 21:23

## Status

Aufgabe 017 ist umgesetzt und getestet. OpenWebUI laeuft wieder gesund unter `http://localhost:3000` und ist auf Qdrant + lokale Ollama-Embeddings konfiguriert.

## Technische Umsetzung

- OpenWebUI neu erstellt mit:
  - `VECTOR_DB=qdrant`
  - `QDRANT_URI=http://host.docker.internal:6333`
  - `RAG_EMBEDDING_ENGINE=ollama`
  - `RAG_EMBEDDING_MODEL=nomic-embed-text`
- `video_knowledge` bleibt Master-Collection.
- OpenWebUI bekommt eine kompatible Spiegelung in `open-webui_knowledge`.
- Knowledge-Tenants:
  - `nexi-video-knowledge` = alle Kategorien, 54 Punkte
  - `nexi-video-knowledge-it-news` = 15 Punkte
  - plus Kategorie-Tenants fuer IT, IT-HACKING-SICHERHEIT, KI-IT, Finanzen usw.
- Sofinello ist nicht enthalten.

## Neue Dateien

- `C:\AI\projects\09-video-analyse\scripts\sync_openwebui_qdrant.py`
- `C:\AI\projects\09-video-analyse\scripts\test_openwebui_rag_query.py`
- `C:\Users\nexil\Desktop\KI\scripts\configure-openwebui-qdrant.ps1`
- `C:\Users\nexil\Desktop\KI\OPENWEBUI-RAG-SETUP.md`

## Tests

- OpenWebUI Container: healthy
- OpenWebUI Web: HTTP 200
- OpenWebUI Config im Container: `qdrant`, `ollama`, `nomic-embed-text`
- OpenWebUI Vector Client:
  - `nexi-video-knowledge`: vorhanden, 54 Punkte
  - `nexi-video-knowledge-it-news`: vorhanden, 15 Punkte
- Testfrage:
  - Frage: `Was wurde in den IT-Sicherheits-Videos zu Tools gesagt?`
  - Retrieval: 4 echte Quellen aus `IT-HACKING-SICHERHEIT`
  - Antwort: lokal mit `qwen3:4b` aus den Quellen generiert

## Nutzung

In OpenWebUI eine Knowledge-Base auswaehlen, z.B. `Nexi Video Knowledge - IT-HACKING-SICHERHEIT`, dann mit `qwen3:30b` oder `qwen3:4b` fragen.

## Naechster Vorschlag

Weiter mit Aufgabe 014: Telegram-Bot fuer Status und Push-Benachrichtigungen vom Handy.
