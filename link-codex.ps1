#requires -Version 7.0

<#
.SYNOPSIS
    Связывает агентные активы репозитория с Codex CLI через junction-ы (Windows).
    Повторный запуск безопасен.

    Куда Codex смотрит (по офиц. докам):
      - агенты:   ~/.codex/agents          (user)  и  .codex/agents        (project)
      - скиллы:   ~/.agents/skills          (user)  и  .agents/skills       (project)
    Каталог ~/.codex/skills Codex НЕ сканирует.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repo = $PSScriptRoot

$links = @(
    @{
        Link   = Join-Path $HOME '.codex\agents'
        Target = Join-Path $repo '.codex\agents'
    },
    @{
        Link   = Join-Path $HOME '.agents\skills\deferred-review'
        Target = Join-Path $repo 'skills\deferred-review'
    },
    @{
        Link   = Join-Path $repo '.agents\skills'
        Target = Join-Path $repo 'skills'
    }
)

function Test-Junction {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $item = Get-Item -LiteralPath $Path -Force
    return $item.LinkType -eq 'Junction' -or $item.LinkType -eq 'SymbolicLink'
}

function Remove-Junction {
    param([string]$Path)
    if (Test-Junction -Path $Path) {
        Remove-Item -LiteralPath $Path -Force -Recurse
        Write-Host "  removed existing junction: $Path"
    } elseif (Test-Path -LiteralPath $Path) {
        throw "Каталог $Path существует и не является junction. Удали его вручную и повтори."
    }
}

function Remove-StaleJunction {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return }
    if (Test-Junction -Path $Path) {
        Remove-Item -LiteralPath $Path -Force -Recurse
        Write-Host "  removed stale junction: $Path"
    }
}

Remove-StaleJunction -Path (Join-Path $HOME '.codex\skills\deferred-review')

foreach ($link in $links) {
    Write-Host "Link: $($link.Link)"

    $parent = Split-Path -Parent $link.Link
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        Write-Host "  created parent: $parent"
    }

    if (-not (Test-Path -LiteralPath $link.Target)) {
        throw "Цель не существует: $($link.Target)"
    }

    Remove-Junction -Path $link.Link
    New-Item -ItemType Junction -Path $link.Link -Target $link.Target | Out-Null
    Write-Host "  created junction -> $($link.Target)"
}

Write-Host ''
Write-Host 'Готово.'
