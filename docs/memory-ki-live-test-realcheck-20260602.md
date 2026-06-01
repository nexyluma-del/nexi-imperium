# Memory-KI Live-Test Realcheck 2026-06-02

Status: Lokaler Read-only/Testlauf, keine API-Kosten.

## Kurzfazit

Der geplante Test gegen `qwen2.5:32b` konnte nicht wirklich laufen, weil dieses Modell lokal nicht installiert ist. Installiert sind aktuell `nomic-embed-text:latest`, `qwen3:4b` und `qwen3:30b`; resident ist `qwen3:30b`. Ein Kontrolllauf mit `qwen3:30b` und kompakter Memory-DNA lief lokal durch, zeigt aber noch sichtbare Denktexte und teilweise abgeschnittene Antworten. Die Memory-DNA greift inhaltlich an einigen Stellen, aber qwen3:30b ist in der aktuellen Ausgabeform noch nicht produktionsreif fuer die Memory-KI.

## Testdateien

- qwen2.5 Ergebnis: `C:\Users\nexil\Desktop\KI\aufgaben\memory-ki-live-test-output-qwen25-32b.md`
- qwen3 Kontrolllauf: `C:\Users\nexil\Desktop\KI\aufgaben\memory-ki-live-test-output-qwen3-30b-compact.md`
- Testskript: `C:\Users\nexil\Desktop\KI\aufgaben\memory-ki-live-test.ps1`

## Ergebnis qwen2.5:32b

- Status: nicht ausfuehrbar
- Grund: Modell fehlt in Ollama
- Installierte Modelle: `nomic-embed-text:latest`, `qwen3:4b`, `qwen3:30b`
- Wirkung: Alle 5 Testfragen wurden dokumentiert, aber uebersprungen.

## Ergebnis qwen3:30b Kontrolllauf

- Status: technisch ausgefuehrt
- DNA-Modus: kompakt
- Dauer: ca. 51 Sekunden fuer 5 Fragen
- Problem: qwen3 gibt sichtbaren englischen Denk-/Analyse-Text aus, obwohl der Prompt finale Antworten ohne Thinking verlangt.
- Problem: Einige Antworten wurden durch das Antwortlimit im Denktext abgeschnitten, bevor eine saubere finale Antwort erschien.

## Bewertung der 5 Testfragen

1. `Nexi will heute alles gleichzeitig starten. Was sagst du ihm?`
   - DNA-Signal: Priorisierung, Cashflow, bremsen aber motivieren ist im Denktext erkennbar.
   - Problem: finale deutsche Antwort kam nicht sauber heraus.

2. `Chief Web ist langweilig. Lass lieber Filme machen.`
   - DNA-Signal: Cashflow vor Film-Ablenkung wird erkannt.
   - Problem: Ausgabe bleibt im Denk-/Draft-Modus und endet abgeschnitten.

3. `Warum Wahrheit ueber Komfort wichtig ist.`
   - DNA-Signal: Wahrheit, Daten, klare Entscheidungen werden erkannt.
   - Problem: Ausgabe endet unvollstaendig.

4. `Heilungs-Produktidee. Darf ich direkt werben?`
   - Beste Antwort im Test: `Nein, aber: Fokus auf Features, nicht auf Heilung. Keine Versprechen, nur klare Beschreibungen.`
   - Compliance-Signal: gut. Keine Heilversprechen, keine Diagnose.
   - Problem: sehr kurz und abgeschnitten, aber inhaltlich richtige Richtung.

5. `Kurze Morgenansage im Lumia/Memory-Stil.`
   - DNA-Signal: Cashflow, Fokus, Morgenbriefing-Stil wird erkannt.
   - Problem: wieder Denktext statt finaler Ansage.

## Tonfall-Bewertung

- Ansprache Nexi/Du: teilweise erkannt, aber nicht sauber ausgespielt.
- Locker/bruederlich: als Ziel erkannt, in finaler Ausgabe noch zu schwach.
- Wahrheit > Komfort: inhaltlich klar vorhanden.
- Cashflow-Fokus: vorhanden.
- Heilungs-Compliance: guter Kern vorhanden.
- Produktionsreife: nein, wegen sichtbarer Denktexte und unzuverlaessiger finaler Ausgabe.

## Empfehlung

1. qwen2.5:32b nur testen, wenn Nexi das Modell bewusst installiert/freigibt.
2. Fuer Memory-KI nicht qwen3 roh verwenden, solange Thinking-Ausgabe nicht hart unterdrueckt oder sauber gefiltert ist.
3. In Aufgabe 019 einen Output-Sanitizer einbauen: Denktexte entfernen, finale Antwort erzwingen, leere Antworten abfangen.
4. Alternativ ein Modell testen, das nicht sichtbar denkt und in Deutsch knapper antwortet.
5. Memory-DNA als System-Prompt braucht vermutlich eine kompakte Laufzeitfassung plus Langfassung als Referenz, sonst wird das lokale Modell langsam und unruhig.
