param(
    [string]$ProjectDir = "C:\AI\projects\09-video-analyse"
)

$ErrorActionPreference = "Stop"

$BundledPython = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$VenvPython = Join-Path $ProjectDir ".venv-win\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    if (-not (Test-Path -LiteralPath $BundledPython)) {
        throw "Python nicht gefunden: $BundledPython"
    }
    & $BundledPython -m venv (Join-Path $ProjectDir ".venv-win")
}

& $VenvPython -m pip install --upgrade pip keyboard sounddevice requests
Write-Host "Voice-Capture-Abhaengigkeiten sind installiert."
