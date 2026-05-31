<#
AUFGABE 002 - Restic-Passwort fuer unbeaufsichtigtes Backup hinterlegen

Dieses Skript schreibt RESTIC_PASSWORD in C:\AI\projects\09-video-analyse\.env,
aber nur wenn BitLocker auf C: aktiv ist. Es gibt das Passwort nie aus.
#>

[CmdletBinding()]
param(
    [string]$EnvFile = "C:\AI\projects\09-video-analyse\.env"
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

function Assert-BitLockerActive {
    $output = & manage-bde -status C: 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "BitLocker-Check fehlgeschlagen. Starte PowerShell als Administrator und versuche es erneut.`n$output"
    }
    $text = ($output | Out-String)
    $protectionOk = $text -match "Schutzstatus:\s+Der Schutz ist aktiviert" -or $text -match "Protection Status:\s+Protection On"
    $encryptedOk = $text -match "Verschluesselt \(Prozent\):\s+100" -or $text -match "Verschlüsselt \(Prozent\):\s+100" -or $text -match "Percentage Encrypted:\s+100"
    if (-not ($protectionOk -and $encryptedOk)) {
        throw "Sicherheitsstopp: BitLocker auf C: ist nicht eindeutig aktiv und 100% verschluesselt. RESTIC_PASSWORD wird nicht gespeichert."
    }
}

function Set-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [Parameter(Mandatory = $true)] [string]$Name,
        [Parameter(Mandatory = $true)] [string]$Value
    )
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $lines = @()
    if (Test-Path -LiteralPath $Path) {
        $lines = [System.IO.File]::ReadAllLines($Path, [System.Text.Encoding]::UTF8)
    }
    $filtered = @($lines | Where-Object { $_.TrimStart([char]0xFEFF) -notmatch "^$([regex]::Escape($Name))=" })
    $filtered += "$Name=$Value"
    [System.IO.File]::WriteAllLines($Path, $filtered, [System.Text.UTF8Encoding]::new($false))
}

Assert-BitLockerActive

$securePassword = Read-Host "Restic-Passwort aus Standard Notes eingeben" -AsSecureString
$plainPassword = ConvertFrom-SecureStringToPlain -Secure $securePassword
if (-not $plainPassword -or $plainPassword.Length -lt 20) {
    throw "Sicherheitsstopp: Passwort fehlt oder ist zu kurz."
}

Set-DotEnvValue -Path $EnvFile -Name "RESTIC_PASSWORD" -Value $plainPassword
Write-Host "RESTIC_PASSWORD wurde in $EnvFile gespeichert. Passwort wurde nicht ausgegeben." -ForegroundColor Green
