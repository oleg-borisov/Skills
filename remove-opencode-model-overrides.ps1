#requires -Version 7.0

[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$ConfigPath = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.config\opencode\opencode.json')
)

$ErrorActionPreference = 'Stop'

$agentNames = @('implementer', 'verifier', 'standards-reviewer', 'spec-reviewer', 'reviser', 'scout')

function Read-JsonConfig {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        # Unary comma: JsonObject is IEnumerable and would otherwise unwrap to Object[].
        return ,([System.Text.Json.Nodes.JsonObject]::new())
    }

    $content = Get-Content -LiteralPath $Path -Raw
    $documentOptions = [System.Text.Json.JsonDocumentOptions]::new()
    $documentOptions.CommentHandling = [System.Text.Json.JsonCommentHandling]::Skip
    $documentOptions.AllowTrailingCommas = $true

    $node = [System.Text.Json.Nodes.JsonNode]::Parse($content, $null, $documentOptions)
    if ($node -isnot [System.Text.Json.Nodes.JsonObject]) {
        throw "OpenCode config должен быть JSON object: $Path"
    }

    return ,([System.Text.Json.Nodes.JsonObject]$node)
}

$config = Read-JsonConfig -Path $ConfigPath

$agentsNode = $null
if ($config.TryGetPropertyValue('agents', [ref]$agentsNode) -and $agentsNode -is [System.Text.Json.Nodes.JsonObject]) {
    $agents = [System.Text.Json.Nodes.JsonObject]$agentsNode
    foreach ($agentName in $agentNames) {
        $agentNode = $null
        if (-not $agents.TryGetPropertyValue($agentName, [ref]$agentNode)) { continue }
        if ($agentNode -isnot [System.Text.Json.Nodes.JsonObject]) { continue }

        $agent = [System.Text.Json.Nodes.JsonObject]$agentNode
        if ($agent.Remove('model')) {
            Write-Host "Removed model: agents.$agentName"
        }

        if ($agent.Count -eq 0) {
            $agents.Remove($agentName) | Out-Null
            Write-Host "Removed empty section: agents.$agentName"
        }
    }

    if ($agents.Count -eq 0) {
        $config.Remove('agents') | Out-Null
        Write-Host "Removed empty section: agents"
    }
}
else {
    Write-Host "No 'agents' section in $ConfigPath, nothing to clean."
}

$parent = Split-Path -Parent $ConfigPath
if ($PSCmdlet.ShouldProcess($ConfigPath, 'Удалить model-overrides rr-loop агентов')) {
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    if (Test-Path -LiteralPath $ConfigPath) {
        $backupPath = "$ConfigPath.bak.$(Get-Date -Format 'yyyyMMddHHmmss')"
        Copy-Item -LiteralPath $ConfigPath -Destination $backupPath -ErrorAction Stop
        Write-Host "Backup: $backupPath"
    }

    $serializerOptions = [System.Text.Json.JsonSerializerOptions]::new()
    $serializerOptions.WriteIndented = $true
    $json = $config.ToJsonString($serializerOptions)
    [System.IO.File]::WriteAllText($ConfigPath, $json + [Environment]::NewLine)
    Write-Host "Updated: $ConfigPath"
}
