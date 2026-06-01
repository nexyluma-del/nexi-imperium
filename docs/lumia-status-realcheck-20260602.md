# Lumia Status Realcheck 2026-06-02

Status: Read-only Realcheck, keine Aenderungen an Lumia ausgefuehrt.

## Kurzfazit

Lumia ist als lokaler Prototyp aktiv und im richtigen Scope geblieben. Die laufenden Python-Prozesse liegen unter `C:\Users\nexil\Desktop\KI\lumia\.venv\Scripts\python.exe`; ein erwarteter Alternativpfad `C:\AI\projects\lumia` existiert nicht. Wakeword, Double-Clap, lokaler Interface-Bridge-Server, Voice-Out und Qdrant-Speicherung laufen grundsaetzlich. Der Build ist aber noch kein stabiler Produktionsmodus: Whisper produziert/erkennt teils Stille oder Halluzinationen, Ollama hat Busy/Timeout-Phasen, und qwen3:30b erzeugt sichtbare Denktexte.

## Scope-Check

- Hauptordner: `C:\Users\nexil\Desktop\KI\lumia`
- Alternativordner geprueft: `C:\AI\projects\lumia`
- Ergebnis: `C:\AI\projects\lumia` existiert nicht.
- Befund: Die aktiven Lumia-Prozesse und Logs zeigen auf den Desktop-Lumia-Ordner. Kein Hinweis aus diesem Check, dass Lumia ausserhalb ihres erwarteten Scopes gebaut hat.

Hinweis: Das ist ein projektbezogener Realcheck, kein vollstaendiger Forensik-Scan ueber die ganze Festplatte.

## Laufende Komponenten

- Python-Prozesse aktiv aus `C:\Users\nexil\Desktop\KI\lumia\.venv\Scripts\python.exe`
- Interface-Bridge aktiv laut Logs auf `http://127.0.0.1:8765`
- Wakeword-Modell aktiv: `hey_lumia.onnx`
- Erkennung laut Log: `Hey Lumia`, `double_clap`, spaeter auch `strong single clap`
- Voice-Out erzeugt WAV/MP3-Dateien und spielt diese ab
- Qdrant-Speicherung funktioniert: Conversation Points wurden geschrieben

## Heute geaenderte / erzeugte Dateien

Notable Code-/Konfigdateien mit heutigen Aenderungen:

- `C:\Users\nexil\Desktop\KI\lumia\lumia\app.py`
- `C:\Users\nexil\Desktop\KI\lumia\lumia\interface_bridge.py`
- `C:\Users\nexil\Desktop\KI\lumia\lumia\wake.py`
- `C:\Users\nexil\Desktop\KI\lumia\lumia\config.py`
- `C:\Users\nexil\Desktop\KI\lumia\lumia\ollama_client.py`
- `C:\Users\nexil\Desktop\KI\lumia\lumia\qdrant_store.py`
- `C:\Users\nexil\Desktop\KI\lumia\lumia\voice_out.py`
- `C:\Users\nexil\Desktop\KI\lumia\scripts\verify_audio_once.py`
- `C:\Users\nexil\Desktop\KI\lumia\scripts\verify_double_clap_trigger.py`
- `C:\Users\nexil\Desktop\KI\lumia\scripts\mic_live_probe.py`
- `C:\Users\nexil\Desktop\KI\lumia\interface\app.js`
- `C:\Users\nexil\Desktop\KI\lumia\interface\state.json`
- `C:\Users\nexil\Desktop\KI\lumia\interface\state.js`

Viele weitere heutige Dateien sind Logs, Wake-/Command-WAVs, Voice-Out-MP3/WAVs und Browser-QA-Profil-/Cachedateien unter `interface\qa`.

## Was funktioniert

- Wakeword-Loop startet wiederholt sauber.
- `Hey Lumia` wird erkannt.
- Double-Clap wird erkannt.
- Nach Wake-Event wird ein Greeting erzeugt und abgespielt.
- Spracheingaben werden aufgenommen.
- Whisper akzeptiert echte Transkripte und verwirft mehrere leere/unsichere Transkripte.
- Antworten werden ueber TTS erzeugt und abgespielt.
- Qdrant-Insert fuer Gespraechspunkte funktioniert.

## Probleme / offene Punkte

- Whisper erkennt bei Stille teils Texte wie `Vielen Dank.` und verwirft sie erst ueber No-Speech-Pruefung. Das ist gut, aber braucht weitere Haertung.
- Mehrere Aufnahmen waren sehr leise (`rms_dbfs` teils unter -90 dBFS) und wurden zurecht verworfen.
- Ollama hatte Busy/Timeout-Phasen, z.B. bei einem akzeptierten Transcript nach ca. 49 Sekunden.
- qwen3:30b ist resident, qwen2.5:32b ist nicht installiert.
- qwen3:30b zeigt sichtbare Denktexte in Antworten und ist fuer Memory/Lumia ohne Output-Filter noch nicht sauber.
- Latenz ist noch hoch: einzelne komplette Dialoge lagen bei ca. 28-33 Sekunden.

## Build-Stand

Einschaetzung: Stufe 1 Prototyp funktioniert. Lumia kann hoeren, reagieren, sprechen und Erinnerungen speichern. Fuer Alltag/Produktionsbetrieb fehlen noch Modell-/Thinking-Fix, bessere Audio-Gates, stabilere Ollama-Timeout-Behandlung und ein sauberer Start/Stop-Betriebsmodus.

## Empfehlung

Vor weiterer Feature-Arbeit zuerst stabilisieren:

1. Modell-Ausgabe filtern oder Modell wechseln, damit keine Denktexte gesprochen/angezeigt werden.
2. Audio-Gate nachschaerfen: sehr leise Aufnahmen frueher abbrechen.
3. Ollama-Busy sauber behandeln: kurze Rueckmeldung statt langer Stille.
4. QA-Profil/Cache aus Git/Backup-Prio herausnehmen, falls noch nicht ausgeschlossen.
