#requires -Version 7.0

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$sourceRoot = Join-Path $repoRoot 'agents'
$pluginDir = Join-Path $repoRoot '.gemini\plugins\serenity-agents'
$outputAgentsDir = Join-Path $pluginDir 'agents'
$agentNames = @('implementer', 'verifier', 'standards-reviewer', 'spec-reviewer', 'reviser')

if (-not (Test-Path -LiteralPath $outputAgentsDir)) {
    New-Item -ItemType Directory -Path $outputAgentsDir -Force | Out-Null
}

# 1. Сборка манифеста plugin.json
$pluginManifest = [ordered]@{
    name = "serenity-agents"
    displayName = "Serenity Workflow Agents"
    version = "1.0.0"
    description = "Комплект специализированных субагентов для цикла разработки rr-loop (implementer, verifier, standards-reviewer, spec-reviewer, reviser)."
    suggestedPrompts = @(
        "Run implementer to build work from spec",
        "Run verifier gate for test suite",
        "Run spec and standards code review"
    )
} | ConvertTo-Json -Depth 5

$manifestPath = Join-Path $pluginDir 'plugin.json'
Set-Content -LiteralPath $manifestPath -Value $pluginManifest -Encoding utf8NoBOM

# 2. README для плагина
$readmeContent = @"
# Serenity Workflow Agents Plugin

Плагин субагентов для Antigravity, сгенерированный из канонических спецификаций в `agents/`.

## Содержимое
- `implementer`: Реализует spec в одной rr-loop фазе, выполняет targeted checks и коммитит.
- `verifier`: Read-only full-suite gate для нового HEAD, возвращающий failure inventory.
- `standards-reviewer`: Read-only Standards-axis review заданного diff по repo standards.
- `spec-reviewer`: Read-only Spec-axis review заданного diff против originating spec.
- `reviser`: Исправляет заданные rr-loop findings, выполняет targeted checks и коммитит правки.
"@

Set-Content -LiteralPath (Join-Path $pluginDir 'README.md') -Value $readmeContent -Encoding utf8NoBOM

# 3. Синхронизация файлов субагентов
foreach ($agentName in $agentNames) {
    $sourcePath = Join-Path $sourceRoot "$agentName.md"
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Отсутствует канонический агент: $sourcePath"
    }

    $raw = Get-Content -LiteralPath $sourcePath -Raw
    $documentMatch = [regex]::Match(
        $raw,
        '\A---\r?\n(?<frontmatter>.*?)\r?\n---\r?\n(?<body>.*)\z',
        [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if (-not $documentMatch.Success) {
        throw "Некорректный frontmatter: $sourcePath"
    }

    $frontmatter = $documentMatch.Groups['frontmatter'].Value
    $body = $documentMatch.Groups['body'].Value.Trim()

    $descriptionMatch = [regex]::Match($frontmatter, '(?m)^description:\s*(?<value>.+)$')
    if (-not $descriptionMatch.Success) {
        throw "В $sourcePath отсутствует description"
    }
    $description = $descriptionMatch.Groups['value'].Value.Trim()

    # Формируем чистый frontmatter для Antigravity plugin subagent
    $generatedFrontmatter = @(
        '---'
        "name: $agentName"
        "description: $description"
        $frontmatter.Trim() -split "`r?`n" | Where-Object { $_ -notmatch '^(name|description):' }
        '---'
    ) -join "`n"

    $generated = @($generatedFrontmatter; ''; $body) -join "`n"
    $outputPath = Join-Path $outputAgentsDir "$agentName.md"
    Set-Content -LiteralPath $outputPath -Value $generated -Encoding utf8NoBOM
}

Write-Host "Generated serenity-agents plugin with $($agentNames.Count) subagents in $pluginDir"
