<#
AUFGABE 002 - Manuelles Restic-Backup starten
AUFGABE 010b - 2026-05-29 erweitert um C:\AI mit Exclude-Datei

Dieses Skript:
- installiert nichts
- loescht keine Quelldaten
- speichert das Restic-Passwort nicht im Klartext
- fragt das Passwort interaktiv ab, wenn RESTIC_PASSWORD nicht gesetzt ist
#>

[CmdletBinding()]
param(
    [string]$ResticExe = "C:\Users\nexil\Desktop\KI\tools\restic\restic.exe",
    [string]$Repository = "D:\Restic-Backup",
    [string]$ExcludeFile = "D:\Restic-Backup\restic-excludes.txt",
    [string]$LogDir = "C:\Users\nexil\Desktop\KI\logs\backup"
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

function Test-PathPresent {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        return $true
    }
    Write-Warning "Quelle nicht gefunden und wird uebersprungen: $Path"
    return $false
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

if (-not (Test-Path -LiteralPath $Repository)) {
    throw "Restic-Repository wurde nicht gefunden: $Repository"
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$logPath = Join-Path $LogDir ("backup-" + (Get-Date -Format "yyyy-MM-dd_HHmmss") + ".log")

$sources = @(
    "C:\Users\nexil\Desktop",
    "C:\Users\nexil\Documents",
    "C:\Users\nexil\Pictures",
    "C:\Users\nexil\Videos",
    "C:\AI"
) | Where-Object { Test-PathPresent $_ }

if (-not $sources -or $sources.Count -eq 0) {
    throw "Keine gueltigen Backup-Quellen gefunden."
}

$passwordWasProvided = $false
if (-not $env:RESTIC_PASSWORD) {
    $securePassword = Read-Host "Restic-Passwort eingeben" -AsSecureString
    $env:RESTIC_PASSWORD = ConvertFrom-SecureStringToPlain -Secure $securePassword
    $passwordWasProvided = $true
}

try {
    $start = Get-Date
    "Backup gestartet: $start" | Tee-Object -FilePath $logPath
    "Repository: $Repository" | Tee-Object -FilePath $logPath -Append
    "Quellen:" | Tee-Object -FilePath $logPath -Append
    $sources | ForEach-Object { " - $_" | Tee-Object -FilePath $logPath -Append }

    $excludeArgs = @()
    if (Test-Path -LiteralPath $ExcludeFile) {
        "Exclude-Datei: $ExcludeFile" | Tee-Object -FilePath $logPath -Append
        $excludeArgs = @("--exclude-file", $ExcludeFile)
    }
    else {
        Write-Warning "Exclude-Datei nicht gefunden, Backup laeuft ohne Excludes: $ExcludeFile"
        "WARNUNG: Exclude-Datei nicht gefunden: $ExcludeFile" | Tee-Object -FilePath $logPath -Append
    }

    & $ResticExe -r $Repository backup @sources @excludeArgs --verbose 2>&1 | Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) {
        throw "Restic backup meldete Exit-Code $LASTEXITCODE"
    }

    $end = Get-Date
    $duration = New-TimeSpan -Start $start -End $end
    "Backup beendet: $end" | Tee-Object -FilePath $logPath -Append
    "Dauer: $($duration.ToString())" | Tee-Object -FilePath $logPath -Append

    & $ResticExe -r $Repository snapshots 2>&1 | Tee-Object -FilePath $logPath -Append
    Write-Host "Backup erfolgreich. Log: $logPath"
}
finally {
    if ($passwordWasProvided) {
        Remove-Item Env:\RESTIC_PASSWORD -ErrorAction SilentlyContinue
    }
}
