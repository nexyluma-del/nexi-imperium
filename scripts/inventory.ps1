<#
AUFGABE 001 - Bestandsaufnahme & Backup-Foundation
Read-only Inventory-Skript fuer Nexis HP Omen Max.

Dieses Skript:
- installiert nichts
- deinstalliert nichts
- aendert keine Registry-Werte
- liest keine Passwoerter, Lizenzschluessel oder WLAN-Schluessel aus
- schreibt nur den Markdown-Bericht BESTANDSAUFNAHME.md
#>

[CmdletBinding()]
param(
    [string]$OutputPath = "C:\Users\nexil\Desktop\KI\BESTANDSAUFNAHME.md"
)

$ErrorActionPreference = "Continue"
$ReportDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Convert-BytesToGB {
    param([Nullable[Double]]$Bytes)
    if ($null -eq $Bytes -or $Bytes -le 0) { return "" }
    return [Math]::Round(($Bytes / 1GB), 2)
}

function Convert-ToMarkdownTable {
    param(
        [Parameter(Mandatory = $true)] [AllowEmptyCollection()] [array]$Rows,
        [Parameter(Mandatory = $true)] [string[]]$Columns
    )

    if (-not $Rows -or $Rows.Count -eq 0 -or ($Rows.Count -eq 1 -and $null -eq $Rows[0])) {
        return "_Keine Daten gefunden._`n"
    }

    $out = @()
    $out += "| " + ($Columns -join " | ") + " |"
    $out += "| " + (($Columns | ForEach-Object { "---" }) -join " | ") + " |"

    foreach ($row in $Rows) {
        $values = foreach ($col in $Columns) {
            $value = $row.$col
            if ($null -eq $value) { $value = "" }
            ($value -as [string]).Replace([string][char]0, "").Replace("|", "\|").Replace("`r", " ").Replace("`n", " ")
        }
        $out += "| " + ($values -join " | ") + " |"
    }

    return ($out -join "`n") + "`n"
}

function Invoke-Safe {
    param(
        [Parameter(Mandatory = $true)] [scriptblock]$ScriptBlock,
        [string]$Fallback = "_Konnte nicht gelesen werden._"
    )

    try {
        & $ScriptBlock
    }
    catch {
        $Fallback
    }
}

function Get-CommandOutput {
    param([string]$Command, [string[]]$Arguments = @())
    try {
        $cmd = Get-Command $Command -ErrorAction Stop
        $output = & $cmd.Source @Arguments 2>&1
        $text = ($output | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) {
                $_.Exception.Message
            }
            else {
                $_.ToString()
            }
        }) -join "`n"
        $text = $text.Replace([string][char]0, "").Trim()
        if ($LASTEXITCODE -ne 0 -and -not $text) {
            return "_Befehl lieferte keinen nutzbaren Output._"
        }
        return $text
    }
    catch {
        return "_Nicht verfuegbar: ${Command}_"
    }
}

function Get-RegistryPrograms {
    $paths = @(
        "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )

    $programs = foreach ($path in $paths) {
        Get-ItemProperty -Path $path -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName } |
            Select-Object @{
                Name = "Name"; Expression = { $_.DisplayName }
            }, @{
                Name = "Version"; Expression = { $_.DisplayVersion }
            }, @{
                Name = "Publisher"; Expression = { $_.Publisher }
            }, @{
                Name = "InstallDate"; Expression = { $_.InstallDate }
            }
    }

    $programs | Sort-Object Name -Unique
}

function Get-ToolMarkers {
    param([array]$Programs)

    $toolNames = @(
        "Python", "Node", "Git", "Docker", "Cursor", "Visual Studio Code",
        "VS Code", "NVIDIA", "CUDA", "Ollama", "LM Studio", "ComfyUI",
        "DaVinci", "Topaz", "Obsidian", "Tailscale", "Bitwarden",
        "Proton Pass", "WSL", "Ubuntu", "PowerShell"
    )

    foreach ($tool in $toolNames) {
        $matches = $Programs | Where-Object {
            $_.Name -match [Regex]::Escape($tool) -or $_.Publisher -match [Regex]::Escape($tool)
        }

        [PSCustomObject]@{
            Tool = $tool
            Status = if ($matches) { "gefunden" } else { "nicht gefunden" }
            Treffer = if ($matches) { (($matches | Select-Object -First 5 -ExpandProperty Name) -join "; ") } else { "" }
        }
    }
}

function Get-TopLevelFolderSizes {
    param([string]$Root = "C:\")

    $folders = Get-ChildItem -LiteralPath $Root -Directory -Force -ErrorAction SilentlyContinue
    $results = foreach ($folder in $folders) {
        $size = 0
        $errors = 0
        try {
            Get-ChildItem -LiteralPath $folder.FullName -Recurse -Force -File -ErrorAction SilentlyContinue |
                ForEach-Object { $size += $_.Length }
        }
        catch {
            $errors++
        }

        [PSCustomObject]@{
            Ordner = $folder.FullName
            GroesseGB = Convert-BytesToGB $size
            Hinweis = if ($errors -gt 0) { "Teilweise nicht lesbar" } else { "" }
        }
    }

    $results | Sort-Object GroesseGB -Descending | Select-Object -First 20
}

$cpu = Invoke-Safe { Get-CimInstance -ClassName Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed }
$gpu = Invoke-Safe { Get-CimInstance -ClassName Win32_VideoController | Select-Object Name, DriverVersion, AdapterRAM, VideoProcessor }
$ramModules = Invoke-Safe {
    Get-CimInstance -ClassName Win32_PhysicalMemory | Select-Object @{
        Name = "Bank"; Expression = { $_.BankLabel }
    }, @{
        Name = "KapazitaetGB"; Expression = { Convert-BytesToGB $_.Capacity }
    }, Speed, Manufacturer, PartNumber
}
$totalRamGB = Invoke-Safe { [Math]::Round(((Get-CimInstance -ClassName Win32_ComputerSystem).TotalPhysicalMemory / 1GB), 2) }
$diskDrives = Invoke-Safe {
    Get-CimInstance -ClassName Win32_DiskDrive | Select-Object Model, InterfaceType, MediaType, @{
        Name = "GroesseGB"; Expression = { Convert-BytesToGB $_.Size }
    }, Partitions
}
$partitions = Invoke-Safe {
    Get-Partition | Sort-Object DiskNumber, PartitionNumber | Select-Object DiskNumber, PartitionNumber, DriveLetter, Type, @{
        Name = "GroesseGB"; Expression = { Convert-BytesToGB $_.Size }
    }, GptType
}
$volumes = Invoke-Safe {
    Get-Volume | Sort-Object DriveLetter | Select-Object DriveLetter, FileSystemLabel, FileSystem, DriveType, @{
        Name = "GroesseGB"; Expression = { Convert-BytesToGB $_.Size }
    }, @{
        Name = "FreiGB"; Expression = { Convert-BytesToGB $_.SizeRemaining }
    }
}
$bios = Invoke-Safe { Get-CimInstance -ClassName Win32_BIOS | Select-Object Manufacturer, SMBIOSBIOSVersion, ReleaseDate }
$baseboard = Invoke-Safe { Get-CimInstance -ClassName Win32_BaseBoard | Select-Object Manufacturer, Product, Version }
$os = Invoke-Safe {
    Get-CimInstance -ClassName Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture, InstallDate, LastBootUpTime
}
$hotfixes = Invoke-Safe { Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 25 HotFixID, Description, InstalledOn }
$programs = Invoke-Safe { Get-RegistryPrograms }
$storeApps = Invoke-Safe { Get-AppxPackage | Sort-Object Name | Select-Object Name, Version, Publisher }
$toolMarkers = Invoke-Safe { Get-ToolMarkers -Programs $programs }
$logicalDisks = Invoke-Safe {
    Get-CimInstance -ClassName Win32_LogicalDisk | Select-Object DeviceID, VolumeName, FileSystem, DriveType, @{
        Name = "GroesseGB"; Expression = { Convert-BytesToGB $_.Size }
    }, @{
        Name = "FreiGB"; Expression = { Convert-BytesToGB $_.FreeSpace }
    }
}
$netAdapters = Invoke-Safe { Get-NetAdapter | Select-Object Name, InterfaceDescription, Status, LinkSpeed }
$ipAddresses = Invoke-Safe {
    Get-NetIPAddress | Where-Object { $_.AddressFamily -in @("IPv4", "IPv6") -and $_.IPAddress -notlike "fe80*" } |
        Select-Object InterfaceAlias, AddressFamily, IPAddress, PrefixLength
}
$wlanProfiles = Get-CommandOutput -Command "netsh.exe" -Arguments @("wlan", "show", "profiles")
$nvidiaSmi = Get-CommandOutput -Command "nvidia-smi.exe" -Arguments @("--query-gpu=name,driver_version,memory.total", "--format=csv,noheader")
$wslStatus = Get-CommandOutput -Command "wsl.exe" -Arguments @("--status")
if ($wslStatus -match "wslinstall" -or $wslStatus -match "nicht installiert") {
    $wslStatus = "WSL ist nicht installiert. Windows meldet: Installation waere mit 'wsl.exe --install' moeglich. Fuer Aufgabe 001 wurde nichts installiert."
}
$dockerVersion = Get-CommandOutput -Command "docker.exe" -Arguments @("--version")
$activationStatus = Get-CommandOutput -Command "cscript.exe" -Arguments @("//Nologo", "$env:windir\System32\slmgr.vbs", "/xpr")
$bitlocker = try {
    Get-BitLockerVolume -ErrorAction Stop | Select-Object MountPoint, VolumeStatus, ProtectionStatus, EncryptionPercentage, KeyProtector
}
catch {
    @()
}
$bitlockerManageBde = Get-CommandOutput -Command "manage-bde.exe" -Arguments @("-status", "C:")

$topFolders = Invoke-Safe { Get-TopLevelFolderSizes -Root "C:\" }

$externalCandidates = @($logicalDisks) | Where-Object {
    $_ -ne $null -and $_.DeviceID -ne "C:" -and ([double]($_.GroesseGB)) -ge 500
}

$lines = New-Object System.Collections.Generic.List[string]

$lines.Add("# BESTANDSAUFNAHME - Nexi KI-Laptop")
$lines.Add("")
$lines.Add("**Erstellt:** $ReportDate")
$lines.Add("**Datenklasse:** D1 intern")
$lines.Add("**Risiko-Level:** R0/R1 - nur gelesen und lokal dokumentiert")
$lines.Add("")
$lines.Add("> Hinweis: Dieses Skript liest keine Passwoerter, Lizenzschluessel oder WLAN-Schluessel aus. Es installiert, deinstalliert und veraendert nichts.")
$lines.Add("")

$lines.Add("## 1. Hardware-Snapshot")
$lines.Add("")
$lines.Add("### CPU")
$lines.Add((Convert-ToMarkdownTable -Rows @($cpu) -Columns @("Name", "NumberOfCores", "NumberOfLogicalProcessors", "MaxClockSpeed")))
$lines.Add("### GPU")
$gpuRows = foreach ($g in @($gpu)) {
    [PSCustomObject]@{
        Name = $g.Name
        DriverVersion = $g.DriverVersion
        AdapterRAMGB = Convert-BytesToGB $g.AdapterRAM
        VideoProcessor = $g.VideoProcessor
    }
}
$lines.Add((Convert-ToMarkdownTable -Rows @($gpuRows) -Columns @("Name", "DriverVersion", "AdapterRAMGB", "VideoProcessor")))
$lines.Add("### NVIDIA-SMI")
$lines.Add('```text')
$lines.Add($nvidiaSmi)
$lines.Add('```')
$lines.Add("")
$lines.Add('> Hinweis: Die Windows-WMI-Angabe `AdapterRAMGB` kann bei modernen GPUs falsch wirken. Fuer die RTX 5090 ist `nvidia-smi` hier die massgebliche Quelle und meldet rund 24 GB VRAM.')
$lines.Add("")
$lines.Add("### RAM")
$lines.Add("Gesamter System-RAM laut Windows: **$totalRamGB GB**")
$lines.Add((Convert-ToMarkdownTable -Rows @($ramModules) -Columns @("Bank", "KapazitaetGB", "Speed", "Manufacturer", "PartNumber")))
$lines.Add("### Speichergeraete")
$lines.Add((Convert-ToMarkdownTable -Rows @($diskDrives) -Columns @("Model", "InterfaceType", "MediaType", "GroesseGB", "Partitions")))
$lines.Add("### Partitionen")
$lines.Add((Convert-ToMarkdownTable -Rows @($partitions) -Columns @("DiskNumber", "PartitionNumber", "DriveLetter", "Type", "GroesseGB", "GptType")))
$lines.Add("### BIOS")
$lines.Add((Convert-ToMarkdownTable -Rows @($bios) -Columns @("Manufacturer", "SMBIOSBIOSVersion", "ReleaseDate")))
$lines.Add("### Mainboard")
$lines.Add((Convert-ToMarkdownTable -Rows @($baseboard) -Columns @("Manufacturer", "Product", "Version")))

$lines.Add("## 2. OS-Snapshot")
$lines.Add("")
$lines.Add("### Windows")
$lines.Add((Convert-ToMarkdownTable -Rows @($os) -Columns @("Caption", "Version", "BuildNumber", "OSArchitecture", "InstallDate", "LastBootUpTime")))
$lines.Add("### Installierte Updates - letzte 25")
$lines.Add((Convert-ToMarkdownTable -Rows @($hotfixes) -Columns @("HotFixID", "Description", "InstalledOn")))
$lines.Add("### Windows-Aktivierung")
$lines.Add('```text')
$lines.Add($activationStatus)
$lines.Add('```')
$lines.Add("")
$lines.Add("### WSL-Status")
$lines.Add('```text')
$lines.Add($wslStatus)
$lines.Add('```')
$lines.Add("")
$lines.Add("### Docker-Version")
$lines.Add('```text')
$lines.Add($dockerVersion)
$lines.Add('```')
$lines.Add("")
$lines.Add("### BitLocker-Status")
$lines.Add((Convert-ToMarkdownTable -Rows @($bitlocker) -Columns @("MountPoint", "VolumeStatus", "ProtectionStatus", "EncryptionPercentage")))
$lines.Add("### BitLocker-Fallback via manage-bde")
$lines.Add('```text')
$lines.Add($bitlockerManageBde)
$lines.Add('```')
$lines.Add("")

$lines.Add("## 3. Software-Inventar")
$lines.Add("")
$lines.Add("### KI- und Entwickler-Tools - Schnellcheck")
$lines.Add((Convert-ToMarkdownTable -Rows @($toolMarkers) -Columns @("Tool", "Status", "Treffer")))
$lines.Add("### Installierte klassische Programme")
$lines.Add((Convert-ToMarkdownTable -Rows @($programs) -Columns @("Name", "Version", "Publisher", "InstallDate")))
$lines.Add("### Microsoft Store Apps")
$lines.Add((Convert-ToMarkdownTable -Rows @($storeApps) -Columns @("Name", "Version", "Publisher")))

$lines.Add("## 4. Speicher-Analyse")
$lines.Add("")
$lines.Add("### Laufwerke / Volumes")
$lines.Add((Convert-ToMarkdownTable -Rows @($volumes) -Columns @("DriveLetter", "FileSystemLabel", "FileSystem", "DriveType", "GroesseGB", "FreiGB")))
$lines.Add("### Logical Disks")
$lines.Add((Convert-ToMarkdownTable -Rows @($logicalDisks) -Columns @("DeviceID", "VolumeName", "FileSystem", "DriveType", "GroesseGB", "FreiGB")))
$lines.Add("### Externe-SSD-Kandidaten")
if (@($externalCandidates).Count -gt 0) {
    $lines.Add((Convert-ToMarkdownTable -Rows @($externalCandidates) -Columns @("DeviceID", "VolumeName", "FileSystem", "DriveType", "GroesseGB", "FreiGB")))
}
else {
    $lines.Add("_Kein Laufwerk ab 500 GB ausser C: erkannt. Falls die externe 2-TB-SSD vorhanden ist, bitte anschliessen und Skript erneut ausfuehren._`n")
}
$lines.Add("### C:\ Top-Level-Ordner nach Groesse")
$lines.Add("> Hinweis: Das ist eine vorsichtige Top-Level-Analyse. Systemgeschuetzte Ordner koennen teilweise nicht vollstaendig gelesen werden.")
$lines.Add((Convert-ToMarkdownTable -Rows @($topFolders) -Columns @("Ordner", "GroesseGB", "Hinweis")))

$lines.Add("## 5. Netzwerk-Konfiguration")
$lines.Add("")
$lines.Add("### WLAN-Profile ohne Passwoerter")
$lines.Add('```text')
$lines.Add($wlanProfiles)
$lines.Add('```')
$lines.Add("")
$lines.Add("### Netzwerk-Adapter")
$lines.Add((Convert-ToMarkdownTable -Rows @($netAdapters) -Columns @("Name", "InterfaceDescription", "Status", "LinkSpeed")))
$lines.Add("### IP-Konfiguration")
$lines.Add((Convert-ToMarkdownTable -Rows @($ipAddresses) -Columns @("InterfaceAlias", "AddressFamily", "IPAddress", "PrefixLength")))

$lines.Add("## 6. Backup-Empfehlung")
$lines.Add("")
$lines.Add("Prioritaet vor jeder groesseren Systemaenderung:")
$lines.Add("")
$lines.Add("1. **Externe SSD anschliessen und testen.** Sie muss erkannt werden, genug freien Speicher haben und fehlerfrei schreiben/lesen.")
$lines.Add("2. **BitLocker-Recovery-Key sichern.** Wenn BitLocker aktiv ist, muss der Recovery-Key bekannt und ausserhalb des Laptops gesichert sein.")
$lines.Add("3. **Benutzerordner sichern:** Desktop, Dokumente, Downloads, Bilder, Videos, Musik, Projekte, KI-Ordner, Browser-Exports.")
$lines.Add('4. **KI-Ordner versionieren/sichern:** `C:\Users\nexil\Desktop\KI` inklusive v3, Policies, Chiefs, Aufgaben.')
$lines.Add("5. **Browser-Bookmarks exportieren.** Browser-Passwoerter nur ueber einen Passwortmanager, nicht als ungeschuetzte CSV.")
$lines.Add("6. **Cloud-Backup erst verschluesselt.** Backblaze B2 oder aehnlich nur mit clientseitiger Verschluesselung, z.B. Restic.")
$lines.Add("7. **Restore-Test machen.** Ein Backup zaehlt erst, wenn mindestens eine Test-Wiederherstellung erfolgreich war.")
$lines.Add("")

$lines.Add("## 7. Risiko-Liste vor Aufgabe 002")
$lines.Add("")
$riskItems = New-Object System.Collections.Generic.List[string]
$bitlockerArray = @($bitlocker) | Where-Object { $_ -ne $null -and $_.MountPoint }
if ($bitlockerArray.Count -gt 0) {
    foreach ($b in $bitlockerArray) {
        if ($b.ProtectionStatus -ne "On") {
            $riskItems.Add("- BitLocker-Schutz auf $($b.MountPoint) ist nicht als 'On' gemeldet. Vor sensiblen Daten pruefen.")
        }
    }
}
else {
    if ($bitlockerManageBde -match "Schutzstatus:\s+Schutz\s+aktiviert" -or $bitlockerManageBde -match "Protection Status:\s+Protection On") {
        $riskItems.Add("- BitLocker scheint laut manage-bde aktiv zu sein. Recovery-Key vor Aufgabe 002 trotzdem extern sichern.")
    }
    else {
        $riskItems.Add("- BitLocker-Status konnte nicht eindeutig per PowerShell gelesen werden. manage-bde-Ausgabe im Bericht manuell pruefen.")
    }
}
if (@($externalCandidates).Count -eq 0) {
    $riskItems.Add("- Externe 2-TB-SSD wurde nicht eindeutig erkannt. Vor Backup/Phase 0B anschliessen und pruefen.")
}
if ($dockerVersion -like "_Nicht verfuegbar*") {
    $riskItems.Add("- Docker wurde nicht im PATH gefunden. Das ist fuer Aufgabe 001 kein Problem, aber Phase 1 braucht spaeter Docker Desktop.")
}
if ($wslStatus -like "_Nicht verfuegbar*") {
    $riskItems.Add("- WSL wurde nicht im PATH gefunden oder ist noch nicht eingerichtet. Phase 0B sollte WSL2 sauber einrichten.")
}
if ($nvidiaSmi -like "_Nicht verfuegbar*") {
    $riskItems.Add("- nvidia-smi wurde nicht gefunden. NVIDIA-Treiber/CUDA-Faehigkeit vor lokaler KI pruefen.")
}
if ($riskItems.Count -eq 0) {
    $riskItems.Add("- Keine harten Blocker aus der automatischen Bestandsaufnahme erkannt. Details dennoch manuell gegenlesen.")
}
$lines.Add(($riskItems -join "`n"))
$lines.Add("")

$lines.Add("## 8. Empfehlung fuer Aufgabe 002")
$lines.Add("")
$lines.Add("**Was:** Phase 0B Sicherheit starten: Updates pruefen, BitLocker/Recovery-Key sichern, Passwortmanager/2FA, Tailscale und verschluesseltes Backup-Konzept.")
$lines.Add("")
$lines.Add("**Warum:** Bevor lokale KI, Agenten oder sensible Inhalte verarbeitet werden, muss die Maschine gegen Datenverlust und Zugriffsausfall abgesichert sein.")
$lines.Add("")
$lines.Add("**Risiko:** Wenn wir ohne Backup und Recovery-Key weitermachen, koennen Datenverlust oder ausgesperrtes Windows bei spaeteren Systemaenderungen teuer werden.")
$lines.Add("")
$lines.Add("**Optionen:** A) Erst Backup+Recovery-Key, dann WSL2. B) Erst WSL2, Backup danach. C) Alles gleichzeitig.")
$lines.Add("")
$lines.Add("**Empfehlung:** A - erst Backup+Recovery-Key, dann technische Einrichtung.")
$lines.Add("")

$outputDir = Split-Path -Parent $OutputPath
if (-not (Test-Path -LiteralPath $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

$lines -join "`n" | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Output $OutputPath
