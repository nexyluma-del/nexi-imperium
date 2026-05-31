<#
Restic Clean Restart - Clipboard Flow

Ziel: Windows/PowerShell SecureString-Paste-Probleme umgehen.
- Nexi kopiert das neue Restic-Passwort aus dem Passwort-Manager in die Zwischenablage.
- Dieses Skript liest es EINMAL aus der Zwischenablage.
- Es setzt RESTIC_PASSWORD fuer diese Session und speichert es in .env fuer unbeaufsichtigte Backups.
- Danach wird die Zwischenablage geleert.
- Es loescht kein Repository; vorhandene D:\Restic-Backup-Neuversuche werden nur umbenannt.
#>

[CmdletBinding()]
param(
    [string]$ResticExe = "C:\Users\nexil\Desktop\KI\tools\restic\restic.exe",
    [string]$Repository = "D:\Restic-Backup",
    [string]$OldRepository = "D:\Restic-Backup-old-2026-05-31",
    [string]$BackupScript = "C:\Users\nexil\Desktop\KI\scripts\run-backup.ps1",
    [string]$LogDir = "C:\Users\nexil\Desktop\KI\logs\backup",
    [string]$EnvFile = "C:\AI\projects\09-video-analyse\.env",
    [string]$PythonExe = "C:\AI\projects\09-video-analyse\.venv-win\Scripts\python.exe",
    [string]$TelegramSend = "C:\AI\projects\09-video-analyse\scripts\telegram_send.py"
)

$ErrorActionPreference = "Stop"

function Assert-ExactPath {
    param(
        [Parameter(Mandatory = $true)] [string]$Actual,
        [Parameter(Mandatory = $true)] [string]$Expected
    )
    $actualFull = [System.IO.Path]::GetFullPath($Actual).TrimEnd("\")
    $expectedFull = [System.IO.Path]::GetFullPath($Expected).TrimEnd("\")
    if (-not $actualFull.Equals($expectedFull, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Sicherheitsstopp: Unerwarteter Pfad. Erwartet '$expectedFull', bekommen '$actualFull'."
    }
}

function Send-Telegram {
    param([Parameter(Mandatory = $true)] [string]$Message)
    try {
        if ((Test-Path -LiteralPath $PythonExe) -and (Test-Path -LiteralPath $TelegramSend)) {
            & $PythonExe -B $TelegramSend $Message | Out-Null
        }
    }
    catch {
        Write-Warning "Telegram-Push fehlgeschlagen: $($_.Exception.Message)"
    }
}

function Set-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [Parameter(Mandatory = $true)] [string]$Name,
        [Parameter(Mandatory = $true)] [string]$Value
    )
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $lines = @()
    if (Test-Path -LiteralPath $Path) {
        $lines = [System.IO.File]::ReadAllLines($Path, [System.Text.Encoding]::UTF8)
    }
    $filtered = @($lines | Where-Object { $_.TrimStart([char]0xFEFF) -notmatch "^$([regex]::Escape($Name))=" })
    $filtered += "$Name=$Value"
    [System.IO.File]::WriteAllLines($Path, $filtered, [System.Text.UTF8Encoding]::new($false))
}

function Move-CurrentRepositoryAside {
    param([Parameter(Mandatory = $true)] [string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
    $target = "D:\Restic-Backup-failed-init-$stamp"
    Assert-ExactPath -Actual $Path -Expected "D:\Restic-Backup"
    if (Test-Path -LiteralPath $target) {
        throw "Ziel fuer fehlgeschlagenen Neuversuch existiert bereits: $target"
    }
    Write-Host "Vorhandenes neues Repo wird NICHT geloescht, sondern umbenannt:" -ForegroundColor Yellow
    Write-Host "  $Path -> $target"
    Rename-Item -LiteralPath $Path -NewName (Split-Path -Leaf $target)
}

function Get-RepoSizeGiB {
    param([Parameter(Mandatory = $true)] [string]$Path)
    $sum = (Get-ChildItem -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    return "{0:N2}" -f (($sum -as [double]) / 1GB)
}

function Get-LatestBackupSnapshot {
    param([Parameter(Mandatory = $true)] [string]$Path)
    $log = Get-ChildItem -LiteralPath $Path -Filter "backup-*.log" -ErrorAction Stop |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $log) {
        return @{ Snapshot = ""; Log = "" }
    }
    $text = Get-Content -LiteralPath $log.FullName -ErrorAction Stop
    $match = $text | Select-String -Pattern "snapshot ([0-9a-f]{8,64}) saved" | Select-Object -Last 1
    $snapshot = ""
    if ($match) {
        $snapshot = $match.Matches[0].Groups[1].Value
    }
    return @{ Snapshot = $snapshot; Log = $log.FullName }
}

Assert-ExactPath -Actual $Repository -Expected "D:\Restic-Backup"
Assert-ExactPath -Actual $OldRepository -Expected "D:\Restic-Backup-old-2026-05-31"

if (-not (Test-Path -LiteralPath $ResticExe)) {
    throw "Restic wurde nicht gefunden: $ResticExe"
}
if (-not (Test-Path -LiteralPath $BackupScript)) {
    throw "Backup-Skript wurde nicht gefunden: $BackupScript"
}
if (-not (Test-Path -LiteralPath $OldRepository)) {
    throw "Altes Repository wurde nicht gefunden: $OldRepository"
}

Write-Host ""
Write-Host "RESTIC CLIPBOARD-FIX" -ForegroundColor Cyan
Write-Host "1. Kopiere JETZT das neue Restic-Passwort aus deinem Passwort-Manager in die Zwischenablage." -ForegroundColor Yellow
Write-Host "2. Komm zurueck in dieses Fenster und druecke Enter." -ForegroundColor Yellow
Write-Host "Das Passwort wird NICHT angezeigt. Die Zwischenablage wird danach geleert." -ForegroundColor Yellow
Read-Host "Enter druecken, sobald das Passwort in der Zwischenablage ist"

$password = Get-Clipboard -Raw
if ($null -eq $password) {
    throw "Zwischenablage ist leer."
}
$password = $password.TrimEnd("`r", "`n")
if (-not $password -or $password.Length -lt 20) {
    throw "Sicherheitsstopp: Zwischenablage enthaelt kein plausibles Restic-Passwort."
}

$env:RESTIC_PASSWORD = $password
Set-DotEnvValue -Path $EnvFile -Name "RESTIC_PASSWORD" -Value $password
try {
    Set-Clipboard -Value " "
}
catch {
    Write-Warning "Konnte Zwischenablage nicht leeren: $($_.Exception.Message)"
}

try {
    Move-CurrentRepositoryAside -Path $Repository
    New-Item -ItemType Directory -Path $Repository -Force | Out-Null

    $oldExclude = Join-Path $OldRepository "restic-excludes.txt"
    $newExclude = Join-Path $Repository "restic-excludes.txt"
    if (Test-Path -LiteralPath $oldExclude) {
        Copy-Item -LiteralPath $oldExclude -Destination $newExclude -Force
    }

    Write-Host ""
    Write-Host "Initialisiere neues Repo mit Passwort aus Zwischenablage ..." -ForegroundColor Cyan
    & $ResticExe -r $Repository init
    if ($LASTEXITCODE -ne 0) {
        throw "restic init ist fehlgeschlagen."
    }

    Write-Host ""
    Write-Host "Verifiziere neues Repo ..." -ForegroundColor Cyan
    & $ResticExe -r $Repository snapshots | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Repo-Verifikation nach Init fehlgeschlagen."
    }

    $saveMessage = "Restic neues Repo ist initialisiert. Passwort ist in .env fuer unbeaufsichtigte Backups gespeichert. WICHTIG: Passwort auch im Passwort-Manager unter 'Restic Repo D:\Restic-Backup' speichern, sonst Datenverlust beim Restore."
    Write-Host ""
    Write-Host $saveMessage -ForegroundColor Red
    Send-Telegram -Message $saveMessage
    Read-Host "Wenn Passwort im Manager gespeichert ist, Enter druecken. Danach startet das erste Backup"

    Write-Host ""
    Write-Host "Erstes frisches Backup startet jetzt." -ForegroundColor Cyan
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $BackupScript
    if ($LASTEXITCODE -ne 0) {
        throw "run-backup.ps1 meldete Exit-Code $LASTEXITCODE"
    }

    $snapshot = Get-LatestBackupSnapshot -Path $LogDir
    $repoSize = Get-RepoSizeGiB -Path $Repository
    $finalMessage = "Restic Clipboard-Fix fertig. Neuer Snapshot: $($snapshot.Snapshot). Repo-Groesse: $repoSize GiB. Log: $($snapshot.Log). Jetzt kann Nexi nach Review 'Go Stufe 2' geben."
    Write-Host ""
    Write-Host $finalMessage -ForegroundColor Green
    Send-Telegram -Message $finalMessage
}
finally {
    Remove-Item Env:\RESTIC_PASSWORD -ErrorAction SilentlyContinue
}
