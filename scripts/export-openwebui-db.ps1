<#
AUFGABE 010c - OpenWebUI SQLite-Dump fuer Restic exportieren

Erzeugt per sqlite backup API eine konsistente Kopie von webui.db und legt
zusaetzlich ein leichtes Daten-Tar ohne Cache und interne Vector-DB ab.
#>

[CmdletBinding()]
param(
    [string]$ContainerName = "open-webui",
    [string]$OutputRoot = "D:\Restic-Sources\openwebui"
)

$ErrorActionPreference = "Stop"

function Invoke-DockerChecked {
    param([Parameter(Mandatory = $true)] [string[]]$Arguments)
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & docker @Arguments 2>&1
    }
    finally {
        $ErrorActionPreference = $oldPreference
    }
    if ($LASTEXITCODE -ne 0) {
        $text = ($output | Out-String).Trim()
        throw "Docker-Befehl fehlgeschlagen: docker $($Arguments -join ' ')`n$text"
    }
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [Parameter(Mandatory = $true)] $Value
    )
    $Value | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$runDir = Join-Path $OutputRoot $stamp
$containerTmp = "/tmp/restic-openwebui-$stamp"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

Invoke-DockerChecked @("inspect", $ContainerName)
Invoke-DockerChecked @("exec", $ContainerName, "sh", "-lc", "rm -rf '$containerTmp' && mkdir -p '$containerTmp'")

$python = "import sqlite3; src=sqlite3.connect('/app/backend/data/webui.db'); dst=sqlite3.connect('$containerTmp/webui.db'); src.backup(dst); dst.close(); src.close()"
Invoke-DockerChecked @("exec", $ContainerName, "python3", "-c", $python)
Invoke-DockerChecked @("exec", $ContainerName, "sh", "-lc", "tar -czf '$containerTmp/openwebui-data-light.tgz' -C /app/backend/data --exclude='./cache' --exclude='./vector_db' .")
Invoke-DockerChecked @("cp", "$ContainerName`:$containerTmp/.", $runDir)
Invoke-DockerChecked @("exec", $ContainerName, "sh", "-lc", "rm -rf '$containerTmp'")

$dbFile = Get-Item -LiteralPath (Join-Path $runDir "webui.db")
$tarFile = Get-Item -LiteralPath (Join-Path $runDir "openwebui-data-light.tgz")

$manifest = [ordered]@{
    type = "openwebui-db-export"
    started_at = $stamp
    finished_at = (Get-Date).ToString("s")
    container = $ContainerName
    output_dir = $runDir
    database = $dbFile.FullName
    database_size_bytes = $dbFile.Length
    light_volume_tar = $tarFile.FullName
    light_volume_tar_size_bytes = $tarFile.Length
    excluded = @("cache", "vector_db")
}

$manifestPath = Join-Path $runDir "manifest.json"
Write-JsonFile -Path $manifestPath -Value $manifest

Write-Host "OpenWebUI-DB-Export erfolgreich: $runDir"
Write-Host "Manifest: $manifestPath"
