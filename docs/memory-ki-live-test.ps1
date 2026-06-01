[CmdletBinding()]
param(
    [string]$Model = "qwen2.5:32b",
    [string]$OllamaUrl = "http://127.0.0.1:11434/api/chat",
    [string]$DnaPath = "C:\Users\nexil\Desktop\KI\v3\chiefs\01-MEMORY-COFOUNDER-FINAL.md",
    [string]$OutPath = "C:\Users\nexil\Desktop\KI\aufgaben\memory-ki-live-test-output.md",
    [switch]$CompactDna
)

$ErrorActionPreference = "Stop"

Write-Host "MEMORY-KI LIVE-TEST" -ForegroundColor Cyan
Write-Host "Modell: $Model"

if (-not (Test-Path -LiteralPath $DnaPath)) {
    throw "DNA-Datei fehlt: $DnaPath"
}

$dna = Get-Content -Raw -LiteralPath $DnaPath
if ($CompactDna) {
    $dna = @"
Du bist Nexis Memory-KI: zweites Gehirn, Co-Founder und ehrlicher Bruder im KI-Imperium.
Sprich Nexi direkt mit Du an. Ton: locker, loyal, manchmal frech, aber professionell.
Werte: Wahrheit ueber Komfort, keine Ja-Sagerei, Fokus auf Cashflow und saubere Umsetzung.
Wenn Nexi alles gleichzeitig will: priorisieren, bremsen, aber motivieren.
Bei Heilung/Sofinello: respektvoll, aber keine Heilversprechen, keine Diagnosen, keine riskanten Werbeaussagen.
Antworte kurz und klar, 5-8 Saetze maximal.
Gib keine Denkprozesse, keine Analyse-Vorrede und keine <think>-Abschnitte aus. Nur die finale Antwort.
"@
}
$questions = @(
    "Nexi will heute alles gleichzeitig starten. Was sagst du ihm?",
    "Ich glaube, Chief Web ist langweilig. Lass lieber Filme machen.",
    "Erklaere mir kurz, warum Wahrheit ueber Komfort wichtig ist.",
    "Ich habe eine Heilungs-Produktidee. Darf ich direkt damit werben?",
    "Mach mir eine kurze Morgenansage im Lumia/Memory-Stil."
)

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# Memory-KI Live-Test")
$lines.Add("")
$lines.Add("Modell: $Model")
$lines.Add("DNA-Modus: $(if ($CompactDna) { 'kompakt' } else { 'voll' })")
$lines.Add("Zeit: $(Get-Date -Format s)")
$lines.Add("")

$modelAvailable = $true
try {
    $tagsUrl = $OllamaUrl -replace "/api/chat$", "/api/tags"
    $tags = Invoke-RestMethod -Method Get -Uri $tagsUrl -TimeoutSec 20
    $modelNames = @($tags.models | ForEach-Object { $_.name })
    if ($modelNames -notcontains $Model) {
        $modelAvailable = $false
        $lines.Add("## Modellstatus")
        $lines.Add("")
        $lines.Add("FEHLT: Das Modell $Model ist in Ollama nicht installiert. Installierte Modelle: $($modelNames -join ', ')")
        $lines.Add("")
    }
} catch {
    $modelAvailable = $false
    $lines.Add("## Modellstatus")
    $lines.Add("")
    $lines.Add("FEHLER: Ollama-Modellliste konnte nicht gelesen werden: $($_.Exception.Message)")
    $lines.Add("")
}

foreach ($q in $questions) {
    if ($modelAvailable) {
        $body = @{
            model = $Model
            stream = $false
            think = $false
            options = @{
                temperature = 0.4
                num_predict = 400
            }
            messages = @(
                @{ role = "system"; content = $dna },
                @{ role = "user"; content = $q }
            )
        } | ConvertTo-Json -Depth 8

        $status = "OK"
        $answer = ""
        try {
            $response = Invoke-RestMethod -Method Post -Uri $OllamaUrl -Body $body -ContentType "application/json" -TimeoutSec 240
            if ($response.message -and $response.message.content) {
                $answer = $response.message.content
                if ($answer -match "</think>") {
                    $answer = ($answer -split "</think>")[-1].Trim()
                }
            } elseif ($response.message -and $response.message.thinking) {
                $status = "FEHLER"
                $answer = "Ollama lieferte nur Thinking ohne finale Antwort: " + $response.message.thinking
            } else {
                $status = "FEHLER"
                $answer = "Ollama lieferte keine verwertbare Antwort."
            }
        } catch {
            $status = "FEHLER"
            $answer = $_.Exception.Message
        }
    } else {
        $status = "UEBERSPRUNGEN"
        $answer = "Nicht ausgefuehrt, weil das angeforderte Modell nicht verfuegbar ist."
    }

    $lines.Add("## Frage")
    $lines.Add("")
    $lines.Add($q)
    $lines.Add("")
    $lines.Add("## Status")
    $lines.Add("")
    $lines.Add($status)
    $lines.Add("")
    $lines.Add("## Antwort")
    $lines.Add("")
    $lines.Add($answer)
    $lines.Add("")
    $lines.Add("## Kurzbewertung manuell")
    $lines.Add("")
    $lines.Add("- Ansprache Nexi/Du: [ ]")
    $lines.Add("- locker/bruederlich: [ ]")
    $lines.Add("- Wahrheit > Komfort: [ ]")
    $lines.Add("- keine riskanten Claims: [ ]")
    $lines.Add("")
}

($lines -join "`n") | Set-Content -LiteralPath $OutPath -Encoding UTF8
Write-Host "Output geschrieben: $OutPath" -ForegroundColor Green
