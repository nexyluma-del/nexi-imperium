<#
Restic Clean Restart - 2026-05-31

Dieses Skript:
- loescht nichts
- benennt das alte Repository nur um
- initialisiert ein neues Repository interaktiv
- erinnert Nexi direkt nach Init, das neue Passwort im Passwort-Manager zu speichern
- startet danach das erste frische Backup mit allen Quellen aus run-backup.ps1
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

Assert-ExactPath -Actual $Repository -Expected "D:\Restic-Backup"
Assert-ExactPath -Actual $OldRepository -Expected "D:\Restic-Backup-old-2026-05-31"

if (-not (Test-Path -LiteralPath $ResticExe)) {
    throw "Restic wurde nicht gefunden: $ResticExe"
}
if (-not (Test-Path -LiteralPath $BackupScript)) {
    throw "Backup-Skript wurde nicht gefunden: $BackupScript"
}
if (-not (Test-Path -LiteralPath $Repository)) {
    throw "Altes Repository wurde nicht gefunden: $Repository"
}
if (Test-Path -LiteralPath $OldRepository) {
    throw "Ziel fuer altes Repository existiert bereits: $OldRepository"
}

Write-Host ""
Write-Host "RESTIC CLEAN RESTART" -ForegroundColor Cyan
Write-Host "Altes Repo wird umbenannt, nicht geloescht:" -ForegroundColor Yellow
Write-Host "  $Repository -> $OldRepository"
Write-Host ""

Rename-Item -LiteralPath $Repository -NewName (Split-Path -Leaf $OldRepository)
New-Item -ItemType Directory -Path $Repository -Force | Out-Null

Write-Host "Neues Repository wird jetzt initialisiert." -ForegroundColor Cyan
Write-Host "Bitte neues Restic-Passwort eingeben und WIRKLICH merken/speichern." -ForegroundColor Yellow
& $ResticExe -r $Repository init
if ($LASTEXITCODE -ne 0) {
    throw "restic init ist fehlgeschlagen."
}

$oldExclude = Join-Path $OldRepository "restic-excludes.txt"
$newExclude = Join-Path $Repository "restic-excludes.txt"
if (Test-Path -LiteralPath $oldExclude) {
    Copy-Item -LiteralPath $oldExclude -Destination $newExclude -Force
}

$saveMessage = "Restic neues Repo ist initialisiert. WICHTIG: Passwort JETZT im Passwort-Manager speichern unter 'Restic Repo D:\Restic-Backup'. Ohne dieses Passwort sind Restores unmoeglich."
Write-Host ""
Write-Host $saveMessage -ForegroundColor Red
Send-Telegram -Message $saveMessage
Read-Host "Wenn das Passwort gespeichert ist, Enter druecken. Danach startet das erste Backup"

Write-Host ""
Write-Host "Erstes frisches Backup startet jetzt." -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $BackupScript
if ($LASTEXITCODE -ne 0) {
    throw "run-backup.ps1 meldete Exit-Code $LASTEXITCODE"
}

$snapshot = Get-LatestBackupSnapshot -Path $LogDir
$repoSize = Get-RepoSizeGiB -Path $Repository
$finalMessage = "Restic Clean Restart fertig. Neuer Snapshot: $($snapshot.Snapshot). Repo-Groesse: $repoSize GiB. Log: $($snapshot.Log). Jetzt kann Nexi nach Review 'Go Stufe 2' geben."
Write-Host ""
Write-Host $finalMessage -ForegroundColor Green
Send-Telegram -Message $finalMessage
