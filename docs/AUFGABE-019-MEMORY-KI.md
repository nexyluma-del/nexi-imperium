# AUFGABE 019 - Memory-KI / Zweites Gehirn

Zugewiesen an: Codex (Coder-Modus)
Basis-DNA: `C:\Users\nexil\Desktop\KI\v3\chiefs\01-MEMORY-COFOUNDER-FINAL.md`
Vorgaenger: Aufgabe 014 Telegram-Bot, 017 OpenWebUI/Qdrant, 018 Voice-Capture
Phase: 3 Vorbereitung
Risiko-Level: R2/R3 je nach Cloud-/Scheduler-Anteil

## Ziel

Die Memory-KI wird Nexis lokales zweites Gehirn:

- spricht Nexi im richtigen Ton an
- liest Qdrant-Wissen aus `video_knowledge`, `sofinello_knowledge`, `memory_voice`
- sendet Telegram-Briefings um 07:00, 13:00, 19:00
- erkennt neue Verknuepfungen zwischen Videos, Voice-Notizen und bestehenden Themen
- respektiert R3/R4-Regeln und Cloud-Freigaben

## Nicht-Ziele

- Kein Cloud-Upload sensibler D3/D4-Daten
- Keine externen Nachrichten ohne Approval
- Keine Kosten ohne Approval
- Keine echte 24/7-Server-Infrastruktur vor Cashflow

## Technische Bausteine

1. Lokaler Memory-Service
   - Python-Service oder n8n/Windows Task Scheduler Hybrid
   - nutzt lokal `qwen3:30b` fuer tiefere Antworten
   - nutzt `qwen3:4b` fuer kurze Klassifikation/Tags

2. Qdrant-RAG
   - Read-Zugriff auf alle Wissens-Collections
   - Quellenangabe mit Collection + Payload-Pfad
   - Konfidenz/Unsicherheit klar markieren

3. Telegram-Hauptkanal
   - Briefings
   - Verknuepfungs-Pushes
   - Status/Abfrage-Kommandos

4. Verknuepfungs-Detector
   - bei neuen Pipeline-Outputs Embedding-Suche
   - wenn Aehnlichkeit ueber Schwelle: Push-Vorschlag an Nexi

5. Briefing-Scheduler
   - 07:00 Morgenbriefing
   - 13:00 Mittagscheck
   - 19:00 Tagesabschluss

## Erste Schritte fuer Codex

1. Memory-DNA-Datei lesen und als System-Prompt-Vorlage versionieren.
2. Bestehende Telegram-/Qdrant-Helfer wiederverwenden.
3. Mini-Prototyp bauen:
   - Frage an Memory-KI
   - Qdrant-Suche ueber `memory_voice` + `video_knowledge`
   - lokale qwen3-Antwort mit Quellen
4. Danach Briefing-Scheduler und Push-Logik.

## Akzeptanz-Kriterien

- Memory-KI antwortet im DNA-Ton auf eine Testfrage.
- Antwort nutzt Qdrant-Quellen sichtbar.
- Telegram-Push fuer ein Test-Briefing funktioniert.
- Neue Voice-Notiz kann eine Verknuepfungspruefung triggern.
- Keine Cloud-API wird ohne explizite Freigabe genutzt.
