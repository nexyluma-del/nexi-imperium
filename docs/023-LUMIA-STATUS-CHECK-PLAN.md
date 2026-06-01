# Plan 023 - Lumia Status-Check (Read-Only)

Stand: 2026-06-01 20:35  
Modus: Plan / Read-Only, nichts ausgefuehrt

## Kurzfazit

Lumia ist nicht tot und nicht nur Theorie. Heute wurden aktiv Interface, Wake-Word, Voice-Capture, Voice-Out, Qdrant-Speicherung und lokale Chat-Bruecke getestet. Der Scope blieb nach sichtbaren Dateien im Projekt `C:\Users\nexil\Desktop\KI\lumia\`; `C:\AI\projects\lumia` existiert aktuell nicht. Stufe 1 wirkt funktional, aber noch nicht produktionsreif, weil Ollama/qwen3-Residency, Timeout-Verhalten und Antwortlatenz stabilisiert werden muessen.

## Gepruefte Orte

| Pfad | Befund |
|---|---|
| `C:\Users\nexil\Desktop\KI\lumia` | aktiv, viele neue Dateien/Logs |
| `C:\Users\nexil\Desktop\KI\lumia\logs` | aktiv, Voice-/Wake-/Bridge-Logs |
| `C:\Users\nexil\Desktop\KI\lumia\interface` | aktiv, UI/Status-Dateien |
| `C:\AI\projects\lumia` | existiert nicht |

## Was Lumia heute gemacht hat

Sichtbare Aktivitaeten:

- `Hey Lumia` Wake-Word wurde mehrfach erkannt.
- Double-Clap Trigger wurde erkannt.
- Voice-Aufnahmen wurden geschrieben.
- Whisper-Transkripte wurden akzeptiert oder korrekt verworfen.
- Dialoge wurden an Ollama/qwen3 geschickt.
- Antworten wurden erzeugt, z.B. `Hallo Nexi`, `OK, Nexi`, `Nexi, hier Lumia. Alles klar.`
- Qdrant-Speicherung erfolgte mit frischen `point_id`.
- Voice-Out wurde erzeugt und abgespielt.
- Lokale Interface-Bridge lief auf `http://127.0.0.1:8765`.
- Status-Polls des Interfaces liefen stabil mit HTTP 200.

## Wichtige Dateien/Logs

| Datei | Bedeutung |
|---|---|
| `DIAGNOSE.md` | Diagnose-Ausgabe, zuletzt aktualisiert |
| `logs\lumia.log` | Hauptlog fuer Wake, Whisper, Ollama, Qdrant, TTS |
| `logs\interface-bridge.log` | HTTP-Status und Chat-Bridge |
| `logs\interface-listener.log` | Interface Listener |
| `logs\voice-out\*.wav/mp3` | generierte Sprachausgabe |
| `logs\wake-*.wav` | Wake-Aufnahmen |
| `interface\state.json` / `state.js` | UI-Status |
| `lumia\app.py` | Haupt-App |
| `lumia\interface_bridge.py` | lokale Browser-/Interface-Bruecke |
| `lumia\qdrant_store.py` | Qdrant-Speicherung |
| `lumia\ollama_client.py` | Modellzugriff |

## Build-Stand

| Baustein | Status |
|---|---|
| Venv | vorhanden |
| Wake-Word `Hey Lumia` | funktioniert |
| Double-Clap | funktioniert |
| Whisper large-v3 on demand | funktioniert |
| Empty/Low-Confidence-Abwehr | vorhanden |
| Ollama/qwen3:30b Anbindung | funktioniert, aber empfindlich |
| Qdrant Collection `lumia_conversations` | wird genutzt |
| Voice-Out | funktioniert |
| Interface-Bridge | funktioniert |
| Lokales Dashboard | begonnen |

## Offene Punkte / Risiken

1. **Ollama Residency**
   - Lumia verweigert absichtlich Calls, wenn `qwen3:30b` nicht in `/api/ps` resident ist.
   - Gut fuer Kontrolle, aber fuer Alltag muss ein sauberer Start-/Keepalive-Prozess her.

2. **Ollama Timeout/BUSY**
   - Logs zeigen `Ollama timeout/busy` und einmal `Ollama returned an empty answer`.
   - Braucht Retry/Queue/Statusanzeige, damit Lumia nicht "stumm" wirkt.

3. **Antwortlatenz**
   - Dialoge lagen teils bei ca. 13-38 Sekunden.
   - Fuer Voice ist das noch zu langsam.

4. **Scope-Sicherheit**
   - README sagt: Lumia aendert keine Video-Pipeline, keinen Telegram-Bot, kein Backup.
   - Read-Only-Befund bestaetigt bisher keinen Ausbruch aus `Desktop\KI\lumia`.

5. **Interface**
   - Vision ist stark, aber noch frueh.
   - Status-Dashboard existiert, aber noch nicht finaler Lumia-Look.

## Empfehlung

Lumia nicht stoppen, aber auch nicht zur Haupt-Prioritaet machen. Nach Chief Web sollte Lumia in einem eigenen Stabilisierungspaket weitergehen:

1. qwen3-Residency/Keepalive sauber machen.
2. Queue und Busy-Status einbauen.
3. Voice-Latenz messen und reduzieren.
4. Interface finalisieren.
5. Qdrant/Memo-Anbindung mit Memory-KI abstimmen.

## Entscheidung fuer Nexi

Morgen reicht:

- A: Lumia parken bis Chief Web steht. **Empfohlen.**
- B: 1-2 Stunden Lumia-Stabilisierung direkt einschieben.
- C: Lumia als eigenstaendige Session weiterlaufen lassen, aber Codex fasst nur Ergebnisse zusammen.

