param(
    [string]$Distro = "Ubuntu-24.04",
    [string]$ProjectDir = "/mnt/c/AI/projects/09-video-analyse"
)

$ErrorActionPreference = "Stop"

$TaskName = "Nexi Sofinello Batch B Resume"
$ScriptArgs = "scripts/resume_sofinello_batch_b.py"
$Action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d $Distro -- bash -lc `"cd '$ProjectDir' && .venv/bin/python $ScriptArgs`""
$Trigger = New-ScheduledTaskTrigger -Daily -At 02:30

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Description "Startet Sofinello Batch B nach Gemini-Quota-Reset erneut, wenn er nicht laeuft und noch nicht fertig ist." `
    -Force | Out-Null

Write-Host "Sofinello Batch B Resume registriert: taeglich 02:30."
