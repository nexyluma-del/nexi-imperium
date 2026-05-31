# Uebergabe: Critical Pipeline Bug Fix

Stand: 2026-05-31 15:05

## Problem

Telegram-Shares mit Instagram-URLs lieferten teilweise NASA/LADEE/LLCD-Analysen aus dem alten Setup-Testvideo. Ursache war keine Gemini-Halluzination, sondern Cross-Contamination vor Gemini: mehrere Telegram-Runs verwendeten denselben Slug `TELEGRAM-SHARE-1`, wodurch neue URL-Metadaten neben altem MP4/Audio lagen.

## Fix

- Batch- und Single-Video-Pipeline erzeugen nun Slugs mit URL-Hash und Zeitstempel.
- `yt-dlp`-Metadaten werden gegen den erwarteten Instagram-Shortcode geprueft.
- Audio-Download/Transkription stoppen jetzt hart bei Fehlern; kein stiller Fallback mehr.
- Gemini File API wird vor und nach Analyse-Runs geleert.
- Analyse-JSONs enthalten SHA256 fuer Video und Transkript.
- Qdrant bekommt Provenance-Daten pro neuem Video-Eintrag.
- OpenWebUI-RAG-Sync ignoriert `tainted`, `exclude_from_rag` und Setup-Testquellen.
- Telegram-Startskript wurde robuster gemacht und startet den Bot als WSL-Prozess mit Logdateien.

## Daten-Audit

- Report: `C:\AI\projects\09-video-analyse\failed-or-corrupt.md`
- JSON: `C:\AI\projects\09-video-analyse\failed-or-corrupt.json`
- Primär verdächtig: 8 Eintraege in `video_knowledge`, alle als `tainted=true` markiert.
- Erwartete NASA-Testdaten: 5 Eintraege in `video_knowledge`, aus OpenWebUI-RAG ausgeschlossen.
- OpenWebUI-RAG-Spiegel: neu synchronisiert, 0 NASA-Treffer im Spiegel.
- Sofinello-Audit: 200 Eintraege geprueft, 0 NASA/LADEE/LLCD-Treffer; frueherer Treffer war ein False Positive durch das Wort `nasal`.

## Verifikation

Testdatei: `C:\AI\projects\09-video-analyse\work\critical-bug-verify-3.md`

3 reale Instagram-URLs wurden frisch analysiert:

1. `https://www.instagram.com/reel/DXhKrOciC0l/`
   - Analyse: `C:\AI\projects\09-video-analyse\analysis\CRITICAL-BUG-VERIFY-1-59b7a492744d-2026-05-31_144921-59b7a492744d-2026-05-31_144922.full-gemini-2026-05-31_144950.md`
   - Qdrant ID: `72e75a90-2e12-ab36-586c-24d9398016c9`

2. `https://www.instagram.com/reel/DWHfjzODdSJ/`
   - Analyse: `C:\AI\projects\09-video-analyse\analysis\CRITICAL-BUG-VERIFY-2-a606baac56fc-2026-05-31_145035-a606baac56fc-2026-05-31_145036.full-gemini-2026-05-31_145104.md`
   - Qdrant ID: `5a33c8da-7a21-d353-be06-3a88c4963107`

3. `https://www.instagram.com/reel/DY3HHuVt4IP/`
   - Analyse: `C:\AI\projects\09-video-analyse\analysis\CRITICAL-BUG-VERIFY-3-e5e0408f793f-2026-05-31_145146-e5e0408f793f-2026-05-31_145146.full-gemini-2026-05-31_145212.md`
   - Qdrant ID: `78e0f7b2-8177-fb93-95cd-9f6ae45acce9`

Ergebnis:

- 3/3 `yt-dlp` erfolgreich.
- 3/3 URL-IDs korrekt in Video- und Audio-`info.json`.
- 3/3 unterschiedliche Video-SHA256.
- 0 NASA/LADEE/LLCD Treffer in den drei neuen Analyse-Markdowns.
- Gesamtkosten: `$0.052426`, also ca. 5.24 Cent.

## Aktueller Betriebszustand

- Telegram-Bot laeuft wieder.
- Sofinello-Resume-Task bleibt deaktiviert.
- Sofinello-Batch wird nicht automatisch fortgesetzt, bis Nexi das explizit wieder freigibt.
