param(
    [string]$Distro = "Ubuntu-24.04",
    [string]$ProjectDir = "/mnt/c/AI/projects/09-video-analyse"
)

$ErrorActionPreference = "Stop"

function Register-MemoryTask {
    param(
        [string]$Name,
        [string]$ScriptArgs,
        [object]$Trigger,
        [string]$Description
    )

    $Action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d $Distro -- bash -lc `"cd '$ProjectDir' && .venv/bin/python $ScriptArgs`""
    Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger -Description $Description -Force | Out-Null
}

$BriefingScript = "scripts/memory_briefing.py"
$PushScanScript = "scripts/memory_ki_push_scan.py"

Register-MemoryTask `
    -Name "Nexi Memory-KI Morgenbriefing" `
    -ScriptArgs "$BriefingScript --kind morning --send-telegram" `
    -Trigger (New-ScheduledTaskTrigger -Daily -At 07:00) `
    -Description "Memory-KI Morgenbriefing via Telegram."

Register-MemoryTask `
    -Name "Nexi Memory-KI Mittagscheck" `
    -ScriptArgs "$BriefingScript --kind midday --send-telegram" `
    -Trigger (New-ScheduledTaskTrigger -Daily -At 13:00) `
    -Description "Memory-KI Mittagscheck via Telegram."

Register-MemoryTask `
    -Name "Nexi Memory-KI Tagesabschluss" `
    -ScriptArgs "$BriefingScript --kind evening --send-telegram" `
    -Trigger (New-ScheduledTaskTrigger -Daily -At 19:00) `
    -Description "Memory-KI Tagesabschluss via Telegram."

Register-MemoryTask `
    -Name "Nexi Memory-KI KI-PUSH Wochen-Scan" `
    -ScriptArgs "$PushScanScript --send-telegram" `
    -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 17:00) `
    -Description "Memory-KI scannt Desktop\KI\KI-PUSH fuer neue KI-Best-Practices."

Write-Host "Memory-KI Tasks registriert: 07:00, 13:00, 19:00 und KI-PUSH sonntags 17:00."
