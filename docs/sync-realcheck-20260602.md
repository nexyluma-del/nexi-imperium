# Sync Realcheck 2026-06-02

## Erledigt

1. Lumia-Status-Check ausgefuehrt.
   - Report: `C:\Users\nexil\Desktop\KI\sync\lumia-status-realcheck-20260602.md`

2. Memory-KI Live-Test ausgefuehrt/dokumentiert.
   - qwen2.5:32b fehlt lokal, daher sauber als nicht ausfuehrbar dokumentiert.
   - qwen3:30b Kontrolllauf mit kompakter DNA ausgefuehrt.
   - Report: `C:\Users\nexil\Desktop\KI\sync\memory-ki-live-test-realcheck-20260602.md`

3. _unsortiert-Wahrscheinlichkeit aus Run-001 und Run-002 geschaetzt.
   - Ergebnis: 0.79 % _unsortiert, unter Warnschwelle.
   - Report: `C:\Users\nexil\Desktop\KI\sync\unsortiert-risk-realcheck-20260602.md`

## Wichtigste Befunde

- Lumia lebt: Wakeword, Double-Clap, Voice-Out, Qdrant-Speicherung und Interface-Bridge funktionieren.
- Lumia ist noch Prototyp: Audio-Gates, Ollama-Busy und qwen3-Denktexte muessen gehaertet werden.
- Memory-KI: qwen2.5:32b ist nicht installiert; qwen3:30b ist als Rohmodell fuer Memory wegen sichtbarer Denktexte noch nicht sauber.
- _unsortiert-Risiko liegt aktuell unter 5 %, aber Stufe 3 sollte nach 100/300 Videos erneut messen.

## Naechste sinnvolle Entscheidungen fuer Nexi

1. Soll qwen2.5:32b installiert werden oder testen wir ein anderes lokales Memory-Modell?
2. Soll qwen3:30b weiter fuer Wissensfragen bleiben, aber Memory-KI ein anderes Modell bekommen?
3. Soll die `KIFilme -> 07-FILME` Ordnerregel vor Stufe 3 noch aufgenommen werden?
