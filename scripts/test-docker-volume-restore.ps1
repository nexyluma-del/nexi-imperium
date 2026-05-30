<#
AUFGABE 010c - Restore-Proben fuer Docker-Exports

Testet die zuletzt erzeugten Exports isoliert:
- Qdrant Snapshot wird in einem temporaeren Qdrant-Container wiederhergestellt.
- n8n Volume-Tar wird in ein temporaeres Docker-Volume entpackt und per n8n CLI gelesen.
- OpenWebUI SQLite-Dump wird in einem temporaeren Container geoeffnet.

Live-Container bleiben unveraendert.
#>

[CmdletBinding()]
param(
    [string]$ExportRoot = "D:\Restic-Sources",
    [string]$RestoreTestRoot = "D:\Restic-Restore-Test"
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
    return ($output | Out-String).Trim()
}

function Get-LatestDir {
    param([Parameter(Mandatory = $true)] [string]$Path)
    $dir = Get-ChildItem -LiteralPath $Path -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $dir) {
        throw "Kein Export-Verzeichnis gefunden: $Path"
    }
    return $dir
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [Parameter(Mandatory = $true)] $Value
    )
    $Value | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$testDir = Join-Path $RestoreTestRoot "docker-volumes-$stamp"
New-Item -ItemType Directory -Force -Path $testDir | Out-Null

$result = [ordered]@{
    type = "docker-volume-restore-test"
    started_at = (Get-Date).ToString("s")
    test_dir = $testDir
    qdrant = $null
    n8n = $null
    openwebui = $null
}

# Qdrant: restore snapshot into an isolated temporary Qdrant container.
$qdrantExport = Get-LatestDir (Join-Path $ExportRoot "qdrant")
$qdrantManifest = Get-Content -LiteralPath (Join-Path $qdrantExport.FullName "manifest.json") | ConvertFrom-Json
$qdrantItem = $qdrantManifest.collections[0]
$qdrantSnapshotRoot = Join-Path $testDir "qdrant-snapshots"
$qdrantCollectionDir = Join-Path $qdrantSnapshotRoot $qdrantItem.name
New-Item -ItemType Directory -Force -Path $qdrantCollectionDir | Out-Null
Copy-Item -LiteralPath $qdrantItem.file -Destination (Join-Path $qdrantCollectionDir $qdrantItem.snapshot_name) -Force

$qdrantContainer = "qdrant-restore-test"
try {
    Invoke-DockerChecked @("rm", "-f", $qdrantContainer) | Out-Null
}
catch {}

try {
    Invoke-DockerChecked @("run", "-d", "--name", $qdrantContainer, "-p", "127.0.0.1:6335:6333", "-v", "${qdrantSnapshotRoot}:/qdrant/snapshots", "qdrant/qdrant") | Out-Null
    Start-Sleep -Seconds 4
    $body = @{ location = "file:///qdrant/snapshots/$($qdrantItem.name)/$($qdrantItem.snapshot_name)" } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://127.0.0.1:6335/collections/$($qdrantItem.name)/snapshots/recover" -Method Put -ContentType "application/json" -Body $body | Out-Null
    $collectionInfo = Invoke-RestMethod -Uri "http://127.0.0.1:6335/collections/$($qdrantItem.name)" -Method Get
    $result.qdrant = [ordered]@{
        ok = $true
        collection = $qdrantItem.name
        points_count = $collectionInfo.result.points_count
        snapshot = $qdrantItem.snapshot_name
    }
}
finally {
    try {
        Invoke-DockerChecked @("rm", "-f", $qdrantContainer) | Out-Null
    }
    catch {}
}

# n8n: restore tar into a temporary Docker volume and verify the CLI can read workflows.
$n8nExport = Get-LatestDir (Join-Path $ExportRoot "n8n")
$n8nVolume = "restic_restore_test_n8n"
try {
    Invoke-DockerChecked @("volume", "rm", "-f", $n8nVolume) | Out-Null
}
catch {}
try {
    Invoke-DockerChecked @("volume", "create", $n8nVolume) | Out-Null
    Invoke-DockerChecked @("run", "--rm", "-v", "${n8nVolume}:/home/node/.n8n", "-v", "$($n8nExport.FullName):/restore:ro", "--entrypoint", "sh", "docker.n8n.io/n8nio/n8n", "-lc", "tar -xzf /restore/n8n-volume.tgz -C /home/node/.n8n && test -f /home/node/.n8n/database.sqlite && test -f /home/node/.n8n/config") | Out-Null
    $workflowRead = Invoke-DockerChecked @("run", "--rm", "-v", "${n8nVolume}:/home/node/.n8n", "docker.n8n.io/n8nio/n8n", "export:workflow", "--all")
    try {
        $workflowObjects = $workflowRead | ConvertFrom-Json
        $workflowCount = @($workflowObjects).Count
    }
    catch {
        $workflowCount = $null
    }
    $result.n8n = [ordered]@{
        ok = $true
        export_dir = $n8nExport.FullName
        workflow_count = $workflowCount
        workflow_read_probe = "restored volume could be read by n8n export:workflow"
    }
}
finally {
    try {
        Invoke-DockerChecked @("volume", "rm", "-f", $n8nVolume) | Out-Null
    }
    catch {}
}

# OpenWebUI: open exported SQLite DB in an isolated container.
$openWebuiExport = Get-LatestDir (Join-Path $ExportRoot "openwebui")
$sqliteProbe = Invoke-DockerChecked @("run", "--rm", "--entrypoint", "python3", "-v", "$($openWebuiExport.FullName):/restore:ro", "ghcr.io/open-webui/open-webui:main", "-c", "import sqlite3; con=sqlite3.connect('file:///restore/webui.db?mode=ro&immutable=1', uri=True); rows=con.execute('select name from sqlite_master limit 5').fetchall(); con.close(); print(len(rows))")
$result.openwebui = [ordered]@{
    ok = $true
    export_dir = $openWebuiExport.FullName
    table_probe_count = [int]$sqliteProbe
}

$result.finished_at = (Get-Date).ToString("s")
$resultPath = Join-Path $testDir "restore-test-result.json"
Write-JsonFile -Path $resultPath -Value $result

Write-Host "Docker-Volume-Restore-Test erfolgreich: $resultPath"
