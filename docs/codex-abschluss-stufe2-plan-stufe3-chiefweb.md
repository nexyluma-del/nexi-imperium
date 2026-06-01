# Codex Abschluss - Stufe 2, Stufe 3 Plan, Chief-Web-Korrektur

Stand: 2026-06-01 20:25

## 1) Abschluss-Paket Stufe 2

### Sanity-Check

| Komponente | Status |
|---|---|
| Ollama | OK, HTTP 200 |
| Qdrant | OK, HTTP 200 |
| OpenWebUI | OK, HTTP 200 |
| n8n | OK, HTTP 200 |
| Docker | OK, Container `open-webui`, `n8n`, `qdrant` laufen |
| Telegram Bot v2 | OK, Prozess aktiv |
| Bot v2 `/status` | OK, kompakt |
| Bot v2 `/last 5` | OK, kompakt |

Bot-v2-Smoke-Test Ergebnis:

- `/status` zeigt Run-002 als `complete`, Prozess `nicht aktiv`, 200/200, Cost, Services, letzte Kategorien.
- `/last 5` zeigt kurze Eintraege mit Kategorie, Per-Video-Ordner und Dashboard-Link.
- Keine Vollanalyse/Whisper-Texte im Telegram-Format.

### Run-002 Ergebnis

| Kennzahl | Wert |
|---|---:|
| Geplant | 200 |
| Fertig | 200 |
| Gemini verarbeitet | 174 |
| Duplikat-Referenzen | 26 |
| Unsortiert | 0 |
| Aktive Fehler | 0 |
| Klassifizierer | 100% |
| Kosten | 1.814692 USD |
| NASA/LADEE/LLCD-Hard-Audit | 0 Treffer |
| Gemini-503 Events | 36 |
| Betroffene 503-Videos | 11 |

### Backup

Frischer Restic-Snapshot:

- Snapshot-ID: `bbe1bf71`
- Zeit: 2026-06-01 20:22
- Quellen: Desktop, Documents, Pictures, Videos, `C:\AI`, `D:\Restic-Sources`
- Groesse: 47.395 GiB
- Neu ins Repository: 5.622 GiB, davon 2.824 GiB gespeichert
- Log: `C:\Users\nexil\Desktop\KI\logs\backup\backup-2026-06-01_202157.log`

## 2) Stufe 3 - realistischer Plan

Stufe 3 soll nicht blind starten. Sie ist ein Hintergrundlauf mit Telegram-Status, Cost-Cap und Resume-Logik.

### Aktueller Inventarstand

Aus `videos/_inventory/full-inventory.json`:

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
| Gesamtgroesse lokal | ca. 28.29 GiB |

Hinweis: Nexi spricht von rund 3000 Videos. Das aktuelle lokale Inventar zeigt 2378 lokale Dateien; Differenz kann aus URL-Listen, Duplikaten, spaeter manuellen Downloads oder noch nicht inventarisierten Dateien stammen.

### Cost-Schaetzung

Run-002 Flash-Realwert:

- 1.814692 USD fuer 200 geplante IT-Videos
- 174 echte Gemini-Calls
- Durchschnitt je Gemini-Video: ca. 0.01043 USD

Sofinello-Pro-Referenz:

- 3 Sofinello-Tests: 0.044907 USD gesamt
- Durchschnitt Test: ca. 0.01497 USD
- Bisherige konservative 722er-Schaetzung: 18-43 USD
- Hochgerechnet auf 1204 Sofinello-Videos: ca. 30-72 USD konservativ

Gesamt fuer 3000er-Lauf:

| Szenario | Schaetzung |
|---|---:|
| Nur linear nach Run-002 | ca. 27 USD |
| Flash + Sofinello Pro konservativ | ca. 60-115 USD |
| Sicherheitsfaktor fuer 503/Retry/Laenge/OCR | ca. 80-150 USD |
| Empfohlener Hard-Cap | 160 USD |
| Warnung | ab 120 USD per Telegram |

Bewertung: Der alte Hard-Cap 160 USD bleibt sinnvoll. 120 USD bleibt Warnschwelle.

### Laufzeit-Schaetzung

Run-002 brauchte wegen Gemini-503-Hochlast mehrere 15-30-Minuten-Wartephasen.

Realistische Laufzeit:

| Szenario | Laufzeit |
|---|---:|
| Optimistisch, wenig 503 | 2-3 Tage |
| Realistisch bei aehnlicher 503-Haeufigkeit | 3-5 Tage |
| Schlechtes Gemini-Fenster / Pro langsamer / mehr OCR | 5-7 Tage |

Stufe 3 darf parallel laufen, darf aber keine Chief-Web-Arbeit blockieren.

### Stufe-3-Regeln

- Kein Start ohne Nexis Go.
- Vor Start: Restic-Snapshot notieren.
- Gemini Flash fuer normale Kategorien.
- Gemini Pro fuer Sofinello.
- _unsortiert geht nicht automatisch durch Gemini.
- 503-Backoff bleibt aktiv.
- Telegram alle 100 Videos.
- Hard Stop bei LADEE/LLCD/lunar laser communication/laser communications demonstration.
- NASA nur Soft-Flag.
- Cost-Warnung ab 120 USD, Hard-Cap 160 USD.
- Resume-Manifest Pflicht.

## 3) Restic/BitLocker-Haertung

Korrektur: Die Aussage "BitLocker ist inaktiv" ist noch nicht bewiesen.

Aktueller Check:

- `manage-bde -status C:` wurde versucht.
- Ergebnis: Zugriff verweigert wegen fehlender Adminrechte.
- Schlussfolgerung: Wir brauchen morgen einen Admin/UAC-Check, bevor wir behaupten, dass Aufgabe 003 wirklich inaktiv oder aktiv ist.

Plan morgen:

1. Admin-PowerShell oeffnen.
2. `manage-bde -status C:` pruefen.
3. Wenn BitLocker aktiv und Schutzstatus an: Restic-Passwort haerten.
4. Neues 32-Zeichen-Restic-Passwort generieren.
5. Passwort in Passwortmanager speichern.
6. `.env` lokal aktualisieren.
7. Test: `restic snapshots`, kleines Backup, Restore-Probe.
8. LESSONS.md ergaenzen: Aufgabe 003 wurde als erledigt angenommen, aber spaeter nicht admin-verifiziert.

## 4) Chief Web parallel

Chief Web ist Cashflow-Prioritaet #1.

Gelesene Quelle:

- `C:\Users\nexil\Desktop\KI\v3\chiefs\07-CHIEF-WEB.md`

Kernaussage:

- Chief Web ist Geldmaschine #1.
- Ziel: professionelle Websites fuer Kunden in Tagen statt Wochen.
- Stack: Next.js + Tailwind, Vercel, Cloudflare, Cal.com/Calendly, ggf. Stripe/Mollie.
- Agenten: Akquise, Briefing, Design, Code, Content, SEO, Launch.
- Erst Plan, dann Nexis Go.

Morgen soll ein Chief-Web-Plan entstehen:

1. Angebotspakete und Preise.
2. Template-Bibliothek.
3. Erste 3 Zielgruppen.
4. Akquise-Liste.
5. Agentenrollen.
6. Beispiel-Kundenbriefing.
7. 7-Tage-Plan fuer ersten zahlbaren Auftrag.

## 5) Lumia-Session

Aktueller Befund:

- Lumia-Ordner ist aktiv.
- Es laufen Python-/Codex-Prozesse aus `C:\Users\nexil\Desktop\KI\lumia`.
- Logs wurden heute aktualisiert, z.B. `lumia.log`, `interface-bridge.log`, Voice-Dateien.
- Lumia ist also nicht tot; sie ist aktiv/hat gearbeitet.

Prioritaet:

- Vorerst nicht anfassen.
- Nach Chief Web wieder aufnehmen.

## 6) Empfohlene Reihenfolge

Heute abgeschlossen:

- Stufe-2-Abschluss.
- Bot v2 Smoke-Test.
- Frischer Restic-Snapshot.
- Stufe-3-Cost-/Laufzeit-Plan.
- Chief-Web-Korrektur angenommen.
- Lumia-Status geprueft.

Morgen:

1. BitLocker/Admin-Check.
2. Restic-Haertung.
3. Chief-Web-Plan.

Diese Woche:

1. Stufe 3 nach Nexis Go im Hintergrund starten.
2. Chief Web parallel bauen.

Naechste Woche:

1. Weitere Chiefs nach Cashflow-Reihenfolge.
2. Memory-KI-Finalisierung, sobald Pipeline und erste Cashflow-Chief-Struktur genug Wissen liefern.
