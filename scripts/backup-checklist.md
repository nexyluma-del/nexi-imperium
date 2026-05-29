# BACKUP-CHECKLISTE - Aufgabe 001

**Ziel:** Vor Phase 0B/0C und vor jeder groesseren Systemaenderung sicherstellen, dass Nexis wichtige Daten nicht wieder verloren gehen.

**Regel:** Ein Backup zaehlt erst, wenn mindestens eine Test-Wiederherstellung funktioniert hat.

## 1. Externe SSD pruefen

- [ ] Externe 2-TB-SSD anschliessen.
- [ ] Im Explorer pruefen, welcher Laufwerksbuchstabe zugewiesen wurde.
- [ ] Freien Speicher pruefen.
- [ ] Eine kleine Testdatei auf die SSD kopieren und wieder oeffnen.
- [ ] Testdatei danach manuell loeschen, wenn Nexi das moechte.
- [ ] Optional spaeter: SMART-/Gesundheitscheck mit geeignetem Tool.

## 2. Windows-Zugriff absichern

- [ ] Windows-PIN/Passwort bekannt.
- [ ] Microsoft-Konto-Zugang bekannt.
- [ ] BitLocker-Status von C: pruefen.
- [ ] Falls BitLocker aktiv: Recovery-Key finden und ausserhalb des Laptops sichern.
- [ ] Recovery-Key nicht nur auf dem Laptop speichern.

## 3. Wichtigste Ordner sichern

- [ ] `C:\Users\nexil\Desktop`
- [ ] `C:\Users\nexil\Documents`
- [ ] `C:\Users\nexil\Downloads`
- [ ] `C:\Users\nexil\Pictures`
- [ ] `C:\Users\nexil\Videos`
- [ ] `C:\Users\nexil\Music`
- [ ] `C:\Users\nexil\Desktop\KI`
- [ ] Projektordner unter `C:\Users\nexil\Documents\Codex`
- [ ] Alle vorhandenen Claude-/ChatGPT-/KI-Exportdateien

## 4. Browser und Accounts

- [ ] Bookmarks/Favoriten aus jedem genutzten Browser exportieren.
- [ ] Wichtige Browser-Profile notieren: Chrome, Edge, Firefox, Brave.
- [ ] Browser-Passwoerter nicht als ungeschuetzte CSV herumliegen lassen.
- [ ] Passwortmanager festlegen: Bitwarden, 1Password oder Proton Pass.
- [ ] Recovery-Codes fuer wichtige Accounts sichern.
- [ ] 2FA fuer E-Mail, GitHub, ChatGPT, Claude und Cloud-Speicher pruefen.

## 5. KI- und Projektwissen

- [ ] `MASTER-PROMPT-v3.md` sichern.
- [ ] `v3/policies/` sichern.
- [ ] `v3/chiefs/` sichern.
- [ ] `aufgaben/` sichern.
- [ ] Eigene Drehbuecher, Heilungswissen, Finanznotizen und Erfindungen getrennt als D3/D4 markieren.
- [ ] D3/D4-Daten nicht unverschluesselt in Cloud-Speicher legen.

## 6. Verschluesseltes Backup spaeter vorbereiten

- [ ] Entscheiden: externe SSD zuerst, Cloud spaeter.
- [ ] Fuer Cloud-Backup nur clientseitig verschluesselt planen, z.B. Restic + Backblaze B2.
- [ ] Separates starkes Backup-Passwort erzeugen und im Passwortmanager sichern.
- [ ] Restore-Test monatlich einplanen.

## 7. Restore-Test

- [ ] Einen kleinen Ordner testweise sichern.
- [ ] Den Ordner an einen anderen Ort wiederherstellen.
- [ ] Datei oeffnen und Inhalt pruefen.
- [ ] Im Backup-Protokoll notieren: Datum, Quelle, Ziel, Ergebnis.

## 8. Vor Aufgabe 002 bestaetigen

- [ ] Externe SSD ist vorhanden und funktioniert.
- [ ] BitLocker-Recovery-Key ist gesichert oder BitLocker-Status ist bewusst geklaert.
- [ ] KI-Ordner ist gesichert.
- [ ] Wichtigste Benutzerordner sind gesichert.
- [ ] Nexi weiss, wo die Backups liegen.
- [ ] Mindestens ein Restore-Test wurde erfolgreich gemacht.
