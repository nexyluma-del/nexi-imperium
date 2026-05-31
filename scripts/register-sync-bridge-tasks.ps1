param(
    [string]$Distro = "Ubuntu-24.04",
    [string]$ProjectDir = "/mnt/c/AI/projects/09-video-analyse"
)

$ErrorActionPreference = "Stop"

$TaskName = "Nexi KI-Sync Master-Context Wochenexport"
$ScriptArgs = "scripts/export_master_context.py --archive-old --send-telegram"
$Action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d $Distro -- bash -lc `"cd '$ProjectDir' && .venv/bin/python $ScriptArgs`""
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 18:00

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Description "Erstellt sonntags ein frisches Master-Context-Paket fuer externe KI-Sessions." `
    -Force | Out-Null

Write-Host "KI-Sync Wochenexport registriert: Sonntag 18:00."
