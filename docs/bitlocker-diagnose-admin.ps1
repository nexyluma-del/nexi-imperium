[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "BITLOCKER DIAGNOSE - C:" -ForegroundColor Cyan
Write-Host "Dieses Skript muss als Administrator laufen." -ForegroundColor Yellow
Write-Host ""

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "STATUS: NICHT ALS ADMIN GESTARTET" -ForegroundColor Red
    Write-Host "Bitte PowerShell als Administrator oeffnen und erneut ausfuehren."
    exit 2
}

$statusText = & manage-bde -status C: 2>&1
$statusText | ForEach-Object { Write-Host $_ }

$joined = ($statusText -join "`n")
Write-Host ""
Write-Host "AUSWERTUNG:" -ForegroundColor Cyan

if ($joined -match "Schutzstatus:\s+Der Schutz ist aktiviert|Protection Status:\s+Protection On") {
    Write-Host "BITLOCKER_SCHUTZ: AKTIV" -ForegroundColor Green
} elseif ($joined -match "Schutzstatus:\s+Der Schutz ist deaktiviert|Protection Status:\s+Protection Off") {
    Write-Host "BITLOCKER_SCHUTZ: INAKTIV" -ForegroundColor Red
} else {
    Write-Host "BITLOCKER_SCHUTZ: UNKLAR - bitte Output an Codex geben" -ForegroundColor Yellow
}

if ($joined -match "Verschl[uü]sselt \(Prozent\):\s+([0-9,.]+)\s*%") {
    Write-Host ("VERSCHLUESSELUNG_PROZENT: " + $Matches[1] + "%")
}

if ($joined -match "Numerisches Kennwort|Numerical Password") {
    Write-Host "RECOVERY_KEY_PROTECTOR: VORHANDEN" -ForegroundColor Green
} else {
    Write-Host "RECOVERY_KEY_PROTECTOR: NICHT ERKANNT - vor Aktivierung klaeren" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Naechster Schritt: Output an Codex/Nexi geben. Nichts automatisch aktivieren." -ForegroundColor Cyan

