#requires -Version 7.0

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$sourceRoot = Join-Path $repoRoot 'agents'
$outputRoot = Join-Path $repoRoot '.zcode\agents'
$agentNames = @('implementer', 'verifier', 'standards-reviewer', 'spec-reviewer', 'reviser')
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

    $descriptionMatch = [regex]::Match($documentMatch.Groups['frontmatter'].Value, '(?m)^description:\s*(?<value>.+)$')
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
    if ($agentName -in $readOnlyAgents) {
        $frontmatter += 'tools:'
        $frontmatter += ($readOnlyTools | ForEach-Object { "  - $_" })
    }
    $frontmatter += '---'

    $generated = @($frontmatter; ''; $body) -join "`n"
    Set-Content -LiteralPath (Join-Path $outputRoot "$agentName.md") -Value $generated -Encoding utf8NoBOM
}

Write-Host "Generated $($agentNames.Count) ZCode agent profiles."
