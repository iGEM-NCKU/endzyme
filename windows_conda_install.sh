# ==========================================
# Conda Auto Installer Script
# Author: Richie
# Date: 2025/9/30
# ==========================================

#Requires -RunAsAdministrator
# RUN IN POWERSHELL
$ErrorActionPreference = "Stop"

$InstallPath = "C:\Miniconda3"
$arch = $env:PROCESSOR_ARCHITECTURE
if ($arch -eq "ARM64") {
    $Url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-ARM64.exe"
} else {
    $Url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
}

$Installer = Join-Path $env:TEMP "Miniconda3-latest-Windows.exe"
Write-Host "Downloading $Url ..."
Invoke-WebRequest -Uri $Url -OutFile $Installer


$Args = @(
  "/InstallationType=AllUsers",
  "/AddToPath=1",
  "/RegisterPython=0",
  "/S",
  "/D=$InstallPath"
)

Write-Host "Installing to $InstallPath ..."
Start-Process -FilePath $Installer -ArgumentList $Args -Wait

$pathsToAdd = @("$InstallPath", "$InstallPath\Library\bin", "$InstallPath\Scripts")
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")

foreach ($p in $pathsToAdd) {
  if ($machinePath -notmatch [Regex]::Escape($p)) {
    $machinePath = $machinePath.TrimEnd(';') + ";" + $p
  }
}
[Environment]::SetEnvironmentVariable("Path", $machinePath, "Machine")

Write-Host "Miniconda installed. You may need to open a NEW PowerShell window."

& "$InstallPath\Scripts\conda.exe" --version
