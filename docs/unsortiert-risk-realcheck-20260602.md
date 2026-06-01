# _unsortiert Risiko Realcheck 2026-06-02

Status: Read-only Auswertung aus vorhandenen Run-Manifesten.

## Datenbasis

- `run-001-validation`: 50 Manifest-Eintraege
- `run-002-it-stress-200`: 202 Manifest-Eintraege
- Gesamt ausgewertet: 252 Manifest-Eintraege

Hinweis: Run-002 war als 200er Lauf geplant, das JSON enthaelt 202 Manifest-Eintraege durch Resume-/Duplikat-/Buchhaltungslogik. Fuer die Risikoquote ist das okay, weil es um Routing-Eintraege geht.

## Ergebnis

- `_unsortiert`: 2 von 252 = 0.79 %
- `09-SONSTIGES`: 9 von 252 = 3.57 %
- `_unsortiert + SONSTIGES`: 11 von 252 = 4.37 %
- Hochrechnung `_unsortiert` auf 3000: ca. 24 Videos
- Warnschwelle laut Auftrag: > 5 %
- Ergebnis: Keine Warnschwelle erreicht.

## Verteilung

- `03-KI-IT`: 82
- `02-IT-HACKS`: 79
- `04-TECHNIK`: 57
- `09-SONSTIGES`: 9
- `06-FINANZEN`: 8
- `10-SOFINELLO`: 5
- `08-MUSIK`: 4
- `_unsortiert`: 2
- `05-NEWS`: 2
- `01-IT`: 1

## _unsortiert Beispiele

1. `KIFilme`, erwartet `07-FILME`
   - Quelle: `C:\Users\nexil\Desktop\Instagram Videos\KIFilme\SnapInsta.to_AQNUw-ol9OpXkZ41NDSbI5a9VSvD2MPWDKwZ0FPVA-Z5T9rNM1QBf4YA9lXu3qI_zVKUEvj02bcxbln4crdZG683NgtiXznHRikyMxQ.mp4`
   - Befund: Film/KI-Film sollte kuenftig per Ordnerregel stabil nach `07-FILME` gehen, nicht nach `_unsortiert`.

2. `Amore  de Paris`, keine erwartete Kategorie
   - Quelle: `C:\Users\nexil\Desktop\Instagram Videos\Amore  de Paris\SnapInsta.to_AQNBAZdgBU4GobbAzxlggVL1D0-4oqkwsor-lcssMbdj8o_ukxeFYHXJ7pCK9BKfDUTp3V7Q725jBJ9bPLItvDaG9B1si63G4dvZZkE.mp4`
   - Befund: echter unklarer Ordner, manuelle Entscheidung sinnvoll.

## Einschaetzung fuer Stufe 3

Die reine `_unsortiert`-Gefahr wirkt niedrig. Selbst wenn man `09-SONSTIGES` als Review-nahe Kategorie mitzählt, liegt die Quote bei 4.37 % und damit knapp unter 5 %. Trotzdem ist die Stichprobe IT-lastig, daher sollte Stufe 3 nach den ersten 100 und 300 Videos automatisch melden, wie hoch `_unsortiert` real liegt.

## Vorschlag

1. Ordnerregel ergaenzen: `KIFilme` und aehnliche Filmordner direkt nach `07-FILME`.
2. `_unsortiert` weiterhin nicht automatisch durch Gemini jagen.
3. Telegram-Warnung bei `_unsortiert > 5 %` im laufenden Vollrun.
4. Wenn `_unsortiert + 09-SONSTIGES > 10 %`, Nexi eine Review-Liste schicken, damit kein Geld auf unklare Inhalte verbrannt wird.
