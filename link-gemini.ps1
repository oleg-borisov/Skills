#requires -Version 7.0

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$userProfilePath = [Environment]::GetFolderPath('UserProfile')
$geminiPluginsRoot = Join-Path $userProfilePath '.gemini\config\plugins'
$pluginDir = Join-Path $repoRoot '.gemini\plugins\serenity-agents'

function Assert-PathWithin {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Root
    )

    $resolvedPath = [IO.Path]::GetFullPath($Path)
    $resolvedRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    if (-not $resolvedPath.StartsWith($resolvedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Небезопасный путь вне разрешённого корня: $resolvedPath"
    }
}

function Sync-DirectoryContents {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination,
        [Parameter(Mandatory)][string]$Root
    )

    Assert-PathWithin -Path $Destination -Root $Root
    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Исходный каталог отсутствует: $Source"
    }

    if (Test-Path -LiteralPath $Destination) {
        $item = Get-Item -LiteralPath $Destination -Force
        if ($item.LinkType) {
            Remove-Item -LiteralPath $Destination -Force -Recurse
        }
    }

    if (-not (Test-Path -LiteralPath $Destination)) {
        New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    }

    # Синхронизация файлов и каталогов (Mirror)
    robocopy $Source $Destination /MIR /NP /NFL /NDL /NJH /NJS | Out-Null
    Write-Host "Synced plugin to: $Destination"
}

# 1. Генерируем плагин в локальном каталоге .gemini
& (Join-Path $repoRoot 'sync-gemini-agents.ps1')

# 2. Синхронизируем плагин в ~/.gemini/config/plugins/serenity-agents
# (Antigravity plugin discovery на Windows требует прямой каталог, а не NTFS ReparsePoint / Junction)
$targetPluginDir = Join-Path $geminiPluginsRoot 'serenity-agents'
Sync-DirectoryContents -Source $pluginDir -Destination $targetPluginDir -Root $geminiPluginsRoot

Write-Host "Antigravity plugin 'serenity-agents' installed and synchronized successfully."
