[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "BITLOCKER AKTIVIERUNG - VORBEREITET, NICHT BLIND AUSFUEHREN" -ForegroundColor Yellow
Write-Host "Nur starten, wenn Nexi explizit Go gegeben hat und Recovery-Key-Speicherung bereit ist." -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Tippe exakt BITLOCKER-AKTIVIEREN um fortzufahren"
if ($confirm -ne "BITLOCKER-AKTIVIEREN") {
    Write-Host "Abgebrochen. Keine Aenderung." -ForegroundColor Cyan
    exit 0
}

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Nicht als Administrator gestartet. Abbruch." -ForegroundColor Red
    exit 2
}

Write-Host "Aktiviere BitLocker fuer C: mit TPM + Recovery Password..." -ForegroundColor Cyan
Enable-BitLocker -MountPoint "C:" -EncryptionMethod XtsAes128 -UsedSpaceOnly -TpmProtector -RecoveryPasswordProtector

Write-Host ""
Write-Host "Status nach Aktivierung:" -ForegroundColor Cyan
manage-bde -status C:

Write-Host ""
Write-Host "WICHTIG: Recovery-Key jetzt in Passwortmanager/Standard Notes speichern und danach Codex den Status geben." -ForegroundColor Yellow

