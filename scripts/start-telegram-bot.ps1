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

$command = "cd '$ProjectDir' && mkdir -p logs/telegram && nohup .venv/bin/python scripts/telegram_bot.py >> logs/telegram/bot.out 2>&1 & echo started"
& wsl.exe -d $Distro -- bash -lc $command | Out-Null
Start-Sleep -Seconds 2

$after = wsl.exe -d $Distro -- bash -lc "ps -ef | grep 'scripts/telegram_bot.py' | grep -v grep || true"
if ($after -match "telegram_bot.py") {
    Write-Host "Telegram-Bot gestartet."
    Write-Host $after
}
else {
    Write-Warning "Telegram-Bot konnte nicht bestaetigt werden. Log pruefen: C:\AI\projects\09-video-analyse\logs\telegram\bot.out"
}
