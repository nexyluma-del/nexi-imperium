# Codex Uebergabe - Run-002 Stufe 2 IT-Stress-Test

Stand: 2026-06-01 17:55

## Kurzfazit

Run-002 ist sauber abgeschlossen: 200/200 Videos, 0 aktive Fehler, 0 unsortiert, Klassifizierer 100%.
Gemini hatte mehrere 503-Hochlastfenster, aber die neue Retry-/Backoff-Logik hat den Lauf erfolgreich stabilisiert.
Es gab keinen LADEE/LLCD/NASA-Cross-Contamination-Hard-Treffer; der bekannte NASA-Soft-Flag von Video 134 bleibt als manuell verifizierter False Positive dokumentiert.

## Ergebnis

| Kennzahl | Wert |
|---|---:|
| Geplant | 200 |
| Fertig | 200 |
| Gemini verarbeitet | 174 |
| Duplikat-Referenzen | 26 |
| Unsortiert | 0 |
| Aktive Fehler | 0 |
| Behobene/transiente Fehler | 3 |
| Klassifizierer-Genauigkeit | 100% |
| Kosten gesamt | 1.814692 USD |
| Durchschnitt je Gemini-Video | 0.010429 USD |
| NASA/LADEE/LLCD-Hard-Audit | 0 Treffer |
| Quality Flags | 1, manuell verifizierter False Positive |

## Kosten-Hochrechnung

| Szenario | Hochrechnung |
|---|---:|
| Linear auf 3000 Videos | ca. 27.22 USD |
| Linear x 1.3 Sicherheitspuffer | ca. 35.39 USD |

Hinweis: Das gilt fuer aehnliche IT/Tech-Videos mit Gemini Flash. Sofinello mit Gemini Pro waere teurer und muss separat kalkuliert werden.

## Gemini-503

| Kennzahl | Wert |
|---|---:|
| 503-Events gesamt | 36 |
| Betroffene eindeutige Videos | 11 |
| Zeitraum | 2026-06-01 12:04 bis 17:32 |

Bewertung: Kein Pipeline-Bug. Gemini war phasenweise ueberlastet. Die lange Retry-Policy funktioniert jetzt praktisch.

## Wichtige Pfade

- Run-Report: `C:\AI\projects\09-video-analyse\videos\_runs\run-002-it-stress-200\run-002-it-stress-200.md`
- Run-JSON: `C:\AI\projects\09-video-analyse\videos\_runs\run-002-it-stress-200\run-002-it-stress-200.json`
- 503-Events: `C:\AI\projects\09-video-analyse\videos\_runs\gemini-503-events.json`
- Quality Flags: `C:\AI\projects\09-video-analyse\videos\_quality_flags.json`

## Naechster Schritt

Telegram Bot v2 wird nach diesem erfolgreichen Run aktiviert:
- Telegram bekommt nur noch kurze Statusmeldungen.
- Volle Analysen bleiben im Per-Video-Ordner.
- `/status` und `/last 5` werden kompakt.

Stufe 3 startet nicht automatisch. Vor dem 3000er-Voll-Lauf kommt ein separater Plan mit Backup, Risiko, Kosten, Rollback und Nexis Go.
