[CmdletBinding()]
param(
    [string]$Service = "polymarket-bot",
    [string]$RemoteDataDir = "/app/data",
    [string]$OutputDir = "data/runtime_import",
    [string]$PolicyEnvSnapshotName = "policy_env_snapshot.json",
    [string[]]$Files = @(
        "shadow_city_tracking.json",
        "cycles_history.jsonl",
        "cycle_summary.json",
        "decisions.log",
        "performance.json",
        "postmortem.json",
        "skip_log.jsonl",
        "trade_lifecycle.json",
        "audit.json",
        "city_policy_state.json",
        "signals.json"
    )
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$railwaySafe = Join-Path $repoRoot "tools/railway_safe.ps1"
$targetDir = Join-Path $repoRoot $OutputDir
$targetParent = Split-Path -Parent $targetDir
$targetLeaf = Split-Path -Leaf $targetDir
$manifestName = "runtime_import_manifest.json"
$tmpDir = Join-Path $targetParent ("_{0}.tmp.{1}" -f $targetLeaf, ([Guid]::NewGuid().ToString("N")))
$backupDir = Join-Path $targetParent ("_{0}.previous.{1}" -f $targetLeaf, ([Guid]::NewGuid().ToString("N")))

New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

$manifest = [ordered]@{
    pulled_at = [DateTimeOffset]::UtcNow.ToString("o")
    source_service = $Service
    remote_data_dir = $RemoteDataDir
    output_dir = $OutputDir
    files = @()
}

try {
    foreach ($file in $Files) {
        if ($file -match "[/\\]") {
            throw "File names must not contain path separators: $file"
        }

        $remotePath = "$RemoteDataDir/$file"
        $targetPath = Join-Path $tmpDir $file
        $command = "cat $remotePath"
        $content = & powershell -ExecutionPolicy Bypass -File $railwaySafe ssh -s $Service $command
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to pull $remotePath from $Service"
        }

        Set-Content -LiteralPath $targetPath -Value $content -Encoding UTF8
        $item = Get-Item -LiteralPath $targetPath
        $manifest.files += [ordered]@{
            name = $file
            remote_path = $remotePath
            local_path = [System.IO.Path]::GetFullPath((Join-Path $targetDir $file))
            bytes = $item.Length
        }
    }

    $policyVarsRaw = & powershell -ExecutionPolicy Bypass -File $railwaySafe variable list -s $Service --json
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to pull Railway variables for $Service"
    }

    $policyVars = $policyVarsRaw | ConvertFrom-Json
    $policyVarNames = $policyVars.PSObject.Properties.Name
    function Get-EnvVarValue([string]$name) {
        if ($policyVarNames -contains $name) { return [string]$policyVars.$name }
        return $null  # NOT_SET — distingue de var seteada vacía
    }
    $policySnapshot = [ordered]@{
        pulled_at = [DateTimeOffset]::UtcNow.ToString("o")
        source_service = $Service
        variables = [ordered]@{
            ACTIVE_TRADING_CITIES = Get-EnvVarValue "ACTIVE_TRADING_CITIES"
            CANARY_TRADING_CITIES = Get-EnvVarValue "CANARY_TRADING_CITIES"
            BLOCKED_CITIES = Get-EnvVarValue "BLOCKED_CITIES"
        }
    }

    $policySnapshotPath = Join-Path $tmpDir $PolicyEnvSnapshotName
    $policySnapshot | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $policySnapshotPath -Encoding UTF8
    $policyItem = Get-Item -LiteralPath $policySnapshotPath
    $manifest.files += [ordered]@{
        name = $PolicyEnvSnapshotName
        remote_path = "railway:variables"
        local_path = [System.IO.Path]::GetFullPath((Join-Path $targetDir $PolicyEnvSnapshotName))
        bytes = $policyItem.Length
    }

    $manifestPath = Join-Path $tmpDir $manifestName
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    $expected = @($manifest.files | ForEach-Object { $_.name } | Sort-Object)
    $actual = @(Get-ChildItem -LiteralPath $tmpDir -File |
        Where-Object { $_.Name -ne $manifestName } |
        ForEach-Object { $_.Name } |
        Sort-Object)
    $missing = @($expected | Where-Object { $actual -notcontains $_ })
    $extra = @($actual | Where-Object { $expected -notcontains $_ })
    if ($missing.Count -gt 0 -or $extra.Count -gt 0) {
        throw "Manifest drift in temp snapshot. Missing=[$($missing -join ', ')] Extra=[$($extra -join ', ')]"
    }

    if (Test-Path -LiteralPath $targetDir) {
        Move-Item -LiteralPath $targetDir -Destination $backupDir
    }
    Move-Item -LiteralPath $tmpDir -Destination $targetDir
    if (Test-Path -LiteralPath $backupDir) {
        Remove-Item -LiteralPath $backupDir -Recurse -Force
    }
} catch {
    $originalError = $_
    if ((Test-Path -LiteralPath $backupDir) -and -not (Test-Path -LiteralPath $targetDir)) {
        try {
            Move-Item -LiteralPath $backupDir -Destination $targetDir
        } catch {
            Write-Warning "Failed to restore previous snapshot from $backupDir to ${targetDir}: $_"
        }
    }
    if (Test-Path -LiteralPath $tmpDir) {
        try {
            Remove-Item -LiteralPath $tmpDir -Recurse -Force
        } catch {
            Write-Warning "Failed to remove temp snapshot directory ${tmpDir}: $_"
        }
    }
    throw $originalError
}

$manifestPath = Join-Path $targetDir $manifestName

Write-Host "Runtime snapshot pulled to $targetDir"
Write-Host "Manifest written to $manifestPath"
