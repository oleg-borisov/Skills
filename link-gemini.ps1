#requires -Version 7.0

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$userProfilePath = [Environment]::GetFolderPath('UserProfile')
$pluginDir = Join-Path $userProfilePath '.gemini\config\plugins\serenity-agents'
$manifestPath = Join-Path $pluginDir 'plugin.json'

if ((Get-Item -LiteralPath $pluginDir -Force -ErrorAction SilentlyContinue).LinkType) {
    throw "Antigravity требует обычный каталог плагина: $pluginDir"
}
New-Item -ItemType Directory -Path $pluginDir -Force | Out-Null
if (-not (Test-Path -LiteralPath $manifestPath)) {
    @{ name = 'serenity-agents'; displayName = 'Serenity Workflow'; version = '1.0.0' } |
        ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding utf8NoBOM
}

foreach ($skill in @('spec-delivery', 'setup-agents')) {
    $source = Join-Path $PSScriptRoot "skills\$skill"
    $skillRoot = Join-Path $pluginDir 'skills'
    $target = Join-Path $skillRoot $skill
    foreach ($path in @($skillRoot, $target)) {
        if ((Get-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue).LinkType) {
            throw "Antigravity требует обычный каталог навыков: $path"
        }
    }
    robocopy $source $target /E /XJ /XD __pycache__ /NP /NFL /NDL /NJH /NJS | Out-Null
    if ($LASTEXITCODE -ge 8) {
        throw "Не удалось скопировать навык в ${target}: robocopy $LASTEXITCODE"
    }
    Write-Host "Copied skill: $target"
}
