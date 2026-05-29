# WSL2-SETUP

Status: abgeschlossen
Datum: 2026-05-29

## 1. Ergebnis

Aufgabe 004 richtet den Linux-/Container-Unterbau fuer die spaetere lokale KI-Phase ein.

Erledigt:
- WSL2 ist installiert.
- Ubuntu 24.04 LTS laeuft als WSL2-Distribution.
- CUDA/GPU-Zugriff in Ubuntu funktioniert.
- Docker Desktop ist installiert.
- Docker Desktop nutzt den Linux-/WSL2-Context.
- Docker ist in Ubuntu verfuegbar.
- `docker run hello-world` funktioniert in Ubuntu.
- Basis-Pakete in Ubuntu sind installiert.

Nicht installiert:
- Keine Ollama-/OpenWebUI-/KI-Tools.
- Kein Dual-Boot.
- Keine BitLocker-Aenderungen.

## 2. Windows und WSL

Windows:
- Version: `10.0.26200.8457`

WSL:
- Standardversion: `2`
- WSL-Version: `2.7.3.0`
- WSL-Kernel: `6.6.114.1-1`
- WSLg-Version: `1.0.73`

Distributionen:

```text
Ubuntu-24.04        Running/Stopped je nach Nutzung, Version 2, Hauptdistribution
docker-desktop      Running wenn Docker Desktop aktiv ist, Version 2
```

Hinweis:
- `Ubuntu-24.04-LTS` entstand beim Diagnoseversuch wegen eines Sandbox-/Kontext-Unterschieds.
- Nexi hat das Loeschen freigegeben.
- Die Diagnose-Distribution wurde entfernt.
- Hauptdistribution `Ubuntu-24.04` bleibt erhalten.

## 3. Ubuntu

Hauptdistribution:
- Name: `Ubuntu-24.04`
- Ubuntu: `Ubuntu 24.04.4 LTS`
- Kernel in Ubuntu: `6.6.114.1-microsoft-standard-WSL2`
- Linux-User: `nexiluma`
- Home-Pfad in Windows: `\\wsl$\Ubuntu-24.04\home\nexiluma`
- Windows-Laufwerk C: in Ubuntu: `/mnt/c/`

Start:

```powershell
wsl.exe -d Ubuntu-24.04
```

Stop:

```powershell
wsl.exe --shutdown
```

Passwort:
- Linux-Passwort wurde von Codex nicht gesehen und nicht gespeichert.
- Nexi hat bestaetigt, dass es in Standard Notes gespeichert ist.
- Notiz: `Linux User WSL Ubuntu`

## 4. Ubuntu-Basis-Pakete

Installiert:

```bash
build-essential
curl
git
python3-pip
```

Gepruefte Versionen:

```text
gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
git version 2.43.0
curl 8.5.0
Python 3.12.3
pip 24.0
```

## 5. CUDA / GPU-Test

Testbefehl in Ubuntu:

```bash
nvidia-smi
```

Ergebnis:

```text
NVIDIA GeForce RTX 5090 Laptop GPU
Driver Version: 596.49
CUDA Version laut nvidia-smi: 13.2
VRAM: 24463 MiB
```

Bewertung:
- CUDA/GPU-Zugriff in WSL2 funktioniert.
- Die RTX 5090 ist fuer spaetere lokale KI-Stacks in Ubuntu sichtbar.

## 6. Docker Desktop

Installation:
- Docker Desktop wurde per `winget` installiert.
- Version laut Installer: `Docker Desktop 4.74.0`
- Backend: `wsl-2`

Docker-Version:

```text
Client 29.4.3 / Server 29.4.3
```

Direkter Windows-CLI-Pfad, falls eine alte PowerShell den neuen PATH noch nicht kennt:

```powershell
C:\Program Files\Docker\Docker\resources\bin\docker.exe
```

Docker in Ubuntu:

```bash
docker --version
docker run hello-world
```

Ergebnis:
- `Docker version 29.4.3`
- `Hello from Docker!`

## 7. Wichtige Befehle

Windows:

```powershell
wsl.exe --status
wsl.exe --version
wsl.exe --list --verbose
wsl.exe -d Ubuntu-24.04
wsl.exe --shutdown
```

Ubuntu:

```bash
sudo apt update
sudo apt upgrade -y
nvidia-smi
docker --version
docker run hello-world
```

## 8. Offene Punkte

- [x] Aufgabe 004 gelesen.
- [x] Windows-Build geprueft.
- [x] WSL2 installiert.
- [x] WSL2 als Standardversion gesetzt.
- [x] WSL aktualisiert.
- [x] Windows neu gestartet.
- [x] Ubuntu 24.04 gestartet und Linux-User vorhanden.
- [x] Linux-Passwort in Standard Notes von Nexi bestaetigt.
- [x] Ubuntu-Basis-Pakete installiert.
- [x] `nvidia-smi` in Ubuntu geprueft.
- [x] Docker Desktop installiert.
- [x] Docker WSL2-Integration geprueft.
- [x] `docker run hello-world` in Ubuntu geprueft.
- [x] Unbenutzte Distribution `Ubuntu-24.04-LTS` nach Zustimmung entfernt.
- [x] WSL2-SETUP.md final aktualisiert.

## 9. Quellen

- Microsoft Learn WSL Installation: https://learn.microsoft.com/windows/wsl/install
- Microsoft Learn WSL Basic Commands: https://learn.microsoft.com/windows/wsl/basic-commands
- Ubuntu WSL Dokumentation: https://documentation.ubuntu.com/wsl/latest/howto/install-ubuntu-wsl2/
- Docker Desktop Windows Installation: https://docs.docker.com/desktop/setup/install/windows-install/
- Docker Desktop WSL2 Backend: https://docs.docker.com/desktop/features/wsl/
