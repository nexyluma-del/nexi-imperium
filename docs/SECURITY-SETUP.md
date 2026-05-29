# SECURITY-SETUP - Aufgabe 003

**Status:** abgeschlossen am 2026-05-29
**Phase:** 0B Sicherheit - Teil 2
**Datenklasse:** D1 intern
**Risiko-Level:** R3 fuer BitLocker-Aktivierung, R0/R1 fuer Dokumentation und Audit

## 1. Voraussetzungen

| Punkt | Status |
|---|---|
| Aufgabe 001 Bestandsaufnahme | abgeschlossen |
| Aufgabe 002 Restic-Backup | abgeschlossen |
| Restic-Passwort | in Standard Notes gespeichert, von Nexi bestaetigt |
| Lokales Backup | `D:\Restic-Backup`, Snapshot `6a94fd33` |
| Restore-Test | bestanden |

## 2. BitLocker-Status

**Status:** geprueft am 2026-05-29 mit `manage-bde -status`.

Ergebnis:

| Laufwerk | Rolle | BitLocker | Verschluesselt | Methode | Schutzstatus | Hinweis |
|---|---|---|---|---|---|---|
| `C:` Windows | Betriebssystemvolume | aktiv | 100.0 % | XTS-AES 128 | Schutz aktiviert | Schluesselschutz: Numerisches Kennwort + TPM |
| `D:` KINGSTON | Datenvolume / externe SSD | nicht aktiv | 0.0 % | keine | Schutz deaktiviert | Soll aktuell nicht mit BitLocker verschluesselt werden |

Wichtig:
- BitLocker-Aktivierung ist fuer `C:` nicht noetig, weil Schutz bereits aktiv ist.
- `D:` bleibt unverschluesselt, damit Restic-Repository und externe SSD unkompliziert funktionieren.
- Naechster Pflichtschritt: Recovery-Key fuer `C:` lokal anzeigen lassen und in Standard Notes sichern.

## 3. Recovery-Key-Strategie

**Status:** Recovery-Key fuer `C:` wurde von Nexi am 2026-05-29 in Standard Notes gespeichert.

Empfohlener Standard-Notes-Eintrag:

```text
Titel: BitLocker Recovery Key C:
Datum: 2026-05-29
Geraet: HP Omen Max / Nexi KI-Laptop
Laufwerk: C:
Recovery-Key: [lokal aus PowerShell kopieren, NICHT in Chat posten]
```

Zusaetzliche Empfehlung:
- Recovery-Key zusaetzlich auf Papier sichern.
- Nicht nur auf dem Laptop speichern.
- Nicht unverschluesselt auf Desktop oder in eine normale Textdatei legen.

## 4. BitLocker-Aktivierung

**Status:** nicht noetig fuer `C:`, da BitLocker bereits aktiv ist.

Regel:
BitLocker-Aktivierung auf `C:` darf nur nach explizitem R3-Approval von Nexi passieren.

## 5. Smartphone / Authenticator

Nexi nutzt: **iPhone**

Empfehlung:
- Primaer: 2FAS Authenticator oder Ente Auth, weil beide aktiv gepflegt und backup-faehig sind.
- Alternative: Authy, wenn Komfort wichtiger ist als maximale Kontrolle.
- Raivo OTP wird nicht mehr als erste Empfehlung gesetzt, weil die App-Historie/Vertrauenslage spaeter geprueft werden sollte.

Pflichtregel:
Backup-Codes jedes Accounts in Standard Notes sichern.

## 6. 2FA-Audit - Prioritaet

Von Nexi priorisierte Accounts:

| Prioritaet | Account | 2FA-Status | Empfehlung |
|---|---|---|---|
| 1 | Instagram | aktiv auf iPhone, von Nexi bestaetigt | Backup-Codes in Standard Notes sichern |
| 2 | ChatGPT / OpenAI | aktiv auf iPhone, von Nexi bestaetigt | Recovery-Codes in Standard Notes sichern |
| 3 | Claude / Anthropic | aktiv auf iPhone, von Nexi bestaetigt | Login-Methode und Sitzungen regelmaessig pruefen |
| 4 | Telegram | aktiv auf iPhone, von Nexi bestaetigt | 2-Step-Verifizierungspasswort und Recovery-E-Mail sichern |
| 5 | Standard Notes | aktiv auf iPhone, von Nexi bestaetigt | Recovery-Optionen und Account-Mail schuetzen |
| 6 | WhatsApp | aktiv auf iPhone, von Nexi bestaetigt | 6-stellige PIN und Recovery-E-Mail sichern |

Weitere empfohlene Accounts fuer spaeter:
- Apple ID
- Google
- Microsoft
- GitHub
- PayPal/Banking, falls online genutzt

## 6A. 2FA-Audit - konkrete Pruefschritte

Wichtig:
- Codex aendert keine Account-Einstellungen.
- Nexi prueft die Accounts selbst und meldet nur den Status: `aktiv`, `nicht aktiv` oder `unsicher`.
- Backup-Codes und Recovery-Codes werden in Standard Notes gespeichert, nicht im Chat.

### Instagram

Quelle: Instagram Help Center.

Pruefen:
1. Instagram App oeffnen.
2. Einstellungen / Accounts Center.
3. `Password and security` / Passwort und Sicherheit.
4. `Two-factor authentication` / Zwei-Faktor-Authentifizierung.
5. Authenticator-App bevorzugen, SMS nur als Reserve.
6. Backup-Codes speichern.

Status: aktiv auf iPhone, von Nexi bestaetigt

### ChatGPT / OpenAI

Quelle: OpenAI Help Center.

Pruefen:
1. ChatGPT / OpenAI Account oeffnen.
2. Account-/Security-Einstellungen oeffnen.
3. MFA aktivieren, wenn noch nicht aktiv.
4. Authenticator-App bevorzugen.
5. Recovery-Codes speichern.

Status: aktiv auf iPhone, von Nexi bestaetigt

### Claude / Anthropic

Quelle: Claude Help Center.

Pruefen:
1. Claude Account oeffnen.
2. Login-Methode feststellen: Google Login oder E-Mail-Link.
3. Wenn Google Login genutzt wird: Google-Account mit 2FA absichern.
4. Wenn E-Mail-Link genutzt wird: E-Mail-Account mit 2FA absichern.
5. Claude-Sitzungen pruefen und unbekannte Sitzungen abmelden.

Status: aktiv auf iPhone, von Nexi bestaetigt

### Telegram

Quelle: Telegram FAQ.

Pruefen:
1. Telegram App oeffnen.
2. Settings / Einstellungen.
3. Privacy and Security / Privatsphaere und Sicherheit.
4. Two-Step Verification / Zwei-Schritt-Verifizierung aktivieren.
5. Starkes Passwort setzen.
6. Recovery-E-Mail setzen und die E-Mail ebenfalls mit 2FA schuetzen.

Status: aktiv auf iPhone, von Nexi bestaetigt

### Standard Notes

Quelle: Standard Notes Security/Features.

Pruefen:
1. Standard Notes Account-Einstellungen oeffnen.
2. Two-Factor Authentication aktivieren, falls noch nicht aktiv.
3. Recovery-/Backup-Optionen dokumentieren.
4. Fuer kritische Notizen starke Account-Sicherheit beibehalten.

Status: aktiv auf iPhone, von Nexi bestaetigt

### WhatsApp

Quelle: WhatsApp Help Center.

Pruefen:
1. WhatsApp oeffnen.
2. Settings / Einstellungen.
3. Account.
4. Two-step verification / Zwei-Schritt-Verifizierung.
5. 6-stellige PIN setzen.
6. Recovery-E-Mail hinterlegen und in Standard Notes dokumentieren.

Status: aktiv auf iPhone, von Nexi bestaetigt

### Apple ID / Apple Account - dringend empfohlen, obwohl nicht in Top-6

Quelle: Apple Support.

Pruefen:
1. iPhone Einstellungen oeffnen.
2. Oben auf deinen Namen tippen.
3. Sign-In & Security / Anmeldung & Sicherheit.
4. Two-Factor Authentication pruefen.
5. Trusted Phone Numbers und trusted devices pruefen.

Status: aktiv auf iPhone, von Nexi bestaetigt

### Authenticator auf iPhone

Optionen:
- Apple Passwords kann Verification Codes lokal erzeugen und automatisch ausfuellen.
- 2FAS Authenticator ist eine separate Authenticator-App mit iOS-Backup-Funktion.
- Ente Auth ist ebenfalls eine Option, falls Nexi eine separate App bevorzugt.

Empfehlung fuer Start:
1. Wenn du maximal einfach starten willst: Apple Passwords / iPhone Verification Codes.
2. Wenn du eine getrennte Authenticator-App willst: 2FAS Authenticator.
3. Egal welche Option: Backup-/Recovery-Codes der Websites zusaetzlich in Standard Notes speichern.

## 6B. Quellen fuer 2FA-Anleitung

- Instagram: https://www.facebook.com/help/instagram/566810106808145
- OpenAI MFA: https://help.openai.com/en/articles/7967234-enabling-multi-factor-authentication-mfa-with-openai
- Claude Login/Sessions: https://support.claude.com/en/articles/13189465-log-in-to-your-claude-account
- Telegram FAQ: https://telegram.org/faq
- Standard Notes Security: https://standardnotes.com/help/security
- Standard Notes Features / 2FA: https://standardnotes.com/features
- WhatsApp two-step verification: https://faq.whatsapp.com/general/verification/about-two-step-verification
- Apple Account 2FA: https://support.apple.com/guide/iphone/use-two-factor-authentication-iphd709a3c46/ios
- Apple Verification Codes: https://support.apple.com/en-ca/guide/iphone/ipha6173c19f/ios
- 2FAS iOS Backup: https://2fas.com/support/2fas-auth-mobile-app/does-ios-backup-work-with-2fas/

## 7. Passwortmanager-Strategie

Aktueller Stand:
Nexi nutzt **Standard Notes** fuer sensible Passwoerter/Keys.

Bewertung:
Standard Notes ist fuer Recovery-Keys, Backup-Passwoerter und hochsensible Geheimnisse okay, weil Ende-zu-Ende-verschluesselt.

Empfehlung:
- Standard Notes weiter fuer Recovery-Keys, Backup-Secrets, BitLocker-Key, Restic-Passwort und 2FA-Backup-Codes nutzen.
- Fuer den Start ist Standard Notes ausreichend, solange Nexi pro Account eigene starke Passwoerter nutzt.
- Optional spaeter Bitwarden oder 1Password fuer Alltags-Passwoerter, Browser-Autofill und Passwortgenerierung ergaenzen.
- Keine Migration erzwingen, solange Standard Notes sauber genutzt wird.

Entscheidung fuer Phase 0B:
**Standard Notes bleibt der Hauptspeicher fuer kritische Secrets.**

Empfohlene Standard-Notes-Struktur:

```text
SECURITY / BitLocker Recovery Key C:
SECURITY / Restic Backup Imperium
SECURITY / 2FA Backup Codes - Instagram
SECURITY / 2FA Backup Codes - ChatGPT OpenAI
SECURITY / 2FA Backup Codes - Claude Anthropic
SECURITY / 2FA Telegram Recovery
SECURITY / 2FA Standard Notes Recovery
SECURITY / 2FA WhatsApp PIN + Recovery E-Mail
SECURITY / Apple ID Recovery / Trusted Devices
```

## 7A. Backup-Codes-Check

Ziel:
2FA ist nur dann wirklich sicher, wenn Nexi nicht beim Verlust des iPhones ausgesperrt ist.

Checkliste:

| Account | Was sichern | Status |
|---|---|---|
| Instagram | Backup-Codes / Recovery-Codes | in Standard Notes gespeichert, von Nexi bestaetigt |
| ChatGPT / OpenAI | Recovery-Codes oder MFA-Recovery-Option | in Standard Notes gespeichert, von Nexi bestaetigt |
| Claude / Anthropic | Login-Methode, E-Mail-Account absichern, aktive Sitzungen pruefen | in Standard Notes gespeichert, von Nexi bestaetigt |
| Telegram | 2-Step-Verifizierungspasswort + Recovery-E-Mail | in Standard Notes gespeichert, von Nexi bestaetigt |
| Standard Notes | 2FA-Recovery/Account-Recovery-Optionen | in Standard Notes gespeichert, von Nexi bestaetigt |
| WhatsApp | 6-stellige PIN + Recovery-E-Mail | in Standard Notes gespeichert, von Nexi bestaetigt |
| Apple ID | Trusted Devices, trusted phone numbers, ggf. Recovery Key/Recovery Contact | in Standard Notes gespeichert, von Nexi bestaetigt |

Codex hat keine Codes gesehen und soll sie nicht sehen. Nexi prueft lokal und bestaetigt nur, wenn sie in Standard Notes gespeichert sind.

## 8. Offene Punkte

- [x] BitLocker-Status per Admin-PowerShell pruefen.
- [x] Recovery-Key lokal anzeigen lassen und in Standard Notes speichern.
- [x] BitLocker-Aktivierung nicht noetig; kein R3-Approval erforderlich.
- [x] 2FA-Status der priorisierten Accounts von Nexi erfragen/abgleichen.
- [x] Authenticator-App-Entscheidung treffen: iPhone wird genutzt; Standard Notes bleibt Secret-Speicher.
- [x] Backup-Codes / Recovery-Optionen der priorisierten Accounts in Standard Notes bestaetigen.
- [x] SECURITY-SETUP.md final aktualisieren.

## 9. Abschluss Aufgabe 003

Ergebnis:
- BitLocker auf `C:` ist aktiv.
- BitLocker-Recovery-Key fuer `C:` ist in Standard Notes gespeichert.
- Restic-Backup aus Aufgabe 002 ist vorhanden und Restore-getestet.
- 2FA ist auf dem iPhone fuer alle priorisierten Accounts aktiv.
- Backup-/Recovery-Codes fuer alle priorisierten Accounts sind in Standard Notes gespeichert.
- Standard Notes bleibt in Phase 0B der Hauptspeicher fuer kritische Secrets.

Naechster empfohlener Schritt:
Aufgabe 004 - WSL2 + Docker Desktop vorbereiten/installieren.
