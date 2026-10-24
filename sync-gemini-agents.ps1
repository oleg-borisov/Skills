#requires -Version 7.0

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
$sourceRoot = Join-Path $repoRoot 'agents'
$pluginDir = Join-Path $repoRoot '.gemini\plugins\serenity-agents'
$outputAgentsDir = Join-Path $pluginDir 'agents'
$agentNames = @('implementer', 'verifier', 'standards-reviewer', 'spec-reviewer', 'reviser', 'scout')

if (-not (Test-Path -LiteralPath $outputAgentsDir)) {
    New-Item -ItemType Directory -Path $outputAgentsDir -Force | Out-Null
}

# 1. Сборка манифеста plugin.json
$pluginManifest = [ordered]@{
    name = "serenity-agents"
    displayName = "Serenity Workflow Agents"
    version = "1.0.0"
    description = "Комплект специализированных субагентов для цикла разработки rr-loop (implementer, verifier, standards-reviewer, spec-reviewer, reviser, scout)."
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
- `scout`: Опциональный exploration-агент: однократно исследует код по вопросам контроллера и пишет заметки в notes_dir.
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

# 4. Синхронизация и адаптация навыков для Antigravity
$skillsDir = Join-Path $repoRoot 'skills'
$outputSkillsDir = Join-Path $pluginDir 'skills'
$skillNames = @('rr-loop', 'rr-cascade-loop-fast', 'rr-parallel-loop')

foreach ($skillName in $skillNames) {
    $sourceSkillDir = Join-Path $skillsDir $skillName
    if (-not (Test-Path -LiteralPath (Join-Path $sourceSkillDir 'SKILL.md'))) {
        throw "Отсутствует канонический skill: $sourceSkillDir"
    }
    # References — исполняемая часть контракта, включая общий протокол rr-loop.
    foreach ($sourceFile in Get-ChildItem -LiteralPath $sourceSkillDir -File -Recurse) {
        $relativePath = [IO.Path]::GetRelativePath($sourceSkillDir, $sourceFile.FullName)
        $targetPath = Join-Path (Join-Path $outputSkillsDir $skillName) $relativePath
        New-Item -ItemType Directory -Path (Split-Path -Parent $targetPath) -Force | Out-Null
        $content = [IO.File]::ReadAllText($sourceFile.FullName)
        if ($skillName -eq 'rr-loop' -and $relativePath.Replace('\', '/') -eq 'references/protocol.md') {
            $content = $content.Replace(
                'Нет named role/subagents → BLOCKED_UNSUPPORTED_HOST, без подмены роли.',
                'В Antigravity запускай leaf-agents через TypeName: `self`, Role = имя роли (`Implementer`, `Verifier`, `Spec Reviewer`, `Standards Reviewer`, `Reviser`, `Scout`) с контрактом роли в системной инструкции. Нет этого механизма → BLOCKED_UNSUPPORTED_HOST.')
        }
        Set-Content -LiteralPath $targetPath -Value $content.TrimEnd() -Encoding utf8NoBOM
    }
}

# Удаляем прежние известные references после переноса в общий rr-loop каталог.
$legacyReferencesDir = Join-Path $outputSkillsDir 'rr-parallel-loop\references'
foreach ($name in @('recovery.md', 'completion.md')) {
    $legacyPath = Join-Path $legacyReferencesDir $name
    if (Test-Path -LiteralPath $legacyPath) {
        Remove-Item -LiteralPath $legacyPath -Force
    }
}
if ((Test-Path -LiteralPath $legacyReferencesDir) -and
    -not (Get-ChildItem -LiteralPath $legacyReferencesDir -Force | Select-Object -First 1)) {
    Remove-Item -LiteralPath $legacyReferencesDir
}

# Удаляем прежние известные references после переноса в общий rr-loop каталог.
$legacyReferencesDir = Join-Path $outputSkillsDir 'rr-parallel-loop\references'
foreach ($name in @('recovery.md', 'completion.md')) {
    $legacyPath = Join-Path $legacyReferencesDir $name
    if (Test-Path -LiteralPath $legacyPath) {
        Remove-Item -LiteralPath $legacyPath -Force
    }
}
if ((Test-Path -LiteralPath $legacyReferencesDir) -and
    -not (Get-ChildItem -LiteralPath $legacyReferencesDir -Force | Select-Object -First 1)) {
    Remove-Item -LiteralPath $legacyReferencesDir
}

# 5. Правило плагина для Antigravity
$rulesDir = Join-Path $pluginDir 'rules'
if (-not (Test-Path -LiteralPath $rulesDir)) {
    New-Item -ItemType Directory -Path $rulesDir -Force | Out-Null
}
$rulesContent = @"
# Antigravity Subagent Rules for RR Workflows

При выполнении workflows \`rr-loop\`, \`rr-cascade-loop-fast\` и \`rr-parallel-loop\` в Antigravity все leaf-agents (\`implementer\`, \`verifier\`, \`standards-reviewer\`, \`spec-reviewer\`, \`reviser\`, \`scout\`) вызываются через инструмент \`invoke_subagent\` с \`TypeName: "self"\`, Role = имя роли (\`Implementer\`, \`Verifier\`, \`Standards Reviewer\`, \`Spec Reviewer\`, \`Reviser\`, \`Scout\`), а контракт и инструкции роли передаются в системной инструкции / prompt. Это гарантирует наследование необходимых write и execution инструментов от родителя.
"@
Set-Content -LiteralPath (Join-Path $rulesDir 'AGENTS.md') -Value $rulesContent -Encoding utf8NoBOM

Write-Host "Generated serenity-agents plugin with $($agentNames.Count) subagents, $($skillNames.Count) skills, and rules in $pluginDir"

