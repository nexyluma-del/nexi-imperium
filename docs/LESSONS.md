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

## 2026-05-31 - Restic-Passwort-Drift durch PowerShell SecureString/Clipboard

**Symptom:** Neues Restic-Repository wurde initialisiert, aber direkt danach scheiterte `restic backup` wiederholt mit `Fatal: wrong password or no key found`, obwohl Nexi das Passwort korrekt kopiert hatte.

**Root Cause:** Der Ablauf fragte das Passwort mehrfach ab (`restic init`, danach Backup/Restore). PowerShell SecureString- und Clipboard-Flows fuehrten zu Passwort-Drift: Init bekam nicht garantiert exakt denselben Wert wie der spaetere Backup-Prozess. Zusaetzlich verursachte `Set-Clipboard -Value ""` in Windows PowerShell einen Fehler, wodurch der Clipboard-Flow unzuverlaessig wurde.

**Fix:** Notnagel-Flow: temporaeres Passwort bewusst als Klartext nur lokal in einem nicht versionierten Skript bzw. als `RESTIC_PASSWORD` in `.env` gesetzt. `restic init` und `restic backup` liefen damit non-interaktiv in derselben Logik. Alte Repository-Ordner wurden nur umbenannt, nicht geloescht. Snapshot `3ec4e511` mit Tag `stufe2-pre` bestaetigt.

**Lehre:** Bei Backup-/Recovery-Bootstrap zaehlt Reproduzierbarkeit vor Eleganz. Fuer Notfaelle keine mehrfachen Passwort-Prompts, kein SecureString-Paste-Raten, kein Clipboard-Raetsel. Erst ein gruenes, wiederholbar verifizierbares Backup herstellen; sichere Passwort-Rotation erst danach als separaten Auftrag durchfuehren.

## 2026-06-01 - Anti-NASA-Waechter zu grob

**Symptom:** Stufe 2 stoppte bei Video 134 wegen `NASA`, obwohl das Video korrekt zu Elon Musk/Grok gehoerte. Gemini erkannte visuell ein NASA-Logo auf der Jacke einer animierten Figur; Whisper sprach nur ueber Grok/xAI und erwaehnte NASA nicht.

**Root Cause:** Der Waechter nutzte den generischen Begriff `NASA` als harten Stop-Marker. Das ist fuer Cross-Contamination zu breit, weil NASA-Logos, Kleidung, Plakate oder allgemeine Referenzen legitim in Tech-Videos auftauchen koennen.

**Fix:** Harte Stops werden auf die spezifischen Signaturen des urspruenglichen Bugs begrenzt: `LADEE`, `LLCD`, `lunar laser communication`, `laser communications demonstration`. `NASA` allein wird nur noch als Soft-Flag in `videos/_quality_flags.json` geloggt, wenn es in Gemini, aber nicht im Whisper-Transkript auftaucht.

**Lehre:** Waechter muessen spezifische Bug-Marker pruefen, nicht generische Woerter. Generische Begriffe verursachen False Positives und duerfen hoechstens in eine Review-Queue laufen.
