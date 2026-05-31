param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$ProjectDir = "C:\AI\projects\09-video-analyse"
$Python = Join-Path $ProjectDir ".venv-win\Scripts\python.exe"
$Script = Join-Path $ProjectDir "scripts\status_dashboard.py"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python wurde nicht gefunden: $Python"
}

if (-not (Test-Path -LiteralPath $Script)) {
    throw "Dashboard-Skript wurde nicht gefunden: $Script"
}

& $Python $Script --serve --port $Port
