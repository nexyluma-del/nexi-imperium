<#
Restic hardening after BitLocker confirmation.

This script:
- generates a new 32-character password with a cryptographic RNG
- sends that password to Nexi via Telegram before changing the repository
- archives the current D:\Restic-Backup folder by renaming it, never deleting it
- initializes a fresh D:\Restic-Backup repository
- writes RESTIC_PASSWORD to the local project .env
- runs backup and restore-test non-interactively
- sends a final Telegram status

The generated password is never printed to stdout and never written to logs.
#>

[CmdletBinding()]
param(
    [string]$ResticExe = "C:\Users\nexil\Desktop\KI\tools\restic\restic.exe",
    [string]$Repository = "D:\Restic-Backup",
    [string]$EnvFile = "C:\AI\projects\09-video-analyse\.env",
    [string]$LogDir = "C:\Users\nexil\Desktop\KI\logs\backup",
    [string]$RunBackupScript = "C:\Users\nexil\Desktop\KI\scripts\run-backup.ps1",
    [string]$RunRestoreTestScript = "C:\Users\nexil\Desktop\KI\scripts\run-restore-test.ps1",
    [string]$PythonExe = "C:\AI\projects\09-video-analyse\.venv-win\Scripts\python.exe",
    [string]$TelegramSend = "C:\AI\projects\09-video-analyse\scripts\telegram_send.py"
)

$ErrorActionPreference = "Stop"

function New-ResticPassword {
    $alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    $bytes = [byte[]]::new(32)
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }
    $chars = for ($i = 0; $i -lt 32; $i++) {
        $alphabet[$bytes[$i] % $alphabet.Length]
    }
    -join $chars
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

function Send-TelegramStrict {
    param([Parameter(Mandatory = $true)] [string]$Message)
    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw "Telegram-Python fehlt: $PythonExe"
    }
    if (-not (Test-Path -LiteralPath $TelegramSend)) {
        throw "Telegram-Sendeskript fehlt: $TelegramSend"
    }

    $Message | & $PythonExe -B $TelegramSend
    if ($LASTEXITCODE -ne 0) {
        throw "Telegram-Push fehlgeschlagen."
    }
}

function Get-RepoSizeGiB {
    param([Parameter(Mandatory = $true)] [string]$Path)
    $sum = (Get-ChildItem -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    return "{0:N2}" -f (($sum -as [double]) / 1GB)
}

function Get-LatestSnapshot {
    param(
        [Parameter(Mandatory = $true)] [string]$ResticPath,
        [Parameter(Mandatory = $true)] [string]$RepoPath
    )
    $snapshotsJson = & $ResticPath snapshots -r $RepoPath --json
    if ($LASTEXITCODE -ne 0 -or -not $snapshotsJson) {
        throw "Restic snapshots konnte nicht gelesen werden."
    }
    $snapshots = $snapshotsJson | ConvertFrom-Json
    $latest = @($snapshots | Sort-Object time | Select-Object -Last 1)[0]
    $snapshotId = [string]$latest.short_id
    if (-not $snapshotId) {
        $snapshotId = ([string]$latest.id).Substring(0, 8)
    }
    [pscustomobject]@{
        Snapshot = $snapshotId
        Time = $latest.time
        Paths = $latest.paths
    }
}

function Assert-ExactPath {
    param(
        [Parameter(Mandatory = $true)] [string]$Actual,
        [Parameter(Mandatory = $true)] [string]$Expected
    )
    $actualFull = [System.IO.Path]::GetFullPath($Actual).TrimEnd("\")
    $expectedFull = [System.IO.Path]::GetFullPath($Expected).TrimEnd("\")
    if (-not [string]::Equals($actualFull, $expectedFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Sicherheitsstopp: Pfad '$Actual' ist nicht exakt '$Expected'."
    }
}

if (-not (Test-Path -LiteralPath $ResticExe)) {
    throw "Restic wurde nicht gefunden: $ResticExe"
}
if (-not (Test-Path -LiteralPath $RunBackupScript)) {
    throw "Backup-Skript fehlt: $RunBackupScript"
}
if (-not (Test-Path -LiteralPath $RunRestoreTestScript)) {
    throw "Restore-Test-Skript fehlt: $RunRestoreTestScript"
}

Assert-ExactPath -Actual $Repository -Expected "D:\Restic-Backup"
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$logPath = Join-Path $LogDir ("restic-hardening-" + (Get-Date -Format "yyyy-MM-dd_HHmmss") + ".log")
"Restic-Haertung gestartet: $(Get-Date)" | Tee-Object -FilePath $logPath

$newPassword = New-ResticPassword
$passwordMessage = @"
RESTIC-HAERTUNG: Neues Restic-Passwort fuer D:\Restic-Backup

$newPassword

JETZT im Passwortmanager speichern unter: Restic Repo D:\Restic-Backup
Ohne dieses Passwort ist ein Restore nicht moeglich.
"@
Send-TelegramStrict -Message $passwordMessage
"Neues Passwort wurde per Telegram gesendet. Passwort wird nicht geloggt." | Tee-Object -FilePath $logPath -Append

$archivePath = $null
$excludeSource = $null
if (Test-Path -LiteralPath $Repository) {
    $excludeCandidate = Join-Path $Repository "restic-excludes.txt"
    if (Test-Path -LiteralPath $excludeCandidate) {
        $excludeSource = Join-Path $env:TEMP ("restic-excludes-" + [guid]::NewGuid().ToString("N") + ".txt")
        Copy-Item -LiteralPath $excludeCandidate -Destination $excludeSource -Force
    }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $archivePath = "D:\Restic-Backup-notnagel-archiv-$stamp"
    if (Test-Path -LiteralPath $archivePath) {
        throw "Archivziel existiert bereits: $archivePath"
    }
    "Archiviere aktuelles Repo: $Repository -> $archivePath" | Tee-Object -FilePath $logPath -Append
    Rename-Item -LiteralPath $Repository -NewName (Split-Path -Leaf $archivePath)
}

New-Item -ItemType Directory -Path $Repository -Force | Out-Null
if ($excludeSource -and (Test-Path -LiteralPath $excludeSource)) {
    Copy-Item -LiteralPath $excludeSource -Destination (Join-Path $Repository "restic-excludes.txt") -Force
}

Set-DotEnvValue -Path $EnvFile -Name "RESTIC_PASSWORD" -Value $newPassword
$env:RESTIC_PASSWORD = $newPassword
$env:RESTIC_CACHE_DIR = "C:\AI\projects\09-video-analyse\.restic-cache"
New-Item -ItemType Directory -Path $env:RESTIC_CACHE_DIR -Force | Out-Null

"Initialisiere neues Repo: $Repository" | Tee-Object -FilePath $logPath -Append
& $ResticExe init -r $Repository 2>&1 | Tee-Object -FilePath $logPath -Append
if ($LASTEXITCODE -ne 0) {
    throw "restic init fehlgeschlagen."
}

"Starte frisches Backup ueber run-backup.ps1" | Tee-Object -FilePath $logPath -Append
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $RunBackupScript 2>&1 | Tee-Object -FilePath $logPath -Append
if ($LASTEXITCODE -ne 0) {
    throw "run-backup.ps1 fehlgeschlagen."
}

"Starte Restore-Test ueber run-restore-test.ps1" | Tee-Object -FilePath $logPath -Append
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $RunRestoreTestScript 2>&1 | Tee-Object -FilePath $logPath -Append
if ($LASTEXITCODE -ne 0) {
    throw "run-restore-test.ps1 fehlgeschlagen."
}

$latestSnapshot = Get-LatestSnapshot -ResticPath $ResticExe -RepoPath $Repository
$repoSize = Get-RepoSizeGiB -Path $Repository

$result = [pscustomobject]@{
    status = "green"
    snapshot = $latestSnapshot.Snapshot
    snapshot_time = $latestSnapshot.Time
    repo_size_gib = $repoSize
    archived_repo = $archivePath
    repository = $Repository
    env_file = $EnvFile
    log = $logPath
}
$resultPath = Join-Path $LogDir ("restic-hardening-result-" + (Get-Date -Format "yyyy-MM-dd_HHmmss") + ".json")
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $resultPath -Encoding UTF8

$finalMessage = "RESTIC-HAERTUNG GRUEN. Neues Repo: D:\Restic-Backup. Snapshot: $($latestSnapshot.Snapshot). Groesse: $repoSize GiB. Restore-Test bestanden. Altes Notnagel-Repo archiviert: $archivePath. Passwort wurde vor Start per Telegram gesendet und steht lokal in .env."
$finalMessage | Tee-Object -FilePath $logPath -Append
Send-TelegramStrict -Message $finalMessage

Remove-Item Env:\RESTIC_PASSWORD -ErrorAction SilentlyContinue
"Restic-Haertung beendet: $(Get-Date)" | Tee-Object -FilePath $logPath -Append
Write-Host "RESTIC_HARDENING_GREEN snapshot=$($latestSnapshot.Snapshot) size_gib=$repoSize result=$resultPath"
