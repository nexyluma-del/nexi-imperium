<#
Starts the local WSL bridge used by n8n workflow 100-Video-Pipeline-Manual.
#>

[CmdletBinding()]
param(
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"

wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /mnt/c/AI/projects/09-video-analyse && chmod +x scripts/start_pipeline_bridge.sh && scripts/start_pipeline_bridge.sh $Port"

