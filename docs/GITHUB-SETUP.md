# GitHub Setup

Geplanter GitHub-Username: $GitHubUser
Geplanter privater Repo-Name: 
exi-imperium

## Wichtig

Das GitHub-Repo muss privat sein.
Keine sensiblen Inhalte pushen.

## Schritte auf GitHub

1. Auf https://github.com/new gehen.
2. Repository name: 
exi-imperium
3. Visibility: Private
4. Keine README, keine .gitignore, keine License auf GitHub erzeugen.
5. Repo erstellen.

Danach lokal:

`powershell
cd C:\AI\imperium-config
git push -u origin main
`
"@

 = @(
    "inbox",
    "chiefs\ceo",
    "chiefs\memory",
    "chiefs\finanz",
    "chiefs\film",
    "chiefs\musik",
    "chiefs\ecommerce",
    "chiefs\heilung",
    "chiefs\web",
    "chiefs\callcenter",
    "chiefs\video-analyse",
    "chiefs\it-engineering",
    "projects",
    "knowledge",
    "briefings",
    "archive"
)

Ensure-Dir C:\Users\nexil\Documents\Obsidian-Imperium
foreach (C:\AI\projects\10-it-engineering in ) {
    Ensure-Dir (Join-Path C:\Users\nexil\Documents\Obsidian-Imperium C:\AI\projects\10-it-engineering)
}

Write-IfMissing (Join-Path C:\Users\nexil\Documents\Obsidian-Imperium "inbox\Willkommen im Imperium.md") @"
# Willkommen im Imperium

Dies ist die erste Testnotiz im lokalen Obsidian-Vault.

Grundregel:
- Schnell erfassen in inbox.
- Danach in Chiefs, Projects, Knowledge, Briefings oder Archive sortieren.
- D3/D4-Inhalte bleiben lokal und werden nicht ins Git-Repo gepusht.
