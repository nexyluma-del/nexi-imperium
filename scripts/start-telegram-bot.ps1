<#
Startet Nexis Telegram-Bot im Hintergrund ueber WSL.
#>

[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu-24.04",
    [string]$ProjectDir = "/mnt/c/AI/projects/09-video-analyse"
)

$ErrorActionPreference = "Stop"

$check = wsl.exe -d $Distro -- bash -lc "ps -ef | grep 'scripts/telegram_bot.py' | grep -v grep || true"
if ($check -match "telegram_bot.py") {
    Write-Host "Telegram-Bot laeuft bereits:"
    Write-Host $check
    return
}

$windowsProjectDir = "C:\AI\projects\09-video-analyse"
$logDir = Join-Path $windowsProjectDir "logs\telegram"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stdout = Join-Path $logDir "bot.out"
$stderr = Join-Path $logDir "bot.err"

Start-Process `
    -FilePath "wsl.exe" `
    -ArgumentList @(
        "-d", $Distro,
        "--cd", $ProjectDir,
        "--exec", ".venv/bin/python", "-u", "-B", "scripts/telegram_bot.py"
    ) `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr

Start-Sleep -Seconds 2

$after = wsl.exe -d $Distro -- bash -lc "ps -ef | grep 'scripts/telegram_bot.py' | grep -v grep || true"
if ($after -match "telegram_bot.py") {
    Write-Host "Telegram-Bot gestartet."
    Write-Host $after
}
else {
    Write-Warning "Telegram-Bot konnte nicht bestaetigt werden. Log pruefen: C:\AI\projects\09-video-analyse\logs\telegram\bot.out"
}
