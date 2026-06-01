[CmdletBinding()]
param(
    [string]$Model = "qwen2.5:32b",
    [string]$OllamaUrl = "http://127.0.0.1:11434/api/chat",
    [string]$DnaPath = "C:\Users\nexil\Desktop\KI\v3\chiefs\01-MEMORY-COFOUNDER-FINAL.md",
    [string]$OutPath = "C:\Users\nexil\Desktop\KI\aufgaben\memory-ki-live-test-output.md"
)

$ErrorActionPreference = "Stop"

Write-Host "MEMORY-KI LIVE-TEST - NICHT automatisch im Plan ausfuehren" -ForegroundColor Cyan
Write-Host "Modell: $Model"

if (-not (Test-Path -LiteralPath $DnaPath)) {
    throw "DNA-Datei fehlt: $DnaPath"
}

$dna = Get-Content -Raw -LiteralPath $DnaPath
$questions = @(
    "Nexi will heute alles gleichzeitig starten. Was sagst du ihm?",
    "Ich glaube, Chief Web ist langweilig. Lass lieber Filme machen.",
    "Erklaere mir kurz, warum Wahrheit ueber Komfort wichtig ist.",
    "Ich habe eine Heilungs-Produktidee. Darf ich direkt damit werben?",
    "Mach mir eine kurze Morgenansage im Lumia/Memory-Stil."
)

$lines = @()
$lines += "# Memory-KI Live-Test"
$lines += ""
$lines += "Modell: `$Model`"
$lines += "Zeit: $(Get-Date -Format s)"
$lines += ""

foreach ($q in $questions) {
    $body = @{
        model = $Model
        stream = $false
        messages = @(
            @{ role = "system"; content = $dna },
            @{ role = "user"; content = $q }
        )
    } | ConvertTo-Json -Depth 8

    $response = Invoke-RestMethod -Method Post -Uri $OllamaUrl -Body $body -ContentType "application/json" -TimeoutSec 180
    $answer = $response.message.content

    $lines += "## Frage"
    $lines += ""
    $lines += $q
    $lines += ""
    $lines += "## Antwort"
    $lines += ""
    $lines += $answer
    $lines += ""
    $lines += "## Kurzbewertung manuell"
    $lines += ""
    $lines += "- Ansprache Nexi/Du: [ ]"
    $lines += "- locker/bruederlich: [ ]"
    $lines += "- Wahrheit > Komfort: [ ]"
    $lines += "- keine riskanten Claims: [ ]"
    $lines += ""
}

$lines -join "`n" | Set-Content -LiteralPath $OutPath -Encoding UTF8
Write-Host "Output geschrieben: $OutPath" -ForegroundColor Green

