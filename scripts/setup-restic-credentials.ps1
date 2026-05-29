<#
AUFGABE 002 - Restic-Passwort richtig sichern

Dieses Skript fuehrt keine Einrichtung aus. Es zeigt nur die Anleitung.
#>

Write-Host ""
Write-Host "RESTIC-PASSWORT - WICHTIG" -ForegroundColor Yellow
Write-Host ""
Write-Host "Ohne Restic-Passwort ist das Backup unbrauchbar. Es gibt keine Hintertuer."
Write-Host ""
Write-Host "Empfohlene Ablage fuer Nexi:"
Write-Host "1. In Standard Notes als eigenen Eintrag speichern:"
Write-Host "   Titel: Restic Backup Imperium"
Write-Host "   Felder: Repository = D:\Restic-Backup, Passwort = [dein Passwort]"
Write-Host "2. Zusaetzlich optional auf Papier notieren und sicher weglegen."
Write-Host "3. Niemals nur als Klartext-Datei auf demselben Laptop speichern."
Write-Host ""
Write-Host "Empfohlenes Passwort:"
Write-Host "- mindestens 24 Zeichen"
Write-Host "- besser: 5-6 zufaellige Woerter plus Zahlen/Sonderzeichen"
Write-Host "- nicht identisch mit Windows, E-Mail, ChatGPT, Claude oder Standard Notes"
Write-Host ""
Write-Host "Beim Start von run-backup.ps1 oder run-restore-test.ps1 wirst du interaktiv danach gefragt."
Write-Host "Das Passwort wird dabei nicht in den Skripten gespeichert."
Write-Host ""

