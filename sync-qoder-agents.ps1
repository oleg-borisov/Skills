#requires -Version 7.0

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$sourceRoot = Join-Path $repoRoot 'agents'
$outputRoot = Join-Path $repoRoot '.qoder\agents'
$agentNames = @('implementer', 'verifier', 'standards-reviewer', 'spec-reviewer', 'reviser', 'scout')
$readOnlyAgents = @('verifier', 'standards-reviewer', 'spec-reviewer')
$readOnlyTools = @('Read', 'Grep', 'Glob', 'Bash')

if (-not (Test-Path -LiteralPath $outputRoot)) {
    New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
}

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

    $sourceFrontmatter = $documentMatch.Groups['frontmatter'].Value
    $descriptionMatch = [regex]::Match($sourceFrontmatter, '(?m)^description:\s*(?<value>.+)$')
    if (-not $descriptionMatch.Success) {
        throw "В $sourcePath отсутствует description"
    }

    $description = $descriptionMatch.Groups['value'].Value.Trim().Trim('"').Trim("'")
    $body = $documentMatch.Groups['body'].Value.Trim()
    $frontmatter = @(
        '---'
        "name: $agentName"
        "description: $description"
    )

    $temperatureMatch = [regex]::Match($sourceFrontmatter, '(?m)^temperature:\s*(?<value>[0-9.]+)\s*$')
    if ($temperatureMatch.Success) {
        $frontmatter += "temperature: $($temperatureMatch.Groups['value'].Value)"
    }

    if ($agentName -in $readOnlyAgents) {
        $frontmatter += 'tools:'
        $frontmatter += ($readOnlyTools | ForEach-Object { "  - $_" })
    }
    else {
        $frontmatter += 'disallowedTools:'
        $frontmatter += '  - Agent'
    }

    $frontmatter += '---'

    $generated = @($frontmatter; ''; $body) -join "`n"
    Set-Content -LiteralPath (Join-Path $outputRoot "$agentName.md") -Value $generated -Encoding utf8NoBOM
}

Write-Host "Generated $($agentNames.Count) Qoder agent profiles."