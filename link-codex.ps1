#requires -Version 7.0

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$userProfilePath = [Environment]::GetFolderPath('UserProfile')
$orcaAccountsRoot = Join-Path $env:APPDATA 'orca\codex-accounts'
$workflowNames = @('spec-delivery')

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

$repoSkillsPath = Join-Path $repoRoot 'skills'

$userAgentsRoot = Join-Path $userProfilePath '.agents'
$claudeRoot = Join-Path $userProfilePath '.claude'
$opencodeRoot = Join-Path $userProfilePath '.config\opencode'

Set-DirectoryJunction -Path (Join-Path $repoRoot '.agents\skills') -Target $repoSkillsPath -Root $repoRoot

$skills = @('spec-delivery', 'setup-agents')

foreach ($skill in $skills) {
    foreach ($hostRoot in @($userAgentsRoot, $claudeRoot, $opencodeRoot)) {
        Set-DirectoryJunction -Path (Join-Path $hostRoot "skills\$skill") -Target (Join-Path $repoSkillsPath $skill) -Root $hostRoot
    }
}

foreach ($hostConfig in @(
    @{ Root = $claudeRoot; Commands = Join-Path $claudeRoot 'command' },
    @{ Root = $opencodeRoot; Commands = Join-Path $opencodeRoot 'command' }
)) {
    foreach ($workflowName in $workflowNames) {
        Set-FileCopy -Path (Join-Path $hostConfig.Commands "$workflowName.md") -Source (Join-Path $repoRoot "command\$workflowName.md") -Root $hostConfig.Root
    }
}

if (Test-Path -LiteralPath $orcaAccountsRoot) {
    foreach ($accountDirectory in Get-ChildItem -LiteralPath $orcaAccountsRoot -Directory -Force) {
        $accountHomePath = Join-Path $accountDirectory.FullName 'home'
        if (-not (Test-Path -LiteralPath $accountHomePath)) { continue }

        $accountSkillsPath = Join-Path $accountHomePath 'skills'

        foreach ($skill in $skills) {
            Set-DirectoryJunction -Path (Join-Path $accountSkillsPath $skill) -Target (Join-Path $repoSkillsPath $skill) -Root $accountHomePath
        }
    }
}

Write-Host 'Skills and command adapters synchronized.'
