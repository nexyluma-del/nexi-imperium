# Plan 026 - BitLocker Diagnose und Restic-Haertung

Stand: 2026-06-01 20:55  
Modus: Plan, Skripte vorbereitet, nicht ausgefuehrt

## Problem

Aufgabe 003 wurde als abgeschlossen behandelt, aber spaeter gab es Unsicherheit, ob BitLocker wirklich aktiv ist. Ein Check mit `manage-bde -status C:` aus der normalen Codex-Umgebung scheiterte mit Zugriff verweigert, weil Adminrechte noetig sind.

Deshalb morgen:

1. Admin-PowerShell.
2. Diagnose-Skript ausfuehren.
3. Wenn C: aktiv und Schutz an: Restic-Passwort haerten.
4. Wenn C: nicht aktiv: Aktivierung nur nach Nexis Go.

## Dateien

Vorbereitet:

- `C:\Users\nexil\Desktop\KI\aufgaben\bitlocker-diagnose-admin.ps1`
- `C:\Users\nexil\Desktop\KI\aufgaben\bitlocker-aktivierung-vorbereitet.ps1`

Nicht automatisch ausfuehren.

## Morgen Ablauf

### Schritt 1 - Diagnose

Nexi oeffnet PowerShell als Administrator:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\nexil\Desktop\KI\aufgaben\bitlocker-diagnose-admin.ps1"
```

Erwarteter Output:

- BitLocker aktiv/inaktiv
- Verschluesselungsprozent
- Schutzstatus
- Key-Protectoren
- Recovery-Key-Hinweis

### Schritt 2 - Entscheidung

Wenn aktiv:

- Weiter zu Restic-Haertung.

Wenn inaktiv:

- Nicht automatisch aktivieren.
- Nexi entscheidet, ob `bitlocker-aktivierung-vorbereitet.ps1` ausgefuehrt wird.

### Schritt 3 - Restic-Haertung

1. Neues 32-Zeichen-Passwort generieren.
2. Nexi speichert es im Passwortmanager.
3. `.env` lokal aktualisieren:
   - `RESTIC_PASSWORD=...`
4. Restic-Repo neu initialisieren oder Passwortrotation pruefen.
5. Backup starten.
6. Restore-Test.

## LESSONS.md Ergaenzung

Nach Diagnose:

- Lesson: Aufgabe 003 nicht nur als "done" markieren, sondern admin-verifizierte Beweise speichern.
- Lehre: Security-Aufgaben brauchen maschinenlesbaren Proof, nicht nur Chat-Bestaetigung.

## Risiko

| Risiko | Gegenmassnahme |
|---|---|
| BitLocker-Aktivierung braucht Reboot | nur mit Nexis Zeitfenster |
| Recovery-Key nicht gespeichert | vorher stoppen |
| Restic-Passwort erneut verloren | Passwortmanager + Restore-Test |
| .env liegt unverschluesselt | nur akzeptabel wenn C: BitLocker aktiv |

## Go-Entscheidung fuer Nexi

- A: Nur Diagnose morgen frueh. **Empfohlen.**
- B: Diagnose + BitLocker aktivieren, falls inaktiv.
- C: Restic-Haertung verschieben.

