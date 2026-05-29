# ARBEITSSTRUKTUR

Status: eingerichtet
Datum: 2026-05-29
Phase: 0C Arbeitsstruktur

## 1. Ergebnis

Die lokale Arbeitsstruktur fuer Nexis KI-Zentrale ist angelegt.

Erledigt:
- `C:\AI` wurde angelegt.
- Projektordner fuer alle Abteilungen wurden angelegt.
- Jeder Projektordner hat eine kurze `README.md`.
- `models` und `backups` sind als Platzhalter angelegt.
- Obsidian wurde installiert.
- Lokaler Obsidian-Vault `Obsidian-Imperium` wurde angelegt.
- Lokales Git-Repo `C:\AI\imperium-config` wurde initialisiert.
- `.gitignore` schuetzt vor versehentlichem Commit sensibler Inhalte.
- GitHub-Remote fuer `nexyluma-del/nexi-imperium` ist vorbereitet.

Nicht gemacht:
- Keine KI-Tools installiert.
- Keine sensiblen Inhalte verschoben.
- Keine Daten geloescht.
- Kein GitHub-Push ausgefuehrt.
- Kein Public-Repo erstellt.

## 2. C:\AI Struktur

Hauptpfad:

```text
C:\AI
```

Struktur:

```text
C:\AI
├── projects
│   ├── 02-finanz
│   ├── 03-film
│   ├── 04-musik
│   ├── 05-ecommerce
│   ├── 06-heilung
│   ├── 07-web
│   ├── 08-callcenter
│   ├── 09-video-analyse
│   └── 10-it-engineering
├── models
├── backups
└── imperium-config
```

Wofuer:
- `projects`: aktive Arbeit nach Abteilung.
- `models`: spaeter lokale KI-Modelle, aktuell leer lassen.
- `backups`: spaeter lokale Snapshots/Exports, nicht fuer Passwoerter.
- `imperium-config`: technisches Git-Repo fuer Skripte und Konfiguration.

## 3. Datenklassen-Regel

Einfache Regel:
- D0/D1: harmlos, darf dokumentiert werden.
- D2: intern, vorsichtig behandeln.
- D3/D4: sensibel, nicht in Git und nicht in fremde Clouds.

Niemals ins Git:
- Passwoerter
- Tokens/API-Keys
- Recovery Keys
- Restic-Passwort
- BitLocker-Recovery-Key
- echte Drehbuecher/Rohideen
- Heilungs-Rohwissen
- Finanzstrategien
- Memory-Rohdaten
- private Chatverlaeufe

## 4. Obsidian

Installiert:

```text
Obsidian 1.12.7
```

Vault:

```text
C:\Users\nexil\Documents\Obsidian-Imperium
```

Struktur:

```text
Obsidian-Imperium
├── inbox
├── chiefs
│   ├── ceo
│   ├── memory
│   ├── finanz
│   ├── film
│   ├── musik
│   ├── ecommerce
│   ├── heilung
│   ├── web
│   ├── callcenter
│   ├── video-analyse
│   └── it-engineering
├── projects
├── knowledge
├── briefings
└── archive
```

Testnotiz:

```text
C:\Users\nexil\Documents\Obsidian-Imperium\inbox\Willkommen im Imperium.md
```

Benutzung:
- Neue Ideen zuerst in `inbox`.
- Chief-spezifische Notizen in `chiefs`.
- Laufende Vorhaben in `projects`.
- Wissen/Recherche in `knowledge`.
- Tagesbriefings in `briefings`.
- Altes Material in `archive`.

Wichtig:
- Vault lokal lassen.
- Nicht nach iCloud, OneDrive oder andere Cloud-Syncs verschieben, solange D3/D4-Inhalte darin liegen koennen.

## 5. Git-Repo

Lokales Repo:

```text
C:\AI\imperium-config
```

Status:
- Git initialisiert.
- Branch: `main`
- Initialer Commit: `Initial imperium config structure`
- Arbeitsbaum sauber.

Remote vorbereitet:

```text
https://github.com/nexyluma-del/nexi-imperium.git
```

Wichtig:
- Das GitHub-Repo muss privat sein.
- Codex hat nichts gepusht.
- Nexi erstellt das private Repo selbst auf GitHub.

## 6. GitHub-Schritt

Auf GitHub:

1. https://github.com/new oeffnen.
2. Repository name: `nexi-imperium`
3. Owner: `nexyluma-del`
4. Visibility: `Private`
5. Keine README, keine `.gitignore`, keine License auf GitHub erzeugen.
6. Repo erstellen.

Danach lokal:

```powershell
cd C:\AI\imperium-config
git push -u origin main
```

Vor jedem Push:

```powershell
git status
```

Wenn dort sensible Dateien auftauchen: nicht pushen.

## 7. Git Basics fuer Nexi

Status ansehen:

```powershell
git status
```

Aenderungen ansehen:

```powershell
git diff
```

Dateien vormerken:

```powershell
git add README.md
```

Commit erstellen:

```powershell
git commit -m "Kurze Beschreibung"
```

Zum privaten GitHub-Repo pushen:

```powershell
git push
```

Merksatz:
- Git ist fuer Technik, Skripte und harmlose Struktur.
- Obsidian ist fuer Denken, Wissen, Chiefs und Ideen.
- Sensible Rohdaten bleiben lokal und werden bewusst getrennt.

## 8. Offene Punkte

- [x] GitHub-Username erfragt: `nexyluma-del`
- [x] Obsidian-Vault-Pfad bestaetigt.
- [x] `C:\AI` angelegt.
- [x] Projektordner angelegt.
- [x] README-Dateien angelegt.
- [x] Obsidian installiert.
- [x] Obsidian-Vault lokal angelegt.
- [x] Lokales Git-Repo initialisiert.
- [x] `.gitignore` angelegt.
- [x] GitHub-Remote vorbereitet.
- [ ] Privates GitHub-Repo von Nexi auf github.com erstellen.
- [ ] Ersten Push erst nach privater Repo-Erstellung ausfuehren.

## 9. Naechster Schritt

Nach Aufgabe 005 kommt Phase 1.

Empfohlene Aufgabe 006:
- Lokale KI Minimal-Stack
- Erstes Tool: Ollama
- Danach OpenWebUI
- Danach Qdrant/n8n nach Plan

Vorher gilt:
- Keine sensiblen Inhalte in Git.
- Obsidian-Vault lokal halten.
- Restic-Backup weiter als Sicherheitsnetz behalten.
