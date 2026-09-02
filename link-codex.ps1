#requires -Version 7.0

<#
.SYNOPSIS
    Генерирует Codex profiles и синхронизирует rr-loop assets с локальными agent hosts.

.DESCRIPTION
    Directory skills подключаются junction-ами. Flat agent/command files копируются,
    потому что file symlinks не подхватываются используемыми hosts. Скрипт изменяет
    только известные rr-loop assets и сохраняет остальные пользовательские файлы.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$userProfilePath = [Environment]::GetFolderPath('UserProfile')
$orcaAccountsRoot = Join-Path $env:APPDATA 'orca\codex-accounts'
$agentNames = @('implementer', 'verifier', 'standards-reviewer', 'spec-reviewer', 'reviser')

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

function Set-DirectoryJunction {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Target,
        [Parameter(Mandatory)][string]$Root
    )

    Assert-PathWithin -Path $Path -Root $Root
    if (-not (Test-Path -LiteralPath $Target)) {
        throw "Цель junction отсутствует: $Target"
    }

    $parentPath = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parentPath)) {
        New-Item -ItemType Directory -Path $parentPath -Force | Out-Null
    }

    if (Test-Path -LiteralPath $Path) {
        $item = Get-Item -LiteralPath $Path -Force
        if ($item.LinkType -notin @('Junction', 'SymbolicLink')) {
            throw "Путь существует и не является junction: $Path"
        }
        Remove-Item -LiteralPath $Path -Force -Recurse
    }

    New-Item -ItemType Junction -Path $Path -Target $Target | Out-Null
    Write-Host "Junction: $Path -> $Target"
}

function Set-FileCopy {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Root
    )

    Assert-PathWithin -Path $Path -Root $Root
    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Источник файла отсутствует: $Source"
    }

    $parentPath = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parentPath)) {
        New-Item -ItemType Directory -Path $parentPath -Force | Out-Null
    }

    if (Test-Path -LiteralPath $Path) {
        $item = Get-Item -LiteralPath $Path -Force
        if ($item.PSIsContainer) {
            throw "На месте файла существует каталог: $Path"
        }
        if ($item.LinkType) {
            Remove-Item -LiteralPath $Path -Force
        }
    }

    Copy-Item -LiteralPath $Source -Destination $Path -Force
    Write-Host "Copied: $Path"
}

& (Join-Path $repoRoot 'sync-codex-agents.ps1')
& (Join-Path $repoRoot 'sync-zcode-agents.ps1')

$repoSkillsPath = Join-Path $repoRoot 'skills'
$rrLoopSkillPath = Join-Path $repoSkillsPath 'rr-loop'
$repoMarkdownAgentsPath = Join-Path $repoRoot 'agents'
$repoCodexAgentsPath = Join-Path $repoRoot '.codex\agents'
$repoZCodeAgentsPath = Join-Path $repoRoot '.zcode\agents'
$commandSourcePath = Join-Path $repoRoot 'command\rr-loop.md'

$userAgentsRoot = Join-Path $userProfilePath '.agents'
$claudeRoot = Join-Path $userProfilePath '.claude'
$codexRoot = Join-Path $userProfilePath '.codex'
$opencodeRoot = Join-Path $userProfilePath '.config\opencode'
$zcodeRoot = Join-Path $userProfilePath '.zcode'

Set-DirectoryJunction -Path (Join-Path $repoRoot '.agents\skills') -Target $repoSkillsPath -Root $repoRoot
Set-DirectoryJunction -Path (Join-Path $codexRoot 'agents') -Target $repoCodexAgentsPath -Root $codexRoot

foreach ($skillInstall in @(
    @{ Path = Join-Path $userAgentsRoot 'skills\rr-loop'; Root = $userAgentsRoot },
    @{ Path = Join-Path $claudeRoot 'skills\rr-loop'; Root = $claudeRoot },
    @{ Path = Join-Path $opencodeRoot 'skills\rr-loop'; Root = $opencodeRoot }
)) {
    Set-DirectoryJunction -Path $skillInstall.Path -Target $rrLoopSkillPath -Root $skillInstall.Root
}

foreach ($hostConfig in @(
    @{ Root = $claudeRoot; Agents = Join-Path $claudeRoot 'agents'; Command = Join-Path $claudeRoot 'command\rr-loop.md' },
    @{ Root = $opencodeRoot; Agents = Join-Path $opencodeRoot 'agents'; Command = Join-Path $opencodeRoot 'command\rr-loop.md' }
)) {
    foreach ($agentName in $agentNames) {
        Set-FileCopy -Path (Join-Path $hostConfig.Agents "$agentName.md") -Source (Join-Path $repoMarkdownAgentsPath "$agentName.md") -Root $hostConfig.Root
    }

    Set-FileCopy -Path $hostConfig.Command -Source $commandSourcePath -Root $hostConfig.Root
}

foreach ($agentName in $agentNames) {
    Set-FileCopy -Path (Join-Path $zcodeRoot "agents\$agentName.md") -Source (Join-Path $repoZCodeAgentsPath "$agentName.md") -Root $zcodeRoot
}

if (Test-Path -LiteralPath $orcaAccountsRoot) {
    foreach ($accountDirectory in Get-ChildItem -LiteralPath $orcaAccountsRoot -Directory -Force) {
        $accountHomePath = Join-Path $accountDirectory.FullName 'home'
        if (-not (Test-Path -LiteralPath $accountHomePath)) { continue }

        $accountAgentsPath = Join-Path $accountHomePath 'agents'
        $accountSkillsPath = Join-Path $accountHomePath 'skills'

        foreach ($agentName in $agentNames) {
            Set-FileCopy -Path (Join-Path $accountAgentsPath "$agentName.toml") -Source (Join-Path $repoCodexAgentsPath "$agentName.toml") -Root $accountHomePath
        }

        Set-DirectoryJunction -Path (Join-Path $accountSkillsPath 'rr-loop') -Target $rrLoopSkillPath -Root $accountHomePath
    }
}

Write-Host 'Agent assets synchronized.'
