#requires -Version 7.0

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$userProfilePath = [Environment]::GetFolderPath('UserProfile')
$qoderRoot = Join-Path $userProfilePath '.qoder'

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

function Test-DirectoryContentEqual {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Source
    )

    $sourceFiles = @(Get-ChildItem -LiteralPath $Source -File -Recurse -Force)
    $targetFiles = @(Get-ChildItem -LiteralPath $Path -File -Recurse -Force)
    if ($sourceFiles.Count -ne $targetFiles.Count) { return $false }

    foreach ($sourceFile in $sourceFiles) {
        $relativePath = [IO.Path]::GetRelativePath($Source, $sourceFile.FullName)
        $targetFile = Join-Path $Path $relativePath
        if (-not (Test-Path -LiteralPath $targetFile -PathType Leaf)) { return $false }

        $sourceText = [IO.File]::ReadAllText($sourceFile.FullName).Replace("`r`n", "`n")
        $targetText = [IO.File]::ReadAllText($targetFile).Replace("`r`n", "`n")
        if ($sourceText -ne $targetText) { return $false }
    }

    return $true
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
        if ($item.LinkType -in @('Junction', 'SymbolicLink')) {
            Remove-Item -LiteralPath $Path -Force -Recurse
        }
        elseif ($item.PSIsContainer) {
            if (-not (Test-DirectoryContentEqual -Path $Path -Source $Target)) {
                throw "Каталог отличается от репозитория и не будет удалён: $Path"
            }
            Remove-Item -LiteralPath $Path -Force -Recurse
            Write-Host "Removed stale copy: $Path"
        }
        else {
            throw "На месте каталога существует файл: $Path"
        }
    }

    New-Item -ItemType Junction -Path $Path -Target $Target | Out-Null
    Write-Host "Junction: $Path -> $Target"
}

$repoSkillsPath = Join-Path $repoRoot 'skills'
$skillNames = @(
    Get-ChildItem -LiteralPath $repoSkillsPath -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') } |
        ForEach-Object { $_.Name }
)
if (-not $skillNames.Count) {
    throw "В $repoSkillsPath нет skills с SKILL.md"
}

foreach ($skillName in $skillNames) {
    Set-DirectoryJunction -Path (Join-Path $qoderRoot "skills\$skillName") -Target (Join-Path $repoSkillsPath $skillName) -Root $qoderRoot
}

Write-Host "Qoder skills synchronized: $($skillNames.Count)."
