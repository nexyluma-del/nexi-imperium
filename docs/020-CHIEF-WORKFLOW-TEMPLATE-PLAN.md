# Plan 020 - Chief-Workflow-Template

Stand: 2026-06-01 20:50  
Modus: Plan, nicht implementiert

## Ziel

Ein einheitliches Template fuer alle Chiefs, damit jeder Chief in 1-2 Stunden operationalisiert werden kann statt jedes Mal neu erfunden zu werden.

Abdeckung:

- CEO-Agent
- Memory-Chief
- Chief Finanz
- Chief Film
- Chief Musik
- Chief E-Commerce
- Chief Heilung
- Chief Web
- Chief Call-Center
- Chief Video-Analyse
- Chief IT & Engineering

## Standard-Chief-Datei

Jeder Chief bekommt:

```md
# Chief [Name]

## Mission
## Scope
## Datenklassen
## Erlaubte Tools
## Verbotene Aktionen
## Inputs
## Outputs
## Approval-Regeln
## Memory-KI-Anbindung
## CEO-Reporting
## Spezialisten-Agenten
## KPI
## Standard-Workflow
## Fehler-/Lesson-Regeln
```

## Input-Standard

Jede Aufgabe an einen Chief kommt in diesem Format:

```md
## Auftrag
[Was soll erreicht werden]

## Kontext
[Dateien, Links, Notizen, Qdrant-Sammlungen]

## Datenklasse
D0/D1/D2/D3/D4

## Risiko-Level
R0/R1/R2/R3/R4

## Gewuenschter Output
[Plan, Bericht, Code, Angebot, Liste, Analyse]

## Grenzen
[Nicht tun]

## Deadline/Prioritaet
[Heute/Morgen/Diese Woche]
```

## Output-Standard

```md
# Chief Report - [Thema]

## Kurzfazit
## Entscheidung fuer Nexi
## Ergebnis
## Risiken
## Kosten/Zeit
## Naechster Schritt
## Quellen/Dateien
## Konfidenz
```

## Approval-Logik

| Level | Chief darf |
|---|---|
| R0 | autonom erledigen |
| R1 | autonom erledigen, kurz loggen |
| R2 | autonom, Report an CEO/Nexi |
| R3 | Approval von Nexi Pflicht |
| R4 | Approval + Crosscheck + ggf. Compliance/Rechtscheck |

Harte R3/R4 Beispiele:

- Geld ausgeben
- Account-Aktionen
- externe Nachrichten
- Social Posts
- sensible D3/D4-Daten
- Loeschungen
- grosse Batches
- medizinische/Heilungs-Claims

## Memory-KI-Anbindung

Jeder Chief bekommt:

- Read-Zugriff auf relevante Qdrant-Collections
- Memory-KI als Kontextgeber
- keine direkte Cloud-Nutzung fuer D3/D4
- Rueckgabe wichtiger Erkenntnisse an Memory
- Lessons bei Fehlern

## Auto-Routing

| Aufgabe | Chief |
|---|---|
| Website, Landingpage, SEO, Kundenprojekt | Chief Web |
| Code, Infrastruktur, Pipeline, Security | Chief IT |
| Markt, Geld, Krypto, Szenarien | Chief Finanz |
| Videos analysieren, Wissensdatenbank | Chief Video-Analyse |
| Heilung, Sofinello, Dr. Sebi, Frequenzen | Chief Heilung |
| Filmideen, Serien, Trailer, Drehbuch | Chief Film |
| Musik, Soundtrack, Frequenz-Audio | Chief Musik |
| Dropshipping, Shop, Produkte, 3D-Druck | Chief E-Commerce |
| Voice-Agenten, Kundenservice | Chief Call-Center |
| Tageskoordination, Prioritaeten | CEO-Agent |
| Persoenliche Ideen, Wissen, Verknuepfungen | Memory-Chief |

## Chief-Lifecycle

1. Chief-DNA lesen.
2. Datenklassen und Scope setzen.
3. Tools erlauben.
4. 1 Testauftrag.
5. Output gegen Template pruefen.
6. In CEO-Routing aufnehmen.
7. Memory-Rueckfluss aktivieren.

## Erste Umsetzung

Empfohlen:

1. Chief Web als erster produktiver Chief.
2. Chief IT bleibt Codex/Infra.
3. CEO-Agent als einfacher Router.
4. Memory-KI spaeter finalisieren, wenn Chief Web und Stufe 3 Futter liefern.

## Go-Entscheidung fuer Nexi

Morgen:

- A: Template als Markdown-Standard einfuehren. **Empfohlen.**
- B: Erst nur Chief Web damit bauen.
- C: Sofort alle Chief-Dateien umschreiben.

