# LESSONS.md

Lebendes Fehler- und Lernprotokoll fuer Nexis KI-Imperium. Bei jedem echten Bug wird unten ein neuer Eintrag angehaengt: Symptom, Root Cause, Fix, Lehre.

## 2026-05-31 - NASA-Cross-Contamination-Bug

**Symptom:** Instagram-/Telegram-Analysen lieferten teilweise NASA/LADEE/LLCD-Inhalte aus dem alten Setup-Testvideo, obwohl andere reale Instagram-URLs verarbeitet wurden.

**Root Cause:** Slug-Wiederverwendung. Mehrere Telegram-Runs nutzten denselben statischen Slug `TELEGRAM-SHARE-1`. Dadurch konnten frische URL-Metadaten neben alten Medienartefakten liegen: neue `info.json`, aber altes NASA-MP4/Audio/Transkript.

**Fix:** Clean-Slate ausgefuehrt, alte Analysen und Qdrant-Wissenseintraege geloescht, Gemini File API geleert, Pipeline auf eindeutige Run-Provenance umgebaut. Kuenftige Outputs liegen pro Video isoliert unter `C:\AI\projects\09-video-analyse\videos\<thema>\<video-id>\`.

**Lehre:** Jeder Pipeline-Run braucht eine eindeutige ID/UUID bzw. einen URL-/Datei-Hash im Slug. Niemals statische Dateinamen fuer wiederholte Runs verwenden. Bei Download- oder Transkriptionsfehlern hart stoppen, nie still auf alte Dateien oder Testmedien zurueckfallen.

## 2026-05-31 - Gemini-Key in WSL durch .env-BOM unsichtbar

**Symptom:** Telegram-Share startete korrekt, Download/Batch liefen an, aber der Schritt `gemini_analyze_full` brach mit `GEMINI_API_KEY fehlt` ab. In Windows war der Key in `.env` sichtbar, in WSL/Python wurde er nicht als exakt `GEMINI_API_KEY` erkannt.

**Root Cause:** Die erste Zeile der `.env` hatte ein BOM/Encoding-Problem durch PowerShell-Schreibweise. Dadurch konnte `python-dotenv` unter WSL den Key als Variable mit unsichtbarem Prefix lesen statt als sauberes `GEMINI_API_KEY`.

**Fix:** `gemini_common.load_settings()` laedt `.env` jetzt mit `encoding="utf-8-sig"`. Danach wurde der fehlgeschlagene Telegram-Auftrag erfolgreich erneut verarbeitet.

**Lehre:** Projektweite `.env`-Loader muessen BOM-tolerant sein, weil Windows PowerShell Dateien anders schreiben kann als Linux-Tools erwarten. Secrets nie im Chat ausgeben; nur boolean/Status pruefen.
