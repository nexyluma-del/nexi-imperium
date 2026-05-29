# Gemini API Setup - Aufgabe 011

Stand: 2026-05-29

## Status

Aufgabe 011 ist abgeschlossen. Gemini Pro laeuft in der lokalen Video-Pipeline.

Historie:

- Zunaechst blockierte Google mit `429 RESOURCE_EXHAUSTED`, weil kein nutzbares AI-Studio-Prepay-Guthaben aktiv war.
- Nach Aufladung von 50 EUR und Budget-Limit 40 EUR liefen die Live-Tests erfolgreich.
- `gemini-2.5-pro` meldete temporaer `503 UNAVAILABLE` wegen hoher Nachfrage.
- Der Pro-Alias `gemini-pro-latest` lief sauber durch und bleibt als Standard gesetzt.

Finaler Verbrauch der erfolgreichen Abschluss-Tests:

```text
analyze_video.py: 0.012651 USD geschaetzt
analyze_full.py:  0.016775 USD geschaetzt
Summe:            0.029426 USD geschaetzt
```

Hinweis: Beim ersten erfolgreichen Visual-Call trat danach ein lokaler JSON-Serialisierungsfehler auf. Dieser Call kostete geschaetzt `0.010401 USD`; der Bug wurde behoben und der saubere Test erneut ausgefuehrt. Auch inklusive dieses Debug-Calls blieb der gesamte Verbrauch bei ca. `0.039827 USD`, also klar unter 0,30.

## Sicherheit API-Key

Der Gemini API-Key liegt lokal hier:

```text
C:\AI\projects\09-video-analyse\.env
```

Die Datei enthaelt:

```text
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-pro-latest
GEMINI_COST_CAP_EUR=0.30
```

Wichtig:

- Der API-Key wurde nicht im Chat ausgegeben.
- Der API-Key wurde nicht in Logs geschrieben.
- `.env` steht in `.gitignore`.
- Die Windows-ACL wurde eingeschraenkt auf Nexi, Codex-Prozess, SYSTEM und Administratoren.

Lokale Gitignore:

```text
C:\AI\projects\09-video-analyse\.gitignore
```

## Modellentscheidung

Die Aufgaben-Datei nannte `gemini-2.0-pro`. Laut aktueller Google-Doku ist die 2.0-Reihe als vorherige/deprecated Modellfamilie gefuehrt. Fuer den stabilen Pro-Pfad wurde deshalb verwendet:

```text
gemini-pro-latest
```

Begruendung:

- Pro-Qualitaet statt Flash
- offizieller Pro-Alias im eigenen Projekt
- `gemini-2.5-pro` war beim Test temporaer durch hohe Nachfrage blockiert (`503 UNAVAILABLE`)
- Kosten fuer das D0-Testvideo bleiben deutlich unter 0,30 EUR

## Installierte Pakete

In der bestehenden Video-Pipeline-venv:

```text
C:\AI\projects\09-video-analyse\.venv
```

Installiert:

```text
google-genai        2.7.0
google-generativeai 0.8.6
python-dotenv       1.2.2
```

Die Scripts nutzen das aktuelle `google-genai` SDK. `google-generativeai` wurde zusaetzlich installiert, weil es in der Aufgaben-Datei genannt war.

## Testvideo

Oeffentliches NASA-D0-Testvideo:

```text
C:\AI\projects\09-video-analyse\downloads\nsn-llcd-1.mp4
```

Quelle:

```text
https://www.nasa.gov/wp-content/uploads/2023/09/nsn-llcd-1.mp4
```

Eigenschaften:

```text
Groesse: 8.665 MB
Dauer: 58.166 s
Datenklasse: D0
```

Passendes Whisper-Transkript:

```text
C:\AI\projects\09-video-analyse\transcripts\nsn-llcd-1.txt
```

## Scripts

Gemeinsame Gemini-Helfer:

```text
C:\AI\projects\09-video-analyse\scripts\gemini_common.py
```

Visuelle Analyse:

```text
C:\AI\projects\09-video-analyse\scripts\analyze_video.py
```

Kombinierte Analyse aus Video + Whisper-Transkript:

```text
C:\AI\projects\09-video-analyse\scripts\analyze_full.py
```

Beide Scripts:

- laden `.env`
- nutzen `gemini-2.5-pro`
- pruefen Groesse, Dauer und Kosten vor dem API-Call
- stoppen bei Kosten-Schaetzung > 0,30 EUR
- blockieren D3/D4 ohne explizites `--allow-sensitive`
- loeschen hochgeladene Gemini Files nach dem Run standardmaessig wieder
- schreiben Markdown + JSON-Metadaten in `analysis/`

## Dry-Run Ergebnisse

Visuelle Analyse ohne API-Call:

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/analyze_video.py downloads/nsn-llcd-1.mp4 --data-class D0 --dry-run
```

Ergebnis:

```text
Model: gemini-2.5-pro
Size MB: 8.665
Duration seconds: 58.166
Estimated input tokens: 19449
Estimated output tokens: 2000
Estimated cost: $0.044311
```

Full-Analyse ohne API-Call:

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/analyze_full.py downloads/nsn-llcd-1.mp4 --transcript transcripts/nsn-llcd-1.txt --data-class D0 --dry-run
```

Ergebnis:

```text
Model: gemini-2.5-pro
Size MB: 8.665
Duration seconds: 58.166
Estimated input tokens: 19550
Estimated output tokens: 2500
Estimated cost: $0.049438
```

USD wird lokal konservativ 1:1 als EUR-Cap behandelt. Damit sind beide geplanten Tests deutlich unter 0,30.

## Erfolgreicher Live-Test

Visuelle Analyse:

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/analyze_video.py downloads/nsn-llcd-1.mp4 --data-class D0 --source-url "https://www.nasa.gov/wp-content/uploads/2023/09/nsn-llcd-1.mp4"
```

Output:

```text
C:\AI\projects\09-video-analyse\analysis\nsn-llcd-1.visual-gemini-2026-05-29_194217.md
C:\AI\projects\09-video-analyse\analysis\nsn-llcd-1.visual-gemini-2026-05-29_194217.json
```

Messwerte:

```text
Modell: gemini-pro-latest
Prompt tokens: 5369
Output tokens: 594
Total tokens: 7365
Geschaetzte Ist-Kosten: 0.012651 USD
```

Kombi-Analyse:

```bash
cd /mnt/c/AI/projects/09-video-analyse
scripts/analyze_full.py downloads/nsn-llcd-1.mp4 --transcript transcripts/nsn-llcd-1.txt --data-class D0 --source-url "https://www.nasa.gov/wp-content/uploads/2023/09/nsn-llcd-1.mp4"
```

Output:

```text
C:\AI\projects\09-video-analyse\analysis\nsn-llcd-1.full-gemini-2026-05-29_194303.md
C:\AI\projects\09-video-analyse\analysis\nsn-llcd-1.full-gemini-2026-05-29_194303.json
```

Messwerte:

```text
Modell: gemini-pro-latest
Prompt tokens: 5684
Output tokens: 967
Total tokens: 8180
Geschaetzte Ist-Kosten: 0.016775 USD
```

Gemini File API Cleanup:

```text
client.files.list(): files 0
```

## Cost-Tracking

Google listet Gemini 2.5 Pro im Paid Tier mit:

```text
Input:  $1.25 / 1M Tokens bis 200k Prompt Tokens
Output: $10.00 / 1M Tokens bis 200k Prompt Tokens
```

Die lokale Kostenlogik nutzt diese Preise und behandelt USD konservativ 1:1 als EUR-Cap. Der Schutz ist absichtlich vorsichtig.

Video-Tokenregel laut Google:

```text
ca. 300 Tokens pro Videosekunde bei Default Media Resolution
ca. 100 Tokens pro Videosekunde bei Low Media Resolution
```

Fuer Aufgabe 011 bleibt Default aktiv, weil Qualitaet wichtiger ist als Minimalpreis.

## Rate Limits

Stand laut Google-Doku:

- Rate Limits werden pro Projekt bewertet, nicht pro API-Key.
- Typische Dimensionen sind RPM, TPM und RPD.
- Konkrete aktive Limits haengen von Tier, Modell und Accountstatus ab und sind in AI Studio sichtbar.
- Preview-Modelle koennen strengere Limits haben.

Fuer diese lokale Pipeline gilt vor Aufgabe 012:

- keine parallelen Test-Runs
- nur D0-Testvideo
- Kosten-Cap 0,30 EUR pro Run
- keine privaten Videos

## Billing-Hinweise

Google meldete vorher leeres Prepay-Guthaben. Laut Google muss im Prepay-Modell ein positiver Credit Balance vorhanden sein; bei 0 Credits stoppen API-Keys im verknuepften Billing Account.

Update 2026-05-29 ca. 19:00:

- Nexi hat in der Google Cloud Console ein aktiviertes Konto mit `0 von 257 EUR Guthaben verwendet` gezeigt.
- Ein erneuter Live-Test mit `analyze_video.py` wurde versucht.
- Die Gemini API antwortete weiterhin mit `429 RESOURCE_EXHAUSTED` und `Your prepayment credits are depleted`.
- `client.files.list()` zeigte danach `files 0`; es ist keine Gemini-Testdatei liegen geblieben.
- Verbrauch weiterhin: `0 EUR`.

Interpretation:

Das in der Cloud Console sichtbare Guthaben ist sehr wahrscheinlich Google-Cloud-/Trial-Guthaben, aber nicht das fuer Gemini API noetige AI-Studio-Prepay-Guthaben bzw. noch nicht fuer das API-Key-Projekt aktiv. Google dokumentiert, dass Gemini API im Prepay-Modell einen positiven Prepay Credit Balance braucht; bei 0 Credits stoppen API-Keys. Ausserdem koennen Google-Cloud-Welcome-Credits je nach Account nicht fuer Gemini API / AI Studio nutzbar sein.

Aktueller Stand:

```text
50 EUR Guthaben aktiv
Budget-Limit: 40 EUR
Aufgabe-011-Testverbrauch: ca. 0.029426 USD fuer die beiden finalen Tests
```

Danach kann der Live-Test erneut ausgefuehrt werden.

## Quellen

- Google Video Understanding: https://ai.google.dev/gemini-api/docs/video-understanding
- Google Models: https://ai.google.dev/gemini-api/docs/models
- Google Pricing: https://ai.google.dev/gemini-api/docs/pricing
- Google Rate Limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Google Billing: https://ai.google.dev/gemini-api/docs/billing
