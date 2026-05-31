<#
Restic Clean Restart V2 - one password entry

Fix fuer Passwort-Mismatch:
- liest das neue Restic-Passwort genau EINMAL
- setzt RESTIC_PASSWORD nur in dieser PowerShell-Session
- initialisiert damit das neue Repository
- startet danach das Backup mit exakt derselben RESTIC_PASSWORD-Variable
- loescht nichts; ein fehlgeschlagener Neuversuch wird nur umbenannt
#>

[CmdletBinding()]
param(
    [string]$ResticExe = "C:\Users\nexil\Desktop\KI\tools\restic\restic.exe",
    [string]$Repository = "D:\Restic-Backup",
    [string]$OldRepository = "D:\Restic-Backup-old-2026-05-31",
    [string]$BackupScript = "C:\Users\nexil\Desktop\KI\scripts\run-backup.ps1",
    [string]$LogDir = "C:\Users\nexil\Desktop\KI\logs\backup",
    [string]$PythonExe = "C:\AI\projects\09-video-analyse\.venv-win\Scripts\python.exe",
    [string]$TelegramSend = "C:\AI\projects\09-video-analyse\scripts\telegram_send.py"
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
    Write-Host "Vorhandenes neues Repo wird nicht geloescht, sondern umbenannt:" -ForegroundColor Yellow
    Write-Host "  $Path -> $target"
    Rename-Item -LiteralPath $Path -NewName (Split-Path -Leaf $target)
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
Write-Host "RESTIC CLEAN RESTART V2" -ForegroundColor Cyan
Write-Host "Wichtig: Diesmal wird das Passwort nur EINMAL gelesen und fuer Init + Backup wiederverwendet." -ForegroundColor Yellow
Write-Host "Wenn beim Einfuegen nur ein Stern sichtbar ist, kann das normal sein. Entscheidend ist, dass der gesamte Text aus dem Passwort-Manager in der Zwischenablage ist." -ForegroundColor Yellow
Write-Host ""

$securePassword = Read-Host "NEUES Restic-Passwort eingeben/einfuegen" -AsSecureString
$plainPassword = ConvertFrom-SecureStringToPlain -Secure $securePassword
if (-not $plainPassword -or $plainPassword.Length -lt 20) {
    throw "Sicherheitsstopp: Passwort fehlt oder ist zu kurz."
}

$env:RESTIC_PASSWORD = $plainPassword

try {
    Move-CurrentRepositoryAside -Path $Repository
    New-Item -ItemType Directory -Path $Repository -Force | Out-Null

    $oldExclude = Join-Path $OldRepository "restic-excludes.txt"
    $newExclude = Join-Path $Repository "restic-excludes.txt"
    if (Test-Path -LiteralPath $oldExclude) {
        Copy-Item -LiteralPath $oldExclude -Destination $newExclude -Force
    }

    Write-Host ""
    Write-Host "Initialisiere neues Repo mit RESTIC_PASSWORD aus dieser Session ..." -ForegroundColor Cyan
    & $ResticExe -r $Repository init
    if ($LASTEXITCODE -ne 0) {
        throw "restic init ist fehlgeschlagen."
    }

    $saveMessage = "Restic neues Repo ist initialisiert. WICHTIG: Passwort JETZT im Passwort-Manager speichern unter 'Restic Repo D:\Restic-Backup'. Ohne dieses Passwort sind Restores unmoeglich."
    Write-Host ""
    Write-Host $saveMessage -ForegroundColor Red
    Send-Telegram -Message $saveMessage
    Read-Host "Wenn das Passwort gespeichert ist, Enter druecken. Danach startet das erste Backup ohne erneute Passworteingabe"

    Write-Host ""
    Write-Host "Erstes frisches Backup startet jetzt mit derselben RESTIC_PASSWORD-Session." -ForegroundColor Cyan
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $BackupScript
    if ($LASTEXITCODE -ne 0) {
        throw "run-backup.ps1 meldete Exit-Code $LASTEXITCODE"
    }

    $snapshot = Get-LatestBackupSnapshot -Path $LogDir
    $repoSize = Get-RepoSizeGiB -Path $Repository
    $finalMessage = "Restic Clean Restart V2 fertig. Neuer Snapshot: $($snapshot.Snapshot). Repo-Groesse: $repoSize GiB. Log: $($snapshot.Log). Jetzt kann Nexi nach Review 'Go Stufe 2' geben."
    Write-Host ""
    Write-Host $finalMessage -ForegroundColor Green
    Send-Telegram -Message $finalMessage
}
finally {
    Remove-Item Env:\RESTIC_PASSWORD -ErrorAction SilentlyContinue
}
