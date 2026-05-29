<#
AUFGABE 002 - Monatlicher Restic-Restore-Test
AUFGABE 010b - 2026-05-29 erweitert um Pflichtprobe aus C:\AI, falls vorhanden

Dieses Skript:
- fragt das Restic-Passwort interaktiv ab, wenn RESTIC_PASSWORD nicht gesetzt ist
- stellt einzelne Dateien in D:\Restic-Restore-Test wieder her
- vergleicht Hashes mit den Originaldateien, wenn die Originale noch existieren
- loescht nur den expliziten Testordner D:\Restic-Restore-Test nach erfolgreichem Test
#>

[CmdletBinding()]
param(
    [string]$ResticExe = "C:\Users\nexil\Desktop\KI\tools\restic\restic.exe",
    [string]$Repository = "D:\Restic-Backup",
    [string]$RestoreTarget = "D:\Restic-Restore-Test",
    [string]$LogDir = "C:\Users\nexil\Desktop\KI\logs\backup"
)

$ErrorActionPreference = "Stop"

function ConvertFrom-SecureStringToPlain {
    param([Parameter(Mandatory = $true)] [Security.SecureString]$Secure)
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Convert-ResticPathToWindowsPath {
    param([Parameter(Mandatory = $true)] [string]$ResticPath)
    $trimmed = $ResticPath.TrimStart("/")
    if ($trimmed -match "^([A-Za-z]):/(.*)$") {
        return ($matches[1] + ":\" + $matches[2].Replace("/", "\"))
    }
    if ($trimmed -match "^([A-Za-z])/(.*)$") {
        return ($matches[1] + ":\" + $matches[2].Replace("/", "\"))
    }
    return $null
}

if (-not (Test-Path -LiteralPath $ResticExe)) {
    $cmd = Get-Command restic -ErrorAction SilentlyContinue
    if ($cmd) {
        $ResticExe = $cmd.Source
    }
    else {
        throw "Restic wurde nicht gefunden. Erwartet: $ResticExe"
    }
}

if (-not (Test-Path -LiteralPath $Repository)) {
    throw "Restic-Repository wurde nicht gefunden: $Repository"
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$logPath = Join-Path $LogDir ("restore-test-" + (Get-Date -Format "yyyy-MM-dd_HHmmss") + ".log")

$passwordWasProvided = $false
if (-not $env:RESTIC_PASSWORD) {
    $securePassword = Read-Host "Restic-Passwort eingeben" -AsSecureString
    $env:RESTIC_PASSWORD = ConvertFrom-SecureStringToPlain -Secure $securePassword
    $passwordWasProvided = $true
}

try {
    $resolvedTargetParent = Resolve-Path -LiteralPath (Split-Path -Parent $RestoreTarget) -ErrorAction Stop
    $targetFull = [System.IO.Path]::GetFullPath($RestoreTarget)
    if (-not $targetFull.StartsWith($resolvedTargetParent.Path, [StringComparison]::OrdinalIgnoreCase)) {
        throw "RestoreTarget liegt nicht im erwarteten Parent: $RestoreTarget"
    }
    if ($targetFull -ne "D:\Restic-Restore-Test") {
        throw "Sicherheitsstopp: Dieses Skript loescht nur den expliziten Testordner D:\Restic-Restore-Test."
    }

    if (Test-Path -LiteralPath $RestoreTarget) {
        Remove-Item -LiteralPath $RestoreTarget -Recurse -Force
    }
    New-Item -ItemType Directory -Path $RestoreTarget -Force | Out-Null

    "Restore-Test gestartet: $(Get-Date)" | Tee-Object -FilePath $logPath
    $json = & $ResticExe -r $Repository ls latest --json 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $json) {
        throw "Konnte Dateiliste aus letztem Snapshot nicht lesen."
    }

    $items = $json | ForEach-Object { $_ | ConvertFrom-Json } | Where-Object {
        $_.type -eq "file" -and $_.path -and $_.size -gt 0 -and $_.size -lt 50MB
    }

    $sample = @()
    $aiItems = @($items | Where-Object { $_.path -like "/C/AI/*" })
    $otherItems = @($items | Where-Object { $_.path -notlike "/C/AI/*" })

    if ($aiItems.Count -gt 0) {
        $aiSample = $aiItems | Get-Random -Count 1
        $sample += $aiSample
        "C:\AI Restore-Pflichtprobe: $($aiSample.path)" | Tee-Object -FilePath $logPath -Append
    }
    else {
        "WARNUNG: Im letzten Snapshot wurde keine geeignete C:\AI-Datei fuer den Restore-Test gefunden." | Tee-Object -FilePath $logPath -Append
    }

    $remainingCount = 3 - @($sample).Count
    if ($remainingCount -gt 0 -and $otherItems.Count -gt 0) {
        $sample += $otherItems | Get-Random -Count ([Math]::Min($remainingCount, $otherItems.Count))
    }

    if (-not $sample -and @($items).Count -gt 0) {
        $sample = $items | Get-Random -Count ([Math]::Min(3, @($items).Count))
    }

    if (-not $sample) {
        throw "Keine geeigneten Dateien fuer Restore-Test gefunden."
    }

    foreach ($item in @($sample)) {
        "Restore: $($item.path)" | Tee-Object -FilePath $logPath -Append
        & $ResticExe -r $Repository restore latest --target $RestoreTarget --include $item.path 2>&1 | Tee-Object -FilePath $logPath -Append
        if ($LASTEXITCODE -ne 0) {
            throw "Restore fehlgeschlagen fuer $($item.path)"
        }

        $originalPath = Convert-ResticPathToWindowsPath -ResticPath $item.path
        $restoredPath = Join-Path $RestoreTarget ($item.path.TrimStart("/").Replace("/", "\"))

        if (-not (Test-Path -LiteralPath $restoredPath)) {
            throw "Wiederhergestellte Datei nicht gefunden: $restoredPath"
        }

        if ($originalPath -and (Test-Path -LiteralPath $originalPath)) {
            $origHash = (Get-FileHash -LiteralPath $originalPath -Algorithm SHA256).Hash
            $restoredHash = (Get-FileHash -LiteralPath $restoredPath -Algorithm SHA256).Hash
            if ($origHash -ne $restoredHash) {
                throw "Hash-Vergleich fehlgeschlagen fuer $originalPath"
            }
            "Hash OK: $originalPath" | Tee-Object -FilePath $logPath -Append
        }
        else {
            "Original nicht mehr vorhanden, Restore-Datei existiert: $restoredPath" | Tee-Object -FilePath $logPath -Append
        }
    }

    Remove-Item -LiteralPath $RestoreTarget -Recurse -Force
    "Restore-Test bestanden: $(Get-Date)" | Tee-Object -FilePath $logPath -Append
    Write-Host "Restore-Test erfolgreich. Log: $logPath"
}
finally {
    if ($passwordWasProvided) {
        Remove-Item Env:\RESTIC_PASSWORD -ErrorAction SilentlyContinue
    }
}
