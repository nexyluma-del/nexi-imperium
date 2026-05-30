<#
AUFGABE 010c - n8n Workflows, Credentials und Volume-Snapshot exportieren

Credentials werden bewusst NICHT entschluesselt exportiert. Zusaetzlich wird das
n8n-Volume als tar.gz gesichert, damit Config und Encryption-Key erhalten bleiben.
#>

[CmdletBinding()]
param(
    [string]$ContainerName = "n8n",
    [string]$OutputRoot = "D:\Restic-Sources\n8n"
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
$containerTmp = "/tmp/restic-n8n-$stamp"
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

Invoke-DockerChecked @("inspect", $ContainerName)
Invoke-DockerChecked @("exec", $ContainerName, "sh", "-lc", "rm -rf '$containerTmp' && mkdir -p '$containerTmp/workflows' '$containerTmp/credentials'")
Invoke-DockerChecked @("exec", $ContainerName, "n8n", "export:workflow", "--backup", "--output=$containerTmp/workflows")
$credentialOutput = & docker exec $ContainerName n8n export:credentials --backup "--output=$containerTmp/credentials" 2>&1
if ($LASTEXITCODE -ne 0) {
    $credentialText = ($credentialOutput | Out-String)
    if ($credentialText -match "No credentials found") {
        Invoke-DockerChecked @("exec", $ContainerName, "sh", "-lc", "printf 'No credentials found in this n8n instance.\n' > '$containerTmp/credentials/NO_CREDENTIALS.txt'")
    }
    else {
        throw "n8n Credential-Export fehlgeschlagen:`n$credentialText"
    }
}
Invoke-DockerChecked @("exec", $ContainerName, "sh", "-lc", "tar -czf '$containerTmp/n8n-volume.tgz' -C /home/node/.n8n .")
Invoke-DockerChecked @("cp", "$ContainerName`:$containerTmp/.", $runDir)
Invoke-DockerChecked @("exec", $ContainerName, "sh", "-lc", "rm -rf '$containerTmp'")

$workflowFiles = @(Get-ChildItem -LiteralPath (Join-Path $runDir "workflows") -Filter "*.json" -File -ErrorAction SilentlyContinue)
$credentialFiles = @(Get-ChildItem -LiteralPath (Join-Path $runDir "credentials") -Filter "*.json" -File -ErrorAction SilentlyContinue)
$volumeFile = Get-Item -LiteralPath (Join-Path $runDir "n8n-volume.tgz")

$manifest = [ordered]@{
    type = "n8n-export"
    started_at = $stamp
    finished_at = (Get-Date).ToString("s")
    container = $ContainerName
    output_dir = $runDir
    workflows = $workflowFiles.Count
    credentials = $credentialFiles.Count
    credentials_decrypted = $false
    volume_tar = $volumeFile.FullName
    volume_tar_size_bytes = $volumeFile.Length
}

$manifestPath = Join-Path $runDir "manifest.json"
Write-JsonFile -Path $manifestPath -Value $manifest

Write-Host "n8n-Export erfolgreich: $runDir"
Write-Host "Manifest: $manifestPath"
