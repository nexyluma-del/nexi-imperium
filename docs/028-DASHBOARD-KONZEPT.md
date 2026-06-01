# Plan 028 - Lokales Status-Dashboard Konzept

Stand: 2026-06-01 21:05  
Modus: Konzept, keine Umsetzung

## Ausgangspunkt

Aktuell gibt es ein minimales lokales Dashboard/Status-HTML fuer Pipeline/Imperium-Status. Parallel hat Lumia eine staerkere Interface-Vision:

- Cyberpunk-Synthwave
- Navy / Royal-Violett / Electric Blue / Cyan
- Voice-Ring
- Status: schlaeft, hoert, denkt, spricht
- Haupt-Dashboard ruhig
- Detailfenster fuer lange Antworten

## Zielbild

Ein lokales Kontrollzentrum fuer Nexis KI-Imperium:

- kein Cloud-Abo
- lokal im Browser
- schnell und stabil
- mobile lesbar
- spaeter Lumia-Stil

## Dashboard-Stufen

### Stufe 1 - Status heute

Ziel:

- Pipeline-Status
- Bot-Status
- Services
- Cost
- Qdrant Counts
- letzte Videos
- aktive Runs

Technik:

- lokales HTML + kleiner Python/FastAPI-Server oder statischer Export
- keine Cloud

### Stufe 2 - Operations Dashboard

Ziel:

- Fortschrittsbalken pro Kategorie
- Stufe-3-Run live
- 503-Events
- Cost-Warnungen
- failed-videos
- Quality Flags
- Buttons nur fuer Read-Only/Links, keine riskanten Aktionen

### Stufe 3 - Chief Dashboard

Ziel:

- Chief Web Leads
- Chief IT Tasks
- Chief Finanz Szenarien
- Chief Video Pipeline
- Approvals
- Tagesprioritaeten

### Stufe 4 - Lumia Style

Ziel:

- fester Hauptscreen
- Voice-Ring
- Statusanimation
- Detailfenster
- hochwertiger Look, kein Standard-Admin-Panel

## Tech-Wahl

Empfohlen:

| Ebene | Tool |
|---|---|
| Backend | FastAPI |
| Frontend | statisches HTML/CSS/JS oder spaeter Next.js |
| Charts | Chart.js lokal |
| Icons | lucide |
| Daten | lokale JSON-Dateien + Qdrant HTTP |
| Deployment | localhost |

Keine Cloud, kein Abo.

## Design-Regeln

- Keine Marketing-Landingpage.
- Kein Karten-Chaos.
- Kompakt, operations-orientiert.
- Dunkel, aber lesbar.
- Navy, Lila, Electric Blue sparsam.
- Warnungen klar rot/gelb.
- Mobile Status zuerst.

## Reihenfolge

1. Bestehendes minimales Dashboard stabilisieren.
2. Stufe-3-Run-Anzeige einbauen.
3. Chief-Web-Bereich vorbereiten.
4. Lumia-Look erst, wenn Funktion stabil ist.

## Go-Entscheidung fuer Nexi

- A: Erst funktionales Operations-Dashboard. **Empfohlen.**
- B: Sofort Lumia-Cyberpunk-Design.
- C: Dashboard nach Chief Web verschieben.

