param(
    [string]$ProjectDir = "C:\AI\projects\09-video-analyse",
    [string]$Hotkey = "ctrl+shift+space"
)

$ErrorActionPreference = "Stop"

$Python = Join-Path $ProjectDir ".venv-win\Scripts\python.exe"
$Script = Join-Path $ProjectDir "scripts\voice_capture.py"

if (-not (Test-Path -LiteralPath $Python)) {
    & (Join-Path $ProjectDir "scripts\install-voice-capture-deps.ps1") -ProjectDir $ProjectDir
}

Set-Location $ProjectDir
Write-Host "Voice-Capture startet. Hotkey: $Hotkey"
Write-Host "Erster Druck startet Aufnahme, zweiter Druck stoppt und verarbeitet lokal."
& $Python $Script --hotkey $Hotkey
