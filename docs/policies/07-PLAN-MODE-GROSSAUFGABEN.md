# 07 - Plan-Mode Fuer Grossaufgaben

## Zweck

Diese Policy verhindert, dass grosse Batches, teure API-Laeufe oder architekturrelevante Umbauten ohne vorherige Denkpause gestartet werden.

## Pflicht-Plan vor Ausfuehrung

Vor jeder Aufgabe mit mindestens einem der folgenden Trigger muss zuerst ein Plan vorgelegt werden:

- Mehr als 50 Videos, Posts, Dateien oder URLs werden verarbeitet.
- Erwartete externe API-Kosten liegen ueber 5 EUR.
- Ein Batch betrifft sensible Datenklasse D3/D4.
- Eine Aenderung betrifft zentrale Pipeline-Architektur, Qdrant-Schema, Backup/Restore, Auth, Scheduler oder dauerhafte Automationen.
- Ein Fehler kann grossflaechig falsche Daten in Memory, Qdrant, OpenWebUI oder Sync-Bridge schreiben.

## Plan-Format

Der Plan muss mindestens enthalten:

- **Architektur-Check:** Welche Module/Services sind betroffen? Welche Daten fliessen wohin?
- **Edge-Cases:** Was kann fehlschlagen, und wie wird hart gestoppt statt falsch weitergemacht?
- **Cost-Schaetzung:** Erwartete externe Kosten, konservativer Puffer und Abbruchgrenze.
- **Rollback-Plan:** Was kann geloescht, wiederhergestellt, deaktiviert oder aus Backup/Qdrant bereinigt werden?
- **Verifikation:** Welche kleine Stichprobe beweist, dass der Plan sicher ist?

## Freigabe

Nach dem Plan wird nicht ausgefuehrt, bis Nexi explizit freigibt. Freigabe kann z.B. sein:

- `Freigabe A`
- `Start`
- `Mach genau diesen Plan`

Ohne Freigabe bleiben grosse Batches und Kostenlaeufe pausiert.
