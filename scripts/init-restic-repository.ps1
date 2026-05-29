<#
AUFGABE 002 - Restic-Repository initialisieren

Dieses Skript:
- legt D:\Restic-Backup an, falls es nicht existiert
- fragt das Restic-Passwort interaktiv ab
- speichert das Passwort nicht im Klartext
- initialisiert das Repository nur, wenn es noch nicht initialisiert ist
#>

[CmdletBinding()]
param(
    [string]$ResticExe = "C:\Users\nexil\Desktop\KI\tools\restic\restic.exe",
    [string]$Repository = "D:\Restic-Backup"
)

$ErrorActionPreference = "Stop"

function ConvertFrom-SecureStringToPlain {
    param([Parameter(Mandatory = $true)] [Security.SecureString]$Secure)
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

if (-not (Test-Path -LiteralPath $ResticExe)) {
    $cmd = Get-Command restic -ErrorAction SilentlyContinue
    if ($cmd) {
        $ResticExe = $cmd.Source
    }
    else {
        throw "Restic wurde nicht gefunden. Erwartet: $ResticExe"
    }
}

if (-not (Test-Path -LiteralPath "D:\")) {
    throw "Laufwerk D: wurde nicht gefunden. Bitte externe SSD anschliessen."
}

New-Item -ItemType Directory -Path $Repository -Force | Out-Null

$securePassword = Read-Host "Restic-Passwort eingeben" -AsSecureString
$env:RESTIC_PASSWORD = ConvertFrom-SecureStringToPlain -Secure $securePassword

try {
    $configPath = Join-Path $Repository "config"
    if (Test-Path -LiteralPath $configPath) {
        Write-Host "Repository ist bereits initialisiert: $Repository" -ForegroundColor Green
        exit 0
    }

    & $ResticExe -r $Repository init
    if ($LASTEXITCODE -ne 0) {
        throw "Restic init meldete Exit-Code $LASTEXITCODE"
    }

    Write-Host "Repository erfolgreich initialisiert: $Repository" -ForegroundColor Green
}
finally {
    Remove-Item Env:\RESTIC_PASSWORD -ErrorAction SilentlyContinue
}
