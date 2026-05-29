# ROADMAP — Hardware-Skalierung

> Lebendes Dokument. Wird aktualisiert wenn sich Realitäten ändern.

## Aktuelle Entscheidung (Mai 2026)

**Nexi arbeitet mit Laptop only.** Kein Server, keine wiederkehrenden Kosten — bis es einen klaren Use-Case gibt.

## Trigger für Server-Investition

Server (Mini-VPS oder Hetzner CX22 für 10-20 €/Monat) wird angeschafft, **sobald** einer der folgenden Trigger eintritt:

1. **Finanz-Chief startet 24/7-Betrieb** (Phase 4) — Markt-Monitoring nachts/Wochenende
2. **Web-Business hat ersten Cashflow** (≥ 300-500 € reingekommen) — Server kann sich selbst tragen
3. **Memory-KI braucht Always-On-Sync mit Mobile** — sobald Smartphone-Voice-Capture aktiv wird
4. **Erster externer Kunden-Touchpoint** (Webseiten-Verkauf läuft) — Stabilität wird wichtig

**Erwarteter Zeitpunkt:** 2-4 Wochen ab Mai 2026, je nach Tempo.

## Server-Strategie (Stand Mai 2026, vor Nutzung prüfen)

### Phase 2a — Mini-Server (10-20 €/Monat)
- Anbieter-Empfehlung: Hetzner Cloud CX22 oder ähnlich
- Zweck: CEO-Agent, Memory-Sync, Finanz-Scanner (kein GPU nötig)
- GPU-intensives bleibt auf Laptop

### Phase 2b — Dedizierter Server (später, optional)
- Eigener Server zuhause (Mini-PC, Intel NUC) für 500-800 € einmalig
- ODER GPU-VPS bei Lambda Labs / RunPod für 100-300 €/Monat
- Nur wenn lokale 24/7-LLMs wirklich gebraucht werden

## Was bleibt am Laptop

Auch nach Server-Anschaffung läuft auf Laptop:
- Lokale große LLMs (qwen3:30b) — braucht 24 GB VRAM
- Memory-KI Hauptlogik (sensible Daten = D3/D4)
- Heilungs-Wissensbasis (Dr. Sebi + östliche Heilung)
- Drehbuch-Arbeit
- Voice-Capture

## Kosten-Disziplin

- **Nichts zahlen vor Cashflow-Beweis** außer den existierenden Pro-Abos
- Server-Kosten = Geschäftskosten, müssen durch Umsatz gedeckt sein
- Bei jeder neuen wiederkehrenden Ausgabe: ROI prüfen, „brauche ich das WIRKLICH"-Test

---

**Letztes Update:** Mai 2026, Tag 1 Setup (nach Nexis Architektur-Reflexion)
