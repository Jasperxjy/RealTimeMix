#Requires -Version 5.1
<#
.SYNOPSIS
    Install RealTimeMix Native Messaging Host for Chrome / Edge.

.PARAMETER ExtensionId
    The Chrome extension ID (required). Load the extension in Chrome developer
    mode first, then copy the ID from chrome://extensions.

.EXAMPLE
    .\install_host.ps1 -ExtensionId abcdefghijklmnopqrstuvwxyzabcdef
#>
param(
    [Parameter(Mandatory=$true, HelpMessage="Chrome extension ID from chrome://extensions")]
    [string]$ExtensionId
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$jsonPath = Join-Path $scriptDir "com.realtimix.host.json"
$hostPath = Join-Path $scriptDir "realtime_mix_host.py"

if (-not (Test-Path $hostPath)) {
    Write-Error "Native host script not found: $hostPath"
    exit 1
}

# Update manifest with real paths
$manifest = Get-Content $jsonPath -Raw | ConvertFrom-Json
$manifest.path = $hostPath
$manifest.allowed_origins = @("chrome-extension://$ExtensionId/")
$manifest | ConvertTo-Json -Depth 10 | Set-Content $jsonPath -Encoding UTF8

# Register for Chrome
$chromeKey = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.realtimix.host"
New-Item -Path $chromeKey -Force | Out-Null
Set-ItemProperty -Path $chromeKey -Name "(Default)" -Value $jsonPath

# Register for Edge
$edgeKey = "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\com.realtimix.host"
New-Item -Path $edgeKey -Force | Out-Null
Set-ItemProperty -Path $edgeKey -Name "(Default)" -Value $jsonPath

Write-Host "✅ Native host installed successfully." -ForegroundColor Green
Write-Host "   Chrome registry: $chromeKey"
Write-Host "   Edge registry:   $edgeKey"
Write-Host "   Manifest:        $jsonPath"
Write-Host "   Extension ID:    $ExtensionId"
Write-Host ""
Write-Host "Restart Chrome/Edge if they are already running."
