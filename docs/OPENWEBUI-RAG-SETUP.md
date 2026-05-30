# OpenWebUI RAG Setup

Stand: 2026-05-30

## Status

OpenWebUI ist mit Qdrant verbunden und nutzt lokale Ollama-Embeddings:

- Vector-DB: `qdrant`
- Qdrant URL im Container: `http://host.docker.internal:6333`
- Embedding Engine: `ollama`
- Embedding Modell: `nomic-embed-text`
- OpenWebUI URL: `http://localhost:3000`

## Architektur

`video_knowledge` bleibt der Master-Wissensspeicher fuer die Video-Pipeline. Fuer OpenWebUI wird daraus eine kompatible RAG-Spiegelung erzeugt:

| Quelle | Ziel |
|---|---|
| Qdrant `video_knowledge` | Qdrant `open-webui_knowledge` |
| Payload aus Video-Pipeline | OpenWebUI Payload `text` + `metadata` |
| Themen/Kategorien | OpenWebUI Knowledge-Bases pro Kategorie |

Sofinello ist nicht enthalten. Sofinello bekommt spaeter eine separate Collection `sofinello_knowledge` und einen eigenen Modus.

## Knowledge-Bases in OpenWebUI

Aktuell angelegt:

- `Nexi Video Knowledge - Alle Kategorien`
- `Nexi Video Knowledge - IT-NEWS`
- `Nexi Video Knowledge - IT-HACKING-SICHERHEIT`
- `Nexi Video Knowledge - KI-IT`
- `Nexi Video Knowledge - NEUHEITEN-PRODUKTE`
- `Nexi Video Knowledge - IT`
- `Nexi Video Knowledge - Finanzen`
- weitere kleinere Test-/Kategorie-Bases

Kategorie-Filter funktionieren praktisch ueber die Auswahl der jeweiligen Knowledge-Base. Fuer alles zusammen nutzt du `Alle Kategorien`.

## Nutzung in OpenWebUI

1. Browser: `http://localhost:3000`
2. Modell: `qwen3:30b` oder fuer schnelle Tests `qwen3:4b`
3. Im Chat eine Knowledge-Base hinzufuegen/auswaehlen, z.B. `Nexi Video Knowledge - IT-HACKING-SICHERHEIT`
4. Frage stellen, z.B.:

```text
Was wurde in den IT-Sicherheits-Videos zu Tools gesagt? Nenne Quellen.
```

## Sync nach neuen Analysen

Nach neuen Video-/Bild-/Local-Analysen:

```bash
cd /mnt/c/AI/projects/09-video-analyse
.venv/bin/python scripts/sync_openwebui_qdrant.py --manifest /mnt/c/AI/projects/09-video-analyse/openwebui-rag-manifest.json
```

Danach Knowledge-Liste in OpenWebUI aktualisieren:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\nexil\Desktop\KI\scripts\configure-openwebui-qdrant.ps1 -ManifestPath C:\AI\projects\09-video-analyse\openwebui-rag-manifest.json -SkipContainerRecreate
```

## Test

Technischer Test:

```bash
cd /mnt/c/AI/projects/09-video-analyse
.venv/bin/python scripts/test_openwebui_rag_query.py
```

Ergebnis am 2026-05-30:

- OpenWebUI sieht `nexi-video-knowledge`: 54 Punkte
- OpenWebUI sieht `nexi-video-knowledge-it-news`: 15 Punkte
- Testfrage zu IT-Sicherheits-Tools holte 4 echte Quellen aus Qdrant
- Lokale qwen3:4b-Antwort wurde aus diesen Quellen erzeugt

## Wartung

Wenn OpenWebUI neu erstellt werden muss, diese Konfiguration beibehalten:

```text
VECTOR_DB=qdrant
QDRANT_URI=http://host.docker.internal:6333
QDRANT_COLLECTION_PREFIX=open-webui
ENABLE_QDRANT_MULTITENANCY_MODE=true
RAG_EMBEDDING_ENGINE=ollama
RAG_OLLAMA_BASE_URL=http://host.docker.internal:11434
RAG_EMBEDDING_MODEL=nomic-embed-text
```
