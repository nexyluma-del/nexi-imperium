<#
AUFGABE 017 - OpenWebUI mit lokalem Qdrant-RAG verbinden

Recreated nur den OpenWebUI-Container mit Qdrant/Ollama-RAG-Umgebung.
Qdrant, n8n und Ollama bleiben unangetastet. Das OpenWebUI-Volume bleibt erhalten.
#>

[CmdletBinding()]
param(
    [string]$ManifestPath = "C:\AI\projects\09-video-analyse\openwebui-rag-manifest.json",
    [string]$ContainerName = "open-webui",
    [string]$Image = "ghcr.io/open-webui/open-webui:main",
    [string]$Volume = "open-webui",
    [string]$AdminUserId = "",
    [switch]$SkipContainerRecreate
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

function Wait-OpenWebUI {
    param([int]$TimeoutSeconds = 120)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "OpenWebUI wurde nicht innerhalb von $TimeoutSeconds Sekunden erreichbar."
}

if (-not (Test-Path -LiteralPath $ManifestPath)) {
    throw "Manifest nicht gefunden: $ManifestPath"
}

if (-not $SkipContainerRecreate) {
    try {
        Invoke-DockerChecked @("rm", "-f", $ContainerName) | Out-Null
    }
    catch {}

    Invoke-DockerChecked @(
        "run", "-d",
        "--name", $ContainerName,
        "--restart", "always",
        "-p", "127.0.0.1:3000:8080",
        "-v", "${Volume}:/app/backend/data",
        "--add-host", "host.docker.internal:host-gateway",
        "-e", "OLLAMA_BASE_URL=http://host.docker.internal:11434",
        "-e", "ENABLE_OLLAMA_API=true",
        "-e", "ENABLE_OPENAI_API=false",
        "-e", "ENABLE_OTEL=false",
        "-e", "SCARF_NO_ANALYTICS=true",
        "-e", "DO_NOT_TRACK=true",
        "-e", "ANONYMIZED_TELEMETRY=false",
        "-e", "VECTOR_DB=qdrant",
        "-e", "QDRANT_URI=http://host.docker.internal:6333",
        "-e", "QDRANT_COLLECTION_PREFIX=open-webui",
        "-e", "ENABLE_QDRANT_MULTITENANCY_MODE=true",
        "-e", "RAG_EMBEDDING_ENGINE=ollama",
        "-e", "RAG_OLLAMA_BASE_URL=http://host.docker.internal:11434",
        "-e", "RAG_EMBEDDING_MODEL=nomic-embed-text",
        $Image
    ) | Out-Null

    Wait-OpenWebUI
}

if (-not $AdminUserId) {
    $adminPython = @"
import sqlite3
con = sqlite3.connect('/app/backend/data/webui.db')
row = con.execute("select id from user where role='admin' limit 1").fetchone()
con.close()
print(row[0] if row else '')
"@
    $encodedAdmin = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($adminPython))
    $adminProbe = Invoke-DockerChecked @("exec", $ContainerName, "python3", "-c", "import base64; exec(base64.b64decode('$encodedAdmin').decode('utf-8'))")
    $AdminUserId = $adminProbe.Trim()
}

if (-not $AdminUserId) {
    throw "OpenWebUI Admin-User konnte nicht ermittelt werden."
}

Invoke-DockerChecked @("cp", $ManifestPath, "$ContainerName`:/tmp/openwebui-rag-manifest.json") | Out-Null

$python = @"
import json
import sqlite3
import time

manifest = json.load(open('/tmp/openwebui-rag-manifest.json', encoding='utf-8'))
admin_user_id = '$AdminUserId'
now = int(time.time())
con = sqlite3.connect('/app/backend/data/webui.db')
for item in manifest.get('knowledge_bases', []):
    meta = json.dumps({'source': manifest.get('source_collection'), 'dest': manifest.get('dest_collection'), 'points': item.get('points')})
    existing = con.execute('select id from knowledge where id=?', (item['id'],)).fetchone()
    if existing:
        con.execute(
            'update knowledge set user_id=?, name=?, description=?, meta=?, updated_at=? where id=?',
            (admin_user_id, item['name'], item['description'], meta, now, item['id']),
        )
    else:
        con.execute(
            'insert into knowledge (id, user_id, name, description, meta, created_at, updated_at) values (?, ?, ?, ?, ?, ?, ?)',
            (item['id'], admin_user_id, item['name'], item['description'], meta, now, now),
        )
con.commit()
con.close()
print('knowledge_bases_upserted=' + str(len(manifest.get('knowledge_bases', []))))
"@

$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($python))
Invoke-DockerChecked @("exec", $ContainerName, "python3", "-c", "import base64; exec(base64.b64decode('$encoded').decode('utf-8'))") | Out-Null

Write-Host "OpenWebUI Qdrant-RAG konfiguriert."
Write-Host "Manifest: $ManifestPath"
Write-Host "AdminUserId: $AdminUserId"
