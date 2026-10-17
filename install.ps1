<#
.SYNOPSIS
  Installiert das Add-on und die Integration "DALI-2 IoT Manager" auf Home Assistant OS.

.DESCRIPTION
  Kopiert
    dali2_iot_manager\              -> \\<HaHost>\addons\dali2_iot_manager
    custom_components\dali2_iot\    -> \\<HaHost>\config\custom_components\dali2_iot
  über die Freigaben des Samba-Add-ons ("Samba share").

  Voraussetzung: Das offizielle Add-on "Samba share" ist installiert und gestartet.

.EXAMPLE
  .\install.ps1 -HaHost homeassistant.local
  .\install.ps1 -HaHost 192.168.0.10 -User homeassistant
  .\install.ps1 -Zip            # erzeugt nur dist\dali2_iot_ha.zip
#>
param(
  [string]$HaHost = "homeassistant.local",
  [string]$User,
  [switch]$Zip,
  [switch]$SkipAddon,
  [switch]$SkipIntegration
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$addonSrc = Join-Path $root "dali2_iot_manager"
$integrationSrc = Join-Path $root "custom_components\dali2_iot"

if (-not (Test-Path (Join-Path $addonSrc "www\index.html"))) {
  throw "Frontend fehlt (dali2_iot_manager\www). Bitte zuerst 'npm run build' im Ordner frontend ausführen."
}

function Copy-Clean($src, $dst) {
  if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
  New-Item -ItemType Directory -Force $dst | Out-Null
  Get-ChildItem $src -Force | Where-Object { $_.Name -notin @("__pycache__", ".pytest_cache", "tests") } |
    ForEach-Object { Copy-Item $_.FullName -Destination $dst -Recurse -Force }
  Get-ChildItem $dst -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
}

if ($Zip) {
  $dist = Join-Path $root "dist"
  $stage = Join-Path $dist "stage"
  if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
  Copy-Clean $addonSrc (Join-Path $stage "addons\dali2_iot_manager")
  Copy-Clean $integrationSrc (Join-Path $stage "config\custom_components\dali2_iot")
  Copy-Item (Join-Path $root "INSTALL.md") $stage
  $zipPath = Join-Path $dist "dali2_iot_ha.zip"
  if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
  # Compress-Archive (PowerShell 5.1) writes "\" separators, which break on Linux → build the zip manually
  Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
  $archive = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
  try {
    $base = (Resolve-Path $stage).Path.TrimEnd('\') + '\'
    Get-ChildItem $stage -Recurse -File | ForEach-Object {
      $entry = $_.FullName.Substring($base.Length).Replace('\', '/')
      [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $_.FullName, $entry, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
  } finally {
    $archive.Dispose()
  }
  Remove-Item $stage -Recurse -Force
  Write-Host "ZIP erstellt: $zipPath" -ForegroundColor Green
  return
}

$addonsShare = "\\$HaHost\addons"
$configShare = "\\$HaHost\config"

if ($User) {
  Write-Host "Verbinde mit \\$HaHost als $User ..."
  $cred = Get-Credential -UserName $User -Message "Samba-Passwort für Home Assistant"
  foreach ($share in @($addonsShare, $configShare)) {
    $name = "Dali2IotHA" + [Math]::Abs($share.GetHashCode())
    New-PSDrive -Name $name -PSProvider FileSystem -Root $share -Credential $cred -ErrorAction SilentlyContinue | Out-Null
  }
}

if (-not $SkipAddon) {
  if (-not (Test-Path $addonsShare)) { throw "Freigabe $addonsShare nicht erreichbar. Ist das Samba-Add-on gestartet?" }
  $dst = Join-Path $addonsShare "dali2_iot_manager"
  Write-Host "Kopiere Add-on nach $dst ..."
  Copy-Clean $addonSrc $dst
}

if (-not $SkipIntegration) {
  if (-not (Test-Path $configShare)) { throw "Freigabe $configShare nicht erreichbar. Ist das Samba-Add-on gestartet?" }
  $cc = Join-Path $configShare "custom_components"
  New-Item -ItemType Directory -Force $cc | Out-Null
  $dst = Join-Path $cc "dali2_iot"
  Write-Host "Kopiere Integration nach $dst ..."
  Copy-Clean $integrationSrc $dst
}

Write-Host ""
Write-Host "Fertig! Nächste Schritte:" -ForegroundColor Green
Write-Host " 1. Einstellungen -> Add-ons -> Add-on-Store -> (⋮) 'Nach Updates suchen'"
Write-Host "    -> unter 'Lokale Add-ons' 'DALI-2 IoT Manager' installieren und starten"
Write-Host " 2. Home Assistant neu starten (Einstellungen -> System -> Neu starten)"
Write-Host " 3. Die Integration erscheint unter Einstellungen -> Geräte & Dienste als 'Entdeckt'"
Write-Host "    (oder manuell: Integration hinzufügen -> 'DALI-2 IoT Manager')"
