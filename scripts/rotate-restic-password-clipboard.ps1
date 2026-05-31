<#
Restic password rotation via clipboard.

Use case:
- The current RESTIC_PASSWORD is already in C:\AI\projects\09-video-analyse\.env.
- Nexi creates a NEW password in the password manager and copies it to the clipboard.
- This script reads the new password from the clipboard, writes it to a temp file,
  runs restic key passwd --new-password-file, updates .env only after success,
  then clears clipboard/temp file.
#>

[CmdletBinding()]
param(
    [string]$ResticExe = "C:\Users\nexil\Desktop\KI\tools\restic\restic.exe",
    [string]$Repository = "D:\Restic-Backup",
    [string]$EnvFile = "C:\AI\projects\09-video-analyse\.env",
    [string]$PythonExe = "C:\AI\projects\09-video-analyse\.venv-win\Scripts\python.exe",
    [string]$TelegramSend = "C:\AI\projects\09-video-analyse\scripts\telegram_send.py"
)

$ErrorActionPreference = "Stop"

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [Parameter(Mandatory = $true)] [string]$Name
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        return ""
    }
    foreach ($line in [System.IO.File]::ReadLines($Path, [System.Text.Encoding]::UTF8)) {
        $clean = $line.TrimStart([char]0xFEFF)
        if ($clean.StartsWith("$Name=")) {
            return $clean.Substring($Name.Length + 1)
        }
    }
    return ""
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

function Clear-ClipboardSafe {
    try {
        Set-Clipboard -Value " "
    }
    catch {
        Write-Warning "Konnte Zwischenablage nicht leeren: $($_.Exception.Message)"
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

if (-not (Test-Path -LiteralPath $ResticExe)) {
    throw "Restic wurde nicht gefunden: $ResticExe"
}
if (-not (Test-Path -LiteralPath $Repository)) {
    throw "Restic-Repository wurde nicht gefunden: $Repository"
}

$oldPassword = Get-DotEnvValue -Path $EnvFile -Name "RESTIC_PASSWORD"
if (-not $oldPassword) {
    throw "RESTIC_PASSWORD fehlt in $EnvFile. Passwort-Rotation kann nicht automatisch laufen."
}

Write-Host ""
Write-Host "RESTIC PASSWORD ROTATION" -ForegroundColor Cyan
Write-Host "WICHTIG: Erzeuge jetzt ein NEUES Restic-Passwort im Passwort-Manager." -ForegroundColor Yellow
Write-Host "Kopiere das NEUE Passwort in die Zwischenablage." -ForegroundColor Yellow
Write-Host "NICHT in dieses Fenster einfuegen. Nur kopieren, dann Enter druecken." -ForegroundColor Yellow
Read-Host "Wenn das NEUE Passwort in der Zwischenablage ist, Enter druecken"

$newPassword = Get-Clipboard -Raw
if ($null -eq $newPassword) {
    throw "Zwischenablage ist leer."
}
$newPassword = $newPassword.TrimEnd("`r", "`n")
if (-not $newPassword -or $newPassword.Length -lt 20) {
    throw "Sicherheitsstopp: Zwischenablage enthaelt kein plausibles neues Restic-Passwort."
}
if ($newPassword -eq $oldPassword) {
    throw "Sicherheitsstopp: Neues Passwort ist identisch mit dem alten. Bitte wirklich ein neues erzeugen."
}

$temp = Join-Path $env:TEMP ("restic-new-password-" + [guid]::NewGuid().ToString("N") + ".txt")
try {
    [System.IO.File]::WriteAllText($temp, $newPassword + "`n", [System.Text.UTF8Encoding]::new($false))
    $env:RESTIC_PASSWORD = $oldPassword

    Write-Host "Teste altes Passwort gegen Repo ..." -ForegroundColor Cyan
    & $ResticExe -r $Repository --no-cache snapshots | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Altes Passwort aus .env kann Repository nicht oeffnen."
    }

    Write-Host "Setze neues Repo-Passwort ..." -ForegroundColor Cyan
    & $ResticExe -r $Repository --no-cache key passwd --new-password-file $temp | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "restic key passwd fehlgeschlagen."
    }

    Remove-Item Env:\RESTIC_PASSWORD -ErrorAction SilentlyContinue
    $env:RESTIC_PASSWORD = $newPassword

    Write-Host "Verifiziere neues Passwort ..." -ForegroundColor Cyan
    & $ResticExe -r $Repository --no-cache snapshots | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Neues Passwort konnte Repository nach Rotation nicht oeffnen."
    }

    Set-DotEnvValue -Path $EnvFile -Name "RESTIC_PASSWORD" -Value $newPassword
    Write-Host "RESTIC_PASSWORD wurde in .env aktualisiert." -ForegroundColor Green
    Send-Telegram -Message "RESTIC Passwort-Rotation gruen: neues Passwort funktioniert, .env aktualisiert, Repo verifiziert. Bitte neues Passwort im Passwort-Manager behalten."
}
finally {
    Remove-Item Env:\RESTIC_PASSWORD -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue
    }
    Clear-ClipboardSafe
}
