# Plan 024 - Stufe 3 Voll-Lauf Videoanalyse

Stand: 2026-06-01 20:40  
Modus: Plan, nicht ausfuehren ohne Nexis Go

## Ziel

Stufe 3 soll alle relevanten lokalen Videos kontrolliert verarbeiten:

1. Whisper/Transkript lokal.
2. Klassifizierung/Routing lokal.
3. Visuelle Analyse mit Gemini Flash oder Gemini Pro.
4. Output pro Video in eigener Folder-Struktur.
5. Qdrant-Wissenseintrag.
6. Telegram-Status ueber Bot v2.

Stufe 3 laeuft spaeter im Hintergrund und darf Chief-Web-Arbeit nicht blockieren.

## Ausgangsdaten

Aktuelles Inventar:

| Kategorie | Anzahl |
|---|---:|
| _classifier_required | 773 |
| 01-IT | 1 |
| 02-IT-HACKS | 128 |
| 03-KI-IT | 90 |
| 04-TECHNIK | 65 |
| 05-NEWS | 4 |
| 06-FINANZEN | 105 |
| 07-FILME | 6 |
| 08-MUSIK | 2 |
| 10-SOFINELLO | 1204 |
| Gesamt lokal | 2378 |

Nexis Zielgroesse ist ca. 3000 Videos. Differenz zu 2378 kann aus URL-Listen, Duplikaten, spaeteren manuellen Downloads oder noch nicht inventarisierten Dateien kommen.

## Kategorie-Reihenfolge

Cashflow-Prioritaet:

1. IT / IT-Hacks / KI-IT / Technik
2. News
3. Finanzen
4. Filme / Musik
5. Sonstiges nach manueller Pruefung
6. Sofinello zuletzt, mit Compliance-Layer

`_unsortiert` wird nicht automatisch durch Gemini geschickt. Diese Videos warten auf manuelle Zuordnung.

## Modellstrategie

| Kategorie | Modell |
|---|---|
| IT / Hacks / KI / Technik | Gemini Flash |
| News / Finanzen / Filme / Musik | Gemini Flash |
| Sofinello | Gemini Pro |
| _unsortiert | keine Gemini-Verarbeitung |

Sofinello braucht Pro wegen visueller Details, Mixturen, Produkten und Verpackung/OCR.

## Cost-Schaetzung

Run-002:

- 200 Videos geplant
- 174 echte Gemini-Calls
- 1.814692 USD Kosten
- Durchschnitt: ca. 0.01043 USD pro Gemini-Video

Sofinello-Referenz:

- 3 Tests: 0.044907 USD
- Durchschnitt: ca. 0.01497 USD pro Test
- konservative 722er-Schaetzung aus 016b: 18-43 USD
- auf 1204 Sofinello hochgerechnet: ca. 30-72 USD

Gesamt:

| Szenario | Kosten |
|---|---:|
| Linear nach Run-002 | ca. 27 USD |
| Realistisch Flash + Sofinello Pro | ca. 60-115 USD |
| Mit 503-/Laengen-/OCR-Puffer | ca. 80-150 USD |
| Hard-Cap | 160 USD |
| Telegram-Warnung | ab 120 USD |

Wichtig: Retry-Calls sollten normalerweise nicht voll als neue Analyse zaehlen, aber 503-Zeitfenster koennen indirekt Kosten/Laenge erhoehen, wenn Uploads/Versuche neu gestartet werden muessen.

## Laufzeit-Schaetzung

Run-002 hatte mehrere 15-30-Minuten-Backoffs wegen Gemini 503.

| Szenario | Laufzeit |
|---|---:|
| Optimistisch | 2-3 Tage |
| Realistisch bei aehnlichem Gemini-Verhalten | 3-5 Tage |
| Worst Case bei langen 503-/Quota-Fenstern | bis 7 Tage |

## Stop-Bedingungen

Harter Stop:

- Kosten >= 160 USD
- LADEE
- LLCD
- `lunar laser communication`
- `laser communications demonstration`
- Klassifizierer-Fehler bei Sofinello
- `_unsortiert > 10%`
- Quota/Billing unklar
- Download-Error ohne sauberen Grund
- Manifest/Hash-Mismatch

Soft Flag:

- `NASA` ohne Whisper-Bezug
- sehr niedrige visuelle Sicherheit
- OCR/Packaging unklar
- Compliance unsicher

## 503-/Quota-Strategie

Bestehende Retry-Logik beibehalten:

- 7 Versuche pro Zyklus
- Backoff: sofort, 30s, 60s, 2min, 5min, 15min, 30min
- Danach 60min Pause
- Zweiter Zyklus
- Erst danach Fehleralarm

Zusatz fuer Stufe 3:

- 503-Events pro Kategorie auswerten
- Wenn 503-Rate > 20% in einer Stunde: automatisch 60-120min Pause
- Kein Wechsel auf anderes Modell ohne Nexis Go

## Live-Status via Bot v2

Telegram alle 100 Videos:

```text
Stufe 3 Status
Fertig: X/Y
Kategorie: ...
Kosten: ... USD
503 letzte Stunde: ...
ETA: ...
Naechster Stop: 120 USD Warnung / 160 USD Hard-Cap
```

Bei Alarm:

- kurze Telegram-Meldung
- Link/Pfad zum Run-Report
- keine langen Analysen im Chat

## Rollback

Vor Start:

1. Restic-Snapshot-ID notieren.
2. Git-Commit notieren.
3. Run-Manifest mit `run_id` erstellen.
4. Current Qdrant point counts notieren.

Bei Rollback:

1. Run stoppen.
2. Betroffene `videos/<category>/<video-id>` Ordner nicht loeschen, sondern nach `_quarantine` verschieben.
3. Qdrant-Eintraege des `run_id` loeschen oder exportieren und quarantainen.
4. Restore nur falls Dateisystem wirklich beschaedigt ist.

## Go-Entscheidung fuer Nexi

Option A: Stufe 3 sofort nach Restic/BitLocker-Haertung starten.  
Option B: Zuerst Chief Web 1-2 Tage aufsetzen, Stufe 3 danach.  
Option C: Stufe 3 nur fuer Nicht-Sofinello starten, Sofinello separat.

Empfehlung: **C oder A**, aber nur nach BitLocker/Restic-Haertung und frischem Snapshot.

