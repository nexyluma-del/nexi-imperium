<#
AUFGABE 002 - Manuelles Restic-Backup starten
AUFGABE 010b - 2026-05-29 erweitert um C:\AI mit Exclude-Datei
AUFGABE 010c - 2026-05-30 erweitert um Docker-Exports nach D:\Restic-Sources

Dieses Skript:
- installiert nichts
- loescht keine Quelldaten
- speichert das Restic-Passwort nicht im Klartext
- fragt das Passwort interaktiv ab, wenn RESTIC_PASSWORD nicht gesetzt ist
- stoppt keine Docker-Container
#>

[CmdletBinding()]
param(
    [string]$ResticExe = "C:\Users\nexil\Desktop\KI\tools\restic\restic.exe",
    [string]$Repository = "D:\Restic-Backup",
    [string]$ExcludeFile = "D:\Restic-Backup\restic-excludes.txt",
    [string]$LogDir = "C:\Users\nexil\Desktop\KI\logs\backup",
    [string]$DockerExportRoot = "D:\Restic-Sources",
    [switch]$SkipDockerExports,
    [switch]$ExportOnly
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

function Import-ResticPasswordFromEnvFile {
    param([string]$EnvFile = "C:\AI\projects\09-video-analyse\.env")
    if ($env:RESTIC_PASSWORD -or -not (Test-Path -LiteralPath $EnvFile)) {
        return $false
    }
    foreach ($line in [System.IO.File]::ReadLines($EnvFile, [System.Text.Encoding]::UTF8)) {
        $clean = $line.TrimStart([char]0xFEFF).Trim()
        if (-not $clean -or $clean.StartsWith("#") -or -not $clean.StartsWith("RESTIC_PASSWORD=")) {
            continue
        }
        $env:RESTIC_PASSWORD = $clean.Substring("RESTIC_PASSWORD=".Length)
        return [bool]$env:RESTIC_PASSWORD
    }
    return $false
}

function Invoke-DockerExport {
    param(
        [Parameter(Mandatory = $true)] [string]$ScriptName,
        [Parameter(Mandatory = $true)] [string]$OutputRoot,
        [Parameter(Mandatory = $true)] [string]$LogPath
    )
    $scriptPath = Join-Path $PSScriptRoot $ScriptName
    if (-not (Test-Path -LiteralPath $scriptPath)) {
        throw "Docker-Export-Skript fehlt: $scriptPath"
    }

    "Docker-Export startet: $ScriptName -> $OutputRoot" | Tee-Object -FilePath $LogPath -Append
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath -OutputRoot $OutputRoot 2>&1 |
        Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) {
        throw "Docker-Export fehlgeschlagen: $ScriptName"
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

if (-not (Test-Path -LiteralPath $Repository)) {
    throw "Restic-Repository wurde nicht gefunden: $Repository"
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$logPath = Join-Path $LogDir ("backup-" + (Get-Date -Format "yyyy-MM-dd_HHmmss") + ".log")

if (-not $SkipDockerExports) {
    New-Item -ItemType Directory -Path $DockerExportRoot -Force | Out-Null
    Invoke-DockerExport -ScriptName "export-qdrant-snapshot.ps1" -OutputRoot (Join-Path $DockerExportRoot "qdrant") -LogPath $logPath
    Invoke-DockerExport -ScriptName "export-n8n-workflows.ps1" -OutputRoot (Join-Path $DockerExportRoot "n8n") -LogPath $logPath
    Invoke-DockerExport -ScriptName "export-openwebui-db.ps1" -OutputRoot (Join-Path $DockerExportRoot "openwebui") -LogPath $logPath
}
else {
    "Docker-Exports wurden per -SkipDockerExports uebersprungen." | Tee-Object -FilePath $logPath -Append
}

if ($ExportOnly) {
    "ExportOnly aktiv: Restic-Backup wird nicht gestartet." | Tee-Object -FilePath $logPath -Append
    Write-Host "Docker-Exports erfolgreich. Restic wurde wegen -ExportOnly nicht gestartet. Log: $logPath"
    return
}

$sources = @(
    "C:\Users\nexil\Desktop",
    "C:\Users\nexil\Documents",
    "C:\Users\nexil\Pictures",
    "C:\Users\nexil\Videos",
    "C:\AI",
    $DockerExportRoot
) | Where-Object { Test-PathPresent $_ }

if (-not $sources -or $sources.Count -eq 0) {
    throw "Keine gueltigen Backup-Quellen gefunden."
}

$passwordWasProvided = $false
Import-ResticPasswordFromEnvFile | Out-Null
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
