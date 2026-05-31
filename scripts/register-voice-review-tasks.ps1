param(
    [string]$ProjectDir = "C:\AI\projects\09-video-analyse"
)

$ErrorActionPreference = "Stop"

$Python = Join-Path $ProjectDir ".venv-win\Scripts\python.exe"
$Script = Join-Path $ProjectDir "scripts\voice_review_reminder.py"

if (-not (Test-Path -LiteralPath $Python)) {
    & (Join-Path $ProjectDir "scripts\install-voice-capture-deps.ps1") -ProjectDir $ProjectDir
}

$DailyAction = New-ScheduledTaskAction -Execute $Python -Argument "`"$Script`" --kind daily" -WorkingDirectory $ProjectDir
$DailyTrigger = New-ScheduledTaskTrigger -Daily -At 19:00
Register-ScheduledTask `
    -TaskName "Nexi Voice Memory Daily Review" `
    -Action $DailyAction `
    -Trigger $DailyTrigger `
    -Description "Telegram-Push fuer taegliche Memory-/Voice-Capture-Reflexion." `
    -Force | Out-Null

$WeeklyAction = New-ScheduledTaskAction -Execute $Python -Argument "`"$Script`" --kind weekly" -WorkingDirectory $ProjectDir
$WeeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 18:00
Register-ScheduledTask `
    -TaskName "Nexi Voice Memory Weekly Review" `
    -Action $WeeklyAction `
    -Trigger $WeeklyTrigger `
    -Description "Telegram-Push fuer woechentliches Memory-/Voice-Capture-Review." `
    -Force | Out-Null

Write-Host "Scheduled Reviews registriert: taeglich 19:00, sonntags 18:00."
