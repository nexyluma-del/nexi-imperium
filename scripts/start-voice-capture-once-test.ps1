param(
    [string]$ProjectDir = "C:\AI\projects\09-video-analyse",
    [double]$Seconds = 6
)

$ErrorActionPreference = "Stop"

$Python = Join-Path $ProjectDir ".venv-win\Scripts\python.exe"
$Script = Join-Path $ProjectDir "scripts\voice_capture.py"

if (-not (Test-Path -LiteralPath $Python)) {
    & (Join-Path $ProjectDir "scripts\install-voice-capture-deps.ps1") -ProjectDir $ProjectDir
}

Set-Location $ProjectDir
Write-Host "Voice-Capture Testaufnahme fuer $Seconds Sekunden."
& $Python $Script --once --seconds $Seconds
