# OLLAMA-SETUP

Status: abgeschlossen
Datum: 2026-05-29
Phase: 1 - Lokale KI Minimal-Stack, Schritt 1

## 1. Ergebnis

Ollama laeuft lokal in WSL2/Ubuntu und nutzt die RTX 5090 Laptop GPU.

Erledigt:
- Ollama in Ubuntu 24.04 installiert.
- Ollama-Service ist aktiv und automatisch aktiviert.
- Modell `qwen3:30b` heruntergeladen.
- Erstes lokales Gespraech erfolgreich getestet.
- GPU-Nutzung verifiziert.
- Keine Cloud-API-Keys eingerichtet.
- Kein OpenWebUI installiert.
- Keine zweite LLM-Engine installiert.

## 2. System

WSL-Distribution:

```text
Ubuntu-24.04
```

Ollama:

```text
ollama version is 0.24.0
```

Service:

```text
ollama.service: active (running)
enabled
API: http://127.0.0.1:11434
```

Installationshinweis:
- Der offizielle Installer benoetigte das Ubuntu-Paket `zstd`.
- `zstd` wurde installiert.

## 3. Modell

Startmodell:

```text
qwen3:30b
```

Ollama-Liste:

```text
NAME         ID              SIZE     MODIFIED
qwen3:30b    ad815644918f    18 GB    2026-05-29
```

Modellinformationen:

```text
architecture:     qwen3moe
parameters:       30.5B
context length:   262144
embedding length: 2048
quantization:     Q4_K_M
capabilities:     completion, tools, thinking
```

Aktive Sitzung laut `ollama ps`:

```text
qwen3:30b    21 GB    100% GPU    CONTEXT 32768
```

Hinweis:
- Das Modell kann laut Modellinfo bis `262144` Kontext.
- Die aktive Ollama-Session lief mit Standard-Kontext `32768`.
- Groessere Kontextwerte koennen spaeter gezielt konfiguriert werden.

## 4. Speicherort

Ollama verwaltet Modelle selbst.

Modellspeicher in Ubuntu:

```text
/usr/share/ollama/.ollama/models
```

Aktuelle Groesse:

```text
18G
```

Wichtig:
- Modelle nicht manuell nach `C:\AI\models` verschieben.
- `C:\AI\models` bleibt fuer spaetere strukturierte Modell-/Tool-Entscheidungen reserviert.

## 5. GPU-Test

`ollama ps`:

```text
qwen3:30b    21 GB    100% GPU    CONTEXT 32768
```

`nvidia-smi` nach Modelltest:

```text
NVIDIA GeForce RTX 5090 Laptop GPU
Driver Version: 596.49
CUDA Version: 13.2
VRAM: 23634 MiB / 24463 MiB
GPU-Util: 4% nach abgeschlossener Generation
```

Bewertung:
- Ollama nutzt die GPU.
- `qwen3:30b` passt in den VRAM, aber sehr knapp.
- Waehrend das Modell geladen ist, bleibt wenig VRAM fuer parallele schwere GPU-Tasks.

## 6. Erste lokale Antwort

Testbefehl:

```bash
ollama run --verbose qwen3:30b "Antworte auf Deutsch in genau 2 kurzen Saetzen. Sage Nexi, dass seine erste lokale KI jetzt laeuft und wofuer sie als Startpunkt dient."
```

Bereinigte Antwort:

```text
Nexi, deine erste lokale KI laeuft jetzt.
Sie dient als Startpunkt fuer zukuenftige Entwicklungen.
```

Hinweis:
- `qwen3:30b` besitzt eine `thinking`-Faehigkeit.
- Im CLI-Test gab das Modell trotz `/no_think` kurz Denktext aus.
- Das ist kein Installationsfehler, sondern eine Modelleigenschaft.
- Fuer produktive Nutzung wird spaeter in OpenWebUI ein sauberer System-Prompt bzw. UI-Workflow vorbereitet.

## 7. Performance

Erster Test mit kaltem Modell:

```text
total duration:       47.98s
load duration:        38.63s
prompt eval rate:     491.52 tokens/s
eval rate:            112.89 tokens/s
```

Zweiter Test mit geladenem Modell:

```text
total duration:       1.27s
load duration:        63ms
prompt eval rate:     1134.31 tokens/s
eval rate:            150.46 tokens/s
```

Bewertung:
- Erster Lauf braucht Zeit, weil das Modell in VRAM geladen wird.
- Danach reagiert es sehr schnell.
- `qwen3:30b` ist fuer den Start stark und passend fuer Memory-/Agent-Visionen, aber VRAM-intensiv.

## 8. Wichtige Befehle

Ubuntu starten:

```powershell
wsl.exe -d Ubuntu-24.04
```

Ollama-Version:

```bash
ollama --version
```

Service pruefen:

```bash
systemctl status ollama
systemctl is-active ollama
systemctl is-enabled ollama
```

Service starten/stoppen:

```bash
sudo systemctl start ollama
sudo systemctl stop ollama
sudo systemctl restart ollama
```

Modelle anzeigen:

```bash
ollama list
ollama ps
```

Modell starten:

```bash
ollama run qwen3:30b
```

Einmalige Prompt-Ausfuehrung:

```bash
ollama run qwen3:30b "Schreibe eine kurze Antwort auf Deutsch."
```

Modell herunterladen:

```bash
ollama pull qwen3:30b
```

Modell entfernen:

```bash
ollama rm qwen3:30b
```

GPU pruefen:

```bash
nvidia-smi
```

API pruefen:

```bash
curl http://127.0.0.1:11434/api/version
```

## 9. Notfall / Reset

Ollama stoppen:

```bash
sudo systemctl stop ollama
```

Modell entfernen:

```bash
ollama rm qwen3:30b
```

Ollama-Service deaktivieren:

```bash
sudo systemctl disable ollama
```

Wichtig:
- Vor groesseren Reset-Schritten erst Backup-Status pruefen.
- Keine Modellordner manuell loeschen, solange `ollama rm` funktioniert.

## 10. Offene Punkte

- [x] Ollama in WSL2 installiert.
- [x] Ollama-Service aktiv.
- [x] Ollama-Service enabled.
- [x] `qwen3:30b` geladen.
- [x] Erste lokale Antwort erzeugt.
- [x] GPU-Nutzung verifiziert.
- [x] Performance dokumentiert.
- [x] Keine Cloud-API-Keys eingerichtet.
- [x] Kein OpenWebUI installiert.
- [x] Keine zweite LLM-Engine installiert.

## 11. Naechster Schritt

Empfohlene Aufgabe 007:
- OpenWebUI als lokale Chat-Oberflaeche
- Verbindung zu Ollama
- Saubere System-Prompts fuer no-think/Antwortstil
- Erste lokale KI-Bedienoberflaeche im Browser
