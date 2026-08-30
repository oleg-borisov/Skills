#requires -Version 7.0

[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$ConfigPath = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.config\opencode\opencode.json')
)

$ErrorActionPreference = 'Stop'

$models = [ordered]@{
    'implementer'         = 'omniroute/coder'
    'verifier'            = 'omniroute/coder'
    'reviser'             = 'omniroute/coder'
    'standards-reviewer'  = 'omniroute/architector'
    'spec-reviewer'       = 'omniroute/architector'
}

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

function Get-OrCreateObjectProperty {
    param(
        [Parameter(Mandatory)][System.Text.Json.Nodes.JsonObject]$Parent,
        [Parameter(Mandatory)][string]$Name
    )

    $existing = $null
    [void]$Parent.TryGetPropertyValue($Name, [ref]$existing)
    if ($null -eq $existing) {
        $created = [System.Text.Json.Nodes.JsonObject]::new()
        $Parent.Add($Name, $created)
        return ,$created
    }

    if ($existing -isnot [System.Text.Json.Nodes.JsonObject]) {
        throw "Поле '$Name' должно быть JSON object"
    }

    return ,([System.Text.Json.Nodes.JsonObject]$existing)
}

$config = Read-JsonConfig -Path $ConfigPath
$agents = Get-OrCreateObjectProperty -Parent $config -Name 'agents'

foreach ($agentName in $models.Keys) {
    $agent = Get-OrCreateObjectProperty -Parent $agents -Name $agentName
    $modelValue = [System.Text.Json.Nodes.JsonValue]::Create([string]$models[$agentName])

    $currentModel = $null
    if ($agent.TryGetPropertyValue('model', [ref]$currentModel) -and $null -ne $currentModel) {
        $currentModel.ReplaceWith($modelValue)
    }
    else {
        $agent['model'] = $modelValue
    }
}

$parent = Split-Path -Parent $ConfigPath
if ($PSCmdlet.ShouldProcess($ConfigPath, 'Установить model-overrides rr-loop агентов')) {
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

foreach ($agentName in $models.Keys) {
    Write-Host "$agentName -> $($models[$agentName])"
}
