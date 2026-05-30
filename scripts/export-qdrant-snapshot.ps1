<#
AUFGABE 010c - Qdrant Collection-Snapshots fuer Restic exportieren

Erzeugt pro Qdrant-Collection einen offiziellen Snapshot per API, laedt ihn nach
D:\Restic-Sources\qdrant und entfernt danach nur den frisch erzeugten Snapshot
aus dem laufenden Qdrant-Volume.
#>

[CmdletBinding()]
param(
    [string]$QdrantUrl = "http://127.0.0.1:6333",
    [string]$OutputRoot = "D:\Restic-Sources\qdrant"
)

$ErrorActionPreference = "Stop"

function Write-JsonFile {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [Parameter(Mandatory = $true)] $Value
    )
    $Value | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Escape-UrlPart {
    param([Parameter(Mandatory = $true)] [string]$Value)
    return [System.Uri]::EscapeDataString($Value)
}

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$runDir = Join-Path $OutputRoot $stamp
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

$manifest = [ordered]@{
    type = "qdrant-snapshot-export"
    started_at = (Get-Date).ToString("s")
    qdrant_url = $QdrantUrl
    output_dir = $runDir
    collections = @()
}

$collectionsResponse = Invoke-RestMethod -Uri "$QdrantUrl/collections" -Method Get
$collections = @($collectionsResponse.result.collections | ForEach-Object { $_.name })

foreach ($collection in $collections) {
    $collectionPart = Escape-UrlPart $collection
    $snapshotResponse = Invoke-RestMethod -Uri "$QdrantUrl/collections/$collectionPart/snapshots" -Method Post
    $snapshotName = $snapshotResponse.result.name
    if (-not $snapshotName) {
        throw "Qdrant lieferte keinen Snapshot-Namen fuer Collection $collection."
    }

    $snapshotPart = Escape-UrlPart $snapshotName
    $targetFile = Join-Path $runDir ("{0}__{1}" -f $collection, $snapshotName)
    Invoke-WebRequest -Uri "$QdrantUrl/collections/$collectionPart/snapshots/$snapshotPart" -OutFile $targetFile -UseBasicParsing

    $fileInfo = Get-Item -LiteralPath $targetFile
    if ($fileInfo.Length -le 0) {
        throw "Qdrant-Snapshot ist leer: $targetFile"
    }

    try {
        Invoke-RestMethod -Uri "$QdrantUrl/collections/$collectionPart/snapshots/$snapshotPart" -Method Delete | Out-Null
        $remoteDeleted = $true
    }
    catch {
        $remoteDeleted = $false
    }

    $manifest.collections += [ordered]@{
        name = $collection
        snapshot_name = $snapshotName
        file = $targetFile
        size_bytes = $fileInfo.Length
        remote_snapshot_deleted = $remoteDeleted
    }
}

$manifest.finished_at = (Get-Date).ToString("s")
$manifestPath = Join-Path $runDir "manifest.json"
Write-JsonFile -Path $manifestPath -Value $manifest

Write-Host "Qdrant-Snapshot-Export erfolgreich: $runDir"
Write-Host "Manifest: $manifestPath"
